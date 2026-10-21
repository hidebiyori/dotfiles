import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin/check-project-presets.py"
SYNC = ROOT / "bin/sync-project-presets.py"


class ProjectPresetCheckTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="preset checks ")
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)

    def project(self, name):
        project = self.directory / name
        project.mkdir()
        (project / "package.json").write_text('{"dependencies": {"next": "16.4.2"}}\n')
        result = subprocess.run(
            [sys.executable, "-B", str(SYNC), str(project), "--write"], capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return project

    def run_check(self, *arguments):
        return subprocess.run(
            [sys.executable, "-B", str(SCRIPT), *map(str, arguments)],
            capture_output=True, text=True, encoding="utf-8",
            env={**os.environ, "PYTHONIOENCODING": "utf-8"})

    def snapshot(self):
        return {str(p.relative_to(self.directory)): p.read_bytes()
                for p in self.directory.rglob("*") if p.is_file()}

    def test_multiple_synchronized_projects_are_read_only_and_deduplicated(self):
        first = self.project("first")
        second = self.project("second with spaces")
        before = self.snapshot()
        result = self.run_check(first, second, first)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.count("OK "), 2)
        self.assertEqual(self.snapshot(), before)
        self.assertNotIn(str(self.directory), result.stdout + result.stderr)

    def test_stale_presets_are_reported_without_synchronizing(self):
        project = self.project("outdated")
        destination = project / "config/presets/nextjs"
        contents = b'{"formatter": {"lineWidth": 70}}\n'
        (destination / "biome-next.json").write_bytes(contents)
        manifest_path = destination / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["files"]["biome-next.json"] = hashlib.sha256(contents).hexdigest()
        manifest_path.write_text(json.dumps(manifest))
        before = self.snapshot()
        result = self.run_check(project)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn('UPDATE "outdated"', result.stdout)
        self.assertEqual(self.snapshot(), before)

    def test_one_error_does_not_skip_later_projects_or_disclose_file_contents(self):
        invalid = self.project("invalid")
        (invalid / "package.json").write_text("private-fixture-content")
        valid = self.project("valid")
        before = self.snapshot()
        result = self.run_check(invalid, valid)
        self.assertEqual(result.returncode, 2)
        self.assertIn('ERROR "invalid"', result.stdout)
        self.assertIn('OK "valid"', result.stdout)
        self.assertNotIn("private-fixture-content", result.stdout + result.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_projects_file_resolves_paths_relative_to_its_location(self):
        self.project("app")
        listing = self.directory / "projects.json"
        listing.write_text(json.dumps(["app"]))
        result = self.run_check("--projects-file", listing)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('OK "app"', result.stdout)

    def test_invalid_or_empty_lists_fail_without_printing_contents(self):
        listing = self.directory / "projects.json"
        for contents in ('{"private-fixture-content": true}', '[""]', '[12]', '[]', 'not-json'):
            with self.subTest(contents=contents):
                listing.write_text(contents)
                result = self.run_check("--projects-file", listing)
                self.assertEqual(result.returncode, 2)
                self.assertNotIn("private-fixture-content", result.stdout + result.stderr)
                self.assertNotIn(str(self.directory), result.stdout + result.stderr)
        self.assertEqual(self.run_check().returncode, 2)


if __name__ == "__main__":
    unittest.main()
