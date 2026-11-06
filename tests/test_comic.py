import base64
import json
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from reel import build, comic, publish, quality, script, sounds, voice
from reel.__main__ import parse_options, style_of

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = json.loads((ROOT / 'examples' / 'comic.json').read_text(encoding='utf-8'))
SRC = ROOT / 'remotion' / 'src'
COMIC = SRC / 'comic'


def copy(**changes):
    raw = json.loads(json.dumps(SAMPLE))
    raw.update(changes)
    return raw


class CleanTest(unittest.TestCase):
    def test_sample_becomes_a_story_shaped_script(self):
        s = comic.clean(SAMPLE)
        self.assertEqual((s['style'], s['place'], s['emoji'], s['music']), ('comic', 'bedroom', 'sob', 'comic'))
        self.assertEqual(s['hook'], SAMPLE['hook']['line'])
        self.assertEqual(s['lesson'], SAMPLE['punchline']['line'])  # the punchline sits where a lesson would
        self.assertEqual((s['hook_face'], s['punch_face'], s['punch_gesture']), ('deadpan', 'smug', 'point_self'))
        self.assertEqual(len(s['scenes']), 3)
        self.assertEqual([b['speaker'] for b in s['scenes']], ['narrator', 'other', 'narrator'])
        self.assertEqual(s['scenes'][1]['with'], 'mother')
        self.assertEqual(s['other_voice'], 'mother')
        self.assertEqual(len(script.spoken_lines(s)), 6)

    def test_unknown_names_fall_back(self):
        raw = copy(place='moon', emoji='rocket', other='alien')
        raw['lines'] = [{'line': 'ये तो होना ही था।', 'face': 'laughing', 'gesture': 'moonwalk', 'look': 'sky', 'speaker': 'other'}]
        s = comic.clean(raw)
        self.assertEqual((s['place'], s['emoji']), ('bedroom', 'sob'))
        self.assertEqual({k: s['scenes'][0][k] for k in ('face', 'gesture', 'look', 'speaker', 'with')},
                         {'face': 'deadpan', 'gesture': 'talk', 'look': 'viewer', 'speaker': 'narrator', 'with': 'none'})

    def test_banter_has_at_most_three_off_screen_lines_never_two_in_a_row(self):
        mom = lambda text: {'line': text, 'face': 'angry', 'gesture': 'talk', 'look': 'side', 'speaker': 'other'}  # noqa: E731
        kid = lambda text: {'line': text, 'face': 'cheeky', 'gesture': 'dance', 'look': 'viewer', 'speaker': 'hero'}  # noqa: E731
        raw = copy(lines=[mom('गोलू, उठ जा!'), mom('सुना नहीं?'), kid('सुन लिया मम्मी।'), mom('दूध ले आ!'), kid('ला रहा हूँ।'),
                          mom('अभी!'), kid('अभी तो सो रहा हूँ।'), mom('गोलू!')])
        s = comic.clean(raw)
        speakers = [b['speaker'] for b in s['scenes']]
        self.assertEqual(speakers.count('other'), 3)
        self.assertNotIn(('other', 'other'), list(zip(speakers, speakers[1:])))
        self.assertEqual((s['scenes'][1]['face'], s['scenes'][1]['gesture']), ('cheeky', 'dance'))

    def test_english_punchline_or_empty_rant_is_rejected(self):
        with self.assertRaises(ValueError):
            comic.clean(copy(punchline={'line': 'only English here', 'face': 'smug', 'gesture': 'talk', 'look': 'viewer', 'speaker': 'hero'}))
        with self.assertRaises(ValueError):
            comic.clean(copy(lines=[{'line': 'no Hindi', 'face': 'sad', 'gesture': 'talk', 'look': 'viewer', 'speaker': 'hero'}]))

    def test_visemes_follow_the_words(self):
        segs = [{'text': 'मम्मी बोलो', 'words': [0.0, 0.5], 'end': 1.0}]
        v = voice.visemes(segs, 1.0, fps=10)
        self.assertEqual(v[:2], 'MM')  # म starts closed
        self.assertIn('O', v[5:10])  # बोलो is round
        self.assertEqual(len(v), 11)

    def test_cover_text_is_kept_short(self):
        s = comic.clean(copy(cover_text='पंचानवे नंबर आए फिर भी छुपाया?!'))
        self.assertLessEqual(len(s['cover_text']), comic.LIMITS['cover_text'])
        self.assertEqual(comic.clean(copy())['cover_text'], '')

    def test_missing_hook_object_uses_the_first_option(self):
        s = comic.clean(copy(hook=None))
        self.assertEqual(s['hook'], SAMPLE['hooks'][0])

    def test_english_ask_gets_a_hindi_default(self):
        self.assertTrue(script.DEVANAGARI.search(comic.clean(copy(ask='Comment below'))['ask']))


