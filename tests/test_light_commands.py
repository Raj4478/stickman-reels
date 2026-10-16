import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Runs the command line with numpy (and Whisper, Edge) unavailable, like the light workflows on Actions.
BLOCK = "import sys; sys.modules.update(numpy=None, faster_whisper=None, edge_tts=None); "


class LightCommandsTest(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, '-c', BLOCK + "import runpy, sys; sys.argv = ['reel', *sys.argv[1:]]; "
                               "runpy.run_module('reel', run_name='__main__')", *args],
                              cwd=ROOT, capture_output=True, text=True, timeout=60, env={'PATH': '', 'SYSTEMROOT': 'C:\\Windows'})

    def test_posting_and_checks_need_no_numpy(self):
        for args in (['--help'], ['youtube-check'], ['report', '--help'], ['publish', '--help'], ['refresh-token', '--help'],
                     ['publish-queued', '--help'], ['ideas', '--help']):
            result = self.run_cli(*args)
            self.assertEqual(result.returncode, 0, (args, result.stderr[-500:]))


if __name__ == '__main__':
    unittest.main()
