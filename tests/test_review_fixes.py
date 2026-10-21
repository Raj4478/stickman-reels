"""The fixes for the 2026-10-21 code review: each test is one finding."""
import datetime as dt
import json
import os
import re
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

from reel import gemini, growth, publish
from reel.__main__ import main

ROOT = Path(__file__).resolve().parents[1]
IST = dt.timezone(dt.timedelta(minutes=330))


def ist(day, hour, minute=0):
    return dt.datetime(2026, 10, day, hour, minute, tzinfo=IST).astimezone(dt.timezone.utc)


class QueuedFailureTest(unittest.TestCase):
    """1. A failed queued Instagram post is reported, and the queue run ends red."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)
        (self.folder / 'script.json').write_text(json.dumps({'title': 'T'}), encoding='utf-8')
        receipt = {'platforms': {'instagram': {'status': 'queued', 'container': 'c1', 'publish_at': ist(16, 19).isoformat()}}}
        (self.folder / 'publish.json').write_text(json.dumps(receipt), encoding='utf-8')

    def tearDown(self):
        self.tmp.cleanup()

    def test_failure_is_returned_and_sent_to_telegram(self):
        sent = []
        with mock.patch.object(publish, 'instagram_finish', side_effect=publish.PublishError('container expired')), \
                mock.patch('reel.telegram.send_message', side_effect=sent.append), \
                mock.patch('builtins.print') as printed:
            main(['publish-queued', str(self.folder)])
        self.assertEqual(len(sent), 1)
        self.assertIn('did not go out', sent[0])
        self.assertIn('container expired', sent[0])
        self.assertEqual(printed.call_args_list[-1].args, ('failed',))  # the queue workflow removes it and ends red
        receipt = json.loads((self.folder / 'publish.json').read_text(encoding='utf-8'))
        self.assertEqual(receipt['platforms']['instagram']['status'], 'failed')

    def test_queue_workflow_ends_red_on_failure(self):
        queue = (ROOT / '.github' / 'workflows' / 'queue.yml').read_text(encoding='utf-8')
        self.assertIn('[ "$state" = "failed" ]', queue)
        self.assertIn('exit 1', queue)


class HoldTest(unittest.TestCase):
    """2. Instagram is never held longer than it keeps an upload (24 hours)."""

    def test_a_slot_that_just_passed_posts_now(self):
        with mock.patch.dict(os.environ, {'POST_AT_PEAK': 'true'}):
            self.assertTrue(growth.post_now(ist(16, 18, 55), 19))  # 5 minutes before: the next one is 24 h away
            self.assertTrue(growth.post_now(ist(16, 20, 30), 19))  # 1.5 hours after
            self.assertFalse(growth.post_now(ist(16, 10), 19))  # 9 hours to wait: queue it

    def test_upload_is_published_at_once_when_the_time_is_too_far(self):
        now = dt.datetime.now(dt.timezone.utc)
        self.assertIsNone(publish.hold_until({'publish_at': now + dt.timedelta(hours=23, minutes=30)}))
        soon = now + dt.timedelta(hours=5)
        self.assertEqual(publish.hold_until({'publish_at': soon}), soon)
        self.assertIsNone(publish.hold_until({}))


class ConcurrencyTest(unittest.TestCase):
    """3. A request from the bot never cancels another pending one."""

    def test_only_the_daily_run_shares_a_group(self):
        wf = (ROOT / '.github' / 'workflows' / 'make-reel.yml').read_text(encoding='utf-8')
        group = re.search(r'concurrency:\s+group: (.+)', wf).group(1)
        self.assertIn('github.run_id', group)
        self.assertIn("'daily'", group)


class CompilationTest(unittest.TestCase):
    """4. The weekly compilation counts every posted Reel: from the receipts, AUTO_POST included."""

    def test_posted(self):
        self.assertTrue(publish.posted({'platforms': {'instagram': {'status': 'failed'}, 'youtube': {'status': 'published'}}}))
        self.assertTrue(publish.posted({'platforms': {'instagram': {'status': 'queued'}}}))
        self.assertFalse(publish.posted({'platforms': {'youtube': {'status': 'failed'}}}))
        self.assertFalse(publish.posted({}))

    def test_posted_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'publish.json'
            path.write_text(json.dumps({'platforms': {'youtube': {'status': 'published'}}}), encoding='utf-8')
            with self.assertRaises(SystemExit) as ok:
                main(['posted', str(path)])
            with self.assertRaises(SystemExit) as missing:
                main(['posted', str(Path(tmp) / 'none.json')])
        self.assertEqual((ok.exception.code, missing.exception.code), (0, 1))

    def test_workflow_reads_receipts_and_auto_post_runs(self):
        wf = (ROOT / '.github' / 'workflows' / 'compile.yml').read_text(encoding='utf-8')
        self.assertIn('startswith(\\"posted-\\")', wf)
        self.assertIn('Post them (AUTO_POST)', wf)
        self.assertNotIn('--workflow publish.yml --status success', wf)


class DoublePostTest(unittest.TestCase):
    """5. A Reel is never published twice, and never reported failed once it is live."""

    def setUp(self):
        self.env = mock.patch.dict(os.environ, {'INSTAGRAM_ACCESS_TOKEN': 't', 'INSTAGRAM_USER_ID': 'u'})
        self.env.start()

    def tearDown(self):
        self.env.stop()

    def test_missing_link_still_counts_as_published(self):
        def call(path, fields=None, method='POST', attempts=3):
            if path.endswith('media_publish'):
                return {'id': 'm1'}
            raise publish.PublishError('permalink unavailable')
        with mock.patch.object(publish, 'instagram_call', side_effect=call):
            self.assertEqual(publish.instagram_finish('c1'), {'id': 'm1', 'url': ''})

    def test_publish_is_not_retried_and_a_lost_answer_is_checked(self):
        calls = []

        def call(path, fields=None, method='POST', attempts=3):
            calls.append((path, attempts))
            if path.endswith('media_publish'):
                raise urllib.error.URLError('timed out')
            return {'status_code': 'PUBLISHED'}
        with mock.patch.object(publish, 'instagram_call', side_effect=call):
            result = publish.instagram_finish('c1')
        self.assertEqual(calls[0], ('u/media_publish', 1))  # one attempt only
        self.assertIn('Published', result['note'])

    def test_a_real_failure_is_still_raised(self):
        def call(path, fields=None, method='POST', attempts=3):
            if path.endswith('media_publish'):
                raise publish.PublishError('refused')
            return {'status_code': 'FINISHED'}
        with mock.patch.object(publish, 'instagram_call', side_effect=call), self.assertRaises(publish.PublishError):
            publish.instagram_finish('c1')

    def test_request_attempts(self):
        with mock.patch('urllib.request.urlopen', side_effect=urllib.error.URLError('down')) as opened, \
                mock.patch.object(publish.time, 'sleep'), self.assertRaises(urllib.error.URLError):
            publish.request('https://x', attempts=1)
        self.assertEqual(opened.call_count, 1)


class GeminiKeysTest(unittest.TestCase):
    """6. A rejected Gemini key moves on to the next key instead of stopping."""

    def error(self, code):
        return urllib.error.HTTPError('https://x', code, 'no', {}, None)

    def test_a_refused_key_tries_the_next(self):
        tried = []

        def post(model, key, body):
            tried.append(key)
            if key == 'bad':
                raise self.error(403)
            return {'ok': True}
        with mock.patch.dict(os.environ, {'GEMINI_API_KEY': 'bad', 'GEMINI_API_KEY_2': 'good'}), \
                mock.patch.object(gemini, 'post', post):
            response, _ = gemini.call('text', {})
        self.assertEqual(response, {'ok': True})
        self.assertEqual(tried[:2], ['bad', 'good'])

    def test_every_key_refused_says_so(self):
        with mock.patch.dict(os.environ, {'GEMINI_API_KEY': 'a', 'GEMINI_API_KEY_2': 'b', 'GEMINI_API_KEY_3': ''}), \
                mock.patch.object(gemini, 'post', side_effect=self.error(401)), \
                self.assertRaisesRegex(gemini.GeminiError, 'refused every key'):
            gemini.call('text', {})
