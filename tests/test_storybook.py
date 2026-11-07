import base64
import io
import json
import os
import re
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

from reel import build, images, script, storybook

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = json.loads((ROOT / 'examples' / 'storybook.json').read_text(encoding='utf-8'))
PNG = b'\x89PNG\r\n\x1a\n' + b'0' * 64


class CleanTest(unittest.TestCase):
    def test_sample_becomes_a_story_shaped_script(self):
        s = storybook.clean(SAMPLE)
        self.assertEqual((s['style'], s['series']), ('storybook', 'rishte'))
        self.assertEqual(len(s['scenes']), 15)
        self.assertEqual([c['id'] for c in s['characters']], ['munni', 'papa', 'madam'])
        self.assertTrue(s['hook_roman'].startswith('Us din'))
        self.assertEqual(s['scenes'][3]['cast'], ['papa'])
        self.assertEqual(len(script.spoken_lines(s)), 18)  # hook, 15 beats, moral, question

    def test_unknown_cast_and_shots_are_dropped(self):
        raw = json.loads(json.dumps(SAMPLE))
        raw['beats'][0].update(cast=['munni', 'ghost'], shot='drone')
        s = storybook.clean(raw)
        self.assertEqual((s['scenes'][0]['cast'], s['scenes'][0]['shot']), (['munni'], 'medium'))
        self.assertEqual(storybook.roman_of('Ek hi गाँव mein ✨'), 'Ek hi mein')

    def test_unusable_stories_are_rejected(self):
        with self.assertRaises(ValueError):
            storybook.clean({**SAMPLE, 'characters': []})
        with self.assertRaises(ValueError):
            storybook.clean({**SAMPLE, 'beats': SAMPLE['beats'][:5]})
        with self.assertRaises(ValueError):
            storybook.clean({**SAMPLE, 'hook': {'line': 'English only', 'image': 'x'}})


class PromptTest(unittest.TestCase):
    def test_scene_prompt_carries_the_looks_and_the_references(self):
        s = storybook.clean(SAMPLE)
        line = s['scenes'][12]  # munni and papa
        prompt = images.scene_prompt(line, s['characters'], s['setting'], refs=2)
        self.assertIn('looks exactly like reference image 0', prompt)
        self.assertIn('looks exactly like reference image 1', prompt)
        self.assertIn('two neat plaits', prompt)
        self.assertIn('no text', prompt)
        self.assertNotIn('reference image', images.scene_prompt(line, s['characters'], s['setting'], refs=0))


class Reply:
    def __init__(self, body, content_type='application/json'):
        self.body, self.headers = body, {'Content-Type': content_type}

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class RunTest(unittest.TestCase):
    env = {'CLOUDFLARE_ACCOUNT_ID': 'acc', 'CLOUDFLARE_API_TOKEN': 'tok'}

    def test_flux2_sends_multipart_with_references_and_reads_base64(self):
        sent = {}

        def urlopen(req, timeout=0):
            sent['url'], sent['type'], sent['body'] = req.full_url, req.headers['Content-type'], req.data
            return Reply(json.dumps({'success': True, 'result': {'image': base64.b64encode(PNG).decode()}}).encode())
        with mock.patch.dict(os.environ, self.env), mock.patch('urllib.request.urlopen', urlopen):
            data = images.run(images.KLEIN, 'a farmer', images.SIZE, 7, [PNG, PNG])
        self.assertEqual(data, PNG)
        self.assertTrue(sent['url'].endswith('/accounts/acc/ai/run/@cf/black-forest-labs/flux-2-klein-4b'))
        self.assertTrue(sent['type'].startswith('multipart/form-data; boundary='))
        self.assertIn(b'name="input_image_1"', sent['body'])
        self.assertIn(b'name="width"\r\n\r\n768', sent['body'])

    def test_schnell_sends_json_and_a_raw_image_reply_works(self):
        with mock.patch.dict(os.environ, self.env), mock.patch('urllib.request.urlopen', lambda req, timeout=0: Reply(PNG, 'image/png')):
            self.assertEqual(images.run(images.SCHNELL, 'a farmer', images.SIZE, 7), PNG)

    def test_a_token_without_workers_ai_says_how_to_fix_it(self):
        def urlopen(req, timeout=0):
            raise urllib.error.HTTPError(req.full_url, 403, 'Forbidden', {}, io.BytesIO(b'{"errors":[{"code":10000}]}'))
        with mock.patch.dict(os.environ, self.env), mock.patch('urllib.request.urlopen', urlopen):
            with self.assertRaisesRegex(images.ImageError, 'Workers AI: Read'):
                images.run(images.KLEIN, 'x', images.SIZE, 1)


class BuildTest(unittest.TestCase):
    def test_build_paints_and_passes_pictures_and_captions(self):
        s = storybook.clean(SAMPLE)
        calls = []

        def run(model, prompt, size, seed, refs=()):
            calls.append((model, size, len(refs)))
            return PNG
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, RunTest.env), mock.patch.object(images, 'run', run):
            props, record = build.build(s, Path(tmp) / 'o', Path(tmp) / 'p', narrate=False, music=False, prefix='reels/1/')
            self.assertTrue((Path(tmp) / 'p' / 'reels' / '1' / 'img' / '00.png').exists())
        self.assertEqual(props['style'], 'storybook')
        self.assertEqual(props['series_title'], 'Rishton ki keemat')
        segs = props['segments']
        self.assertEqual([seg.get('image') for seg in segs[:2]], ['reels/1/img/00.png', 'reels/1/img/01.png'])
        self.assertNotIn('image', segs[-1])  # the question keeps the moral's picture
        self.assertTrue(segs[0]['roman'].startswith('Us din') and segs[-1]['roman'].startswith('Aapko'))
        self.assertEqual(sum(1 for c in calls if c[1] == (images.REF, images.REF)), 3)  # a portrait per character
        self.assertEqual(max(c[2] for c in calls), 3)  # the stage scene carries all three portraits
        self.assertEqual(record['pictures']['pictures'], 17)

    def test_template_knows_the_style(self):
        root = (ROOT / 'remotion' / 'src' / 'Root.tsx').read_text(encoding='utf-8')
        self.assertIn('p.style === "storybook"', root)
        self.assertRegex((ROOT / 'bot' / 'src.js').read_text(encoding='utf-8'), re.escape("b: 'style=storybook'"))


if __name__ == '__main__':
    unittest.main()
