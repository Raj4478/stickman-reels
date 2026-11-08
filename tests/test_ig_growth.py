"""The Instagram growth pack: send-worthy endings, keyword captions, custom covers, the AI label, the lint, the
insights loop, the evening window, two-part Kahani and trial Reels."""
import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from reel import __main__ as cli
from reel import build, comic, growth, publish, quality, reach, script, storybook

ROOT = Path(__file__).resolve().parents[1]
RAW = json.loads((ROOT / 'examples' / 'storybook.json').read_text(encoding='utf-8'))
KAHANI = storybook.clean(RAW)
COMIC = comic.clean(json.loads((ROOT / 'examples' / 'comic.json').read_text(encoding='utf-8')))
STORY = script.clean(json.loads((ROOT / 'examples' / 'sample.json').read_text(encoding='utf-8')))
UTC = dt.timezone.utc


def ist(day, hour, minute=0):
    return dt.datetime(2026, 11, day, hour, minute, tzinfo=growth.IST).astimezone(UTC)


class History(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {'REEL_HISTORY': str(Path(self.tmp.name) / 'history.json')})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()


class SendWorthyTest(unittest.TestCase):
    def test_scripts_name_who_to_send_it_to(self):
        self.assertEqual((KAHANI['send_target'], KAHANI['end_line']), ('papa', 'Ye video apne Papa ko bhejo'))
        self.assertEqual(COMIC['send_target'], 'dost')
        for schema in (storybook.SCHEMA, comic.SCHEMA):
            self.assertIn('send_target', schema['required'])
            self.assertIn('end_line', schema['required'])
            self.assertEqual(schema['properties']['send_target']['enum'], list(reach.SEND_TARGETS))

    def test_bait_and_long_lines_fall_back_to_a_send_line(self):
        for bad in ('Comment karo YES agar Maa se pyaar hai', 'Like aur follow karo', 'Maa ko bhejo ' * 6, ''):
            target, line = reach.clean_send({'send_target': 'maa', 'end_line': bad})
            self.assertEqual((target, line), ('maa', 'Ye video apni Maa ko bhejo'))
        self.assertEqual(reach.clean_send({'send_target': 'nobody'}, fallback='bhai')[1], 'Ye video apne Bhai ko bhejo')
        # a missing answer falls back to the series' usual person
        self.assertEqual(storybook.clean(dict(RAW, send_target='', end_line='', series='maa_baap'))['send_target'], 'maa')

    def test_prompts_ask_for_it(self):
        self.assertIn('send_target', reach.rules())
        self.assertIn('never', reach.rules().lower())
        self.assertIn('{send}', storybook.WRITER)
        self.assertIn('{send}', comic.WRITER)

    def test_end_line_reaches_the_props(self):
        starts, end = build.silent_times(KAHANI)
        segs = build.segments(KAHANI, starts, end)
        self.assertEqual(segs[-1]['kind'], 'ask')
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(build.voice, 'word_times', return_value=None), \
                mock.patch('reel.images.paint', return_value=([None] * len(segs), [None] * len(segs), {})), \
                mock.patch('reel.depth.add_depth', return_value={}):
            props, _ = build.build(dict(KAHANI, part='1/2'), Path(tmp) / 'out', Path(tmp) / 'public', narrate=False, music=False)
        self.assertEqual(props['end_line'], KAHANI['end_line'])
        self.assertEqual(props['part'], '1/2')


