import json
import re
import unittest
from pathlib import Path

from reel import build, script, voice

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = json.loads((ROOT / 'examples' / 'sample.json').read_text(encoding='utf-8'))


class ScriptTest(unittest.TestCase):
    def test_sample_is_clean(self):
        story = script.clean(SAMPLE)
        self.assertEqual(len(story['scenes']), 5)
        self.assertEqual(story['hashtags'][0], '#lifelessons')

    def test_unknown_action_and_prop_fall_back(self):
        raw = json.loads(json.dumps(SAMPLE))
        raw['scenes'][0].update(action='moonwalk', prop='dragon', mood='angry')
        beat = script.clean(raw)['scenes'][0]
        self.assertEqual((beat['action'], beat['prop'], beat['mood']), ('point', 'none', 'calm'))

    def test_english_lines_are_dropped_and_too_few_rejected(self):
        raw = json.loads(json.dumps(SAMPLE))
        for beat in raw['scenes'][:3]:
            beat['line'] = 'This line is in English'
        with self.assertRaises(ValueError):
            script.clean(raw)

    def test_english_title_is_rejected(self):
        raw = dict(SAMPLE, title='Where did 5 hours go?')
        with self.assertRaises(ValueError):
            script.clean(raw)

    def test_long_text_is_cut_on_a_word(self):
        text = script.short('शब्द ' * 60, 40)
        self.assertLessEqual(len(text), 41)
        self.assertTrue(text.endswith('।'))

    def test_spoken_order(self):
        story = script.clean(SAMPLE)
        lines = script.spoken_lines(story)
        self.assertEqual(lines[0], story['hook'])
        self.assertEqual(lines[-2:], [story['lesson'], story['ask']])

    def test_template_knows_every_action_and_prop(self):
        actions = (ROOT / 'remotion' / 'src' / 'actions.tsx').read_text(encoding='utf-8')
        cases = set(re.findall(r'case "(\w+)"', actions))
        self.assertLessEqual(set(script.ACTIONS), cases)
        self.assertLessEqual(set(script.PROPS) - {'none'}, cases)

    def test_topics_file(self):
        self.assertTrue(script.pick_topic())


class TimingTest(unittest.TestCase):
    def test_silent_segments_cover_the_reel(self):
        story = script.clean(SAMPLE)
        starts, end = build.silent_times(story)
        segments = build.segments(story, starts, end)
        self.assertEqual([s['kind'] for s in segments], ['hook'] + ['scene'] * 5 + ['lesson', 'ask'])
        self.assertEqual(segments[0]['start'], 0.0)
        for a, b in zip(segments, segments[1:]):
            self.assertEqual(a['end'], b['start'])
            self.assertGreater(a['end'], a['start'])
        self.assertAlmostEqual(segments[-1]['end'], end + build.LEAD + build.TAIL, places=2)
        self.assertEqual(segments[1]['action'], 'scroll_phone')
        self.assertNotIn('line', segments[1])

    def test_lines_snap_to_clear_pauses(self):
        lines = ['एक दो तीन चार', 'पाँच छह सात आठ', 'नौ दस ग्यारह बारह']
        gaps = [(0.0, 0.2), (3.1, 3.6), (6.4, 6.9), (9.6, 10.0)]
        starts, end = voice.split(lines, 10.0, gaps)
        self.assertEqual(end, 9.6)
        self.assertAlmostEqual(starts[1], 3.35)
        self.assertAlmostEqual(starts[2], 6.65)

    def test_no_pauses_falls_back_to_text_share(self):
        starts, end = voice.split(['अ' * 10, 'ब' * 10], 8.0)
        self.assertEqual(end, 8.0)
        self.assertAlmostEqual(starts[1], 4.0)

    def test_build_writes_props_without_narration(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            out, public = Path(tmp) / 'out', Path(tmp) / 'public'
            props, record = build.build(script.clean(SAMPLE), out, public, narrate=False)
            self.assertIsNone(props['audio'])
            self.assertEqual(record['narration'], 'none')
            saved = json.loads((public / 'props.json').read_text(encoding='utf-8'))
            self.assertEqual(saved['duration'], props['segments'][-1]['end'])
            self.assertTrue((out / 'script.json').exists())


if __name__ == '__main__':
    unittest.main()
