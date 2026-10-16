import json
import unittest
from pathlib import Path

from reel import publish, script, telegram

ROOT = Path(__file__).resolve().parents[1]
STORY = script.clean(json.loads((ROOT / 'examples' / 'sample.json').read_text(encoding='utf-8')))


def rows(markup):
    return json.loads(markup)['inline_keyboard']


class CopyButtonsTest(unittest.TestCase):
    def test_caption_and_hashtags_are_separate(self):
        copy = publish.copy_texts(STORY)
        self.assertTrue(copy['caption'].startswith(STORY['title']))
        self.assertIn(STORY['ask'], copy['caption'])
        self.assertNotIn('#', copy['caption'])
        self.assertTrue(copy['hashtags'].startswith('#hindikahani #lifelessons #seekhsketch'))
        self.assertEqual(copy['hashtags'].count('#lifelessons'), 1)  # no repeats

    def test_one_button_copies_caption_and_hashtags(self):
        copy = publish.copy_texts(STORY)
        keys = rows(telegram.review_buttons('99', '2', copy))
        self.assertEqual([b['text'] for b in keys[-1]], ['📋 Copy caption + hashtags'])
        self.assertEqual(keys[-1][0]['copy_text']['text'], copy['caption'] + '\n\n' + copy['hashtags'])
        self.assertEqual(keys[0][0]['callback_data'], 'post:99:2')

    def test_auto_post_keeps_only_copy(self):
        keys = rows(telegram.review_buttons('99', '1', publish.copy_texts(STORY), actions=False))
        self.assertEqual(len(keys), 1)
        self.assertEqual(len(keys[0]), 1)
        self.assertIn('copy_text', keys[0][0])

    def test_long_caption_gets_one_tap_to_copy_block(self):
        copy = {'caption': 'शब्द ' * 50, 'hashtags': '#a #b'}
        self.assertIsNone(telegram.review_buttons('', '1', copy))  # too long for a button, no other buttons
        message = telegram.copy_message(copy)
        self.assertEqual(message.count('<pre>'), 1)
        self.assertIn('\n\n#a #b</pre>', message)
        self.assertIsNone(telegram.copy_message(publish.copy_texts(STORY)))  # short captions need no extra message

    def test_html_is_escaped(self):
        message = telegram.copy_message({'caption': '<b>' + 'x' * 300, 'hashtags': '#a'})
        self.assertIn('&lt;b&gt;', message)


if __name__ == '__main__':
    unittest.main()
