import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from reel import publish, script

ROOT = Path(__file__).resolve().parents[1]
STORY = script.clean(json.loads((ROOT / 'examples' / 'sample.json').read_text(encoding='utf-8')))


class ReachTextsTest(unittest.TestCase):
    def test_title_puts_the_hook_first_and_stays_short(self):
        title = publish.texts(STORY)['title']
        self.assertTrue(title.startswith(STORY['title']))
        self.assertIn(publish.SEARCH_PHRASE, title)
        self.assertTrue(title.endswith('#shorts'))
        self.assertLessEqual(len(title), 70)

    def test_long_titles_are_cut_to_fit(self):
        title = publish.texts(dict(STORY, title='क' * 150))['title']
        self.assertLessEqual(len(title), 100)
        self.assertTrue(title.endswith('#shorts'))

    def test_description_opens_with_the_hook_and_invites_comments(self):
        with mock.patch.dict(os.environ, {'REEL_HANDLE': '@seekhsketch'}):
            description = publish.texts(STORY)['description']
        self.assertTrue(description.startswith(STORY['hook']))
        self.assertIn(STORY['ask'], description)
        self.assertIn('Subscribe करें @seekhsketch', description)
        last = description.splitlines()[-1].split()
        self.assertEqual(last[:3], publish.CHANNEL_TAGS)  # the three shown above the title
        self.assertLessEqual(len(last), 7)

    def test_hashtags_are_few_and_unique(self):
        tags = publish.hashtag_list(dict(STORY, hashtags=['#LifeLessons', '#life_lessons', '#a', '#b', '#c', '#d', '#e']))
        self.assertEqual(len(tags), 5)
        self.assertEqual(len({t.lower().replace('_', '') for t in tags}), 5)

    def test_upload_is_not_for_kids_and_not_synthetic(self):
        sent = {}

        def request(url, data=None, headers=None, method=None, timeout=120):
            if 'oauth2' in url:
                return {'access_token': 'x'}, {}
            if 'uploadType=resumable' in url:
                sent['body'] = data
                return {}, {'Location': 'https://upload'}
            return {'id': 'v1', 'status': {'privacyStatus': 'public'}}, {}
        env = {'YOUTUBE_CLIENT_ID': 'a', 'YOUTUBE_CLIENT_SECRET': 'b', 'YOUTUBE_REFRESH_TOKEN': 'c', 'YOUTUBE_PRIVACY': ''}
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, env), mock.patch.object(publish, 'request', request):
            video = Path(tmp) / 'v.mp4'
            video.write_bytes(b'mp4')
            result = publish.youtube_upload(video, STORY)
        status = sent['body']['status']
        self.assertIs(status['selfDeclaredMadeForKids'], False)
        self.assertIs(status['containsSyntheticMedia'], False)
        self.assertEqual(sent['body']['snippet']['defaultAudioLanguage'], 'hi')
        self.assertEqual(result['url'], 'https://youtube.com/shorts/v1')
        # only a Reel written for the kids audience is declared made for kids (family is general-audience)
        for audience, kids in (('kids', True), ('family', False), (None, False)):
            with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, env), mock.patch.object(publish, 'request', request):
                video = Path(tmp) / 'v.mp4'
                video.write_bytes(b'mp4')
                publish.youtube_upload(video, {**STORY, **({'audience': audience} if audience else {})})
            self.assertIs(sent['body']['status']['selfDeclaredMadeForKids'], kids, audience)


if __name__ == '__main__':
    unittest.main()
