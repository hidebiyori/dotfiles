import subprocess
import unittest

import test_git_p as git_p_tests


ROOT = git_p_tests.ROOT


class GitUntrackedAliasTests(unittest.TestCase):
    def setUp(self):
        self.fixture = git_p_tests.GitPullAliasTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.checkout = self.fixture.checkout
        self.environment = self.fixture.environment
        (self.fixture.home / "bin/git-ua").symlink_to(ROOT / "src/bin/git-ua")
        alias = self.fixture.git("config", "--file", ROOT / "src/.config/git/config", "--get", "alias.ua")
        self.git("config", "alias.ua", alias)

    def git(self, *arguments):
        return self.fixture.git("-C", self.checkout, *arguments)

    def run_alias(self, cwd=None):
        return subprocess.run(
            ["git", "ua"], cwd=cwd or self.checkout, env=self.environment,
            text=True, capture_output=True,
        )

    def staged_names(self):
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "-z"],
            cwd=self.checkout, env=self.environment, text=True, capture_output=True, check=True,
        )
        return result.stdout.removesuffix("\0").split("\0") if result.stdout else []

    def test_names_with_spaces_quotes_backslashes_newlines_and_unicode_are_added(self):
        names = ["a b.txt", "quote'\".txt", "back\\slash.txt", "line\nbreak.txt", "日本語.txt"]
        for name in names:
            (self.checkout / name).write_text("new file\n")
        result = self.run_alias()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(set(self.staged_names()), set(names))

    def test_option_like_name_does_not_stage_tracked_modifications_or_deletions(self):
        (self.checkout / "deleted").write_text("keep in index\n")
        self.git("add", "deleted")
        self.git("commit", "-m", "Track fixture file")
        (self.checkout / "deleted").unlink()
        (self.checkout / "tracked").write_text("unstaged work\n")
        (self.checkout / "--all").write_text("new file\n")
        result = self.run_alias()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.staged_names(), ["--all"])
        self.assertEqual(self.git("show", ":tracked"), "initial")
        self.assertEqual(self.git("show", ":deleted"), "keep in index")

    def test_pathspec_magic_and_wildcards_are_literal_file_names(self):
        (self.checkout / "tracked").write_text("unstaged work\n")
        names = [":(top)**", "*.txt", "[abc].txt"]
        for name in names:
            (self.checkout / name).write_text("new file\n")
        result = self.run_alias()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(set(self.staged_names()), set(names))
        self.assertEqual(self.git("show", ":tracked"), "initial")

    def test_ignored_files_and_existing_index_contents_are_preserved(self):
        (self.checkout / ".gitignore").write_text("*.ignored\n")
        self.git("add", ".gitignore")
        self.git("commit", "-m", "Ignore fixture files")
        (self.checkout / "tracked").write_text("staged work\n")
        self.git("add", "tracked")
        (self.checkout / "tracked").write_text("unstaged work\n")
        (self.checkout / "new").write_text("new file\n")
        (self.checkout / "private.ignored").write_text("ignored fixture\n")
        result = self.run_alias()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.staged_names(), ["new", "tracked"])
        self.assertEqual(self.git("show", ":tracked"), "staged work")

    def test_empty_untracked_list_succeeds_without_staging_tracked_work(self):
        (self.checkout / "tracked").write_text("unstaged work\n")
        result = self.run_alias()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.staged_names(), [])
        self.assertEqual(self.git("show", ":tracked"), "initial")

    def test_invocation_from_a_subdirectory_still_adds_repository_untracked_files(self):
        nested = self.checkout / "nested"
        nested.mkdir()
        (self.checkout / "root file").write_text("new file\n")
        (nested / "nested file").write_text("new file\n")
        result = self.run_alias(cwd=nested)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.staged_names(), ["nested/nested file", "root file"])


if __name__ == "__main__":
    unittest.main()