class DrawnTest(unittest.TestCase):
    def test_every_face_gesture_room_and_emoji_is_drawn(self):
        kid = (COMIC / 'Kid.tsx').read_text(encoding='utf-8')
        for face in comic.FACES:
            self.assertRegex(kid, rf'\n  {face}: \{{ lid', face)
        gestures = set(re.findall(r'case "(\w+)"', kid)) | {'talk'}  # talk is the default
        self.assertLessEqual(set(comic.GESTURES), gestures)
        rooms = set(re.findall(r'case "(\w+)"', (COMIC / 'rooms.tsx').read_text(encoding='utf-8')))
        self.assertLessEqual(set(comic.ROOMS), rooms)
        emoji = (COMIC / 'Emoji.tsx').read_text(encoding='utf-8')
        for name in set(comic.EMOJI) - {'none'}:
            self.assertRegex(emoji, rf'\n  {name}: \(', name)
        for look in comic.LOOKS:
            self.assertIn(f'{look}: {{ x:', kid)

    def test_every_comic_sound_exists(self):
        reel = (COMIC / 'ComicReel.tsx').read_text(encoding='utf-8')
        names = set(re.findall(r'\[\d+, "([a-z_]+)", [0-9.]+\]', reel)) | set(re.findall(r'"sfx/([a-z_]+)\.wav"', reel))
        names |= {'typing', 'thud'}  # cued with a variable frame
        self.assertTrue({'rimshot', 'pop', 'whip', 'boing', 'sad'} <= names)
        self.assertLessEqual(names, set(sounds.effects()))
        for name in names:
            self.assertTrue((ROOT / 'remotion' / 'public' / 'sfx' / f'{name}.wav').exists(), name)

    def test_comic_music_is_the_right_length(self):
        with tempfile.TemporaryDirectory() as tmp:
            sounds.write_music(Path(tmp) / 'm.wav', 6, 'comic', 'x')
            self.assertAlmostEqual(voice.duration(Path(tmp) / 'm.wav'), 6.5, delta=0.05)


class OptionsTest(unittest.TestCase):
    def test_style_option_and_the_usual_style(self):
        self.assertEqual(parse_options('style=comic voice=female'), {'style': 'comic', 'voice': 'female'})
        self.assertEqual(parse_options('style=funny'), {})
        with mock.patch.dict(os.environ, {'REEL_STYLE': 'comic'}):
            self.assertEqual(style_of({}), 'comic')
            self.assertEqual(style_of({'style': 'story'}), 'story')
        with mock.patch.dict(os.environ, {'REEL_STYLE': 'whatever'}):
            self.assertEqual(style_of({}), 'story')

    def test_topics(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {'REEL_HISTORY': str(Path(tmp) / 'h.json'), 'OCCASIONS': 'off'}):
            self.assertEqual(comic.topic_for('gym membership'), ('gym membership', None))
            self.assertIn('funny situation about money', comic.topic_for('', 'money')[0])
            topics = (ROOT / 'comic_topics.txt').read_text(encoding='utf-8').splitlines()
            self.assertIn(comic.topic_for('', '', 'random')[0], topics)


class BuildAndPostTest(unittest.TestCase):
    def test_build_passes_the_comic_look_to_remotion(self):
        with tempfile.TemporaryDirectory() as tmp:
            props, _ = build.build(comic.clean(SAMPLE), Path(tmp) / 'o', Path(tmp) / 'p', narrate=False, music=False)
        self.assertEqual((props['style'], props['place'], props['emoji']), ('comic', 'bedroom', 'sob'))
        hook, punch = props['segments'][0], props['segments'][-2]
        self.assertEqual((hook['face'], hook['gesture'], hook['look']), ('deadpan', 'type', 'screen'))
        self.assertEqual((punch['kind'], punch['face']), ('lesson', 'smug'))
        self.assertEqual(props['segments'][2]['speaker'], 'other')

    def test_posting_texts_are_comedy_texts(self):
        story = comic.clean(SAMPLE)
        texts = publish.texts(story)
        self.assertIn('देसी कॉमेडी', texts['title'])
        self.assertTrue(publish.hashtags(story).startswith('#hindicomedy'))
        self.assertNotIn('सीख: ', texts['description'])
        self.assertIn('hindi comedy', texts['tags'])
        self.assertIn('सीख: ', publish.texts(script.clean(json.loads((ROOT / 'examples' / 'sample.json').read_text(encoding='utf-8'))))['description'])

    def test_a_short_comic_reel_passes_the_length_check(self):
        info = {'duration': 16.0, 'audio': True, 'width': 1080, 'height': 1920}
        with mock.patch.object(quality, 'probe', return_value=info), mock.patch.object(quality, 'loudness', return_value=-18):
            self.assertEqual(quality.hard_checks('x.mp4', shortest=12)[1], [])
            self.assertEqual(len(quality.hard_checks('x.mp4')[1]), 1)


