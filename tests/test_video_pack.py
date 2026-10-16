import json
import os
import re
import tempfile
import unittest
import urllib.error
import wave
from pathlib import Path
from unittest import mock

from reel import build, gemini, quality, script, voice

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'remotion' / 'src'
SAMPLE = json.loads((ROOT / 'examples' / 'sample.json').read_text(encoding='utf-8'))


def copy():
    return json.loads(json.dumps(SAMPLE))


class DialogueTest(unittest.TestCase):
    def test_sample_has_hero_and_other_lines(self):
        story = script.clean(SAMPLE)
        turns = script.spoken_turns(story)
        self.assertEqual(turns[0][0], 'narrator')
        self.assertEqual([who for who, _ in turns[1:4]], ['hero', 'narrator', 'other'])
        self.assertEqual(story['other_voice'], 'father')
        self.assertEqual(len(turns), len(script.spoken_lines(story)))

    def test_other_without_a_person_becomes_narration(self):
        raw = copy()
        raw['scenes'][0].update(speaker='other')
        raw['scenes'][0]['with'] = 'none'
        self.assertEqual(script.clean(raw)['scenes'][0]['speaker'], 'narrator')

    def test_only_one_other_voice(self):
        raw = copy()
        raw['scenes'][5].update(speaker='other')
        raw['scenes'][5]['with'] = 'mother'  # father already speaks in beat 3
        story = script.clean(raw)
        self.assertEqual(story['scenes'][5]['speaker'], 'narrator')
        self.assertEqual(story['other_voice'], 'father')

    def test_keyword_must_be_in_the_caption(self):
        raw = copy()
        raw['scenes'][0]['keyword'] = 'नहीं'
        self.assertEqual(script.clean(raw)['scenes'][0]['keyword'], '')
        self.assertEqual(script.clean(SAMPLE)['scenes'][0]['keyword'], 'मिनट')

    def test_unknown_sticker_is_dropped(self):
        raw = copy()
        raw['scenes'][0]['sticker'] = 'unicorn'
        self.assertEqual(script.clean(raw)['scenes'][0]['sticker'], 'none')

    def test_gemini_dialogue_request(self):
        sent = {}

        def fake(prompt, voice_name, speakers=None):
            sent.update(prompt=prompt, speakers=speakers)
            return {'mimeType': 'audio/L16;rate=24000', 'data': ''}, 'model'
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(gemini, 'speech_call', fake):
            record = voice.gemini_voice([('narrator', 'एक'), ('other', 'दो'), ('hero', 'तीन')], 'mother', Path(tmp) / 'v.wav')
        self.assertEqual(sent['speakers'], {'Narrator': voice.DEFAULT_VOICE, 'Other': 'Sulafat'})
        self.assertIn('Other: दो', sent['prompt'])
        self.assertIn('Narrator: तीन', sent['prompt'])  # the narrator voices the hero
        self.assertEqual(record['speakers']['Other'], 'Sulafat')


class FallbackTest(unittest.TestCase):
    def tearDown(self):
        gemini.USED.clear()

    def test_speech_falls_back_to_edge(self):
        def broken(*args, **kwargs):
            raise gemini.GeminiError('quota')

        def edge(turns, other, path):
            return {'model': 'edge-tts', 'starts': [0.0, 1.0], 'speech_end': 2.0}
        with mock.patch.object(voice, 'gemini_voice', broken), mock.patch.object(voice, 'edge_voice', edge):
            record = voice.synthesize([('narrator', 'a'), ('narrator', 'b')], Path('.'))
        self.assertEqual(record['model'], 'edge-tts')
        self.assertIn('Edge', gemini.USED[0]['service'])

    def test_text_falls_back_to_groq(self):
        class Reply:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                return json.dumps({'choices': [{'message': {'content': '```json\n{"title": "x"}\n```'}}]}).encode()
        with mock.patch.object(gemini, 'call', side_effect=gemini.GeminiError('quota')), \
                mock.patch.dict(os.environ, {'GROQ_API_KEY': 'k'}, clear=False), \
                mock.patch('urllib.request.urlopen', return_value=Reply()):
            result, model = gemini.json_call('prompt', {'type': 'object'})
        self.assertEqual(result, {'title': 'x'})
        self.assertTrue(model.startswith('groq:'))
        self.assertEqual(gemini.USED[0]['service'].split(' ')[0], 'Groq')

    def test_no_backup_keys_explains_how(self):
        env = {k: v for k, v in os.environ.items() if k not in ('GROQ_API_KEY', 'OPENROUTER_API_KEY')}
        with mock.patch.object(gemini, 'call', side_effect=gemini.GeminiError('quota')), mock.patch.dict(os.environ, env, clear=True):
            with self.assertRaises(gemini.GeminiError) as caught:
                gemini.json_call('prompt', {'type': 'object'})
        self.assertIn('GROQ_API_KEY', str(caught.exception))

    def test_backup_network_error_tries_the_next(self):
        with mock.patch.object(gemini, 'call', side_effect=gemini.GeminiError('quota')), \
                mock.patch.dict(os.environ, {'GROQ_API_KEY': 'k', 'OPENROUTER_API_KEY': ''}, clear=False), \
                mock.patch('urllib.request.urlopen', side_effect=urllib.error.URLError('down')):
            with self.assertRaises(gemini.GeminiError):
                gemini.json_call('prompt', {'type': 'object'})