class CaptionTest(unittest.TestCase):
    def test_first_line_is_hook_plus_keywords_then_the_send_line(self):
        caption = publish.texts(KAHANI)['caption']
        first, second = caption.split('\n')[:2]
        self.assertEqual(first, 'आखिरी कुर्सी वाले पापा | Papa ki kahani | emotional Hindi story | पापा की कहानी')
        self.assertEqual(second, '👉 Ye video apne Papa ko bhejo')
        self.assertLessEqual(len(re.findall(r'#\w+', caption)), 5)

    def test_part_and_story_style(self):
        first = publish.texts(dict(KAHANI, part='2/2'))['caption'].split('\n')[0]
        self.assertTrue(first.startswith('आखिरी कुर्सी वाले पापा (Part 2/2) | '))
        self.assertEqual(publish.texts(STORY)['caption'].split('\n')[0], f"{STORY['title']} | Hindi life lesson")
        self.assertIn('Computer Course | Computer course comedy | Hindi comedy', publish.texts(COMIC)['caption'])

    def test_telegram_caption_and_copy_button_match(self):
        text = cli.caption(KAHANI, {})
        self.assertTrue(text.startswith(publish.opening(KAHANI)))
        self.assertLessEqual(len(re.findall(r'#\w+', text)), 5)
        self.assertTrue(publish.copy_texts(KAHANI)['caption'].startswith(publish.opening(KAHANI)))


