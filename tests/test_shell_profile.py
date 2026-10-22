import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


PROFILE = Path(__file__).resolve().parents[1] / "src/.bash_profile"
BASHRC = PROFILE.with_name(".bashrc")


class ShellProfileTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="dotfiles profile ")
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)
        (self.home / ".bashrc").symlink_to(BASHRC)
        (self.home / "bin").mkdir()
        self.log = self.home / "screen.log"
        screen = self.home / "bin/screen"
        screen.write_text('#!/bin/bash\nprintf "%s\\n" "$*" >> "$TEST_SCREEN_LOG"\n')
        screen.chmod(0o755)
        mise = self.home / "bin/mise"
        mise.write_text("#!/bin/bash\nexit 0\n")
        mise.chmod(0o755)
        self.environment = {
            **os.environ, "HOME": str(self.home), "TERM": "xterm",
            "TEST_SCREEN_LOG": str(self.log),
        }
        self.environment.pop("BASH_ENV", None)

    def run_profile(self, arguments=(), terminal=False, cwd=None, term="xterm"):
        command = ["bash", "--noprofile", "--norc", *arguments, "-e", "-c",
                   'source "$1"; printf command-reached', "bash", str(PROFILE)]
        options = {
            "cwd": cwd or self.home, "env": {**self.environment, "TERM": term},
            "stderr": subprocess.PIPE, "text": True, "timeout": 10,
        }
        if terminal:
            master, slave = os.openpty()
            try:
                result = subprocess.run(command, stdin=slave, stdout=slave, **options)
                self.assertEqual(result.returncode, 0, result.stderr)
                # The marker is short enough to fit in the PTY buffer before reading.
                self.assertIn(b"command-reached", os.read(master, 4096))
            finally:
                os.close(slave)
                os.close(master)
        else:
            result = subprocess.run(command, stdin=subprocess.DEVNULL,
                                    stdout=subprocess.PIPE, **options)
            self.assertEqual(result.stdout, "command-reached", result.stderr)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result

    def test_profile_without_terminal_does_not_interrupt_commands(self):
        result = self.run_profile()
        self.assertEqual(result.stderr, "")
        self.assertFalse(self.log.exists())

    def test_noninteractive_alias_expansion_does_not_start_screen(self):
        self.run_profile(arguments=("-O", "expand_aliases"))
        self.assertFalse(self.log.exists())

    def test_noninteractive_shell_with_terminal_does_not_start_screen(self):
        self.run_profile(terminal=True)
        self.assertFalse(self.log.exists())

    def test_interactive_shell_without_terminal_does_not_start_screen(self):
        self.run_profile(arguments=("-i",))
        self.assertFalse(self.log.exists())

    def test_interactive_terminal_at_home_still_starts_screen(self):
        self.run_profile(arguments=("-i",), terminal=True)
        self.assertEqual(self.log.read_text(), "-U -D -R\n")

    def test_interactive_terminal_inside_screen_does_not_start_another_screen(self):
        self.run_profile(arguments=("-i",), terminal=True, term="screen-256color")
        self.assertFalse(self.log.exists())

    def test_interactive_terminal_outside_home_does_not_start_screen(self):
        self.run_profile(arguments=("-i",), terminal=True, cwd=self.home.parent)
        self.assertFalse(self.log.exists())


class PathReloadTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="dotfiles-path-")
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name) / "home"
        self.home.mkdir()
        (self.home / ".bash_profile").symlink_to(PROFILE)
        (self.home / ".bashrc").symlink_to(BASHRC)
        self.environment = {**os.environ, "HOME": str(self.home), "TERM": "xterm"}
        self.environment.pop("BASH_ENV", None)
        self.prefix = [str(self.home / "bin"), str(self.home / ".config/flutter/bin"),
                       "/usr/local/bin", "/usr/sbin", "/usr/bin", "/bin"]

    def reload_paths(self, initial, unset=False):
        body = '''
function uname() { printf '%s\\n' 'Linux fixture'; }
function __git_ps1() { :; }
if [[ "$3" == unset ]]; then unset PATH; else PATH="$2"; fi
source "$1"
printf '%s\\0' "$PATH"
shopt -s expand_aliases
r
printf '%s\\0' "$PATH"
r
printf '%s\\0' "$PATH"
'''
        result = subprocess.run(
            [shutil.which("bash"), "--noprofile", "--norc", "-uec", body,
             "bash", str(PROFILE), initial, "unset" if unset else "set"],
            cwd=self.home.parent, env=self.environment, capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        paths = [value.split(":") for value in result.stdout.removesuffix("\0").split("\0")]
        self.assertEqual(len(paths), 3)
        self.assertEqual(paths[0], paths[1])
        self.assertEqual(paths[1], paths[2])
        return paths[0]

    def test_reloads_keep_priority_and_collapse_existing_duplicates(self):
        initial = "/custom/one:/usr/bin:/custom/two:/usr/bin:/bin:/custom/one"
        self.assertEqual(self.reload_paths(initial), self.prefix + ["/custom/one", "/custom/two"])

    def test_explicit_empty_entries_keep_their_position_once(self):
        self.assertEqual(self.reload_paths(":/custom/one::/bin:"), self.prefix + ["", "/custom/one"])

    def test_relative_paths_spaces_and_glob_characters_are_literal(self):
        initial = "relative bin:/custom/[abc]*:$LITERAL_DIR/one:relative bin:/custom/[abc]*"
        expected = self.prefix + ["relative bin", "/custom/[abc]*", "$LITERAL_DIR/one"]
        self.assertEqual(self.reload_paths(initial), expected)

    def test_empty_path_adds_managed_paths_without_inserting_current_directory(self):
        self.assertEqual(self.reload_paths(""), self.prefix)

    def test_unset_path_is_supported_with_nounset(self):
        self.assertEqual(self.reload_paths("", unset=True), self.prefix)


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
