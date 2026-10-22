import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class GitPullAliasTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="dotfiles git p ")
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)
        self.environment = {
            **os.environ, "HOME": str(self.home),
            "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_ALLOW_PROTOCOL": "file",
            "GIT_AUTHOR_DATE": "2026-01-01T00:00:00+0000",
            "GIT_COMMITTER_DATE": "2026-01-01T00:00:00+0000",
        }
        self.environment.pop("BASH_ENV", None)
        (self.home / "bin").mkdir()
        (self.home / "bin/git-p").symlink_to(ROOT / "src/bin/git-p")
        self.origin = self.home / "origin.git"
        self.author = self.home / "author"
        self.checkout = self.home / "checkout"
        self.git("init", "--bare", "--initial-branch=main", self.origin)
        self.git("clone", self.origin, self.author)
        self.identity(self.author)
        (self.author / "tracked").write_text("initial\n")
        self.publish()
        self.git("clone", self.origin, self.checkout)
        self.identity(self.checkout)
        alias = self.git("config", "--file", ROOT / "src/.config/git/config", "--get", "alias.p")
        self.git("-C", self.checkout, "config", "alias.p", alias)

    def git(self, *arguments):
        return subprocess.run(
            ["git", *map(str, arguments)], env=self.environment,
            text=True, capture_output=True, check=True,
        ).stdout.strip()

    def identity(self, repository):
        self.git("-C", repository, "config", "user.name", "Fixture Author")
        self.git("-C", repository, "config", "user.email", "fixture@example.invalid")

    def publish(self):
        self.git("-C", self.author, "add", ".")
        self.git("-C", self.author, "commit", "-m", "Update fixture")
        self.git("-C", self.author, "push", "origin", "main")

    def run_alias(self):
        return subprocess.run(
            ["git", "p"], cwd=self.checkout, env=self.environment,
            text=True, capture_output=True,
        )

    def save_older_work(self):
        (self.checkout / "tracked").write_text("older saved work\n")
        self.git("-C", self.checkout, "stash", "push")
        return self.git("-C", self.checkout, "stash", "list", "--format=%H")

    def test_clean_checkout_does_not_apply_or_drop_an_older_stash(self):
        older = self.save_older_work()
        self.git("-C", self.checkout, "branch", "merged-fixture")
        result = self.run_alias()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.checkout / "tracked").read_text(), "initial\n")
        self.assertEqual(self.git("-C", self.checkout, "stash", "list", "--format=%H"), older)
        self.assertEqual(self.git("-C", self.checkout, "status", "--porcelain"), "")

    def test_current_staged_and_unstaged_work_is_restored_without_popping_older_stash(self):
        older = self.save_older_work()
        (self.checkout / "tracked").write_text("staged work\n")
        self.git("-C", self.checkout, "add", "tracked")
        (self.checkout / "tracked").write_text("unstaged work\n")
        result = self.run_alias()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.checkout / "tracked").read_text(), "unstaged work\n")
        self.assertEqual(self.git("-C", self.checkout, "show", ":tracked"), "staged work")
        self.assertEqual(self.git("-C", self.checkout, "stash", "list", "--format=%H"), older)

    def test_identical_saved_contents_are_still_recognized_as_new_work(self):
        older = self.save_older_work()
        (self.checkout / "tracked").write_text("older saved work\n")
        result = self.run_alias()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.checkout / "tracked").read_text(), "older saved work\n")
        self.assertEqual(self.git("-C", self.checkout, "stash", "list", "--format=%H"), older)

    def test_no_merged_branches_is_successful_and_updates_main(self):
        (self.author / "upstream").write_text("new content\n")
        self.publish()
        result = self.run_alias()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.checkout / "upstream").is_file())
        self.assertEqual(self.git("-C", self.checkout, "stash", "list"), "")

    def test_merged_branches_are_deleted_but_main_master_and_unmerged_work_are_kept(self):
        self.git("-C", self.checkout, "branch", "merged-fixture")
        self.git("-C", self.checkout, "branch", "master")
        self.git("-C", self.checkout, "branch", "--set-upstream-to=origin/main", "master")
        self.git("-C", self.checkout, "checkout", "-b", "unmerged-fixture")
        self.git("-C", self.checkout, "commit", "--allow-empty", "-m", "Unmerged work")
        result = self.run_alias()
        self.assertEqual(result.returncode, 0, result.stderr)
        branches = self.git("-C", self.checkout, "for-each-ref", "--format=%(refname:short)", "refs/heads").splitlines()
        self.assertEqual(branches, ["main", "master", "unmerged-fixture"])
        self.assertEqual(self.git("-C", self.checkout, "branch", "--show-current"), "master")

    def test_failed_pull_keeps_saved_work_and_does_not_delete_branches(self):
        (self.checkout / "tracked").write_text("current work\n")
        self.git("-C", self.checkout, "branch", "merged-fixture")
        self.git("-C", self.checkout, "remote", "set-url", "origin", self.home / "missing.git")
        result = self.run_alias()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("退避した作業は stash", result.stderr)
        self.assertEqual(self.git("-C", self.checkout, "show", "stash@{0}:tracked"), "current work")
        self.assertIn("merged-fixture", self.git("-C", self.checkout, "branch", "--list"))

    def test_restore_conflict_keeps_saved_work(self):
        (self.checkout / "tracked").write_text("local work\n")
        (self.author / "tracked").write_text("upstream work\n")
        self.publish()
        result = self.run_alias()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("退避した作業は stash", result.stderr)
        self.assertEqual(self.git("-C", self.checkout, "show", "stash@{0}:tracked"), "local work")


if __name__ == "__main__":
    unittest.main()