class InstagramFieldsTest(unittest.TestCase):
    def test_cover_feed_and_ai_label(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            fields = publish.reel_fields(KAHANI, {'cover_url': 'https://w/m/c.jpg'})
            self.assertEqual((fields['cover_url'], fields['share_to_feed'], fields['is_ai_generated']), ('https://w/m/c.jpg', 'true', 'true'))
            self.assertNotIn('thumb_offset', fields)
            plain = publish.reel_fields(COMIC, {})
            self.assertNotIn('is_ai_generated', plain)  # drawn in code, not AI pictures
            self.assertEqual(plain['thumb_offset'], str(publish.COVER_MS))
            trial = publish.reel_fields(KAHANI, {'cover_url': 'https://w/m/c.jpg'}, trial=True)
            self.assertEqual(json.loads(trial['trial_params']), {'graduation_strategy': 'SS_PERFORMANCE'})
            self.assertNotIn('share_to_feed', trial)
            self.assertNotIn('cover_url', trial)  # hook B has its own hook frame
        with mock.patch.dict(os.environ, {'AI_LABEL': 'false'}):
            self.assertNotIn('is_ai_generated', publish.reel_fields(KAHANI, {}))
        with mock.patch.dict(os.environ, {'AI_LABEL': 'all'}):
            self.assertIn('is_ai_generated', publish.reel_fields(COMIC, {}))

    def test_cover_is_hosted_like_carousel_images(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(publish.cover_url({'folder': tmp}), '')  # no cover rendered
            (Path(tmp) / 'cover.jpg').write_bytes(b'jpg')
            with mock.patch('reel.media.configured', return_value=True), \
                    mock.patch('reel.media.host', return_value=['https://w/m/x.jpg']) as host:
                self.assertEqual(publish.cover_url({'folder': tmp}), 'https://w/m/x.jpg')
            host.assert_called_once_with([Path(tmp) / 'cover.jpg'])
            with mock.patch('reel.media.configured', return_value=False):
                self.assertEqual(publish.cover_url({'folder': tmp}), '')

    def test_refused_optional_fields_are_dropped_not_the_post(self):
        sent = []

        def call(path, fields=None, method='POST', attempts=3):
            if path.endswith('/media'):
                sent.append(dict(fields))
                if 'is_ai_generated' in fields or 'cover_url' in fields:
                    raise publish.PublishError('Instagram refused (100/2207001): Invalid parameter')
                return {'id': 'c1'}
            raise AssertionError(path)
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {'INSTAGRAM_ACCESS_TOKEN': 't', 'INSTAGRAM_USER_ID': 'u'}), \
                mock.patch.object(publish, 'instagram_call', side_effect=call), mock.patch.object(publish, 'request'), \
                mock.patch.object(publish, 'instagram_wait'), \
                mock.patch.object(publish, 'instagram_finish', return_value={'id': 'm', 'url': 'https://ig/m'}):
            video = Path(tmp) / 'v.mp4'
            video.write_bytes(b'mp4')
            result = publish.instagram_reel(video, KAHANI, {'cover_url': 'https://w/c.jpg'})
        self.assertEqual(result['url'], 'https://ig/m')
        self.assertEqual(len(sent), 3)
        self.assertEqual(sent[-1]['thumb_offset'], str(publish.COVER_MS))


class TrialReelTest(unittest.TestCase):
    def test_trial_reels_wait_for_1000_followers(self):
        with tempfile.TemporaryDirectory() as tmp:
            video_b = Path(tmp) / 'b.mp4'
            video_b.write_bytes(b'mp4')
            with mock.patch.object(publish, 'followers', return_value=420):
                result = publish.instagram_trial_upload(video_b, KAHANI, {'video_b': video_b})
            self.assertEqual(result['status'], 'skipped')
            self.assertIn('1,000 followers', result['note'])
            with mock.patch.object(publish, 'followers', return_value=1500), \
                    mock.patch.object(publish, 'instagram_reel', return_value={'id': 't', 'url': 'u'}) as reel:
                result = publish.instagram_trial_upload(video_b, KAHANI, {'video_b': video_b})
            self.assertEqual(result['url'], 'u')
            self.assertTrue(reel.call_args.kwargs['trial'])

    def test_follower_count_from_the_api(self):
        with mock.patch.object(publish, 'instagram_user', return_value='u'), \
                mock.patch.object(publish, 'instagram_call', return_value={'followers_count': 1234}) as call:
            self.assertEqual(publish.followers(), 1234)
        self.assertEqual(call.call_args.args[1], {'fields': 'followers_count'})


class SeriesTest(History):
    def test_part_one_ends_on_a_cliffhanger_and_part_two_keeps_the_people(self):
        self.assertIn('cliffhanger', storybook.series_note('1/2'))
        self.assertIn('same characters', storybook.series_note('2/2', {'title': 'x'}))
        self.assertEqual(storybook.series_note(''), '')
        first = dict(KAHANI, part='1/2')
        changed = dict(KAHANI, characters=[dict(c, look='someone else') for c in KAHANI['characters']], setting='a city')
        kept = storybook.same_people(changed, storybook.summary(first))
        self.assertEqual([c['look'] for c in kept['characters']], [c['look'] for c in KAHANI['characters']])
        self.assertEqual(kept['setting'], KAHANI['setting'])

    def test_series_flag_makes_two_kahani_parts(self):
        calls = []

        def write(topic=None, theme='', source='', part='', previous=None):
            calls.append((part, bool(previous)))
            return dict(KAHANI, part=part)
        args = argparse.Namespace(sample=None, style='storybook', series=True, topic='', theme='', source='', count=1)
        with mock.patch.object(storybook, 'write', side_effect=write):
            parts = [s['part'] for s in cli.stories(args)]
        self.assertEqual(parts, ['1/2', '2/2'])
        self.assertEqual(calls, [('1/2', False), ('2/2', True)])

    def test_telegram_reminds_to_link_the_parts(self):
        receipt = {'platforms': {'instagram': {'status': 'published', 'url': 'https://ig/2'}}}
        text = publish.summary(dict(KAHANI, part='2/2'), receipt)
        self.assertIn('Link a Reel', text)
        self.assertIn('Part 1', text)
        self.assertIn('Link a Reel', publish.summary(dict(KAHANI, part='1/2'), receipt))
        self.assertNotIn('Link a Reel', publish.summary(KAHANI, receipt))
        self.assertNotIn('Link a Reel', publish.summary(dict(KAHANI, part='2/2'), {'platforms': {'instagram': {'status': 'failed'}}}))


class LintTest(History):
    @staticmethod
    def frame(top_bar=False, value=120, w=108, h=192):
        rows = [[(value + 7 * x + 3 * y) % 200 + 30 for x in range(w)] for y in range(h)]
        if top_bar:
            rows[:20] = [[0] * w for _ in range(20)]
            rows[-20:] = [[0] * w for _ in range(20)]
        return rows

    def test_black_bars_are_found_but_dark_pictures_are_not(self):
        self.assertEqual(quality.bars([self.frame(True, v) for v in (10, 60, 90)]), ['top', 'bottom'])
        self.assertEqual(quality.bars([self.frame(False, v) for v in (10, 60, 90)]), [])
        night = [[[max(0, 18 - y) for _ in range(108)] for y in range(192)]] * 3  # dark everywhere, fading
        self.assertEqual(quality.bars(night), [])

    def test_perceptual_hash_spots_a_reupload_and_is_kept(self):
        a = ['f0f0f0f0f0f0f0f0', '0123456789abcdef', 'ffff0000ffff0000']
        near = ['f0f0f0f0f0f0f0f1', '0123456789abcdee', 'ffff0000ffff0000']
        other = ['0f0f0f0f0f0f0f0f', 'fedcba9876543210', '0000ffff0000ffff']
        self.assertTrue(quality.same_video(a, near))
        self.assertFalse(quality.same_video(a, other))
        self.assertEqual(quality.dhash([[1, 2] * 4 + [1]] * 8), f"{int('01010101' * 8, 2):016x}")
        script.remember({'topic': 't1', 'title': 'Old'})
        script.remember({'topic': 't2', 'title': 'New'})
        self.assertEqual(quality.reupload({'title': 'Old'}, a), '')
        self.assertEqual(quality.reupload({'title': 'New'}, near), 'Old')
        self.assertEqual([h.get('phash') for h in script.history()], [a, near])

    def test_captions_stay_a_small_share_and_long_videos_are_flagged(self):
        for story, style in ((KAHANI, 'storybook'), (COMIC, 'comic'), (STORY, 'story')):
            starts, end = build.silent_times(story)
            share = quality.caption_share({'style': style, 'segments': build.segments(story, starts, end)})
            self.assertLess(share, quality.CAPTION_LIMIT, style)
        huge = {'style': 'comic', 'segments': [{'kind': 'scene', 'text': 'शब्द' + 'क' * 200}]}
        self.assertGreater(quality.caption_share(huge), quality.CAPTION_LIMIT)
        with mock.patch.object(quality, 'probe', return_value={'duration': 200.0, 'audio': True, 'width': 1080, 'height': 1920}), \
                mock.patch.object(quality, 'loudness', return_value=-14):
            _, issues = quality.hard_checks('v.mp4', longest=120)
        self.assertIn('under 3 minutes', issues[0])

    def test_caption_boxes_match_the_tsx(self):
        book = (ROOT / 'remotion' / 'src' / 'storybook' / 'StoryBook.tsx').read_text(encoding='utf-8')
        reel = (ROOT / 'remotion' / 'src' / 'StickReel.tsx').read_text(encoding='utf-8')
        self.assertIn(f"const MAX = {quality.CAPTION_BOX['storybook']['chars']};", book)
        self.assertIn(f"const MAX = {quality.CAPTION_BOX['comic']['chars']};", reel)
        self.assertIn('fontSize: 68, lineHeight: 1.25', book)

    @unittest.skipUnless(shutil.which('ffmpeg'), 'needs ffmpeg')
    def test_lint_on_a_real_letterboxed_video(self):
        with tempfile.TemporaryDirectory() as tmp:
            video = Path(tmp) / 'box.mp4'
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'testsrc2=size=1080x1500:rate=10:duration=3',
                            '-vf', 'pad=1080:1920:0:210:black', '-pix_fmt', 'yuv420p', str(video)], check=True, timeout=120)
            issues = quality.lint(tmp, video, {'style': 'storybook', 'segments': []}, {'duration': 3.0})
        self.assertTrue(any('black bars at the top and bottom' in i for i in issues), issues)


