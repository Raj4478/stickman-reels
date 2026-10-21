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
        raw['lines'] = [{'line': 'ये तो होना ही था।', 'face': 'laughing', 'gesture': 'dance', 'look': 'sky', 'speaker': 'other'}]
        s = comic.clean(raw)
        self.assertEqual((s['place'], s['emoji']), ('bedroom', 'sob'))
        self.assertEqual({k: s['scenes'][0][k] for k in ('face', 'gesture', 'look', 'speaker', 'with')},
                         {'face': 'deadpan', 'gesture': 'talk', 'look': 'viewer', 'speaker': 'narrator', 'with': 'none'})

    def test_only_one_off_screen_line(self):
        raw = copy()
        raw['lines'].append({'line': 'और सुन, दूध भी ले आना!', 'face': 'sad', 'gesture': 'talk', 'look': 'side', 'speaker': 'other'})
        s = comic.clean(raw)
        self.assertEqual(sum(b['speaker'] == 'other' for b in s['scenes']), 1)

    def test_english_punchline_or_empty_rant_is_rejected(self):
        with self.assertRaises(ValueError):
            comic.clean(copy(punchline={'line': 'only English here', 'face': 'smug', 'gesture': 'talk', 'look': 'viewer', 'speaker': 'hero'}))
        with self.assertRaises(ValueError):
            comic.clean(copy(lines=[{'line': 'no Hindi', 'face': 'sad', 'gesture': 'talk', 'look': 'viewer', 'speaker': 'hero'}]))

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
        self.assertIn('calling from another room', calls[1][0])
        self.assertEqual(calls[1][2], {'Narrator': 'Zubenelgenubi', 'Other': 'Sulafat'})