class MouthTest(unittest.TestCase):
    def test_loud_frames_open_the_mouth(self):
        import numpy as np
        rate = 24000
        quiet, loud = np.zeros(rate // 2), (np.sin(np.arange(rate // 2) * 0.3) * 12000)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'v.wav'
            voice.write_pcm(path, np.concatenate([quiet, loud]).astype('<i2').tobytes(), rate)
            curve = voice.mouth_curve(path)
        self.assertEqual(len(curve), 30)
        self.assertEqual(max(curve[:14]), 0)
        self.assertGreater(min(curve[16:]), 0.5)

    def test_build_uses_exact_edge_starts(self):
        def fake(turns, out, other='friend'):
            import numpy as np
            voice.write_pcm(out / 'voice.wav', (np.ones(24000 * 20) * 3000).astype('<i2').tobytes(), 24000)
            return {'model': 'edge-tts', 'starts': [i * 2.0 for i in range(len(turns))], 'speech_end': 2.0 * len(turns) - .4}
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(voice, 'synthesize', fake), \
                mock.patch.object(voice, 'heard_words', return_value=None):
            props, record = build.build(script.clean(SAMPLE), Path(tmp) / 'o', Path(tmp) / 'p', music=False)
        self.assertEqual(props['segments'][1]['start'], round(2.0 + build.LEAD, 3))
        self.assertEqual(props['segments'][1]['speaker'], 'hero')
        self.assertTrue(props['mouth'])
        self.assertNotIn('starts', record)


class TemplateTest(unittest.TestCase):
    def test_every_place_and_sticker_is_drawn(self):
        places = set(re.findall(r'case "(\w+)"', (SRC / 'places.tsx').read_text(encoding='utf-8')))
        self.assertLessEqual(set(script.PLACES) - {'plain'}, places)
        stickers = (SRC / 'stickers.tsx').read_text(encoding='utf-8')
        for name in set(script.STICKERS) - {'none'}:
            self.assertRegex(stickers, rf'\n  {name}: ', name)

    def test_no_emoji_drawn_in_the_video(self):
        # the Linux render machine has no emoji font: emoji would render as empty boxes
        for path in SRC.rglob('*.tsx'):
            text = path.read_text(encoding='utf-8')
            self.assertIsNone(re.search('[\U0001f300-\U0001faff☀-➿]', text), path.name)


class QualityTest(unittest.TestCase):
    def test_hard_checks(self):
        info = {'duration': 75.0, 'audio': False, 'width': 1080, 'height': 1920}
        with mock.patch.object(quality, 'probe', return_value=info):
            _, issues = quality.hard_checks('x.mp4')
        self.assertEqual(len(issues), 2)
        self.assertIn('75s', issues[0])

    def test_note(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(quality.note(tmp), '')
            Path(tmp, 'quality.json').write_text(json.dumps({'ok': False, 'issues': ['caption cut off']}), encoding='utf-8')
            self.assertIn('• caption cut off', quality.note(tmp))
            Path(tmp, 'quality.json').write_text(json.dumps({'ok': True, 'looked': True}), encoding='utf-8')
            self.assertIn('passed', quality.note(tmp))


if __name__ == '__main__':
    unittest.main()
