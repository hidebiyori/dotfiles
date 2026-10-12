import contextlib
import importlib.util
import io
import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "bin" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


launcher = load_script("chatgpt-maximized")
setup = load_script("setup-chatgpt-maximized")


class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name)
        self.state_path = self.home / ".codex-global-state.json"
        self.state = {
            launcher.WINDOW_KEY: {"x": 232, "y": 96, "width": 1344, "height": 824, "isMaximized": False},
            "unrelated": {"text": "日本語", "list": [1, False, None], "nested": {"isMaximized": False}},
        }
        self.original = json.dumps(self.state, indent=2).encode()
        self.state_path.write_bytes(self.original)

    def prepare(self):
        return launcher.prepare_state(self.state_path, lambda: False)

    def test_only_maximization_changes_and_private_backup_is_exact(self):
        self.assertEqual(self.prepare(), "corrected")
        expected = self.state
        expected[launcher.WINDOW_KEY]["isMaximized"] = True
        self.assertEqual(json.loads(self.state_path.read_bytes()), expected)
        backup = self.state_path.with_name(self.state_path.name + ".before-maximized-launcher")
        self.assertEqual(backup.read_bytes(), self.original)
        for path in (backup, self.state_path):
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.assertFalse(list(self.home.glob("*.tmp-*")))

    def test_already_maximized_does_not_rewrite_state_or_backup(self):
        self.prepare()
        self.assertEqual(self.prepare(), "already-maximized")
        backup = self.state_path.with_name(self.state_path.name + ".before-maximized-launcher")
        self.assertEqual(backup.read_bytes(), self.original)

    def test_live_app_leaves_all_files_untouched(self):
        self.assertEqual(launcher.prepare_state(self.state_path, lambda: True), "app-running")
        self.assertEqual(self.state_path.read_bytes(), self.original)
        self.assertEqual(list(self.home.iterdir()), [self.state_path])

    def test_app_starting_before_write_is_not_overwritten(self):
        running = mock.Mock(side_effect=[False, False, True])
        self.assertEqual(launcher.prepare_state(self.state_path, running), "app-running")
        self.assertEqual(self.state_path.read_bytes(), self.original)

    def test_concurrent_state_change_is_not_overwritten(self):
        calls = 0
        replacement = b'{"new-state":true}'

        def running():
            nonlocal calls
            calls += 1
            if calls == 3:
                self.state_path.write_bytes(replacement)
            return False

        self.assertEqual(launcher.prepare_state(self.state_path, running), "state-changed")
        self.assertEqual(self.state_path.read_bytes(), replacement)

    def test_invalid_state_is_preserved(self):
        for contents in (b"invalid-json", b"[]", b'{"electron-main-window-bounds":null}',
                         b'{"electron-main-window-bounds":{"x":true}}'):
            with self.subTest(contents=contents):
                self.state_path.write_bytes(contents)
                with self.assertRaises(ValueError):
                    self.prepare()
                self.assertEqual(self.state_path.read_bytes(), contents)

    def test_state_symlink_is_not_replaced(self):
        target = self.home / "target.json"
        self.state_path.rename(target)
        self.state_path.symlink_to(target)
        with self.assertRaises(ValueError):
            self.prepare()
        self.assertTrue(self.state_path.is_symlink())
        self.assertEqual(target.read_bytes(), self.original)

    def test_missing_bounds_and_missing_state_can_start_maximized(self):
        self.state_path.write_text('{"unrelated": [1, 2]}')
        self.assertEqual(self.prepare(), "corrected")
        self.assertEqual(json.loads(self.state_path.read_bytes())["unrelated"], [1, 2])
        self.state_path.unlink()
        self.assertEqual(self.prepare(), "corrected")
        self.assertTrue(json.loads(self.state_path.read_bytes())[launcher.WINDOW_KEY]["isMaximized"])

    def test_failed_write_preserves_original_and_cleans_temporary_file(self):
        with mock.patch.object(launcher.os, "replace", side_effect=OSError):
            with self.assertRaises(OSError):
                self.prepare()
        self.assertEqual(self.state_path.read_bytes(), self.original)
        self.assertFalse(list(self.home.glob("*.tmp-*")))

    def test_invalid_state_still_forwards_arguments_without_logging_contents(self):
        original_launcher = self.home / "chatgpt"
        original_launcher.touch()
        self.state_path.write_text("private-sentinel-invalid-json")
        error_output = io.StringIO()
        arguments = ["codex://threads/example", "path with spaces.csv"]
        with mock.patch.object(launcher, "APP_LAUNCHER", original_launcher), \
             mock.patch.object(launcher, "app_is_running", return_value=False), \
             mock.patch.dict(launcher.os.environ, {"CODEX_HOME": str(self.home)}), \
             mock.patch.object(launcher.os, "execv") as execute, \
             contextlib.redirect_stderr(error_output):
            launcher.main(arguments)
        execute.assert_called_once_with(str(original_launcher), [str(original_launcher), *arguments])
        self.assertNotIn("private-sentinel", error_output.getvalue())
        self.assertEqual(self.state_path.read_text(), "private-sentinel-invalid-json")


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="launcher setup ")
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name)
        self.source = self.home / "packaged.desktop"
        self.original = "[Desktop Entry]\nName=ChatGPT\nExec=chatgpt %U\nIcon=chatgpt\nType=Application\nMimeType=x-scheme-handler/codex;\n"
        self.source.write_text(self.original)
        self.launcher_source = ROOT / "bin/chatgpt-maximized.py"
        self.data_home = self.home / "data"
        self.state_home = self.home / "state"

    def install(self):
        return setup.install(self.source, self.launcher_source, self.home, self.data_home, self.state_home)

    def test_simple_executable_path_needs_no_quoting(self):
        self.assertEqual(setup.desktop_argument("/home/example/.local/bin/chatgpt-maximized"),
                         "/home/example/.local/bin/chatgpt-maximized")

    def test_desktop_override_preserves_packaged_entry_and_is_idempotent(self):
        applications = self.install()
        desktop = applications / "chatgpt.desktop"
        contents = desktop.read_text()
        self.assertEqual(self.source.read_text(), self.original)
        self.assertIn('Exec="' + str(self.home / ".local/bin/chatgpt-maximized") + '" %U\n', contents)
        for line in self.original.splitlines():
            if not line.startswith("Exec="):
                self.assertIn(line + "\n", contents)
        executable = self.home / ".local/bin/chatgpt-maximized"
        self.assertEqual(executable.resolve(), self.launcher_source)
        self.install()
        self.assertEqual(desktop.read_text(), contents)
        self.assertFalse(self.state_home.exists())

    def test_existing_custom_desktop_is_preserved_and_backed_up(self):
        desktop = self.data_home / "applications/chatgpt.desktop"
        desktop.parent.mkdir(parents=True)
        custom = self.original.replace("Name=ChatGPT", "Name=Custom name")
        desktop.write_text(custom)
        self.install()
        self.assertIn("Name=Custom name", desktop.read_text())
        backup = self.state_home / "dotfiles/chatgpt.desktop.before-maximized-launcher"
        self.assertEqual(backup.read_text(), custom)
        self.install()
        self.assertEqual(backup.read_text(), custom)

    def test_unknown_existing_launcher_is_not_overwritten(self):
        executable = self.home / ".local/bin/chatgpt-maximized"
        executable.parent.mkdir(parents=True)
        executable.write_text("existing launcher")
        with self.assertRaises(ValueError):
            self.install()
        self.assertEqual(executable.read_text(), "existing launcher")
        self.assertFalse(self.data_home.exists())


if __name__ == "__main__":
    unittest.main()
