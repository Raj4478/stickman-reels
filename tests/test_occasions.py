import datetime as dt
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from reel import occasions, publish, script
from reel.__main__ import main

D = dt.date


class OccasionTest(unittest.TestCase):
    def test_floating_days(self):
        days = occasions.dates(2027)
        self.assertEqual(days['mothers_day'], D(2027, 5, 9))      # 2nd Sunday of May
        self.assertEqual(days['fathers_day'], D(2027, 6, 20))     # 3rd Sunday of June
        self.assertEqual(occasions.dates(2026)['friendship_day'], D(2026, 8, 2))  # 1st Sunday of August
        self.assertEqual(days['diwali'], D(2027, 10, 29))

    def test_due_a_few_days_ahead_once(self):
        self.assertIsNone(occasions.due(D(2026, 10, 16)))  # Dussehra is 4 days away
        due = occasions.due(D(2026, 10, 17))
        self.assertEqual((due['key'], due['days'], due['tag']), ('dussehra', 3, 'dussehra-2026'))
        self.assertIsNone(occasions.due(D(2026, 10, 18), [{'occasion': 'dussehra-2026'}]))  # already made
        self.assertEqual(occasions.due(D(2026, 11, 6))['key'], 'diwali')

    def test_new_year_across_the_year_end(self):
        self.assertEqual(occasions.due(D(2026, 12, 30))['key'], 'new_year')

    def test_seasons_once_a_week(self):
        first = occasions.due(D(2027, 2, 20))
        self.assertEqual(first['key'], 'board_exams')
        made = [{'occasion': first['tag'], 'made': '2027-02-20'}]
        self.assertIsNone(occasions.due(D(2027, 2, 24), made))
        self.assertEqual(occasions.due(D(2027, 2, 28), made)['key'], 'board_exams')

    def test_switch_off(self):
        with mock.patch.dict(os.environ, {'OCCASIONS': 'off'}):
            self.assertIsNone(occasions.due(D(2026, 10, 17)))

    def test_note_keeps_it_secular(self):
        text = occasions.note({'name': 'दिवाली', 'days': 2})
        self.assertIn('in 2 days', text)
        self.assertIn('no religious', text)

    def test_every_occasion_has_words(self):
        keys = set(occasions.FIXED) | set(occasions.FLOATING) | set(occasions.FESTIVALS) | set(occasions.SEASONS)
        self.assertLessEqual(keys, set(occasions.OCCASIONS))

    def test_remembered_with_the_story(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {'REEL_HISTORY': str(Path(tmp) / 'h.json')}):
            script.remember({'topic': 't', 'title': 'x', 'occasion': 'diwali-2026'})
            self.assertEqual(script.history()[-1]['occasion'], 'diwali-2026')
            self.assertIsNone(occasions.due(D(2026, 11, 6), script.history()))


class YouTubeCheckTest(unittest.TestCase):
    ENV = {'YOUTUBE_CLIENT_ID': 'a', 'YOUTUBE_CLIENT_SECRET': 'b', 'YOUTUBE_REFRESH_TOKEN': 'old'}

    def answers(self, token):
        def fake(url, data=None, headers=None, method=None, timeout=120):
            if 'oauth2' in url:
                return token, {}
            return {'items': [{'snippet': {'title': 'Stickman Seekh'}}]}, {}
        return fake

    def test_rotated_token_is_written_for_saving(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {**self.ENV, 'TOKEN_FILE': str(Path(tmp) / 't')}), \
                mock.patch.object(publish, 'request', self.answers({'access_token': 'x', 'refresh_token': 'new'})):
            self.assertEqual(main(['youtube-check']), 2)
            self.assertEqual((Path(tmp) / 't').read_text(), 'new')

    def test_testing_app_warns_before_it_ends(self):
        sent = []
        with mock.patch.dict(os.environ, self.ENV), mock.patch('reel.telegram.send_message', sent.append), \
                mock.patch.object(publish, 'request', self.answers({'access_token': 'x', 'refresh_token_expires_in': 2 * 86400})):
            self.assertEqual(main(['youtube-check']), 0)
        self.assertIn('ends in 2 day', sent[0])
        self.assertIn('Publish app', sent[0])

    def test_healthy_sign_in_is_quiet(self):
        sent = []
        with mock.patch.dict(os.environ, self.ENV), mock.patch('reel.telegram.send_message', sent.append), \
                mock.patch.object(publish, 'request', self.answers({'access_token': 'x'})):
            self.assertEqual(main(['youtube-check']), 0)
        self.assertEqual(sent, [])

    def test_broken_sign_in_alerts(self):
        sent = []
        with mock.patch.dict(os.environ, self.ENV), mock.patch('reel.telegram.send_message', sent.append), \
                mock.patch.object(publish, 'youtube_token', side_effect=publish.PublishError('revoked')):
            self.assertEqual(main(['youtube-check']), 1)
        self.assertIn('revoked', sent[0])


if __name__ == '__main__':
    unittest.main()
