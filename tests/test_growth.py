import datetime as dt
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from reel import build, carousel, growth, publish, script

ROOT = Path(__file__).resolve().parents[1]
STORY = script.clean(json.loads((ROOT / 'examples' / 'sample.json').read_text(encoding='utf-8')))
UTC = dt.timezone.utc


def ist(day, hour, minute=0):
    return dt.datetime(2026, 10, day, hour, minute, tzinfo=growth.IST).astimezone(UTC)


class History(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {'REEL_HISTORY': str(Path(self.tmp.name) / 'history.json')})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()


class BestTimeTest(History):
    def test_slots(self):
        self.assertEqual(growth.slot_of(ist(16, 18, 40)), 19)
        self.assertEqual(growth.slot_of(ist(16, 7, 10)), 8)

    def test_best_slot_needs_two_posts(self):
        self.assertEqual(growth.best_slot([]), 19)
        history = [{'slot': 8, 'score': 900}, {'slot': 21, 'score': 500}, {'slot': 21, 'score': 700}, {'slot': 13, 'score': 100},
                   {'slot': 13, 'score': 120}]
        self.assertEqual(growth.best_slot(history), 21)  # 8 has only one post

    def test_next_time(self):
        self.assertEqual(growth.next_time(19, ist(16, 10)), ist(16, 19))
        self.assertEqual(growth.next_time(8, ist(16, 10)), ist(17, 8))

    def test_post_now(self):
        with mock.patch.dict(os.environ, {'POST_AT_PEAK': ''}):
            self.assertTrue(growth.post_now(ist(16, 10), 19))
        with mock.patch.dict(os.environ, {'POST_AT_PEAK': 'true'}):
            self.assertFalse(growth.post_now(ist(16, 10), 19))
            self.assertTrue(growth.post_now(ist(16, 18, 30), 19))


class LearningTest(History):
    def test_scores_reach_the_writer(self):
        for i, title in enumerate(['A', 'B', 'C', 'D', 'E']):
            script.remember({'topic': f't{i}', 'title': title})
        growth.record_scores([{'title': f'{t} (भाग 1/2)', 'score': s, 'posted_at': ist(16, 19)}
                              for t, s in zip('ABCDE', (50, 900, 10, 300, 70))])
        history = script.history()
        self.assertEqual(history[1]['score'], 900)
        self.assertEqual(history[1]['slot'], 19)
        text = growth.lessons_learned()
        self.assertLess(text.index('"B"'), text.index('"D"'))
        self.assertIn('"C"', text.split('did worst')[1])

    def test_no_scores_no_advice(self):
        self.assertEqual(growth.lessons_learned([]), '')

    def test_saved_ideas_are_picked_first(self):
        topics = Path(self.tmp.name) / 'topics.txt'
        topics.write_text('X\n', encoding='utf-8')
        growth.remember_ideas({'ideas': [{'topic': 'Old idea'}, {'topic': 'New idea'}]})
        self.assertEqual(script.pick_topic(topics), 'New idea')
        script.remember({'topic': 'New idea', 'title': 'n'})
        self.assertEqual(script.pick_topic(topics), 'Old idea')

    def test_ideas_message(self):
        text = growth.ideas_message({'comments': 12, 'trends': 30, 'notes': [],
                                     'ideas': [{'title': 'माँ की चुप्पी', 'topic': 'Listen to parents', 'why': 'comments'}],
                                     'replies': [{'comment': 'बहुत अच्छा', 'reply': 'धन्यवाद!'}]})
        self.assertIn('1. माँ की चुप्पी', text)
        self.assertIn('↳ धन्यवाद!', text)


class QueueTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)
        (self.folder / 'script.json').write_text(json.dumps(STORY, ensure_ascii=False), encoding='utf-8')
        self.video = self.folder / 'reel.mp4'
        self.video.write_bytes(b'mp4')

    def tearDown(self):
        self.tmp.cleanup()

    def test_scheduled_post_then_queue(self):
        at = ist(16, 19)

        def instagram(video, story, ctx):
            return {'status': 'queued', 'container': 'c1', 'publish_at': ctx['publish_at'].isoformat()}

        def youtube(video, story, ctx):
            return {'id': 'y', 'url': 'u', 'status': 'scheduled', 'publish_at': ctx['publish_at'].isoformat()}
        with mock.patch.dict(publish.UPLOADERS, {'instagram': instagram, 'youtube': youtube}):
            receipt = publish.publish(self.folder, self.video, ['instagram', 'youtube'], publish_at=at)
            again = publish.publish(self.folder, self.video, ['instagram', 'youtube'], publish_at=at)
        self.assertTrue(publish.waiting(receipt))
        self.assertEqual(again['platforms']['instagram']['container'], 'c1')  # not uploaded twice
        self.assertIn('goes live 16 Oct 07:00 PM IST', publish.summary(STORY, receipt))
        with mock.patch.object(publish, 'instagram_finish', return_value={'id': 'm', 'url': 'https://ig/m'}) as finish:
            _, done = publish.publish_queued(self.folder, now=ist(16, 12))
            self.assertEqual(done, [])  # not yet
            receipt, done = publish.publish_queued(self.folder, now=ist(16, 19, 2))
        finish.assert_called_once_with('c1')
        self.assertEqual(done, ['instagram'])
        self.assertFalse(publish.waiting(receipt))

    def test_trial_and_carousel_skip_without_their_files(self):
        self.assertEqual(publish.instagram_trial_upload(self.video, STORY, {'video_b': None})['status'], 'skipped')
        self.assertEqual(publish.carousel_upload(self.video, STORY, {'folder': self.folder})['status'], 'skipped')

    def test_switches(self):
        env = {'INSTAGRAM_ACCESS_TOKEN': 't', 'HOOK_TEST': 'true', 'CAROUSEL': 'true', 'FACEBOOK_PAGE_ID': '1',
               'FACEBOOK_PAGE_TOKEN': 'x', 'CLOUDFLARE_ACCOUNT_ID': 'a', 'CLOUDFLARE_API_TOKEN': 'b'}
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertEqual(publish.configured(), ['instagram', 'facebook', 'carousel', 'instagram_trial'])
        with mock.patch.dict(os.environ, {'INSTAGRAM_ACCESS_TOKEN': 't', 'CAROUSEL': 'true'}, clear=True):
            self.assertEqual(publish.configured(), ['instagram'])  # no image hosting: no carousel


class CarouselTest(unittest.TestCase):
    def test_slide_times(self):
        story = STORY
        starts, end = build.silent_times(story)
        props = {'segments': build.segments(story, starts, end)}
        times = carousel.slide_times(props)
        self.assertEqual(len(times), 5)
        self.assertEqual(times, sorted(times))

    def test_chapters(self):
        marks = carousel.chapters(3.5, [('पहली', 40.0), ('दूसरी', 35.0)])
        self.assertEqual([round(t, 1) for t, _ in marks], [0.0, 3.5, 43.5])
        text = carousel.description(marks, ['सीख 1', 'सीख 2'])
        self.assertIn('0:00 शुरुआत', text)
        self.assertIn('0:43 दूसरी', text)


class HookTestTest(unittest.TestCase):
    def test_second_hook_props(self):
        story = dict(STORY, title_b='रोज़ 5 घंटे गायब!')
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {'HOOK_TEST': 'true'}):
            build.build(story, Path(tmp) / 'o', Path(tmp) / 'p', narrate=False, music=False, prefix='reels/1/')
            variant = json.loads((Path(tmp) / 'p' / 'reels' / '1' / 'props-b.json').read_text(encoding='utf-8'))
        self.assertEqual(variant['segments'][0]['title'], 'रोज़ 5 घंटे गायब!')

    def test_title_b_must_be_hindi_and_different(self):
        raw = json.loads((ROOT / 'examples' / 'sample.json').read_text(encoding='utf-8'))
        self.assertEqual(script.clean(dict(raw, title_b='English'))['title_b'], '')
        self.assertEqual(script.clean(dict(raw, title_b=raw['title']))['title_b'], '')
        self.assertEqual(script.clean(dict(raw, title_b='रोज़ 5 घंटे गायब!'))['title_b'], 'रोज़ 5 घंटे गायब!')


if __name__ == '__main__':
    unittest.main()
