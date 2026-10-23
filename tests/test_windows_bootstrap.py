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
INSTALLER = '''function main() { echo installer >> "$TEST_LOG"; }
if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  echo unexpected-bootstrap >> "$TEST_LOG"
  exit 99
fi
'''


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
  cat > "$3/bin/install.sh" <<'INSTALLER'
@@INSTALLER@@
INSTALLER
elif [[ "$*" == *'status --porcelain' ]]; then
  if [[ "${TEST_STATUS_FAIL:-0}" == 1 ]]; then exit 3; fi
  printf '%s' "${TEST_DIRTY:-}"
elif [[ "$*" == *'branch --show-current' ]]; then
  echo "${TEST_BRANCH:-main}"
elif [[ "$*" == *'config --get-all remote.origin.url' ]]; then
  if [[ "${TEST_ORIGIN_FAIL:-0}" == 1 ]]; then exit 7; fi
  printf '%s\\n' "${TEST_ORIGIN-https://github.com/hidebiyori/dotfiles.git}"
elif [[ "$*" == *'config --get remote.origin.url' ]]; then
  origins="${TEST_ORIGIN-https://github.com/hidebiyori/dotfiles.git}"
  printf '%s\\n' "${origins##*$'\\n'}"
elif [[ "$*" == *'config --get branch.main.remote' ]]; then
  echo "${TEST_UPSTREAM_REMOTE-origin}"
elif [[ "$*" == *'config --get-all branch.main.merge' ]]; then
  printf '%s\\n' "${TEST_UPSTREAM_REF-refs/heads/main}"
elif [[ "$*" == *'pull --ff-only'* ]]; then
  exit "${TEST_PULL_EXIT:-0}"
fi
'''.replace('@@INSTALLER@@', INSTALLER))

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
        (repository / "bin/install.sh").write_text(INSTALLER)
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

    def test_first_clone_followed_by_repeated_bootstraps_reuses_the_checkout(self):
        for _ in range(3):
            result = self.run_bootstrap()
            self.assertEqual(result.returncode, 0, result.stderr)
        calls = self.log.read_text().splitlines()
        self.assertEqual(sum("git clone " in call for call in calls), 1)
        self.assertEqual(sum("pull --ff-only origin main" in call for call in calls), 2)
        self.assertEqual(calls.count("installer"), 3)

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

    def test_missing_or_multiple_origin_urls_stop_before_changes(self):
        self.existing_checkout()
        public = "https://github.com/hidebiyori/dotfiles.git"
        foreign = "https://example.invalid/unrelated.git"
        sentinel = "synthetic-multiple-origin-credential"
        cases = (
            ("read failure", {"TEST_ORIGIN_FAIL": "1"}),
            ("empty", {"TEST_ORIGIN": ""}),
            ("foreign first", {"TEST_ORIGIN": foreign + "\n" + public}),
            ("foreign last", {"TEST_ORIGIN": public + "\n" + foreign}),
            ("duplicate", {"TEST_ORIGIN": public + "\n" + public}),
            ("trailing empty", {"TEST_ORIGIN": public + "\n"}),
            ("leading empty", {"TEST_ORIGIN": "\n" + public}),
            ("credentials first", {"TEST_ORIGIN": public + "?token=" + sentinel + "\n" + public}),
        )
        for label, overrides in cases:
            with self.subTest(kind=label):
                self.log.unlink(missing_ok=True)
                result = self.run_bootstrap(**overrides)
                self.assertNotEqual(result.returncode, 0)
                calls = self.log.read_text()
                for forbidden in ("remote set-url", "pull ", "installer"):
                    self.assertNotIn(forbidden, calls)
                self.assertNotIn(sentinel, result.stdout + result.stderr + calls)

    def test_origin_cases_match_the_shared_identity_check(self):
        self.existing_checkout()
        cases = [
            ("https", "https://github.com/hidebiyori/dotfiles.git", True),
            ("https without suffix", "https://github.com/hidebiyori/dotfiles", True),
            ("scp ssh", "git@github.com:hidebiyori/dotfiles.git", True),
            ("scp without suffix", "git@github.com:hidebiyori/dotfiles", True),
            ("ssh url", "ssh://git@github.com/hidebiyori/dotfiles.git", True),
            ("ssh without suffix", "ssh://git@github.com/hidebiyori/dotfiles", True),
            ("at in foreign path", "https://example.invalid/a@github.com/hidebiyori/dotfiles.git", False),
            ("github as username", "https://github.com@example.invalid/hidebiyori/dotfiles.git", False),
            ("other repository", "https://github.com/another/dotfiles.git", False),
            ("other host", "https://example.invalid/hidebiyori/dotfiles.git", False),
            ("empty origin", "", False),
        ]
        for label, origin, expected in cases:
            with self.subTest(kind=label):
                self.log.unlink(missing_ok=True)
                shared = subprocess.run(
                    ["bash", "--noprofile", "--norc", "-c",
                     'source "$1"; [[ "$(gitRepositoryIdentity "${2:-missing}")" == https://github.com/hidebiyori/dotfiles ]]',
                     "bash", str(ROOT / "lib/install/common.sh"), origin],
                    env=self.environment, text=True, capture_output=True,
                )
                bootstrap = self.run_bootstrap(TEST_ORIGIN=origin)
                self.assertEqual((shared.returncode == 0, bootstrap.returncode == 0), (expected, expected))
                calls = self.log.read_text()
                if not expected:
                    for forbidden in ("remote set-url", "pull ", "installer"):
                        self.assertNotIn(forbidden, calls)

    def test_other_missing_or_multiple_upstreams_stop_before_changes(self):
        self.existing_checkout()
        for overrides in ({"TEST_UPSTREAM_REMOTE": "foreign"}, {"TEST_UPSTREAM_REMOTE": ""},
                          {"TEST_UPSTREAM_REF": ""}, {"TEST_UPSTREAM_REF": "refs/heads/other"},
                          {"TEST_UPSTREAM_REF": "refs/heads/main\nrefs/heads/other"}):
            with self.subTest(settings=overrides):
                self.log.unlink(missing_ok=True)
                result = self.run_bootstrap(**overrides)
                self.assertNotEqual(result.returncode, 0)
                for forbidden in ("remote set-url", "pull ", "installer"):
                    self.assertNotIn(forbidden, self.log.read_text())

    def test_failed_pull_stops_before_installer(self):
        self.existing_checkout()
        result = self.run_bootstrap(TEST_PULL_EXIT="17")
        self.assertEqual(result.returncode, 17)
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
