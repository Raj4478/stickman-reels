import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from reel import comic, gemini
from reel.__main__ import audience_of, parse_options

ROOT = Path(__file__).resolve().parents[1]
KIDS = json.loads((ROOT / 'examples' / 'comic_kids.json').read_text(encoding='utf-8'))


def score(laugh=3, surprise=3, clarity=3, picture=3, safe=5):
    return {'laugh': laugh, 'surprise': surprise, 'clarity': clarity, 'picture': picture, 'safe': safe, 'fix': 'shorter hook'}


class AudienceTest(unittest.TestCase):
    def test_option_and_variable(self):
        self.assertEqual(parse_options('style=comic audience=family'), {'style': 'comic', 'audience': 'family'})
        self.assertEqual(parse_options('audience=toddlers'), {})
        with mock.patch.dict(os.environ, {'REEL_AUDIENCE': 'family'}):
            self.assertEqual(audience_of({}), 'family')
            self.assertEqual(audience_of({'audience': 'adult'}), 'adult')
        with mock.patch.dict(os.environ, {'REEL_AUDIENCE': ''}):
            self.assertEqual(audience_of({}), 'adult')

    def test_kids_sample_keeps_its_audience_and_new_names(self):
        s = comic.clean(KIDS)
        self.assertEqual((s['audience'], s['music']), ('family', 'kids'))
        self.assertEqual((s['hook_face'], s['scenes'][0]['face'], s['scenes'][0]['gesture']), ('cheeky', 'sneaky', 'sneak'))
        self.assertEqual(s['scenes'][2]['face'], 'proud')
        self.assertEqual(s['punch_visual'], 'result')
        self.assertEqual(comic.clean({**KIDS, 'audience': 'aliens'})['audience'], 'adult')

    def test_kids_topics_are_kid_world(self):
        topics = [t for t in (ROOT / 'kids_topics.txt').read_text(encoding='utf-8').splitlines() if t.strip() and not t.startswith('#')]
        self.assertGreaterEqual(len(topics), 40)
        for t in topics:
            self.assertNotRegex(t.lower(), r'salary|boss|office|dating', t)
        env = {'REEL_HISTORY': '', 'OCCASIONS': 'off'}
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {**env, 'REEL_HISTORY': str(Path(tmp) / 'h.json')}):
            self.assertIn(comic.topic_for('', '', 'random', 'family')[0], topics)
            self.assertIn("child's life", comic.topic_for('', 'money', '', 'kids')[0])


class SafetyTest(unittest.TestCase):
    def test_kid_safe_rejects_dangerous_acts(self):
        with self.assertRaises(ValueError):
            comic.kid_safe({'hook': {'line': 'मैंने माचिस से मोमबत्ती जलाई'}, 'lines': [], 'punchline': {'line': 'हा'}})
        comic.kid_safe({'hook': {'line': 'रिपोर्ट कार्ड आया है'}, 'lines': [], 'punchline': {'line': 'पंचानवे आए'}})
        comic.kid_safe(KIDS)


class JudgeTest(unittest.TestCase):
    drafts = [({'n': 0}, 'm0'), ({'n': 1}, 'm1')]

    def test_picks_the_funnier_draft(self):
        with mock.patch.object(gemini, 'json_call', return_value=({'scores': [score(), score(laugh=5, surprise=4)]}, 'j')):
            raw, model, fix = comic.judge(self.drafts, 'family')
        self.assertEqual((raw, model, fix), ({'n': 1}, 'm1', 'shorter hook'))

    def test_never_picks_an_unsafe_draft_for_families(self):
        with mock.patch.object(gemini, 'json_call', return_value=({'scores': [score(), score(laugh=5, safe=3)]}, 'j')):
            self.assertEqual(comic.judge(self.drafts, 'family')[0], {'n': 0})
        with mock.patch.object(gemini, 'json_call', return_value=({'scores': [score(), score(laugh=5, safe=3)]}, 'j')):
            self.assertEqual(comic.judge(self.drafts, 'adult')[0], {'n': 1})  # adults: safety is the editor's job
        with mock.patch.object(gemini, 'json_call', return_value=({'scores': [score(safe=2), score(safe=1)]}, 'j')):
            with self.assertRaises(ValueError):
                comic.judge(self.drafts, 'kids')

    def test_falls_back_to_the_first_draft(self):
        with mock.patch.object(gemini, 'json_call', side_effect=gemini.GeminiError('quota')):
            self.assertEqual(comic.judge(self.drafts, 'family'), ({'n': 0}, 'm0', ''))


class WriteTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {'REEL_HISTORY': str(Path(self.tmp.name) / 'h.json'), 'NARRATOR': '', 'OCCASIONS': 'off'})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def test_family_reel_has_the_recurring_kid(self):
        calls = []

        def fake(prompt, schema, **kw):
            calls.append(prompt)
            if 'scores' in schema.get('properties', {}):
                return {'scores': [score(), score(laugh=5)]}, 'judge'
            return json.loads(json.dumps(KIDS)), 'writer'
        with mock.patch.object(comic, 'DRAFTS', 2), mock.patch.object(gemini, 'json_call', fake):
            s = comic.write('report card', audience='family')
        self.assertEqual((s['name'], s['music'], s['audience']), (comic.CHARACTER['boy'], 'kids', 'family'))
        self.assertEqual(len(calls), 4)  # two drafts, the judge, the editor
        self.assertIn(comic.CHARACTER['catchphrase'], calls[0])
        self.assertIn('KID WORLD ONLY', calls[0])
        self.assertIn('The judges asked for this change: shorter hook', calls[-1])
        self.assertNotEqual(s['ask'], comic.CHARACTER['catchphrase'])  # family Reels keep their question

    def test_made_for_kids_ends_on_the_catchphrase(self):
        def fake(prompt, schema, **kw):
            return json.loads(json.dumps(KIDS)), 'writer'
        with mock.patch.object(comic, 'DRAFTS', 1), mock.patch.object(gemini, 'json_call', fake):
            s = comic.write('report card', audience='kids')
        self.assertEqual(s['ask'], comic.CHARACTER['catchphrase'])


if __name__ == '__main__':
    unittest.main()
