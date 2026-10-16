import datetime as dt
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from reel import occasions, script, voice
from reel.__main__ import OPTIONS, parse_options

ROOT = Path(__file__).resolve().parents[1]


class OptionsTest(unittest.TestCase):
    def test_parse_keeps_only_known_choices(self):
        self.assertEqual(parse_options('theme=money voice=female music=off source=ideas bogus=1'),
                         {'theme': 'money', 'voice': 'female', 'music': 'off', 'source': 'ideas'})
        self.assertEqual(parse_options('theme=unknown voice=robot'), {})
        self.assertEqual(parse_options(''), {})

    def test_bot_themes_match(self):
        bot = (ROOT / 'bot' / 'src.js').read_text(encoding='utf-8')
        keys = re.findall(r"\['(\w+)', '[^']+'\]", bot.split('export const THEMES')[1].split(';')[0])
        self.assertEqual(keys, list(script.THEMES))
        self.assertEqual(OPTIONS['theme'], tuple(script.THEMES))


class TopicChoiceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {'REEL_HISTORY': str(Path(self.tmp.name) / 'history.json')})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def test_own_lesson_wins(self):
        self.assertEqual(script.choose_topic('समय', 'money', 'ideas'), ('समय', None))

    def test_theme(self):
        topic, occasion = script.choose_topic('', 'money')
        self.assertIn('money', topic)
        self.assertIsNone(occasion)

    def test_ideas_source(self):
        (Path(self.tmp.name) / 'ideas.json').write_text('["Listen to your parents"]', encoding='utf-8')
        self.assertEqual(script.choose_topic('', '', 'ideas')[0], 'Listen to your parents')

    def test_festival_source_finds_the_next_one(self):
        soon = occasions.upcoming_any(dt.date(2026, 10, 16))
        self.assertEqual((soon['key'], soon['days']), ('dussehra', 4))  # 4 days: too early for the automatic pick
        self.assertIsNone(occasions.due(dt.date(2026, 10, 16)))
        self.assertEqual(occasions.upcoming_any(dt.date(2026, 10, 16), [{'occasion': 'dussehra-2026'}])['key'], 'diwali')


class FirstPersonAndLoveTest(unittest.TestCase):
    def story(self, hook, *lines):
        return {'hook': hook, 'scenes': [{'line': line, 'speaker': 'narrator'} for line in lines]}

    def test_first_person(self):
        self.assertTrue(script.first_person(self.story('तीन साल मैंने उसके एक मैसेज का इंतज़ार किया।',
                                                       'मेरी क्लास में वो सबसे अलग थी।', 'वो हँस दी।')))
        self.assertFalse(script.first_person(self.story('राहुल ने तीन साल इंतज़ार किया।',
                                                        'उसकी क्लास में वो सबसे अलग थी।', 'वह चुप रहा।')))
        self.assertFalse(script.first_person(self.story('मैंनेजर ने बुलाया।', 'उसने देखा।')))  # a word that only starts like मैंने

    def test_hero_follows_the_voice(self):
        with mock.patch.dict(os.environ, {'NARRATOR': 'female'}):
            self.assertEqual(script.hero(), 'girl')
            self.assertEqual(voice.cast_voice('partner'), 'Orus')  # her partner is a young man
            self.assertEqual(voice.cast_voice('mother'), 'Sulafat')
        with mock.patch.dict(os.environ, {'NARRATOR': ''}):
            self.assertEqual(script.hero(), 'boy')
            self.assertEqual(voice.cast_voice('partner'), 'Despina')

    def test_love_is_first_and_frequent(self):
        self.assertEqual(next(iter(script.THEMES)), 'love')
        self.assertIn('propose', script.TWO_PERSON)
        self.assertIn('shy', script.ACTIONS)
        with mock.patch.dict(os.environ, {'LOVE_SHARE': '1'}):
            self.assertIn('love', script.choose_topic('', '', 'random')[0])
        with mock.patch.dict(os.environ, {'LOVE_SHARE': '0'}):
            self.assertNotIn('love:', script.choose_topic('', '', 'random')[0])


class NarratorTest(unittest.TestCase):
    def test_choice(self):
        with mock.patch.dict(os.environ, {'NARRATOR': 'female', 'REEL_VOICE': ''}):
            self.assertEqual(voice.narrator(), ('Sulafat', 'hi-IN-SwaraNeural'))
        with mock.patch.dict(os.environ, {'NARRATOR': '', 'REEL_VOICE': ''}):
            self.assertEqual(voice.narrator(), ('Achird', 'hi-IN-MadhurNeural'))
        with mock.patch.dict(os.environ, {'NARRATOR': 'female', 'REEL_VOICE': 'Kore'}):
            self.assertEqual(voice.narrator()[0], 'Kore')  # an explicit voice wins


if __name__ == '__main__':
    unittest.main()
