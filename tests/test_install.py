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
        for name in ("WSL_DISTRO_NAME", "WSL_INTEROP", "INSTALL_FLUTTER", "BASH_ENV",
                     "UPGRADE_DESKTOP_APPS", "XDG_CACHE_HOME"):
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
        self.assertNotIn("chatgpt_", calls)
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
function setCodexDesktop() { echo codex-desktop >> "$TEST_LOG"; }
main
''')
        self.assert_common_tools()
        calls = self.log.read_text()
        for expected in ("sudo apt install screen ca-certificates curl\n", "japanese", "linux-code",
                         "codex-desktop", "linux-launcher"):
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

    def desktop_stubs(self, architecture="amd64"):
        self.command("dpkg", f'printf "%s\\n" "{architecture}"\n')
        self.command("sudo", 'printf "%s\\n" "sudo $*" >> "$TEST_LOG"\n')
        self.command("curl", '''printf '%s\\n' "curl $*" >> "$TEST_LOG"
while [[ $# -gt 0 ]]; do
  if [[ "$1" == --output ]]; then printf 'synthetic deb' > "$2"; fi
  shift
done
''')
        self.command("dpkg-deb", '''case "$*" in
  *chatgpt*Package) echo "${TEST_DEB_PACKAGE:-chatgpt}" ;;
  *code*Package) echo "${TEST_DEB_PACKAGE:-code}" ;;
  *Architecture) echo "${TEST_DEB_ARCHITECTURE:-amd64}" ;;
  *) exit 9 ;;
esac
''')

    def test_macos_installs_missing_desktop_apps_with_existing_homebrew(self):
        self.command("brew", '''printf '%s\\n' "brew $*" >> "$TEST_LOG"
if [[ "$1" == list ]]; then exit 1; fi
''')
        self.run_bash('setOptions; setMacDesktopApps')
        calls = self.log.read_text()
        for cask in ("chatgpt", "google-chrome", "visual-studio-code"):
            self.assertIn("brew install --cask " + cask, calls)
        self.assertNotIn("--cask codex\n", calls)

    def test_macos_keeps_installed_desktop_apps_unless_upgrade_is_explicit(self):
        self.command("brew", 'printf "%s\\n" "brew $*" >> "$TEST_LOG"\n')
        self.run_bash('setOptions; setMacDesktopApps')
        self.assertNotIn("install --cask", self.log.read_text())
        self.assertNotIn("upgrade", self.log.read_text())
        self.log.unlink()
        self.run_bash('setOptions; setMacDesktopApps', extra_env={"UPGRADE_DESKTOP_APPS": "1"})
        calls = self.log.read_text()
        for cask in ("chatgpt", "google-chrome", "visual-studio-code"):
            self.assertIn("brew upgrade --cask --greedy " + cask, calls)

    def test_macos_preserves_apps_installed_outside_homebrew(self):
        self.command("brew", '''printf '%s\\n' "brew $*" >> "$TEST_LOG"
if [[ "$1" == list ]]; then exit 1; fi
''')
        (self.home / "Applications/ChatGPT.app").mkdir(parents=True)
        self.run_bash('setOptions; setMacDesktopApps')
        self.assertNotIn("install --cask chatgpt", self.log.read_text())

    def test_codex_desktop_reuses_installed_package_without_download(self):
        self.command("dpkg-query", "echo 'install ok installed'\n")
        self.command("curl", "echo 'Unexpected download' >&2\nexit 99\n")
        self.run_bash('setOptions; setCodexDesktop')
        self.assertFalse(self.log.exists())

    def test_codex_desktop_downloads_architecture_specific_deb_and_reuses_cache(self):
        self.desktop_stubs("arm64")
        self.command("dpkg-query", "exit 1\n")
        body = '''setOptions
function getDesktopLinuxRelease() { echo debian:13; }
setCodexDesktop
'''
        environment = {"TEST_DEB_ARCHITECTURE": "arm64"}
        self.run_bash(body, extra_env=environment)
        calls = self.log.read_text()
        self.assertIn("https://persistent.oaistatic.com/codex-app-prod/linux/deb/latest/chatgpt_arm64.deb", calls)
        self.assertIn("sudo apt install " + str(self.home / ".cache/dotfiles/chatgpt_arm64.deb"), calls)
        self.log.unlink()
        self.run_bash(body, extra_env=environment)
        self.assertNotIn("curl ", self.log.read_text())

    def test_wrong_deb_metadata_stops_before_install(self):
        self.desktop_stubs()
        result = self.run_bash('''setOptions
if installDesktopDeb chatgpt amd64 https://example.invalid/package.deb; then exit 99; fi
''', extra_env={"TEST_DEB_PACKAGE": "other-package"})
        self.assertIn("導入を中止", result.stderr)
        self.assertNotIn("sudo apt install", self.log.read_text())
        self.assertFalse((self.home / ".cache/dotfiles/chatgpt_amd64.deb").exists())

    def test_codex_desktop_refuses_unsupported_release_before_download(self):
        self.command("dpkg-query", "exit 1\n")
        result = self.run_bash('''setOptions
function getDesktopLinuxRelease() { echo debian:12; }
if setCodexDesktop; then exit 99; fi
''')
        self.assertIn("公式対象", result.stderr)
        self.assertFalse(self.log.exists())

    def test_package_database_error_does_not_trigger_desktop_download(self):
        self.command("dpkg-query", "exit 2\n")
        result = self.run_bash('setOptions; if setCodexDesktop; then exit 99; fi')
        self.assertIn("導入状態を確認できません", result.stderr)
        self.assertFalse(self.log.exists())

    def test_failed_download_is_not_installed_even_with_valid_stale_partial(self):
        self.desktop_stubs()
        self.command("curl", "exit 22\n")
        cache = self.home / ".cache/dotfiles/chatgpt_amd64.deb.part"
        cache.parent.mkdir(parents=True)
        cache.write_text("stale incomplete download")
        self.run_bash('''setOptions
if installDesktopDeb chatgpt amd64 https://example.invalid/package.deb; then exit 99; fi
''')
        self.assertFalse(self.log.exists())
        self.assertFalse(cache.with_suffix("").exists())

    def test_vscode_uses_arm64_package_and_keeps_existing_cli(self):
        self.desktop_stubs("arm64")
        self.run_bash('''setOptions
function command() { if [[ "$*" == '-v code' ]]; then return 1; fi; builtin command "$@"; }
setVisualStudioCode
''', extra_env={"TEST_DEB_ARCHITECTURE": "arm64"})
        self.assertIn("https://update.code.visualstudio.com/latest/linux-deb-arm64/stable", self.log.read_text())
        self.log.unlink()
        self.command("code", "exit 0\n")
        self.run_bash('setOptions; setVisualStudioCode')
        self.assertFalse(self.log.exists())


if __name__ == "__main__":
    unittest.main()