class InsightsTest(History):
    def test_in_development_metrics_are_skipped(self):
        def call(path, fields=None, method='POST', attempts=3):
            metrics = fields['metric'].split(',')
            if 'reels_skip_rate' in metrics:
                raise publish.PublishError('Instagram refused (100/None): metric is in development')
            return {'data': [{'name': m, 'values': [{'value': 7}]} for m in metrics]}
        with mock.patch.object(publish, 'instagram_call', side_effect=call):
            found = growth.media_insights('m1')
        self.assertNotIn('reels_skip_rate', found)
        self.assertEqual(found['reach'], 7)
        self.assertEqual(found['ig_reels_avg_watch_time'], 7)

    def snapshots(self, now):
        media = [{'id': 'm1', 'caption': publish.texts(KAHANI)['caption'], 'timestamp': ist(1, 19).isoformat(),
                  'media_product_type': 'REELS', 'like_count': 50, 'comments_count': 4}]
        numbers = {'reach': 1000, 'shares': 40, 'likes': 80, 'saved': 20, 'views': 1500,
                   'ig_reels_avg_watch_time': 24000, 'reels_skip_rate': 35.0}

        def call(path, fields=None, method='POST', attempts=3):
            if path.endswith('/media'):
                return {'data': media}
            return {'data': [{'name': k, 'values': [{'value': v}]} for k, v in numbers.items()]}
        with mock.patch.object(publish, 'instagram_user', return_value='u'), mock.patch.object(publish, 'instagram_call', side_effect=call):
            return growth.snapshot(now=now)

    def test_checkpoints_are_taken_once_each(self):
        script.remember(KAHANI, duration=40)
        self.assertEqual(self.snapshots(ist(1, 23)), [])  # 4 hours: nothing due
        taken = self.snapshots(ist(2, 20))
        self.assertEqual([t[1] for t in taken], ['24h'])
        self.assertEqual(self.snapshots(ist(2, 22)), [])  # not twice
        self.assertEqual([t[1] for t in self.snapshots(ist(9, 20))], ['7d'])  # a late run takes the newest only
        entry = script.history()[-1]
        self.assertEqual(sorted(entry['insights']), ['24h', '7d'])
        r = growth.rates(growth.latest(entry), entry['duration'])
        self.assertEqual((r['shares'], r['likes'], r['saves'], r['watch'], r['skip']), (0.04, 0.08, 0.02, 0.6, 0.35))
        self.assertIn('after 24h: reach 1,000', growth.snapshot_message(taken))

    def test_report_and_writers_learn_from_the_rates(self):
        for i, (style, series, shares, skip) in enumerate((('storybook', 'maa_baap', 60, 20), ('comic', '', 10, 60),
                                                           ('storybook', 'rishte', 30, 40), ('story', '', 5, 70))):
            script.remember({'topic': f't{i}', 'title': f'T{i}', 'style': style, 'series': series, 'hook': f'hook {i}',
                             'send_target': 'maa' if i == 0 else 'dost'}, duration=40)
        history = script.history()
        for i, (shares, skip) in enumerate(((60, 20), (10, 60), (30, 40), (5, 70))):
            history[i]['insights'] = {'72h': {'reach': 1000, 'shares': shares, 'likes': 50, 'saved': 5,
                                               'ig_reels_avg_watch_time': 20000 + i * 1000, 'reels_skip_rate': skip}}
        text = growth.insights_message(history)
        self.assertIn('Style storybook (2): 📤 4.5%', text)
        self.assertLess(text.index('Style storybook'), text.index('Style comic'))
        self.assertIn('Hook fewest skipped: "hook 0" (20%)', text)
        self.assertIn('Most skipped: "hook 3" (70%)', text)
        advice = growth.lessons_learned(history)
        self.assertIn('Most SENT on Instagram (shares per reach, the strongest signal): "T0" (sent to: maa)', advice)
        self.assertIn('"hook 0"', advice)
        self.assertEqual(growth.insights_message([]), '')

    def test_captions_match_their_history_entry(self):
        script.remember(dict(KAHANI, part='1/2'))
        script.remember(dict(KAHANI, part='2/2'))
        history = script.history()
        self.assertIs(growth.entry_for(history, publish.texts(dict(KAHANI, part='1/2'))['caption']), history[0])
        self.assertIs(growth.entry_for(history, publish.texts(dict(KAHANI, part='2/2'))['caption']), history[1])


