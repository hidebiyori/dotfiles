import subprocess
import unittest

import test_install as installer_tests


ROOT = installer_tests.ROOT


class UpdateUpgradeTests(unittest.TestCase):
    def setUp(self):
        self.fixture = installer_tests.InstallerTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def run_entrypoint(self, name, environment=None, check=True):
        return subprocess.run(
            ["bash", str(ROOT / "bin" / name)], cwd=self.fixture.home,
            env={**self.fixture.env, **(environment or {})},
            text=True, capture_output=True, check=check,
        )

    def test_settings_update_applies_each_platform_without_installers_or_upgrades(self):
        for kernel in ("Darwin fixture", "Linux generic", "Linux fixture Microsoft"):
            with self.subTest(kernel=kernel):
                self.fixture.env["TEST_KERNEL"] = kernel
                if not (self.fixture.home / "git/dotfiles").exists():
                    self.fixture.prepare_install(kernel)
                if "Microsoft" in kernel:
                    self.fixture.prepare_windows()
                self.fixture.log.unlink(missing_ok=True)
                result = self.run_entrypoint("update.sh")
                calls = self.fixture.log.read_text()
                self.assertIn("pull --ff-only", calls)
                self.assertTrue((self.fixture.home / ".bashrc").is_symlink())
                for forbidden in ("sudo ", "brew ", "mise ", "skill-python", "windows-upgrade", "flutter", "curl "):
                    self.assertNotIn(forbidden, calls)
                self.assertIn("設定を同期", result.stdout)

    def test_linux_upgrade_uses_global_mise_and_does_not_install_missing_tools(self):
        self.fixture.prepare_install("Linux generic")
        self.run_entrypoint("upgrade.sh")
        calls = self.fixture.log.read_text().splitlines()
        self.assertLess(next(index for index, line in enumerate(calls) if "pull --ff-only" in line),
                        calls.index("sudo apt update"))
        self.assertIn("sudo apt upgrade", calls)
        self.assertIn("mise upgrade --global --jobs 1 --no-prune", calls)
        for forbidden in ("apt install", "mise install", "skill-python", "flutter", "--bump", "windows-upgrade"):
            self.assertNotIn(forbidden, "\n".join(calls))

    def test_macos_upgrade_does_not_run_setup(self):
        self.fixture.prepare_install("Darwin fixture")
        self.run_entrypoint("upgrade.sh")
        calls = self.fixture.log.read_text()
        self.assertIn("brew upgrade --formula\n", calls)
        self.assertIn("brew upgrade --cask --greedy --no-quit chatgpt\n", calls)
        self.assertIn("mise upgrade --global --jobs 1 --no-prune", calls)
        for forbidden in ("brew install", "sudo ", "skill-python", "mise install"):
            self.assertNotIn(forbidden, calls)

    def test_wsl_upgrade_includes_windows_apps_and_propagates_failures(self):
        self.fixture.prepare_install("Linux fixture Microsoft")
        self.fixture.prepare_windows()
        result = self.run_entrypoint("upgrade.sh", {"TEST_WINDOWS_UPGRADE_EXIT": "7"}, check=False)
        self.assertEqual(result.returncode, 7)
        calls = self.fixture.log.read_text()
        self.assertIn("sudo apt upgrade", calls)
        self.assertIn("windows-upgrade", calls)
        self.assertIn("-File C:/fixture/upgrade-windows.ps1", calls)
        self.assertNotIn("-IncludeSteam", calls)
        self.assertNotIn("共通環境を更新しました", result.stdout)

    def test_package_upgrade_failure_stops_before_mise(self):
        self.fixture.prepare_install("Linux generic")
        self.fixture.command("sudo", 'printf "%s\\n" "sudo $*" >> "$TEST_LOG"; exit 9\n')
        result = self.run_entrypoint("upgrade.sh", check=False)
        self.assertEqual(result.returncode, 9)
        self.assertNotIn("mise upgrade", self.fixture.log.read_text())

    def test_configuration_error_stops_before_package_upgrade(self):
        self.fixture.prepare_install("Linux generic")
        (self.fixture.home / ".vimrc").mkdir()
        result = self.run_entrypoint("upgrade.sh", check=False)
        self.assertNotEqual(result.returncode, 0)
        calls = self.fixture.log.read_text()
        self.assertNotIn("sudo ", calls)
        self.assertNotIn("mise upgrade", calls)

    def test_missing_helper_stops_before_settings_or_package_changes(self):
        repository = self.fixture.prepare_install("Linux generic")
        (repository / "lib/install/wsl.sh").unlink()
        result = subprocess.run(
            ["bash", str(repository / "bin/update.sh")], cwd=self.fixture.home,
            env=self.fixture.env, text=True, capture_output=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.fixture.log.exists())
        self.assertFalse((self.fixture.home / ".bashrc").exists())

    def test_aliases_route_settings_and_upgrades_to_separate_scripts(self):
        repository = self.fixture.prepare_install("Linux generic")
        project = self.fixture.home / "project"
        project.mkdir()
        result = subprocess.run(
            ["bash", "--noprofile", "--norc", "-c", '''
function __git_ps1() { :; }
source "$1"
unalias r
function r() { printf '%s\\n' reloaded >> "$TEST_LOG"; }
shopt -s expand_aliases
u
printf '%s\\n' settings-done >> "$TEST_LOG"
up
''', "bash", str(repository / "src/.bashrc")],
            cwd=project, env=self.fixture.env, text=True, capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        settings, upgrades = self.fixture.log.read_text().split("settings-done\n")
        self.assertNotIn("sudo ", settings)
        self.assertNotIn("mise ", settings)
        self.assertIn("sudo apt upgrade", upgrades)
        self.assertIn("mise upgrade --global", upgrades)
        self.assertEqual(self.fixture.log.read_text().count("reloaded\n"), 2)

    def test_failed_pull_does_not_apply_settings_or_upgrade_packages(self):
        self.fixture.prepare_install("Linux generic")
        result = self.run_entrypoint("upgrade.sh", {"TEST_PULL_EXIT": "11"}, check=False)
        self.assertEqual(result.returncode, 11)
        self.assertFalse((self.fixture.home / ".bashrc").exists())
        for forbidden in ("sudo ", "mise ", "linux-launcher"):
            self.assertNotIn(forbidden, self.fixture.log.read_text())


if __name__ == "__main__":
    unittest.main()