class VoiceTest(unittest.TestCase):
    def test_comic_voice_sounds_like_a_real_person(self):
        calls = []

        def speech(prompt, voice_name, speakers=None):
            calls.append((prompt, voice_name, speakers))
            return {'mimeType': 'audio/L16;rate=24000', 'data': base64.b64encode(b'\x00\x00' * 24000).decode()}, 'tts'
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(voice.gemini, 'speech_call', speech), \
                mock.patch.dict(os.environ, {'REEL_VOICE': '', 'NARRATOR': ''}):
            voice.gemini_voice([('narrator', 'एक'), ('narrator', 'दो')], 'friend', Path(tmp) / 'v.wav', style='comic')
            voice.gemini_voice([('narrator', 'एक'), ('other', 'दो')], 'mother', Path(tmp) / 'v.wav', style='comic')
        self.assertIn('never a voice actor, a cartoon', calls[0][0])
        self.assertEqual(calls[0][1], 'Zubenelgenubi')
        self.assertEqual([who for who, _, _ in calls[1][0]], ['Narrator', 'Other'])
        self.assertIn('calling from another room', calls[1][0][1][2])
        self.assertEqual(calls[1][2], {'Narrator': 'Zubenelgenubi', 'Other': 'Sulafat'})

    def test_dialogue_is_sent_as_speaker_tagged_parts(self):
        sent = {}

        def call(kind, body):
            sent.update(body)
            return {'candidates': [{'content': {'parts': [{'inlineData': {'data': '', 'mimeType': 'audio/L16'}}]}}]}, 'tts'
        with mock.patch.object(voice.gemini, 'call', call):
            voice.gemini.speech_call([('Narrator', 'एक', 'dry'), ('Other', 'दो', '')], 'Puck', {'Narrator': 'Puck', 'Other': 'Kore'})
        self.assertEqual(sent['contents'][0]['parts'], [{'text': 'एक', 'speechMetadata': {'speaker': 'Narrator', 'style': 'dry'}},
                                                        {'text': 'दो', 'speechMetadata': {'speaker': 'Other'}}])
        names = [c['speaker'] for c in sent['generationConfig']['speechConfig']['multiSpeakerVoiceConfig']['speakerVoiceConfigs']]
        self.assertEqual(names, ['Narrator', 'Other'])

    def test_the_punchline_gets_a_beat_before_it(self):
        calls = []

        def speech(prompt, voice_name, speakers=None):
            calls.append(prompt)
            return {'mimeType': 'audio/L16;rate=24000', 'data': base64.b64encode(b'\x00\x00' * 24000).decode()}, 'tts'
        turns = script.spoken_turns(comic.clean(SAMPLE))
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(voice.gemini, 'speech_call', speech):
            voice.gemini_voice(turns, 'mother', Path(tmp) / 'v.wav', style='comic')
        styles = [style for _, _, style in calls[0]]
        self.assertTrue(styles[-2].endswith(voice.COMIC_PUNCH))
        self.assertEqual(sum(s.endswith(voice.COMIC_PUNCH) for s in styles), 1)


