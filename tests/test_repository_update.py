import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import unittest

from test_windows_bootstrap import BOOTSTRAP


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_URL = "https://github.com/hidebiyori/dotfiles.git"


class RepositoryUpdateTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="dotfiles repository ")
        self.addCleanup(temporary.cleanup)
        self.scratch = Path(temporary.name)
        self.fixture_home = self.scratch / "home"
        self.fixture_home.mkdir()
        self.environment = {
            **os.environ, "HOME": str(self.fixture_home),
            "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_ALLOW_PROTOCOL": "file",
        }
        for name in ("BASH_ENV", "CODEX_HOME", "WSL_DISTRO_NAME", "WSL_INTEROP"):
            self.environment.pop(name, None)
        self.origin = self.scratch / "dotfiles.git"
        self.author = self.scratch / "author"
        self.checkout = self.fixture_home / "git/dotfiles"
        self.git("init", "--bare", "--initial-branch=main", self.origin)
        self.git("clone", self.origin, self.author)
        self.git("-C", self.author, "config", "user.name", "Fixture Author")
        self.git("-C", self.author, "config", "user.email", "fixture@example.invalid")

    def git(self, *arguments):
        return subprocess.run(
            ["git", *map(str, arguments)], env=self.environment,
            capture_output=True, text=True, check=True,
        ).stdout.strip()

    def publish(self):
        self.git("-C", self.author, "add", ".")
        self.git("-C", self.author, "commit", "-m", "Update fixture")
        self.git("-C", self.author, "push", "origin", "main")

    def create_checkout(self):
        (self.author / "marker").write_text("first")
        self.publish()
        self.checkout.parent.mkdir(parents=True)
        self.git("clone", self.origin, self.checkout)
        self.git("-C", self.checkout, "remote", "set-url", "origin", PUBLIC_URL)
        # Preserve the real public origin while all fetches stay local.
        self.git("-C", self.checkout, "config",
                 "url." + self.origin.as_uri() + ".insteadOf", PUBLIC_URL)

    def update_repository(self, target):
        return subprocess.run(
            ["bash", "--noprofile", "--norc", "-c",
             'source "$1"; setOptions; setGitRepository "$2" "$3"',
             "bash", str(ROOT / "lib/install/common.sh"), PUBLIC_URL, str(target)],
            env=self.environment, capture_output=True, text=True,
        )

    def test_different_origin_is_preserved_without_updating(self):
        self.create_checkout()
        foreign = self.scratch / "foreign.git"
        self.git("init", "--bare", foreign)
        self.git("-C", self.checkout, "remote", "set-url", "origin", foreign)
        result = self.update_repository(self.checkout)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("origin が想定したリポジトリと異なる", result.stderr)
        self.assertEqual(self.git("-C", self.checkout, "config", "--get", "remote.origin.url"), str(foreign))

    def test_missing_or_multiple_origin_urls_stop_before_changes(self):
        self.create_checkout()
        initial = self.git("-C", self.checkout, "rev-parse", "HEAD")
        foreign = self.scratch / "foreign.git"
        self.git("clone", "--bare", self.origin, foreign)
        self.git("-C", self.author, "remote", "add", "foreign", foreign)
        (self.author / "marker").write_text("foreign-only update")
        self.git("-C", self.author, "add", "marker")
        self.git("-C", self.author, "commit", "-m", "Foreign fixture update")
        self.git("-C", self.author, "push", "foreign", "main")
        sentinel = "synthetic-multiple-origin-credential"
        cases = (
            ("missing", ()),
            ("empty", ("",)),
            ("foreign first", (str(foreign), PUBLIC_URL)),
            ("foreign last", (PUBLIC_URL, str(foreign))),
            ("duplicate", (PUBLIC_URL, PUBLIC_URL)),
            ("trailing empty", (PUBLIC_URL, "")),
            ("leading empty", ("", PUBLIC_URL)),
            ("credentials first", (PUBLIC_URL + "?token=" + sentinel, PUBLIC_URL)),
        )
        for label, urls in cases:
            with self.subTest(kind=label):
                self.git("-C", self.checkout, "reset", "--hard", initial)
                fetch_head = self.checkout / ".git/FETCH_HEAD"
                fetch_head.unlink(missing_ok=True)
                self.git("-C", self.checkout, "config", "--replace-all", "remote.origin.url", PUBLIC_URL)
                self.git("-C", self.checkout, "config", "--unset-all", "remote.origin.url")
                for url in urls:
                    self.git("-C", self.checkout, "config", "--add", "remote.origin.url", url)
                configuration = (self.checkout / ".git/config").read_bytes()
                result = self.update_repository(self.checkout)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(self.git("-C", self.checkout, "rev-parse", "HEAD"), initial)
                self.assertEqual((self.checkout / "marker").read_text(), "first")
                self.assertEqual((self.checkout / ".git/config").read_bytes(), configuration)
                self.assertFalse(fetch_head.exists())
                self.assertNotIn(sentinel, result.stdout + result.stderr)

    def test_parent_repository_is_not_used_for_a_nested_directory(self):
        self.create_checkout()
        nested = self.checkout / "nested"
        nested.mkdir()
        result = self.update_repository(nested)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("チェックアウトのルートではありません", result.stderr)

    def test_hand_linked_checkout_can_update_without_replacing_the_link(self):
        self.create_checkout()
        linked = self.scratch / "manual link"
        linked.symlink_to(self.checkout, target_is_directory=True)
        inode = linked.lstat().st_ino
        (self.author / "marker").write_text("second")
        self.publish()
        result = self.update_repository(linked)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((linked / "marker").read_text(), "second")
        self.assertEqual(linked.lstat().st_ino, inode)

    def test_a_foreign_upstream_is_rejected_even_when_origin_is_expected(self):
        self.create_checkout()
        initial = self.git("-C", self.checkout, "rev-parse", "HEAD")
        foreign = self.scratch / "foreign.git"
        self.git("clone", "--bare", self.origin, foreign)
        self.git("-C", self.author, "remote", "add", "foreign", foreign)
        (self.author / "marker").write_text("foreign-only update")
        self.git("-C", self.author, "add", "marker")
        self.git("-C", self.author, "commit", "-m", "Foreign fixture update")
        self.git("-C", self.author, "push", "foreign", "main")
        self.git("-C", self.checkout, "remote", "add", "foreign", foreign)
        self.git("-C", self.checkout, "fetch", "foreign")
        self.git("-C", self.checkout, "branch", "--set-upstream-to=foreign/main", "main")
        result = self.update_repository(self.checkout)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("origin を追跡していない", result.stderr)
        self.assertEqual(self.git("-C", self.checkout, "rev-parse", "HEAD"), initial)
        self.assertEqual((self.checkout / "marker").read_text(), "first")
        self.assertEqual(self.git("-C", self.checkout, "config", "--get", "remote.origin.url"), PUBLIC_URL)

    def test_missing_or_local_upstream_does_not_update(self):
        self.create_checkout()
        (self.author / "marker").write_text("second")
        self.publish()
        for remote in (None, "."):
            with self.subTest(remote=remote):
                if remote is None:
                    self.git("-C", self.checkout, "config", "--unset", "branch.main.remote")
                else:
                    self.git("-C", self.checkout, "config", "branch.main.remote", remote)
                result = self.update_repository(self.checkout)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual((self.checkout / "marker").read_text(), "first")

    def test_detached_head_does_not_update(self):
        self.create_checkout()
        self.git("-C", self.checkout, "checkout", "--detach")
        result = self.update_repository(self.checkout)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("現在のブランチを確認できない", result.stderr)

    def test_missing_or_multiple_merge_refs_do_not_update(self):
        self.create_checkout()
        (self.author / "marker").write_text("second")
        self.publish()
        for refs in ([], ["refs/heads/main", "refs/heads/other"], ["refs/tags/release"]):
            with self.subTest(refs=refs):
                self.git("-C", self.checkout, "config", "--replace-all", "branch.main.merge", "refs/heads/main")
                self.git("-C", self.checkout, "config", "--unset-all", "branch.main.merge")
                for ref in refs:
                    self.git("-C", self.checkout, "config", "--add", "branch.main.merge", ref)
                result = self.update_repository(self.checkout)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual((self.checkout / "marker").read_text(), "first")

    def test_an_origin_branch_other_than_main_can_be_updated(self):
        self.create_checkout()
        self.git("-C", self.author, "checkout", "-b", "stable")
        self.git("-C", self.author, "push", "origin", "stable")
        self.git("-C", self.checkout, "fetch", "origin")
        self.git("-C", self.checkout, "checkout", "-b", "local-stable", "--track", "origin/stable")
        (self.author / "marker").write_text("stable update")
        self.git("-C", self.author, "add", "marker")
        self.git("-C", self.author, "commit", "-m", "Stable fixture update")
        self.git("-C", self.author, "push", "origin", "stable")
        result = self.update_repository(self.checkout)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.checkout / "marker").read_text(), "stable update")
        self.assertEqual(self.git("-C", self.checkout, "branch", "--show-current"), "local-stable")

    def assert_fetched_code_is_used(self, entrypoint, windows_bootstrap=False):
        shutil.copytree(ROOT / "lib", self.author / "lib")
        (self.author / "bin").mkdir()
        shutil.copy2(ROOT / "bin" / entrypoint, self.author / "bin" / entrypoint)
        (self.author / "src").mkdir()
        (self.author / "src/settings.txt").write_text("first settings")
        common = self.author / "lib/install/common.sh"
        common.write_text(common.read_text() + '''
function detectPlatform() { uname="Linux fixture"; }
function applyPlatformSettings() { printf '%s\\n' helper-v1; }
''')
        self.create_checkout()
        common.write_text(common.read_text().replace("helper-v1", "helper-v2"))
        fetched_entry = self.author / "bin" / entrypoint
        fetched_entry.write_text(fetched_entry.read_text() + '''
function main()
{
  setOptions
  detectPlatform
  syncConfiguration
  applyPlatformSettings
  printf '%s\\n' entry-v2
}
''')
        (self.author / "src/settings.txt").write_text("second settings")
        self.publish()

        commands = self.scratch / "commands"
        commands.mkdir()
        git_executable = shlex.quote(shutil.which("git"))
        (commands / "git").write_text('''#!/bin/bash
for argument in "$@"; do
  if [[ "$argument" == pull ]]; then printf '%s\\n' pull >> "$TEST_PULL_LOG"; break; fi
done
exec ''' + git_executable + ' "$@"\n')
        (commands / "id").write_text("#!/bin/bash\necho 1000\n")
        # A regression must never start a real package manager or download.
        for name in ("sudo", "brew", "mise", "curl", "fcitx-autostart", "fcitx-configtool"):
            (commands / name).write_text('#!/bin/bash\necho "Unexpected installer" >&2\nexit 99\n')
        for command in commands.iterdir():
            command.chmod(0o755)
        pull_log = self.scratch / "pull.log"
        result = subprocess.run(
            ["bash", "-c", BOOTSTRAP] if windows_bootstrap else ["bash", str(self.checkout / "bin" / entrypoint)],
            env={**self.environment, "PATH": str(commands) + os.pathsep + os.environ["PATH"],
                 "TEST_PULL_LOG": str(pull_log)},
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("entry-v2", result.stdout)
        self.assertIn("helper-v2", result.stdout)
        self.assertNotIn("helper-v1", result.stdout)
        self.assertEqual((self.fixture_home / "settings.txt").read_text(), "second settings")
        self.assertEqual(pull_log.read_text().splitlines(), ["pull"])

    def test_settings_update_uses_fetched_entrypoint_and_helpers_immediately(self):
        self.assert_fetched_code_is_used("update.sh")

    def test_upgrade_uses_fetched_entrypoint_and_helpers_immediately(self):
        self.assert_fetched_code_is_used("upgrade.sh")

    def test_setup_uses_fetched_entrypoint_and_helpers_immediately(self):
        self.assert_fetched_code_is_used("install.sh")

    def test_windows_bootstrap_uses_fetched_code_without_a_second_pull(self):
        self.assert_fetched_code_is_used("install.sh", windows_bootstrap=True)


if __name__ == "__main__":
    unittest.main()
