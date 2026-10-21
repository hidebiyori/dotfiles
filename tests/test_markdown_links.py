import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin/check-markdown-links.py"


class MarkdownLinkTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="markdown links ")
        self.addCleanup(temporary.cleanup)
        self.project = Path(temporary.name)
        subprocess.run(["git", "init", "-q", str(self.project)], check=True)

    def write(self, name, contents):
        path = self.project / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents, encoding="utf-8")
        subprocess.run(["git", "-C", str(self.project), "add", "--", name],
                       capture_output=True, check=True)

    def run_check(self, project=None):
        return subprocess.run(
            [sys.executable, "-B", str(SCRIPT), str(project or self.project)],
            capture_output=True, text=True, encoding="utf-8",
            env={**os.environ, "PYTHONIOENCODING": "utf-8"})

    def test_relative_inline_image_and_reference_links(self):
        self.write("docs/日本語 file(a).md", "# Target\n")
        self.write("README.md", (
            '[inline](docs/日本語%20file(a).md#target "Title")\n'
            '![image](<docs/日本語 file(a).md>)\n'
            '[named][a reference]\n[a reference][]\n[a reference]\n'
            '[A   Reference]: <docs/日本語 file(a).md>\n'))
        before = (self.project / "README.md").read_bytes()
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("相対リンク 5件", result.stdout)
        self.assertEqual((self.project / "README.md").read_bytes(), before)

    def test_code_comments_and_escaped_examples_are_ignored(self):
        self.write("README.md", (
            '`[inline](missing-inline)`\n'
            '```md\n[example](missing-fenced)\n```\n'
            '~~~md\n[example](missing-tilde)\n~~~\n'
            '``literal ` [example](missing-double)``\n'
            '<!-- [comment](missing-comment) -->\n'
            '\\[escaped](missing-escaped)\n'))
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("相対リンク 0件", result.stdout)

    def test_external_absolute_and_fragment_links_do_not_need_network(self):
        self.write("README.md", (
            '[web](https://example.invalid/a?token=private-fixture#fragment)\n'
            '[mail](mailto:nobody@example.invalid)\n'
            '[absolute](/unavailable/path)\n[anchor](#missing-heading)\n'))
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("相対リンク 0件", result.stdout)
        self.assertNotIn("private-fixture", result.stdout + result.stderr)

    def test_missing_links_report_source_line_without_destination_contents(self):
        self.write("README.md", '# Document\n\n[missing](private-fixture?key=private-query)\n')
        result = self.run_check()
        self.assertEqual(result.returncode, 1)
        self.assertIn('"README.md":3:', result.stdout)
        self.assertNotIn("private-fixture", result.stdout + result.stderr)
        self.assertNotIn("private-query", result.stdout + result.stderr)
        self.assertNotIn(str(self.project), result.stdout + result.stderr)

    def test_unresolved_references_fail_but_plain_brackets_are_text(self):
        self.write("README.md", '[ordinary text]\n[link][undefined]\n')
        result = self.run_check()
        self.assertEqual(result.returncode, 1)
        self.assertIn('"README.md":2:', result.stdout)
        self.assertIn("問題 1件", result.stdout)

    def test_parent_links_work_and_escaping_the_repository_fails(self):
        self.write("README.md", "# Root\n")
        self.write("docs/page.md", '[root](../README.md)\n[outside](../../private-fixture.md)\n')
        result = self.run_check(self.project / "docs")
        self.assertEqual(result.returncode, 1)
        self.assertIn('"docs/page.md":2:', result.stdout)
        self.assertIn("問題 1件", result.stdout)

    def test_untracked_markdown_files_are_not_scanned(self):
        self.write("README.md", "# Root\n")
        (self.project / "local.md").write_text("[bad](missing)\n")
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Markdown 1文書", result.stdout)

    def test_markdown_symlinks_are_skipped_and_preserved(self):
        self.write("README.md", "# Root\n")
        (self.project / "link.md").symlink_to(self.project / "missing")
        subprocess.run(["git", "-C", str(self.project), "add", "--", "link.md"], check=True)
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("リンク文書の除外 1件", result.stdout)
        self.assertTrue((self.project / "link.md").is_symlink())

    def test_invalid_utf8_and_missing_repository_are_reported_without_contents(self):
        self.write("README.md", "placeholder")
        (self.project / "README.md").write_bytes(b"private-fixture\xff")
        result = self.run_check()
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("private-fixture", result.stdout + result.stderr)
        result = self.run_check(self.project / "not-a-repository")
        self.assertEqual(result.returncode, 2)
        self.assertNotIn(str(self.project), result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
