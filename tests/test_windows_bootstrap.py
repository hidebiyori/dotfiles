import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "bin/install-windows.ps1").read_text()
BOOTSTRAP = re.search(
    r"function Get-LinuxBootstrapScript \{\n    @'\n(.*?)\n'@\n\}", SOURCE, re.S
).group(1)


class WindowsLinuxBootstrapTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="windows bootstrap ")
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)
        self.bin = self.home / "commands"
        self.bin.mkdir()
        self.log = self.home / "calls.log"
        self.environment = {
            **os.environ,
            "HOME": str(self.home),
            "PATH": str(self.bin) + os.pathsep + os.environ["PATH"],
            "TEST_LOG": str(self.log),
        }
        self.environment.pop("BASH_ENV", None)
        self.command("id", "echo 1000\n")
        self.command("sudo", 'echo "Unexpected sudo" >&2\nexit 99\n')
        self.command("git", '''printf '%s\\n' "git $*" >> "$TEST_LOG"
if [[ "$1" == clone ]]; then
  mkdir -p "$3/.git" "$3/bin"
  printf '%s\\n' 'echo installer >> "$TEST_LOG"' > "$3/bin/install.sh"
elif [[ "$*" == *'status --porcelain' ]]; then
  if [[ "${TEST_STATUS_FAIL:-0}" == 1 ]]; then exit 3; fi
  printf '%s' "${TEST_DIRTY:-}"
elif [[ "$*" == *'branch --show-current' ]]; then
  echo "${TEST_BRANCH:-main}"
elif [[ "$*" == *'config --get remote.origin.url' ]]; then
  echo "${TEST_ORIGIN:-https://github.com/hidebiyori/dotfiles.git}"
fi
''')

    def command(self, name, body):
        destination = self.bin / name
        destination.write_text("#!/bin/bash\n" + body)
        destination.chmod(0o755)

    def run_bootstrap(self, **environment):
        return subprocess.run(
            ["bash", "--noprofile", "--norc", "-c", BOOTSTRAP],
            env={**self.environment, **environment}, cwd=self.home,
            text=True, capture_output=True,
        )

    def existing_checkout(self):
        repository = self.home / "git/dotfiles"
        (repository / ".git").mkdir(parents=True)
        (repository / "bin").mkdir()
        (repository / "bin/install.sh").write_text('echo installer >> "$TEST_LOG"\n')
        return repository

    def test_first_clone_is_in_linux_home_and_hands_off_to_installer(self):
        result = self.run_bootstrap()
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = self.log.read_text()
        self.assertIn("clone https://github.com/hidebiyori/dotfiles.git " + str(self.home / "git/dotfiles"), calls)
        self.assertIn("installer", calls)
        self.assertNotIn("/mnt/c", calls)

    def test_existing_main_checkout_is_updated_without_another_clone(self):
        self.existing_checkout()
        result = self.run_bootstrap()
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = self.log.read_text()
        self.assertIn("pull --ff-only origin main", calls)
        self.assertIn("installer", calls)
        self.assertNotIn("clone ", calls)

    def test_existing_non_repository_is_preserved(self):
        repository = self.home / "git/dotfiles"
        repository.mkdir(parents=True)
        marker = repository / "keep.txt"
        marker.write_text("keep")
        result = self.run_bootstrap()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(marker.read_text(), "keep")
        self.assertNotIn("installer", self.log.read_text() if self.log.exists() else "")

    def test_dirty_or_other_branch_checkouts_are_not_updated(self):
        self.existing_checkout()
        for environment in ({"TEST_DIRTY": " M README.md"}, {"TEST_BRANCH": "feature"}):
            with self.subTest(environment=environment):
                self.log.unlink(missing_ok=True)
                result = self.run_bootstrap(**environment)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("pull ", self.log.read_text())
                self.assertNotIn("installer", self.log.read_text())

    def test_unrelated_origin_is_not_executed(self):
        self.existing_checkout()
        result = self.run_bootstrap(TEST_ORIGIN="https://example.invalid/unrelated.git")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("pull ", self.log.read_text())
        self.assertNotIn("installer", self.log.read_text())

    def test_failed_checkout_status_stops_before_pull_or_install(self):
        self.existing_checkout()
        result = self.run_bootstrap(TEST_STATUS_FAIL="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("pull ", self.log.read_text())
        self.assertNotIn("installer", self.log.read_text())

    def test_legacy_origin_credentials_are_not_logged(self):
        self.existing_checkout()
        sentinel = "synthetic-bootstrap-credential"
        result = self.run_bootstrap(
            TEST_ORIGIN=f"https://{sentinel}@github.com/hidebiyori/dotfiles.git?token={sentinel}"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn(sentinel, result.stdout + result.stderr + self.log.read_text())
        self.assertIn("remote set-url origin https://github.com/hidebiyori/dotfiles.git", self.log.read_text())

    def test_root_does_not_clone_or_install(self):
        self.command("id", "echo 0\n")
        result = self.run_bootstrap()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.log.exists())
        self.assertFalse((self.home / "git").exists())

    def test_embedded_script_has_valid_bash_syntax(self):
        result = subprocess.run(["bash", "-n"], input=BOOTSTRAP, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