class EveningWindowTest(History):
    def test_default_window_until_a_slot_is_learned(self):
        with mock.patch.dict(os.environ, {'POST_AT_PEAK': 'true'}):
            self.assertTrue(growth.post_now(ist(3, 20, 15)))   # 8:15 pm: inside 7-9 pm
            self.assertTrue(growth.post_now(ist(3, 18, 30)))   # 30 minutes before 7 pm
            self.assertFalse(growth.post_now(ist(3, 11)))      # waits for 7 pm
            self.assertEqual(growth.next_time(growth.best_slot(), ist(3, 11)), ist(3, 19))
            history = [{'slot': 8, 'score': 900}, {'slot': 8, 'score': 800}]
            script.history_path().write_text(json.dumps(history), encoding='utf-8')
            self.assertEqual(growth.learned_slot(), 8)
            self.assertFalse(growth.post_now(ist(3, 20, 15)))  # learned: 8 am is the time now


class SyncTest(unittest.TestCase):
    def test_send_seconds_and_grid_match_the_tsx(self):
        reel = (ROOT / 'remotion' / 'src' / 'StickReel.tsx').read_text(encoding='utf-8')
        zones = (ROOT / 'remotion' / 'src' / 'SafeZones.tsx').read_text(encoding='utf-8')
        self.assertIn(f'export const SEND_SECONDS = {reach.SEND_SECONDS};', reel)
        self.assertIn(f'export const GRID = {{ top: {reach.GRID_34[0]}, bottom: {reach.GRID_34[1]} }};', zones)
        self.assertGreater(reach.SEND_SECONDS, build.TAIL)  # it appears while the question is still being said
        for path in ('storybook/StoryBook.tsx', 'comic/ComicReel.tsx'):
            text = (ROOT / 'remotion' / 'src' / path).read_text(encoding='utf-8')
            self.assertIn('<SendLine text={p.end_line}', text)

    def test_covers_keep_title_series_and_part_inside_the_grid(self):
        book = (ROOT / 'remotion' / 'src' / 'storybook' / 'StoryBook.tsx').read_text(encoding='utf-8')
        cover = (ROOT / 'remotion' / 'src' / 'comic' / 'Cover.tsx').read_text(encoding='utf-8')
        story_cover = book[book.index('export const StoryCover'):]
        strip = re.search(r'const SeriesStrip[\s\S]*?top: (\d+)', book)
        tops = [int(strip.group(1))] + [int(x) for x in re.findall(r'top[:=]\{?\s*(\d+)', story_cover + cover)]
        self.assertIn('<PartBadge part={p.part}', story_cover)
        self.assertIn('<PartBadge part={p.part}', cover)
        low, high = reach.GRID_34
        for top in tops:
            self.assertTrue(low <= top <= high - 250, top)  # room for a line or two of text below each

    def test_workflows_carry_the_new_switches(self):
        flows = ROOT / '.github' / 'workflows'
        self.assertIn('AI_LABEL: ${{ vars.AI_LABEL }}', (flows / 'publish.yml').read_text(encoding='utf-8'))
        self.assertIn('AI_LABEL: ${{ vars.AI_LABEL }}', (flows / 'make-reel.yml').read_text(encoding='utf-8'))
        self.assertIn('python -m reel insights', (flows / 'insights.yml').read_text(encoding='utf-8'))
        make = (flows / 'make-reel.yml').read_text(encoding='utf-8')
        self.assertLess(make.index('python -m reel check'), make.index('Save the topic history'))  # keeps the hashes
        readme = (ROOT / 'README.md').read_text(encoding='utf-8')
        for name in ('AI_LABEL', 'send_target', '3–5 Reels a week', '19:00–21:00 IST', 'Link a Reel', '1,000 followers'):
            self.assertIn(name, readme)


if __name__ == '__main__':
    unittest.main()
