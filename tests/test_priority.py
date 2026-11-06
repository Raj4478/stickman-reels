import io
import json
import os
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

from reel import gemini, voice

KEYS = {'GEMINI_API_KEY': 'k1', 'GEMINI_API_KEY_2': 'k2', 'GEMINI_API_KEY_3': '', 'GEMINI_MODEL': '', 'GEMINI_TTS_MODEL': ''}


def http(code, error=None):
    body = json.dumps({'error': error or {}}).encode()
    return urllib.error.HTTPError('https://x', code, 'err', {}, io.BytesIO(body))


def per_minute(seconds=20):
    return http(429, {'message': 'Resource exhausted', 'details': [{'@type': 'RetryInfo', 'retryDelay': f'{seconds}s'}]})


def per_day():
    return http(429, {'message': 'Quota exceeded', 'details': [{'violations': [{'quotaId': 'GenerateRequestsPerDayPerProjectPerModel'}]}]})


class GeminiFirstTest(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, KEYS)
        self.env.start()
        self.sleep = mock.patch('time.sleep')
        self.slept = self.sleep.start()

    def tearDown(self):
        self.sleep.stop()
        self.env.stop()

    def run_call(self, answers):
        calls = []

        def post(model, key, body, timeout=180):
            calls.append((model, key))
            answer = answers.pop(0)
            if isinstance(answer, Exception):
                raise answer
            return answer
        with mock.patch.object(gemini, 'post', post):
            result = gemini.call('speech', {})
        return result, calls

    def test_per_minute_limit_is_waited_out_on_the_same_key(self):
        (response, model), calls = self.run_call([per_minute(20), {'ok': 1}])
        self.assertEqual(calls, [(gemini.SPEECH_MODELS[0], 'k1')] * 2)
        self.slept.assert_called_once_with(21)
        self.assertEqual(model, gemini.SPEECH_MODELS[0])

    def test_daily_limit_moves_to_the_next_key_without_waiting(self):
        _, calls = self.run_call([per_day(), {'ok': 1}])
        self.assertEqual([k for _, k in calls], ['k1', 'k2'])
        self.slept.assert_not_called()

    def test_long_waits_are_not_worth_it(self):
        _, calls = self.run_call([per_minute(300), {'ok': 1}])
        self.assertEqual([k for _, k in calls], ['k1', 'k2'])
        self.slept.assert_not_called()

    def test_waits_only_once_per_key(self):
        _, calls = self.run_call([per_minute(5), per_minute(5), {'ok': 1}])
        self.assertEqual([k for _, k in calls], ['k1', 'k1', 'k2'])

    def test_outage_tries_the_next_key_then_model(self):
        _, calls = self.run_call([http(503), http(503), {'ok': 1}])
        self.assertEqual(calls, [(gemini.SPEECH_MODELS[0], 'k1'), (gemini.SPEECH_MODELS[0], 'k2'), (gemini.SPEECH_MODELS[1], 'k1')])

    def test_unsupported_request_skips_to_the_next_model(self):
        _, calls = self.run_call([http(400), {'ok': 1}])
        self.assertEqual(calls, [(gemini.SPEECH_MODELS[0], 'k1'), (gemini.SPEECH_MODELS[1], 'k1')])

    def test_everything_failing_hands_over_to_the_backup(self):
        with self.assertRaises(gemini.GeminiError):
            self.run_call([per_day()] * 4)


class VoiceOrderTest(unittest.TestCase):
    TURNS = [('narrator', 'एक'), ('other', 'दो'), ('hero', 'तीन')]

    def tearDown(self):
        gemini.USED.clear()

    def test_two_voice_failure_keeps_gemini_single_voice(self):
        tried = []

        def gemini_voice(turns, other, path, style='story', audience='adult'):
            tried.append([who for who, _ in turns])
            if any(who == 'other' for who, _ in turns):
                raise gemini.GeminiError('multi-speaker refused')
            return {'model': 'gemini-tts'}
        with mock.patch.object(voice, 'gemini_voice', gemini_voice), mock.patch.object(voice, 'edge_voice') as edge:
            record = voice.synthesize(self.TURNS, Path('.'))
        self.assertEqual(tried[1], ['narrator'] * 3)
        self.assertEqual(record['model'], 'gemini-tts')
        self.assertIn('one voice', record['dialogue'])
        edge.assert_not_called()
        self.assertEqual(gemini.USED, [])  # no backup was needed

    def test_edge_only_when_gemini_cannot_speak_at_all(self):
        with mock.patch.object(voice, 'gemini_voice', side_effect=gemini.GeminiError('quota')), \
                mock.patch.object(voice, 'edge_voice', return_value={'model': 'edge-tts'}) as edge:
            record = voice.synthesize(self.TURNS, Path('.'))
        self.assertEqual(record['model'], 'edge-tts')
        edge.assert_called_once()
        self.assertIn('Edge', gemini.USED[0]['service'])


if __name__ == '__main__':
    unittest.main()
