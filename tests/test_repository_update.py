import os
from pathlib import Path
import subprocess
import tempfile
import unittest


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


if __name__ == "__main__":
    unittest.main()
