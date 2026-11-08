import json
import re
import unittest
from pathlib import Path

from reel import comic

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'remotion' / 'src'


class ThreeEngineTest(unittest.TestCase):
    def test_every_comic_room_has_a_3d_version(self):
        rooms = set(re.findall(r'case "(\w+)"', (SRC / 'three' / 'rooms3d.tsx').read_text(encoding='utf-8')))
        self.assertLessEqual(set(comic.ROOMS), rooms)

    def test_remotion_packages_share_one_version(self):
        deps = json.loads((ROOT / 'remotion' / 'package.json').read_text(encoding='utf-8'))['dependencies']
        versions = {v for k, v in deps.items() if k == 'remotion' or k.startswith('@remotion/')}
        self.assertEqual(len(versions), 1, versions)

    def test_no_clock_or_random_in_the_3d_engine(self):
        for path in (SRC / 'three').glob('*.ts*'):
            text = path.read_text(encoding='utf-8')
            for banned in ('Math.random', 'useFrame(', 'new THREE.Clock', 'Date.now'):
                self.assertNotIn(banned, text, path.name)

    def test_every_3d_shot_is_a_known_name(self):
        camera = (SRC / 'three' / 'camera.ts').read_text(encoding='utf-8')
        shots = set(re.findall(r'\n  (\w+): \{ from: c3', camera))
        used = set(re.findall(r'return "(\w+)"', camera))
        used |= set(re.findall(r'"(\w+)"', camera.split('const ANGLES3 = ')[1].split(';')[0]))
        self.assertTrue(used)
        self.assertLessEqual(used, shots)


if __name__ == '__main__':
    unittest.main()
