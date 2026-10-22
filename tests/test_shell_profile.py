import os
from pathlib import Path
import subprocess
import tempfile
import unittest


PROFILE = Path(__file__).resolve().parents[1] / "src/.bash_profile"


class ShellProfileTests(unittest.TestCase):
    def test_profile_without_terminal_does_not_interrupt_commands(self):
        with tempfile.TemporaryDirectory(prefix="dotfiles profile ") as temporary:
            result = subprocess.run(
                ["bash", "--noprofile", "--norc", "-e", "-c",
                 'source "$1"; printf command-reached', "bash", str(PROFILE)],
                cwd=temporary, env={**os.environ, "HOME": temporary},
                stdin=subprocess.DEVNULL, capture_output=True, text=True,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "command-reached")
        self.assertEqual(result.stderr, "")


if __name__ == "__main__":
    unittest.main()
