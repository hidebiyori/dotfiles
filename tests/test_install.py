import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "bin/install.sh"
PUBLIC_URL = "https://github.com/hidebiyori/dotfiles.git"


class InstallerTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="dotfiles install ")
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)
        self.bin = self.home / "commands"
        self.bin.mkdir()
        self.log = self.home / "commands.log"
        self.env = {
            **os.environ,
            "HOME": str(self.home),
            "PATH": str(self.bin) + os.pathsep + os.environ["PATH"],
            "TEST_LOG": str(self.log),
        }

    def command(self, name, contents):
        path = self.bin / name
        path.write_text("#!/bin/bash\n" + contents)
        path.chmod(0o755)

    def run_bash(self, body, trace=False, extra_env=None):
        return subprocess.run(
            ["bash", *( ["-x"] if trace else []), "-c",
             "source " + shlex.quote(str(INSTALLER)) + "\n" + body],
            env={**self.env, **(extra_env or {})},
            text=True,
            capture_output=True,
            check=True,
        )

    def git_stub(self):
        self.command("git", '''printf '%s\\n' "$*" >> "$TEST_LOG"
if [[ "$*" == *"config --get remote.origin.url" ]]; then
  printf '%s\\n' "${TEST_ORIGIN_URL:-}"
fi
''')

    def test_clone_ignores_token_and_disables_inherited_tracing(self):
        self.git_stub()
        sentinel = "synthetic-test-credential"
        result = self.run_bash('setOptions; setGitRepository "$PJ_URL"', trace=True,
                               extra_env={"GH_TOKEN": sentinel})
        self.assertIn("clone " + PUBLIC_URL, self.log.read_text())
        self.assertNotIn(sentinel, result.stdout + result.stderr + self.log.read_text())

    def test_legacy_origin_authentication_is_removed_before_pull(self):
        self.git_stub()
        (self.home / "git/dotfiles").mkdir(parents=True)
        for legacy in (
            "https://synthetic-test-credential@github.com/hidebiyori/dotfiles.git",
            PUBLIC_URL + "?token=synthetic-test-credential#fragment",
        ):
            with self.subTest(kind="userinfo" if "@" in legacy else "query"):
                self.log.unlink(missing_ok=True)
                result = self.run_bash('setOptions; setGitRepository "$PJ_URL"', trace=True,
                                       extra_env={"TEST_ORIGIN_URL": legacy})
                calls = self.log.read_text()
                self.assertLess(calls.index("remote set-url origin " + PUBLIC_URL),
                                calls.index(" pull"))
                self.assertNotIn("synthetic-test-credential", result.stdout + result.stderr + calls)

    def test_ssh_origin_is_preserved(self):
        self.git_stub()
        (self.home / "git/dotfiles").mkdir(parents=True)
        self.run_bash('setOptions; setGitRepository "$PJ_URL"', extra_env={
            "TEST_ORIGIN_URL": "git@github.com:hidebiyori/dotfiles.git",
        })
        self.assertNotIn("set-url", self.log.read_text())
        self.assertIn(" pull", self.log.read_text())


if __name__ == "__main__":
    unittest.main()
