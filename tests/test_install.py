import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "bin/install.sh"
PUBLIC_URL = "https://github.com/hidebiyori/dotfiles.git"


class InstallerTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="dotfiles install ")
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)
        self.bin = self.home / "commands"
        self.bin.mkdir()
        self.log = self.home / "commands.log"
        self.env = {
            **os.environ,
            "HOME": str(self.home),
            "PATH": str(self.bin) + os.pathsep + os.environ["PATH"],
            "TEST_LOG": str(self.log),
        }
        for name in ("WSL_DISTRO_NAME", "WSL_INTEROP", "INSTALL_FLUTTER", "BASH_ENV"):
            self.env.pop(name, None)

    def command(self, name, contents):
        path = self.bin / name
        path.write_text("#!/bin/bash\n" + contents)
        path.chmod(0o755)

    def run_bash(self, body, trace=False, extra_env=None):
        return subprocess.run(
            ["bash", *(["-x"] if trace else []), "-c",
             "source " + shlex.quote(str(INSTALLER)) + "\n" + body],
            env={**self.env, **(extra_env or {})},
            cwd=self.home,
            text=True,
            capture_output=True,
            check=True,
        )

    def git_stub(self):
        self.command("git", '''printf '%s\\n' "$*" >> "$TEST_LOG"
if [[ "$*" == *"config --get remote.origin.url" ]]; then
  printf '%s\\n' "${TEST_ORIGIN_URL:-}"
fi
''')

    def test_clone_ignores_token_and_disables_inherited_tracing(self):
        self.git_stub()
        sentinel = "synthetic-test-credential"
        result = self.run_bash('setOptions; setGitRepository "$PJ_URL"', trace=True,
                               extra_env={"GH_TOKEN": sentinel})
        self.assertIn("clone " + PUBLIC_URL, self.log.read_text())
        self.assertNotIn(sentinel, result.stdout + result.stderr + self.log.read_text())

    def test_legacy_origin_authentication_is_removed_before_pull(self):
        self.git_stub()
        (self.home / "git/dotfiles").mkdir(parents=True)
        for legacy in (
            "https://synthetic-test-credential@github.com/hidebiyori/dotfiles.git",
            PUBLIC_URL + "?token=synthetic-test-credential#fragment",
        ):
            with self.subTest(kind="userinfo" if "@" in legacy else "query"):
                self.log.unlink(missing_ok=True)
                result = self.run_bash('setOptions; setGitRepository "$PJ_URL"', trace=True,
                                       extra_env={"TEST_ORIGIN_URL": legacy})
                calls = self.log.read_text()
                self.assertLess(calls.index("remote set-url origin " + PUBLIC_URL),
                                calls.index(" pull"))
                self.assertNotIn("synthetic-test-credential", result.stdout + result.stderr + calls)

    def test_ssh_origin_is_preserved(self):
        self.git_stub()
        (self.home / "git/dotfiles").mkdir(parents=True)
        self.run_bash('setOptions; setGitRepository "$PJ_URL"', extra_env={
            "TEST_ORIGIN_URL": "git@github.com:hidebiyori/dotfiles.git",
        })
        self.assertNotIn("set-url", self.log.read_text())
        self.assertIn(" pull", self.log.read_text())

    def prepare_install(self, kernel):
        self.env["TEST_KERNEL"] = kernel
        repository = self.home / "git/dotfiles"
        (repository / "bin").mkdir(parents=True)
        shutil.copytree(ROOT / "src", repository / "src")
        (repository / "bin/setup-skill-python.sh").write_text(
            'printf "%s\\n" skill-python >> "$TEST_LOG"\n')
        (repository / "bin/setup-chatgpt-maximized.py").write_text(
            'import os\nwith open(os.environ["TEST_LOG"], "a") as f:\n'
            '    f.write("linux-launcher\\n")\n')
        self.git_stub()
        self.command("uname", 'printf "%s\\n" "$TEST_KERNEL"\n')
        for name in ("sudo", "mise", "brew", "defaults"):
            self.command(name, f'printf "%s\\n" "{name} $*" >> "$TEST_LOG"\n')
        for name in ("curl", "fcitx-autostart", "fcitx-configtool"):
            self.command(name, f'echo "Unexpected GUI/download command: {name}" >&2\nexit 99\n')
        self.command("which", 'exit 1\n')
        return repository

    def prepare_windows(self):
        appdata = self.home / "windows 日本語/AppData/Roaming"
        downloads = self.home / "windows 日本語/移動した Downloads"
        appdata.mkdir(parents=True)
        downloads.mkdir()
        self.env.update({
            "TEST_WINDOWS_APPDATA": r"C:\Users\日本語 User\AppData\Roaming",
            "TEST_WINDOWS_DOWNLOADS": r"D:\移動した Downloads",
            "TEST_APPDATA_LINUX": str(appdata),
            "TEST_DOWNLOADS_LINUX": str(downloads),
        })
        self.command("powershell.exe", '''printf '%s\\r\\n' "$TEST_WINDOWS_APPDATA" "$TEST_WINDOWS_DOWNLOADS"
''')
        self.command("wslpath", '''if [[ "${TEST_WSLPATH_FAIL:-0}" == 1 ]]; then exit 1; fi
case "$2" in
  "$TEST_WINDOWS_APPDATA") printf '%s\\n' "$TEST_APPDATA_LINUX" ;;
  "$TEST_WINDOWS_DOWNLOADS") printf '%s\\n' "$TEST_DOWNLOADS_LINUX" ;;
  *) exit 1 ;;
esac
''')
        return appdata, downloads

    def assert_common_tools(self):
        calls = self.log.read_text()
        self.assertIn("sudo apt install -y python3-venv", calls)
        self.assertIn("skill-python", calls)
        self.assertIn("mise use --global node@lts", calls)
        self.assertIn("mise exec node@lts -- npm install -g firebase-tools", calls)
        self.assertNotIn("flutter", calls)

    def test_wsl_detection_uses_environment_and_kernel_without_affecting_other_platforms(self):
        cases = [
            ("Linux generic", {}, "native"),
            ("Linux generic", {"WSL_DISTRO_NAME": "Ubuntu"}, "wsl"),
            ("Linux generic", {"WSL_INTEROP": "/run/WSL/example_interop"}, "wsl"),
            ("Linux example microsoft-standard-WSL2", {}, "wsl"),
            ("Linux example Microsoft", {}, "wsl"),
            ("Darwin example", {"WSL_DISTRO_NAME": "Ubuntu"}, "native"),
        ]
        for kernel, environment, expected in cases:
            with self.subTest(kernel=kernel, environment=list(environment)):
                result = self.run_bash(
                    'uname=' + shlex.quote(kernel) + '\n'
                    'if isWsl; then echo wsl; else echo native; fi',
                    extra_env=environment,
                )
                self.assertEqual(result.stdout.strip(), expected)

    def test_wsl_install_links_downloads_copies_windows_settings_and_finishes_cli_setup(self):
        repository = self.prepare_install("Linux example microsoft-standard-WSL2")
        appdata, downloads = self.prepare_windows()
        code_user = appdata / "Code/User"
        code_user.mkdir(parents=True)
        (code_user / "settings.json").write_text("old settings")
        self.run_bash("main")
        self.assert_common_tools()
        calls = self.log.read_text()
        self.assertIn("sudo apt install screen ca-certificates curl git vim", calls)
        self.assertNotIn("fcitx", calls)
        self.assertNotIn("vscode.deb", calls)
        self.assertNotIn("linux-launcher", calls)
        self.assertEqual((self.home / "Downloads").resolve(), downloads)
        self.assertFalse((self.home / "MyDrive").is_symlink())
        self.assertFalse((self.home / ".sommelierrc").is_symlink())
        self.assertFalse((self.home / ".config/Code").exists())
        for filename in ("settings.json", "keybindings.json"):
            self.assertEqual((code_user / filename).read_bytes(),
                             (repository / "src/.config/Code/User" / filename).read_bytes())
            self.assertFalse((code_user / filename).is_symlink())
        for filename in (".bashrc", ".bash_profile", ".screenrc", ".ssh/config"):
            self.assertEqual((self.home / filename).resolve(), repository / "src" / filename)

    def test_wsl_windows_failure_still_finishes_cli_setup(self):
        self.prepare_install("Linux example microsoft-standard-WSL2")
        self.command("powershell.exe", "exit 31\n")
        self.command("wslpath", "exit 99\n")
        result = self.run_bash("main")
        self.assert_common_tools()
        self.assertIn("フォルダ取得に失敗", result.stderr)
        self.assertFalse((self.home / "Downloads").is_symlink())

    def test_wsl_unavailable_windows_paths_are_reported_without_stopping_cli_setup(self):
        self.prepare_install("Linux example microsoft-standard-WSL2")
        self.prepare_windows()
        result = self.run_bash("main", extra_env={"TEST_WSLPATH_FAIL": "1"})
        self.assert_common_tools()
        self.assertIn("Downloads にアクセスできない", result.stderr)
        self.assertIn("AppData にアクセスできない", result.stderr)

    def test_wsl_preserves_existing_downloads_directory(self):
        self.prepare_install("Linux example microsoft-standard-WSL2")
        self.prepare_windows()
        downloads = self.home / "Downloads"
        downloads.mkdir()
        existing = downloads / "keep.txt"
        existing.write_text("existing local download")
        result = self.run_bash("main")
        self.assertEqual(existing.read_text(), "existing local download")
        self.assertFalse(downloads.is_symlink())
        self.assertEqual(list(downloads.iterdir()), [existing])
        self.assertIn("既存のディレクトリ", result.stderr)

    def test_native_linux_keeps_existing_gui_and_chromeos_setup(self):
        self.prepare_install("Linux example generic")
        self.run_bash('''function setJapanese() { echo japanese >> "$TEST_LOG"; }
function setVisualStudioCode() { echo linux-code >> "$TEST_LOG"; }
main
''')
        self.assert_common_tools()
        calls = self.log.read_text()
        for expected in ("sudo apt install screen\n", "japanese", "linux-code", "linux-launcher"):
            self.assertIn(expected, calls)
        self.assertEqual(os.readlink(self.home / "Downloads"), "/mnt/chromeos/MyFiles/Downloads")
        self.assertEqual(os.readlink(self.home / "MyDrive"), "/mnt/chromeos/GoogleDrive/MyDrive")
        self.assertTrue((self.home / ".sommelierrc").is_symlink())
        self.assertTrue((self.home / ".config/Code/User/settings.json").is_symlink())

    def test_macos_keeps_homebrew_and_screenshot_setup(self):
        self.prepare_install("Darwin example")
        self.run_bash('''function which() { command -v "$1"; }
main
''')
        calls = self.log.read_text()
        for expected in ("brew update", "brew upgrade", "defaults write com.apple.screencapture", "skill-python",
                         "mise use --global node@lts", "mise exec node@lts -- npm install -g firebase-tools"):
            self.assertIn(expected, calls)
        self.assertNotIn("sudo", calls)
        self.assertNotIn("linux-launcher", calls)
        self.assertFalse((self.home / "Downloads").is_symlink())


if __name__ == "__main__":
    unittest.main()
