import unittest

import numpy as np

from reel import scan


class ScanTest(unittest.TestCase):
    def test_black_frame_is_found_unless_planned(self):
        y = np.random.default_rng(1).uniform(0.45, 0.55, (60, 16, 9)).astype(np.float32)
        y[30] = 0
        self.assertTrue(any('black' in p for p in scan.problems(y)))
        self.assertFalse(any('black' in p for p in scan.problems(y, planned=[30])))

    def test_a_stuck_picture_is_frozen(self):
        y = np.random.default_rng(2).uniform(0.4, 0.6, (60, 16, 9)).astype(np.float32)
        y[20:40] = y[20]
        self.assertTrue(any('frozen' in p for p in scan.problems(y)))

    def test_comic_cuts_follow_words(self):
        props = {'style': 'comic', 'segments': [{'kind': 'scene', 'start': 0, 'end': 6, 'words': [0, 1, 2.1, 4.2, 5.5]}]}
        self.assertEqual(scan.planned_cuts(props), [0, 63, 126])

    def test_story_scenes_cut_at_the_middle_word(self):
        props = {'segments': [{'kind': 'scene', 'start': 0, 'end': 4, 'words': [0, 0.5, 1.9, 2.6, 3.4]}]}
        self.assertEqual(scan.planned_cuts(props), [0, 57])


if __name__ == '__main__':
    unittest.main()
