import os
from pathlib import Path
import subprocess
import tempfile
import unittest


PROFILE = Path(__file__).resolve().parents[1] / "src/.bash_profile"
BASHRC = PROFILE.with_name(".bashrc")


class ShellProfileTests(unittest.TestCase):
    def test_profile_without_terminal_does_not_interrupt_commands(self):
        with tempfile.TemporaryDirectory(prefix="dotfiles profile ") as temporary:
            result = subprocess.run(
                ["bash", "--noprofile", "--norc", "-e", "-c",
                 'source "$1"; printf command-reached', "bash", str(PROFILE)],
                cwd=temporary, env={**os.environ, "HOME": temporary},
                stdin=subprocess.DEVNULL, capture_output=True, text=True,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "command-reached")
        self.assertEqual(result.stderr, "")


class HistoryPromptTests(unittest.TestCase):
    def run_bashrc(self, prompt_setup, execute='eval "$PROMPT_COMMAND"', history="fixture\n"):
        with tempfile.TemporaryDirectory(prefix="dotfiles history ") as temporary:
            fixture_home = Path(temporary) / "home"
            fixture_home.mkdir()
            (fixture_home / ".bash_history").write_text(history)
            environment = {**os.environ, "HOME": str(fixture_home), "TERM": "screen"}
            environment.pop("BASH_ENV", None)
            body = '''
function uname() { printf '%s\\n' 'Linux fixture'; }
function __git_ps1() { :; }
function history() { printf 'history %s\\n' "$*"; }
function custom_hook() { printf '%s\\n' custom; }
function another_hook() { printf '%s\\n' another; }
''' + prompt_setup + '\nfor cycle in 1 2 3; do source "$1"; done\n' + execute
            result = subprocess.run(
                ["bash", "--noprofile", "--norc", "-uec", body, "bash", str(BASHRC)],
                cwd=temporary, env=environment, capture_output=True, text=True,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        return result.stdout.splitlines()

    def test_reloads_run_history_and_existing_scalar_hook_once(self):
        self.assertEqual(self.run_bashrc("PROMPT_COMMAND=custom_hook"),
                         ["history -a", "history -c", "history -r", "custom"])

    def test_legacy_repeated_prefixes_are_collapsed(self):
        legacy = "history -a; history -c; history -r; " * 3
        self.assertEqual(self.run_bashrc("PROMPT_COMMAND='" + legacy + "custom_hook'"),
                         ["history -a", "history -c", "history -r", "custom"])

    def test_existing_array_hooks_are_preserved(self):
        self.assertEqual(self.run_bashrc("PROMPT_COMMAND=(custom_hook another_hook)",
                                        'for command in "${PROMPT_COMMAND[@]}"; do eval "$command"; done'),
                         ["history -a", "history -c", "history -r", "custom", "another"])

    def test_history_already_in_another_array_entry_is_not_added_again(self):
        self.assertEqual(self.run_bashrc(
            "PROMPT_COMMAND=(custom_hook 'history -a; history -c; history -r; another_hook')",
            'for command in "${PROMPT_COMMAND[@]}"; do eval "$command"; done'),
            ["custom", "history -a", "history -c", "history -r", "another"])

    def test_an_external_hook_before_history_is_preserved(self):
        self.assertEqual(self.run_bashrc(
            "PROMPT_COMMAND='another_hook; history -a; history -c; history -r; custom_hook'"),
            ["another", "history -a", "history -c", "history -r", "custom"])

    def test_unset_prompt_command_is_supported_with_nounset(self):
        self.assertEqual(self.run_bashrc("unset PROMPT_COMMAND"),
                         ["history -a", "history -c", "history -r"])

    def test_empty_history_does_not_change_custom_hooks(self):
        self.assertEqual(self.run_bashrc("PROMPT_COMMAND=custom_hook", history=""), ["custom"])


if __name__ == "__main__":
    unittest.main()
