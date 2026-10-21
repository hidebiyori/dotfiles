import json
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

    def prepare_node(self, scripts=None):
        scripts = scripts if scripts is not None else {
            "check": "node check.js", "test:ci": "node --test", "build": "node build.js"}
        (self.project / "package.json").write_text(json.dumps({"scripts": scripts}))
        (self.project / "package-lock.json").write_text('{"lockfileVersion": 3}\n')

    def test_node_profile_creates_ci_and_preserves_mise_version(self):
        self.prepare_node()
        original = '[tools]\nnode = "22"\n'
        (self.project / ".mise.toml").write_text(original)
        preview = self.run_init("--node")
        self.assertEqual(preview.returncode, 0, preview.stderr)
        self.assertFalse((self.project / ".github").exists())
        result = self.run_init("--node", "--write")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.project / ".github/workflows/check.yml").is_file())
        self.assertTrue((self.project / ".github/dependabot.yml").is_file())
        self.assertEqual((self.project / ".mise.toml").read_text(), original)
        self.assertFalse((self.project / "mise.toml").exists())
        self.assertFalse((self.project / "node_modules").exists())

    def test_node_profile_requires_ci_scripts_before_any_write(self):
        self.prepare_node({"test": "node --test"})
        before = set(self.project.iterdir())
        result = self.run_init("--node", "--write")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(set(self.project.iterdir()), before)

    def test_typescript_requires_an_explicit_typecheck(self):
        self.prepare_node()
        package = json.loads((self.project / "package.json").read_text())
        package["devDependencies"] = {"typescript": "5.9.3"}
        (self.project / "package.json").write_text(json.dumps(package))
        result = self.run_init("--node", "--write")
        self.assertEqual(result.returncode, 2)
        self.assertFalse((self.project / ".github").exists())
        package["scripts"]["typecheck"] = "tsc --noEmit"
        (self.project / "package.json").write_text(json.dumps(package))
        self.assertEqual(self.run_init("--node", "--write").returncode, 0)

    def test_missing_lockfile_is_rejected_without_creating_anything(self):
        self.prepare_node()
        (self.project / "package-lock.json").unlink()
        result = self.run_init("--node", "--write")
        self.assertEqual(result.returncode, 2)
        self.assertFalse((self.project / ".editorconfig").exists())

    def test_existing_workflows_and_dependabot_yaml_are_not_duplicated(self):
        self.prepare_node({})
        workflows = self.project / ".github/workflows"
        workflows.mkdir(parents=True)
        original = "name: custom\n"
        (workflows / "release.yaml").write_text(original)
        (workflows.parent / "dependabot.yaml").write_text(original)
        result = self.run_init("--node", "--write")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((workflows / "release.yaml").read_text(), original)
        self.assertEqual((workflows.parent / "dependabot.yaml").read_text(), original)
        self.assertFalse((workflows / "check.yml").exists())
        self.assertFalse((workflows.parent / "dependabot.yml").exists())

    def test_linked_github_directory_is_rejected_before_any_write(self):
        outside = self.directory / "hand-managed"
        outside.mkdir()
        (self.project / ".github").symlink_to(outside, target_is_directory=True)
        result = self.run_init("--github-actions", "--write")
        self.assertEqual(result.returncode, 2)
        self.assertFalse((self.project / ".editorconfig").exists())
        self.assertEqual(list(outside.iterdir()), [])

    def test_actions_profile_does_not_require_npm_or_add_node_workflow(self):
        result = self.run_init("--github-actions", "--write")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.project / ".github/dependabot.yml").is_file())
        self.assertFalse((self.project / ".github/workflows").exists())
        self.assertFalse((self.project / "mise.toml").exists())

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
