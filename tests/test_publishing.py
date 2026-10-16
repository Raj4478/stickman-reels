import datetime as dt
import json
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from reel import publish, report, script, telegram

ROOT = Path(__file__).resolve().parents[1]
STORY = script.clean(json.loads((ROOT / 'examples' / 'sample.json').read_text(encoding='utf-8')))


class TextsTest(unittest.TestCase):
    def test_caption_title_and_tags(self):
        t = publish.texts(STORY)
        self.assertTrue(t['caption'].startswith(STORY['title']))
        self.assertIn(STORY['ask'], t['caption'])
        self.assertIn('#stickman', t['caption'])
        self.assertTrue(t['title'].endswith('#shorts'))
        self.assertLessEqual(len(t['title']), 100)
        self.assertIn('lifelessons', t['tags'])
        self.assertNotIn('#', ''.join(t['tags']))

    def test_series_part_is_in_the_title(self):
        self.assertIn('भाग 1/2', publish.texts(dict(STORY, part='1/2'))['title'])


class PublishTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)
        (self.folder / 'script.json').write_text(json.dumps(STORY, ensure_ascii=False), encoding='utf-8')
        self.video = self.folder / 'reel.mp4'
        self.video.write_bytes(b'mp4')

    def tearDown(self):
        self.tmp.cleanup()

    def test_nothing_configured_is_explained(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            receipt = publish.publish(self.folder, self.video)
        self.assertIn('INSTAGRAM_ACCESS_TOKEN', receipt['skipped'])

    def test_posts_once_and_records_failures(self):
        calls = []
        ok = lambda video, story: calls.append('instagram') or {'id': '1', 'url': 'https://ig/1'}  # noqa: E731

        def broken(video, story):
            raise publish.PublishError('quota')
        with mock.patch.dict(publish.UPLOADERS, {'instagram': ok, 'youtube': broken}):
            first = publish.publish(self.folder, self.video, ['instagram', 'youtube'])
            second = publish.publish(self.folder, self.video, ['instagram', 'youtube'])
        self.assertEqual(calls, ['instagram'])  # never twice
        self.assertEqual(first['platforms']['youtube'], {'status': 'failed', 'error': 'quota'})
        self.assertEqual(second['platforms']['instagram']['url'], 'https://ig/1')
        text = publish.summary(STORY, second)
        self.assertIn('✅ Instagram: https://ig/1', text)
        self.assertIn('❌ YouTube Shorts: quota', text)

    def test_configured_needs_every_youtube_secret(self):
        with mock.patch.dict(os.environ, {'YOUTUBE_CLIENT_ID': 'a', 'YOUTUBE_CLIENT_SECRET': 'b'}, clear=True):
            self.assertEqual(publish.configured(), [])
        with mock.patch.dict(os.environ, {'YOUTUBE_CLIENT_ID': 'a', 'YOUTUBE_CLIENT_SECRET': 'b', 'YOUTUBE_REFRESH_TOKEN': 'c',
                                          'INSTAGRAM_ACCESS_TOKEN': 'd'}, clear=True):
            self.assertEqual(publish.configured(), ['instagram', 'youtube'])


class ReportTest(unittest.TestCase):
    def test_message_ranks_by_engagement(self):
        now = dt.datetime(2026, 10, 19, 4, tzinfo=dt.timezone.utc)
        items = [{'title': 'A', 'url': 'u1', 'views': 1000, 'likes': 10, 'comments': 0, 'saves': 0, 'shares': 0},
                 {'title': 'B', 'url': 'u2', 'views': 800, 'likes': 20, 'comments': 5, 'saves': 9, 'shares': 6}]
        text = report.message({'Instagram': (items, '')}, ['YouTube is not connected yet.'], now)
        self.assertIn('2 Reels', text)
        self.assertIn('👁 1,800', text)
        self.assertLess(text.index('• B'), text.index('• A'))  # shares and saves beat raw views
        self.assertIn('YouTube is not connected', text)

    def test_nothing_connected(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            text = report.weekly()
        self.assertIn('Instagram is not connected', text)
        self.assertIn('YouTube is not connected', text)


class ButtonsTest(unittest.TestCase):
    def test_buttons_match_the_bot(self):
        keys = json.loads(telegram.review_buttons('38859911824', '2'))['inline_keyboard']
        data = [b['callback_data'] for row in keys for b in row]
        self.assertEqual(data, ['post:38859911824:2', 'again:38859911824:2', 'skip:38859911824:2'])
        pattern = re.search(r'/\^\((.+?)\)\$/', (ROOT / 'bot' / 'src.js').read_text(encoding='utf-8')).group(1)
        for d in data:
            self.assertRegex(d, '^(' + pattern + ')$')
            self.assertLessEqual(len(d.encode()), 64)  # Telegram's callback_data limit

    def test_no_run_no_buttons(self):
        self.assertIsNone(telegram.review_buttons('', '1'))


if __name__ == '__main__':
    unittest.main()
