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
