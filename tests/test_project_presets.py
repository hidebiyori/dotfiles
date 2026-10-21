import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ProjectPresetTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="project presets ")
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.dotfiles = self.directory / "dotfiles"
        self.source = self.dotfiles / "src/project-presets/nextjs"
        shutil.copytree(ROOT / "src/project-presets/nextjs", self.source)
        shutil.copytree(ROOT / "src/project-presets/common", self.source.parent / "common")
        (self.dotfiles / "bin").mkdir()
        self.script = self.dotfiles / "bin/sync-project-presets.py"
        shutil.copy2(ROOT / "bin/sync-project-presets.py", self.script)
        self.project = self.directory / "application"
        self.project.mkdir()
        self.package = {"dependencies": {"next": "16.4.2"},
                        "devDependencies": {"typescript": "5.9.3", "@biomejs/biome": "2.5.12"}}
        self.write_package()
        self.destination = self.project / "config/presets/nextjs"

    def write_package(self):
        (self.project / "package.json").write_text(json.dumps(self.package), encoding="utf-8")

    def run_sync(self, *arguments):
        return subprocess.run([sys.executable, "-B", str(self.script), str(self.project), *arguments],
                              capture_output=True, text=True,
                              env={**os.environ, "PYTHONIOENCODING": "utf-8"}, encoding="utf-8")

    def snapshot(self):
        return {str(path.relative_to(self.project)): path.read_bytes()
                for path in self.project.rglob("*") if path.is_file()}

    def test_preview_and_check_never_write_files(self):
        before = self.snapshot()
        preview = self.run_sync("--init")
        self.assertEqual(preview.returncode, 0, preview.stderr)
        self.assertIn("CREATE biome.json", preview.stdout)
        self.assertEqual(self.snapshot(), before)
        self.assertFalse((self.project / "config").exists())
        self.assertEqual(self.run_sync("--init", "--check").returncode, 1)
        self.assertEqual(self.snapshot(), before)

    def test_initialization_is_portable_and_idempotent(self):
        package = (self.project / "package.json").read_bytes()
        result = self.run_sync("--init", "--write")
        self.assertEqual(result.returncode, 0, result.stderr)
        for name in ("biome.json", "tsconfig.json"):
            config = json.loads((self.project / name).read_text())
            inherited = config["extends"]
            if isinstance(inherited, list):
                inherited = inherited[0]
            self.assertTrue((self.project / inherited).is_file())
        self.assertTrue((self.project / ".editorconfig").is_file())
        self.assertTrue((self.project / ".gitattributes").is_file())
        self.assertTrue((self.project / "mise.toml").is_file())
        manifest = json.loads((self.destination / "manifest.json").read_text())
        for name, expected in manifest["files"].items():
            self.assertEqual(hashlib.sha256((self.destination / name).read_bytes()).hexdigest(),
                             expected)
        before = self.snapshot()
        self.assertEqual(self.run_sync("--init", "--check").returncode, 0)
        result = self.run_sync("--init", "--write")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("CREATE", result.stdout)
        self.assertNotIn("UPDATE", result.stdout)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual((self.project / "package.json").read_bytes(), package)
        self.assertFalse((self.project / "node_modules").exists())

    def test_javascript_project_does_not_gain_a_root_tsconfig(self):
        del self.package["devDependencies"]["typescript"]
        self.write_package()
        result = self.run_sync("--init", "--write")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.project / "tsconfig.json").exists())

    def test_existing_mise_configuration_is_preserved(self):
        for name in ("mise.toml", ".mise.toml"):
            with self.subTest(name=name):
                path = self.project / name
                contents = '[tools]\nnode = "22"\n'
                path.write_text(contents)
                result = self.run_sync("--init", "--write")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(path.read_text(), contents)
                self.assertIn("KEEP " + name, result.stdout)
                alternative = ".mise.toml" if name == "mise.toml" else "mise.toml"
                self.assertFalse((self.project / alternative).exists())
                path.unlink()

    def test_existing_jsonc_and_local_settings_are_preserved(self):
        files = {"biome.jsonc": '// Project override\n{"formatter": {"lineWidth": 100}}\n',
                 "tsconfig.json": '// Keep paths and include\n{"compilerOptions": {}}\n',
                 ".editorconfig": "root = true\n[*]\nindent_size = 4\n",
                 ".gitattributes": "*.md whitespace=-blank-at-eof\n"}
        for name, contents in files.items():
            (self.project / name).write_text(contents, encoding="utf-8")
        result = self.run_sync("--init", "--write")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.project / "biome.json").exists())
        for name, contents in files.items():
            self.assertEqual((self.project / name).read_text(), contents)
            self.assertIn("KEEP " + name, result.stdout)

    def test_source_update_changes_only_snapshots(self):
        self.assertEqual(self.run_sync("--init", "--write").returncode, 0)
        local = self.project / "biome.json"
        config = json.loads(local.read_text())
        config["formatter"] = {"lineWidth": 100}
        local.write_text(json.dumps(config), encoding="utf-8")
        previous = local.read_bytes()
        changed = json.loads((self.source / "biome-next.json").read_text())
        changed["formatter"]["lineWidth"] = 90
        updated = (json.dumps(changed, indent=2) + "\n").encode()
        (self.source / "biome-next.json").write_bytes(updated)
        self.assertEqual(self.run_sync("--check").returncode, 1)
        result = self.run_sync("--write")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.destination / "biome-next.json").read_bytes(), updated)
        self.assertEqual(local.read_bytes(), previous)
        self.assertEqual(self.run_sync("--check").returncode, 0)

    def test_locally_edited_snapshot_aborts_before_any_write(self):
        self.assertEqual(self.run_sync("--write").returncode, 0)
        (self.destination / "tsconfig-next.json").write_text('{"custom": true}\n')
        (self.source / "biome-next.json").write_text('{"formatter": {"lineWidth": 90}}\n')
        before = self.snapshot()
        result = self.run_sync("--init", "--write")
        self.assertEqual(result.returncode, 2)
        self.assertIn("tsconfig-next.json", result.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_unmanaged_file_collision_is_preserved(self):
        self.destination.mkdir(parents=True)
        (self.destination / "tsconfig-next.json").write_text('{"custom": true}\n')
        before = self.snapshot()
        result = self.run_sync("--write")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self.snapshot(), before)

    def test_invalid_source_is_rejected_before_initialization(self):
        (self.source / "tsconfig-next.json").write_text("invalid-fixture")
        before = self.snapshot()
        result = self.run_sync("--init", "--write")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self.snapshot(), before)

    def test_invalid_manifest_is_preserved(self):
        self.assertEqual(self.run_sync("--write").returncode, 0)
        for contents in ('{}', '{"formatVersion": 99}', '[]', 'invalid-fixture'):
            with self.subTest(contents=contents):
                (self.destination / "manifest.json").write_text(contents)
                before = self.snapshot()
                result = self.run_sync("--write")
                self.assertEqual(result.returncode, 2)
                self.assertEqual(self.snapshot(), before)

    def test_root_symlink_is_kept_during_initialization(self):
        editor = self.directory / "editorconfig"
        editor.write_text("root = true\n")
        (self.project / ".editorconfig").symlink_to(editor)
        result = self.run_sync("--init", "--write")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.project / ".editorconfig").is_symlink())
        self.assertEqual(editor.read_text(), "root = true\n")

    def test_symlink_in_destination_is_preserved(self):
        outside = self.directory / "hand-managed"
        outside.mkdir()
        for relative in ("config", "config/presets", "config/presets/nextjs"):
            with self.subTest(relative=relative):
                path = self.project / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.symlink_to(outside, target_is_directory=True)
                result = self.run_sync("--write")
                self.assertEqual(result.returncode, 2)
                self.assertTrue(path.is_symlink())
                self.assertEqual(list(outside.iterdir()), [])
                path.unlink()
        self.destination.mkdir(parents=True, exist_ok=True)
        file = outside / "custom.json"
        file.write_text("{}")
        (self.destination / "biome-next.json").symlink_to(file)
        self.assertEqual(self.run_sync("--write").returncode, 2)
        self.assertEqual(file.read_text(), "{}")

    def test_unrelated_or_invalid_package_json_is_rejected_without_contents(self):
        for contents in ('{"dependencies": {}}', '{"dependencies": []}', 'private-fixture-text'):
            with self.subTest(contents=contents):
                (self.project / "package.json").write_text(contents)
                result = self.run_sync("--init", "--write")
                self.assertEqual(result.returncode, 2)
                self.assertNotIn("private-fixture-text", result.stdout + result.stderr)
                self.assertEqual(sorted(self.snapshot()), ["package.json"])


if __name__ == "__main__":
    unittest.main()
