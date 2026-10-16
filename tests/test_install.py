import hashlib
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
                     "UPGRADE_DESKTOP_APPS", "XDG_CACHE_HOME", "CODEX_HOME"):
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

    def test_wsl_browser_passes_url_as_data_and_propagates_failure(self):
        self.command("powershell.exe", 'cat > "$TEST_LOG"; exit "${TEST_BROWSER_EXIT:-0}"\n')
        url = "https://example.com/login?q=a&next=b#fragment"
        script = ROOT / "src/bin/wsl-browser"
        result = subprocess.run([str(script), url], env=self.env, capture_output=True)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(self.log.read_text(), url)
        result = subprocess.run([str(script), url], env={**self.env, "TEST_BROWSER_EXIT": "7"},
                                capture_output=True)
        self.assertEqual(result.returncode, 7)
        result = subprocess.run([str(script), "file:///tmp/example"], env=self.env,
                                capture_output=True)
        self.assertEqual(result.returncode, 2)

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

    def test_repository_can_be_reapplied_and_updated_without_merging_divergence(self):
        def git(*arguments, cwd=None):
            return subprocess.run(["git", *arguments], cwd=cwd or self.home, env=self.env,
                                  text=True, capture_output=True, check=True).stdout.strip()

        origin = self.home / "origin.git"
        author = self.home / "author"
        checkout = self.home / "checkout"
        git("init", "--bare", "--initial-branch=main", str(origin))
        git("clone", str(origin), str(author))
        git("config", "user.name", "Installer test", cwd=author)
        git("config", "user.email", "installer@example.invalid", cwd=author)

        def publish(contents):
            (author / "version").write_text(contents)
            git("add", "version", cwd=author)
            git("commit", "-m", "Update fixture", cwd=author)
            git("push", "origin", "main", cwd=author)

        publish("first")
        body = 'setOptions; setGitRepository ' + shlex.quote(str(origin)) + ' ' + shlex.quote(str(checkout))
        for _ in range(3):
            self.run_bash(body)
        publish("second")
        self.run_bash(body)
        self.assertEqual((checkout / "version").read_text(), "second")
        git("config", "user.name", "Installer test", cwd=checkout)
        git("config", "user.email", "installer@example.invalid", cwd=checkout)
        (checkout / "local-work").write_text("preserve")
        git("add", "local-work", cwd=checkout)
        git("commit", "-m", "Local fixture change", cwd=checkout)
        previous = git("rev-parse", "HEAD", cwd=checkout)
        publish("third")
        with self.assertRaises(subprocess.CalledProcessError):
            self.run_bash(body)
        self.assertEqual(git("rev-parse", "HEAD", cwd=checkout), previous)
        self.assertEqual((checkout / "local-work").read_text(), "preserve")

    def prepare_install(self, kernel):
        self.env["TEST_KERNEL"] = kernel
        self.env["CODEX_HOME"] = str(self.home / ".codex")
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

    def test_codex_instructions_copy_to_custom_home(self):
        repository = self.prepare_install("Linux example")
        target = self.home / "custom codex"
        self.run_bash("setCodexInstructions; setCodexInstructions", extra_env={"CODEX_HOME": str(target)})
        self.assertEqual((target / "AGENTS.md").read_bytes(),
                         (repository / "src/.codex/AGENTS.md").read_bytes())
        self.assertFalse((target / "AGENTS.md").is_symlink())

    def test_wsl_codex_instructions_discover_windows_home(self):
        repository = self.prepare_install("Linux Microsoft")
        target = self.home / "Windows Codex"
        self.command("powershell.exe", "printf '%s' 'C:/Users/example/.codex'\n")
        self.command("wslpath", 'printf "%s" "$TEST_CODEX_TARGET"\n')
        self.run_bash('uname="Linux Microsoft"; setCodexInstructions',
                      extra_env={"CODEX_HOME": "", "TEST_CODEX_TARGET": str(target)})
        self.assertEqual((target / "AGENTS.md").read_bytes(),
                         (repository / "src/.codex/AGENTS.md").read_bytes())

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
        self.assertIn("mise use --global npm@latest", calls)
        self.assertIn("mise exec node@lts npm@latest -- npm install -g firebase-tools", calls)
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
        self.assertIn("sudo apt install screen ca-certificates curl gh git vim", calls)
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

    def test_existing_directory_links_do_not_rewrite_source_files(self):
        repository = self.prepare_install("Linux example microsoft-standard-WSL2")
        source = repository / "src"
        hashes = {str(path.relative_to(source)): hashlib.sha256(path.read_bytes()).hexdigest()
                  for path in source.rglob('*') if path.is_file()}
        destinations = []
        for relative in (".agents/skills/japanese-commit", ".config/git"):
            destination = self.home / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.symlink_to(source / relative, target_is_directory=True)
            destinations.append((destination, destination.lstat().st_ino))
        for _ in range(3):
            self.run_bash('setOptions; setSymbolicLink "$PJ_ROOT/src" "$HOME"')
        self.assertEqual(hashes, {str(path.relative_to(source)): hashlib.sha256(path.read_bytes()).hexdigest()
                                  for path in source.rglob('*') if path.is_file()})
        for destination, inode in destinations:
            self.assertEqual(destination.lstat().st_ino, inode)

    def test_wsl_main_repeatedly_preserves_identical_links_and_copies(self):
        self.prepare_install("Linux example microsoft-standard-WSL2")
        appdata, _ = self.prepare_windows()
        self.run_bash("main")
        destinations = [self.home / name for name in (".bashrc", ".codex/AGENTS.md", "Downloads")]
        destinations += [appdata / "Code/User" / name for name in ("settings.json", "keybindings.json")]
        for path in destinations:
            os.utime(path, ns=(1_000_000_000, 1_000_000_000), follow_symlinks=False)
        before = [(path.lstat().st_ino, path.lstat().st_mtime_ns) for path in destinations]
        for _ in range(2):
            self.run_bash("main")
        self.assertEqual(before, [(path.lstat().st_ino, path.lstat().st_mtime_ns) for path in destinations])

    def test_windows_settings_that_already_reference_source_are_preserved(self):
        repository = self.prepare_install("Linux example microsoft-standard-WSL2")
        appdata, _ = self.prepare_windows()
        code_user = appdata / "Code/User"
        code_user.mkdir(parents=True)
        for name in ("settings.json", "keybindings.json"):
            (code_user / name).symlink_to(repository / "src/.config/Code/User" / name)
        for _ in range(3):
            self.run_bash("main")
        for name in ("settings.json", "keybindings.json"):
            self.assertTrue((code_user / name).is_symlink())

    def test_windows_settings_directory_collision_stops_without_nested_copy(self):
        self.prepare_install("Linux example microsoft-standard-WSL2")
        appdata, _ = self.prepare_windows()
        collision = appdata / "Code/User/settings.json"
        collision.mkdir(parents=True)
        with self.assertRaises(subprocess.CalledProcessError):
            self.run_bash("main")
        self.assertEqual(list(collision.iterdir()), [])

    def test_crostini_repeated_setup_preserves_real_downloads_and_drive_link(self):
        self.prepare_install("Linux example generic")
        downloads = self.home / "Downloads"
        downloads.mkdir()
        marker = downloads / "keep.txt"
        marker.write_text("keep")
        body = '''function setJapanese() { :; }
function setVisualStudioCode() { :; }
function setCodexDesktop() { :; }
main
'''
        self.run_bash(body)
        drive_inode = (self.home / "MyDrive").lstat().st_ino
        for _ in range(2):
            self.run_bash(body)
        self.assertEqual(list(downloads.iterdir()), [marker])
        self.assertEqual(marker.read_text(), "keep")
        self.assertEqual((self.home / "MyDrive").lstat().st_ino, drive_inode)

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
        for expected in ("sudo apt install screen ca-certificates curl gh\n", "japanese", "linux-code",
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
        for expected in ("brew update", "brew upgrade", "brew list --versions gh", "defaults write com.apple.screencapture", "skill-python",
                         "mise use --global node@lts", "mise use --global npm@latest",
                         "mise exec node@lts npm@latest -- npm install -g firebase-tools"):
            self.assertIn(expected, calls)
        self.assertNotIn("sudo", calls)
        self.assertNotIn("linux-launcher", calls)
        self.assertFalse((self.home / "Downloads").is_symlink())

    def test_homebrew_outside_inherited_path_is_reused_on_repeated_runs(self):
        brew = self.home / ".config/brew/bin/brew"
        brew.parent.mkdir(parents=True)
        brew.write_text('#!/bin/bash\nprintf "%s\\n" "brew $*" >> "$TEST_LOG"\n')
        brew.chmod(0o755)
        self.command("curl", "exit 99\n")
        for _ in range(3):
            self.run_bash("setOptions; setBrew", extra_env={"PATH": str(self.bin) + ":/usr/bin:/bin"})
        self.assertEqual(self.log.read_text().splitlines(), ["brew update", "brew upgrade"] * 3)

    def test_homebrew_diagnostic_warning_does_not_fail_successful_bootstrap(self):
        self.command("curl", "exit 0\n")
        self.command("tar", '''mkdir -p "$HOME/.config/brew/bin"
cat > "$HOME/.config/brew/bin/brew" <<'BREW'
#!/bin/bash
printf '%s\\n' "brew $*" >> "$TEST_LOG"
if [[ "$1" == doctor ]]; then exit 1; fi
BREW
chmod +x "$HOME/.config/brew/bin/brew"
''')
        environment = {"PATH": str(self.bin) + ":/usr/bin:/bin"}
        result = self.run_bash("setOptions; setBrew", extra_env=environment)
        self.assertIn("brew doctor の案内", result.stderr)
        self.run_bash("setOptions; setBrew", extra_env=environment)
        self.assertEqual(self.log.read_text().count("brew install --cask google-japanese-ime"), 1)

    def desktop_stubs(self, architecture="amd64"):
        self.command("dpkg", f'printf "%s\\n" "{architecture}"\n')
        self.command("sudo", 'printf "%s\\n" "sudo $*" >> "$TEST_LOG"\n')
        self.command("curl", '''printf '%s\\n' "curl $*" >> "$TEST_LOG"
download_url="${!#}"
while [[ $# -gt 0 ]]; do
  if [[ "$1" == --output ]]; then
    if [[ "$download_url" == */api/update/* ]]; then
      printf '{"productVersion":"1.142.0","sha256hash":"%s"}' "${TEST_CODE_SHA:-@@SHA256@@}" > "$2"
    else
      printf 'synthetic deb' > "$2"
    fi
  fi
  shift
done
'''.replace('@@SHA256@@', hashlib.sha256(b'synthetic deb').hexdigest()))
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
        self.assertIn("https://update.code.visualstudio.com/1.142.0/linux-deb-arm64/stable", self.log.read_text())
        self.log.unlink()
        self.command("code", "exit 0\n")
        self.run_bash('setOptions; setVisualStudioCode')
        self.assertFalse(self.log.exists())

    def test_vscode_checksum_mismatch_stops_before_install(self):
        self.desktop_stubs()
        result = self.run_bash('''setOptions
function command() { if [[ "$*" == '-v code' ]]; then return 1; fi; builtin command "$@"; }
if setVisualStudioCode; then exit 99; fi
''', extra_env={"TEST_CODE_SHA": "0" * 64})
        self.assertIn("SHA256", result.stderr)
        self.assertNotIn("sudo apt install", self.log.read_text())
        self.assertFalse((self.home / ".cache/dotfiles/code_amd64.deb").exists())

    def test_vscode_rechecks_cached_deb_checksum(self):
        self.desktop_stubs()
        body = '''setOptions
function command() { if [[ "$*" == '-v code' ]]; then return 1; fi; builtin command "$@"; }
setVisualStudioCode
'''
        self.run_bash(body)
        (self.home / ".cache/dotfiles/code_amd64.deb").write_text("corrupted cache")
        self.log.unlink()
        result = self.run_bash(body.replace('setVisualStudioCode\n', 'if setVisualStudioCode; then exit 99; fi\n'))
        self.assertIn("SHA256", result.stderr)
        self.assertFalse(self.log.exists())


if __name__ == "__main__":
    unittest.main()
