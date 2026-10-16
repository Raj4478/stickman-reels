import json
import os
import re
import tempfile
import unittest
from pathlib import Path

from reel import build, script, sounds, voice

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = json.loads((ROOT / 'examples' / 'sample.json').read_text(encoding='utf-8'))
SRC = ROOT / 'remotion' / 'src'


def copy(**changes):
    raw = json.loads(json.dumps(SAMPLE))
    raw.update(changes)
    return raw


class ScriptTest(unittest.TestCase):
    def test_sample_is_clean(self):
        story = script.clean(SAMPLE)
        self.assertEqual(len(story['scenes']), 6)
        self.assertEqual(story['hashtags'][0], '#lifelessons')
        self.assertEqual(story['name'], 'रोहन')
        self.assertEqual(story['hook_action'], 'shock')

    def test_unknown_names_fall_back(self):
        raw = copy()
        raw['scenes'][0].update(action='moonwalk', prop='dragon', mood='angry', place='moon', shot='drone', transition='spin')
        beat = script.clean(raw)['scenes'][0]
        self.assertEqual((beat['action'], beat['prop'], beat['mood'], beat['place'], beat['transition']),
                         ('point', 'none', 'calm', 'plain', 'cut'))

    def test_two_person_action_gets_a_person_and_a_two_shot(self):
        raw = copy()
        raw['scenes'][2].update(action='hug', shot='extreme_close')
        raw['scenes'][2]['with'] = 'none'
        beat = script.clean(raw)['scenes'][2]
        self.assertEqual((beat['with'], beat['shot']), ('friend', 'two_shot'))

    def test_same_shot_twice_in_a_row_is_changed(self):
        raw = copy()
        for beat in raw['scenes']:
            beat['shot'] = 'close'
        shots = [b['shot'] for b in script.clean(raw)['scenes']]
        self.assertTrue(all(a != b for a, b in zip(shots, shots[1:])), shots)

    def test_english_lines_are_dropped_and_too_few_rejected(self):
        raw = copy()
        for beat in raw['scenes'][:4]:
            beat['line'] = 'This line is in English'
        with self.assertRaises(ValueError):
            script.clean(raw)

    def test_english_title_is_rejected(self):
        with self.assertRaises(ValueError):
            script.clean(copy(title='Where did 5 hours go?'))

    def test_missing_hook_uses_the_first_hindi_option(self):
        story = script.clean(copy(hook='', hooks=['English hook', 'हिंदी हुक यहाँ है']))
        self.assertEqual(story['hook'], 'हिंदी हुक यहाँ है')

    def test_long_text_is_cut_on_a_word(self):
        text = script.short('शब्द ' * 60, 40)
        self.assertLessEqual(len(text), 41)
        self.assertTrue(text.endswith('।'))

    def test_spoken_order(self):
        story = script.clean(SAMPLE)
        lines = script.spoken_lines(story)
        self.assertEqual(lines[0], story['hook'])
        self.assertEqual(lines[-2:], [story['lesson'], story['ask']])

    def test_series_note(self):
        self.assertEqual(script.series_note('', None), '')
        self.assertIn('PART 1', script.series_note('1/2', None))
        self.assertIn('रोहन', script.series_note('2/2', {'name': 'रोहन'}))


class TemplateTest(unittest.TestCase):
    """The Python lists and the Remotion template must name the same things."""

    def test_every_action_and_prop_is_drawn(self):
        cases = set(re.findall(r'case "(\w+)"', (SRC / 'actions.tsx').read_text(encoding='utf-8')))
        self.assertLessEqual(set(script.ACTIONS), cases)
        self.assertLessEqual(set(script.PROPS) - {'none'}, cases)

    def test_every_place_is_drawn(self):
        cases = set(re.findall(r'case "(\w+)"', (SRC / 'places.tsx').read_text(encoding='utf-8')))
        self.assertLessEqual(set(script.PLACES) - {'plain'}, cases)

    def test_every_shot_is_filmed(self):
        director = (SRC / 'director.ts').read_text(encoding='utf-8')
        for shot in script.SHOTS:
            self.assertRegex(director, rf'\n  {shot}: ', shot)

    def test_every_cast_member_has_a_look(self):
        actions = (SRC / 'actions.tsx').read_text(encoding='utf-8')
        for who in set(script.CAST) - {'none'}:
            self.assertRegex(actions, rf'\n  {who}: \{{ color', who)

    def test_every_sound_cue_exists(self):
        names = set(re.findall(r'"([a-z_]+)", [0-9.]+\]', (SRC / 'actions.tsx').read_text(encoding='utf-8')))
        names |= set(re.findall(r'\[\d+, "([a-z_]+)", [0-9.]+\]', (SRC / 'StickReel.tsx').read_text(encoding='utf-8')))
        self.assertTrue(names)
        self.assertLessEqual(names, set(sounds.effects()))
        for name in names:
            self.assertTrue((ROOT / 'remotion' / 'public' / 'sfx' / f'{name}.wav').exists(), name)


class HistoryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ['REEL_HISTORY'] = str(Path(self.tmp.name) / 'history.json')

    def tearDown(self):
        os.environ.pop('REEL_HISTORY')
        self.tmp.cleanup()

    def test_recent_topics_are_not_picked_again(self):
        topics = Path(self.tmp.name) / 'topics.txt'
        topics.write_text('A\nB\n', encoding='utf-8')
        script.remember({'topic': 'A', 'title': 'x'})
        self.assertEqual({script.pick_topic(topics) for _ in range(20)}, {'B'})

    def test_all_used_falls_back_to_any(self):
        topics = Path(self.tmp.name) / 'topics.txt'
        topics.write_text('A\n', encoding='utf-8')
        script.remember({'topic': 'A', 'title': 'x'})
        self.assertEqual(script.pick_topic(topics), 'A')


class TimingTest(unittest.TestCase):
    def test_silent_segments_cover_the_reel(self):
        story = script.clean(SAMPLE)
        starts, end = build.silent_times(story)
        segments = build.segments(story, starts, end)
        self.assertEqual([s['kind'] for s in segments], ['hook'] + ['scene'] * 6 + ['lesson', 'ask'])
        self.assertEqual(segments[0]['start'], 0.0)
        self.assertEqual(segments[0]['action'], 'shock')
        for a, b in zip(segments, segments[1:]):
            self.assertEqual(a['end'], b['start'])
            self.assertGreater(a['end'], a['start'])
        self.assertAlmostEqual(segments[-1]['end'], end + build.LEAD + build.TAIL, places=2)
        self.assertEqual((segments[1]['action'], segments[3]['with']), ('scroll_phone', 'father'))
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

    def test_heard_words_set_each_written_word(self):
        lines = ['एक दो तीन', 'चार पाँच']
        heard = [(0.1, 0.3), (0.5, 0.7), (1.0, 1.2), (2.0, 2.2), (2.6, 2.9)]
        self.assertEqual(voice.word_times(lines, [0.0, 1.8], 3.0, heard), [[0.1, 0.5, 1.0], [2.0, 2.6]])

    def test_word_count_mismatch_maps_by_position(self):
        times = voice.word_times(['एक दो तीन चार'], [0.0], 2.0, [(0.2, 0.4), (1.2, 1.4)])[0]
        self.assertEqual(len(times), 4)
        self.assertEqual(times, sorted(times))
        self.assertEqual((times[0], times[-1]), (0.2, 1.2))

    def test_no_whisper_spreads_words_by_length(self):
        times = voice.word_times(['एक दो'], [1.0], 3.0, None)[0]
        self.assertEqual(times[0], 1.0)
        self.assertGreater(times[1], 1.0)

    def test_build_writes_props_music_and_word_times(self):
        with tempfile.TemporaryDirectory() as tmp:
            out, public = Path(tmp) / 'out', Path(tmp) / 'public'
            props, record = build.build(script.clean(SAMPLE), out, public, narrate=False, prefix='reels/1/')
            self.assertIsNone(props['audio'])
            self.assertEqual(props['music'], 'reels/1/music.wav')
            self.assertTrue((public / 'reels' / '1' / 'music.wav').exists())
            self.assertEqual(record['narration'], 'none')
            saved = json.loads((public / 'reels' / '1' / 'props.json').read_text(encoding='utf-8'))
            self.assertEqual(saved['duration'], props['segments'][-1]['end'])
            for segment in saved['segments']:
                self.assertEqual(len(segment['words']), len(segment['text'].split()))
            self.assertTrue((out / 'script.json').exists())


class SoundTest(unittest.TestCase):
    def test_music_is_the_right_length_and_level(self):
        mix = sounds.music(4.0, 'tense', 'x')
        self.assertAlmostEqual(len(mix) / sounds.RATE, 4.5, places=1)
        self.assertLessEqual(abs(mix).max(), 0.71)


if __name__ == '__main__':
    unittest.main()
