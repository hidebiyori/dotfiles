import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import venv


ROOT = Path(__file__).resolve().parents[1]
PIP_FIXTURE = '''import json
import os
from pathlib import Path
import sys

Path(os.environ["TEST_PIP_LOG"]).write_text(json.dumps(sys.argv[1:]))
status = int(os.environ.get("TEST_PIP_EXIT", "0"))
if status:
    raise SystemExit(status)
site = Path(__file__).resolve().parents[1]
(site / "yaml.py").write_text('__version__ = "6.0.3"' + chr(10) + '# installed fixture' + chr(10))
'''


class SkillPythonTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="dotfiles skill python ")
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)
        self.working = self.home / "working"
        self.working.mkdir()
        self.skill_env = self.home / ".local/share/codex-skill-python"
        # Use a temporary interpreter without pip; dependencies are local fixtures.
        venv.EnvBuilder(with_pip=False).create(self.skill_env)
        interpreter = self.skill_env / "bin/python"
        site = subprocess.run(
            [str(interpreter), "-I", "-c", "import sysconfig; print(sysconfig.get_path('purelib'))"],
            capture_output=True, text=True, check=True,
        )
        self.site = Path(site.stdout.strip())
        self.yaml = self.site / "yaml.py"
        pip = self.site / "pip"
        pip.mkdir()
        (pip / "__init__.py").write_text("")
        (pip / "__main__.py").write_text(PIP_FIXTURE)
        self.pip_log = self.home / "pip.json"
        self.shadow_log = self.home / "unexpected-import"
        self.environment = {
            **os.environ, "HOME": str(self.home), "TEST_PIP_LOG": str(self.pip_log),
        }
        for name in ("BASH_ENV", "PYTHONPATH", "PYTHONHOME", "PYTHONOPTIMIZE", "PYTHONUSERBASE", "TEST_PIP_EXIT"):
            self.environment.pop(name, None)

    def run_setup(self, **environment):
        return subprocess.run(
            ["bash", str(ROOT / "bin/setup-skill-python.sh")], cwd=self.working,
            env={**self.environment, **environment}, capture_output=True, text=True,
        )

    def shadow_module(self, directory, name, version="6.0.3"):
        (directory / (name + ".py")).write_text(
            "from pathlib import Path\n"
            f"Path({str(self.shadow_log)!r}).write_text('unexpected import')\n"
            f"__version__ = {version!r}\n"
        )

    def assert_success(self, result):
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PyYAML 6.0.3", result.stdout)
        self.assertFalse(self.shadow_log.exists())

    def test_ready_environment_is_reused_without_installing(self):
        self.yaml.write_text('__version__ = "6.0.3"\n')
        before = self.yaml.stat().st_ino
        result = self.run_setup()
        self.assert_success(result)
        self.assertFalse(self.pip_log.exists())
        self.assertEqual(self.yaml.stat().st_ino, before)

    def test_local_yaml_does_not_count_as_an_installed_dependency(self):
        self.shadow_module(self.working, "yaml")
        result = self.run_setup()
        self.assert_success(result)
        self.assertTrue(self.pip_log.exists())
        arguments = json.loads(self.pip_log.read_text())
        self.assertEqual(arguments[-2:], ["-r", str(ROOT / "bin/requirements-skill-python.txt")])

    def test_pythonpath_yaml_does_not_count_as_an_installed_dependency(self):
        injected = self.home / "injected"
        injected.mkdir()
        self.shadow_module(injected, "yaml")
        result = self.run_setup(PYTHONPATH=str(injected))
        self.assert_success(result)
        self.assertTrue(self.pip_log.exists())

    def test_local_yaml_does_not_reinstall_a_ready_dependency(self):
        self.yaml.write_text('__version__ = "6.0.3"\n')
        self.shadow_module(self.working, "yaml", version="0.0.0")
        result = self.run_setup()
        self.assert_success(result)
        self.assertFalse(self.pip_log.exists())

    def test_local_pip_does_not_intercept_dependency_installation(self):
        self.shadow_module(self.working, "pip")
        result = self.run_setup()
        self.assert_success(result)
        self.assertTrue(self.pip_log.exists())

    def test_pythonoptimize_does_not_skip_the_version_check(self):
        self.yaml.write_text('__version__ = "6.0.2"\n')
        result = self.run_setup(PYTHONOPTIMIZE="1")
        self.assert_success(result)
        self.assertTrue(self.pip_log.exists())

    def test_dependency_installation_failure_stops_without_reporting_success(self):
        result = self.run_setup(TEST_PIP_EXIT="17")
        self.assertEqual(result.returncode, 17)
        self.assertTrue(self.pip_log.exists())
        self.assertNotIn("Skill Python:", result.stdout)


if __name__ == "__main__":
    unittest.main()
