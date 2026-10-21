import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin/init-project-config.py"


class ProjectConfigTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="repository config ")
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.project = self.directory / "project"
        self.project.mkdir()

    def run_init(self, *arguments):
        return subprocess.run(
            [sys.executable, "-B", str(SCRIPT), str(self.project), *arguments],
            capture_output=True, text=True, encoding="utf-8",
            env={**os.environ, "PYTHONIOENCODING": "utf-8"})

    def test_preview_and_exclusive_creation(self):
        result = self.run_init()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("CREATE .gitattributes", result.stdout)
        self.assertEqual(list(self.project.iterdir()), [])
        result = self.run_init("--write")
        self.assertEqual(result.returncode, 0, result.stderr)
        before = {p.name: p.read_bytes() for p in self.project.iterdir()}
        result = self.run_init("--write")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("CREATE", result.stdout)
        self.assertEqual({p.name: p.read_bytes() for p in self.project.iterdir()}, before)

    def test_existing_custom_configuration_is_preserved(self):
        original = b"*.md whitespace=-blank-at-eof\n"
        (self.project / ".gitattributes").write_bytes(original)
        result = self.run_init("--write")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("KEEP .gitattributes", result.stdout)
        self.assertEqual((self.project / ".gitattributes").read_bytes(), original)

    def test_hand_managed_and_dangling_links_are_preserved(self):
        outside = self.directory / "custom"
        outside.write_text("custom\n", encoding="utf-8")
        (self.project / ".editorconfig").symlink_to(outside)
        (self.project / ".gitattributes").symlink_to(self.directory / "missing")
        result = self.run_init("--write")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.project / ".editorconfig").is_symlink())
        self.assertTrue((self.project / ".gitattributes").is_symlink())
        self.assertEqual(outside.read_text(), "custom\n")

    def test_invalid_destination_aborts_before_writing(self):
        (self.project / ".gitattributes").mkdir()
        result = self.run_init("--write")
        self.assertEqual(result.returncode, 2)
        self.assertFalse((self.project / ".editorconfig").exists())

    def test_missing_project_does_not_disclose_absolute_path(self):
        self.project.rmdir()
        result = self.run_init("--write")
        self.assertEqual(result.returncode, 2)
        self.assertNotIn(str(self.directory), result.stdout + result.stderr)
        self.assertFalse(self.project.exists())

    def test_attributes_normalize_text_and_preserve_binary_data(self):
        self.assertEqual(self.run_init("--write").returncode, 0)
        subprocess.run(["git", "init", "-q", str(self.project)], check=True)
        (self.project / "script.sh").write_bytes(b"first\r\nsecond\r\n")
        (self.project / "script.cmd").write_bytes(b"first\r\nsecond\r\n")
        data = b"\x00\r\n\xff\x00"
        (self.project / "image.bin").write_bytes(data)
        subprocess.run(["git", "-C", str(self.project), "add", "."],
                       capture_output=True, check=True)
        for name, expected in [("script.sh", b"first\nsecond\n"),
                               ("script.cmd", b"first\nsecond\n"),
                               ("image.bin", data)]:
            result = subprocess.run(["git", "-C", str(self.project), "show", ":" + name],
                                    capture_output=True, check=True)
            self.assertEqual(result.stdout, expected)
        attrs = subprocess.run(
            ["git", "-C", str(self.project), "check-attr", "eol", "--", "script.cmd", "script.sh"],
            capture_output=True, text=True, check=True)
        self.assertIn("script.cmd: eol: crlf", attrs.stdout)
        self.assertIn("script.sh: eol: lf", attrs.stdout)


if __name__ == "__main__":
    unittest.main()