class VisualsTest(unittest.TestCase):
    def line(self, **k):
        return {'line': 'ये तो होना ही था।', 'face': 'sad', 'gesture': 'talk', 'look': 'viewer', 'speaker': 'hero',
                'visual': 'kid', 'visual_text': '', 'screen': 'music', 'who': 'teacher', **k}

    def test_sample_follows_the_words(self):
        s = comic.clean(SAMPLE)
        self.assertEqual(s['hook_visual'], 'kid')
        self.assertEqual([(b['visual'], b['who']) for b in s['scenes']], [('person', 'teacher'), ('person', 'mother'), ('calendar', 'none')])
        self.assertEqual((s['punch_visual'], s['punch_screen'], s['punch_visual_text']), ('screen', 'music', 'गाना.mp3'))

    def test_visual_rules(self):
        raw = copy(hook=self.line(visual='money', visual_text='₹5'))
        raw['lines'] = [self.line(speaker='other', visual='kid'),  # a person speaking is shown
                        self.line(visual='calendar', visual_text=''),  # nothing to show: back to the kid
                        self.line(visual='rocket')]
        s = comic.clean(raw)
        self.assertEqual((s['hook_visual'], s['hook_visual_text']), ('money', '₹5'))  # the first shot follows its words too
        self.assertEqual([(b['visual'], b['who']) for b in s['scenes']], [('person', 'mother'), ('kid', 'none'), ('kid', 'none')])

    def test_at_least_half_the_lines_show_a_character(self):
        raw = copy()
        raw['lines'] = [self.line(visual=v, visual_text='4 साल') for v in ('calendar', 'money', 'clock')]
        raw['punchline'] = self.line(visual='result', visual_text='2/100')
        s = comic.clean(raw)
        visuals = [s['hook_visual'], *(b['visual'] for b in s['scenes']), s['punch_visual']]
        self.assertGreaterEqual(sum(v not in comic.CUTAWAYS for v in visuals) * 2, len(visuals))
        self.assertEqual(s['scenes'][0]['visual'], 'calendar')  # the first cutaways stay

    def test_build_passes_the_visuals(self):
        with tempfile.TemporaryDirectory() as tmp:
            props, _ = build.build(comic.clean(SAMPLE), Path(tmp) / 'o', Path(tmp) / 'p', narrate=False, music=False)
        punch = props['segments'][-2]
        self.assertEqual((punch['visual'], punch['screen'], punch['visual_text']), ('screen', 'music', 'गाना.mp3'))
        self.assertEqual(props['segments'][1]['who'], 'teacher')

    def test_every_visual_screen_and_person_is_drawn(self):
        cut = (COMIC / 'cutaways.tsx').read_text(encoding='utf-8')
        self.assertLessEqual(set(comic.CUTAWAYS), set(re.findall(r'case "(\w+)"', cut)))
        for name in comic.SCREENS:
            self.assertRegex(cut, rf'\n  {name}: \{{ title', name)
        reel = (COMIC / 'ComicReel.tsx').read_text(encoding='utf-8')
        kid = (COMIC / 'Kid.tsx').read_text(encoding='utf-8')
        self.assertEqual(set(comic.VISUALS), set(comic.CUTAWAYS) | {'kid', 'person', 'dream'})
        for who in comic.PEOPLE:
            self.assertRegex(kid, rf'\n  {who}: \{{ \.\.\.', who)
            self.assertIn(f'{who}: "', reel)  # the room they are found in
        sounds_used = set(re.findall(r'\[\d+, "([a-z_]+)", [0-9.]+\]', cut))
        self.assertTrue(sounds_used)
        self.assertLessEqual(sounds_used, set(sounds.effects()))


class WhisperRetryTest(unittest.TestCase):
    def test_listens_again_without_the_hint_when_most_words_are_missed(self):
        import sys
        import types
        prompts = []

        class Model:
            def __init__(self, *a, **k):
                pass

            def transcribe(self, audio, initial_prompt=None, **k):
                prompts.append(initial_prompt)
                n = 1 if initial_prompt else 9
                word = types.SimpleNamespace(start=0.0, end=0.1)
                return [types.SimpleNamespace(words=[word] * n)], None
        fake = types.ModuleType('faster_whisper')
        fake.WhisperModel = Model
        with mock.patch.dict(sys.modules, {'faster_whisper': fake}), \
                mock.patch.object(voice.subprocess, 'run', return_value=types.SimpleNamespace(stdout=b'\x00' * 64)):
            heard = voice.heard_words(Path('v.wav'), 'एक दो तीन चार पाँच छह सात आठ नौ दस')
        self.assertEqual(len(heard), 9)
        self.assertEqual(prompts, ['एक दो तीन चार पाँच छह सात आठ नौ दस', None])


class PlacesTest(unittest.TestCase):
    line = VisualsTest.line

    def test_each_line_has_its_own_place(self):
        raw = copy(place='gym')
        raw['lines'] = [self.line(place='street'), self.line(place='moon')]
        s = comic.clean(raw)
        self.assertEqual([b['place'] for b in s['scenes']], ['street', 'gym'])  # unknown -> the Reel's place
        self.assertEqual(s['hook_place'], 'bedroom')  # the sample's setup says bedroom
        with tempfile.TemporaryDirectory() as tmp:
            props, _ = build.build(s, Path(tmp) / 'o', Path(tmp) / 'p', narrate=False, music=False)
        self.assertEqual([seg.get('place') for seg in props['segments'][:3]], ['bedroom', 'street', 'gym'])
