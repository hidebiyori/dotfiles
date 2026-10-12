#!/usr/bin/python3
"""Install a user desktop override, leaving the packaged app untouched."""

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def desktop_argument(value):
    if "\n" in value or "\r" in value:
        raise ValueError("Unsupported newline in executable path")
    value = value.replace("%", "%%")
    if not any(character in value for character in " \t\"'\\><~|&;$*?#()`"):
        return value
    for character in ("\\", '"', "`", "$"):
        value = value.replace(character, "\\" + character)
    return '"' + value.replace("\\", "\\\\") + '"'


def rewrite_desktop(contents, executable):
    section = None
    result = []
    replaced = False
    for line in contents.splitlines(keepends=True):
        if line.startswith("["):
            section = line.strip()
        if section == "[Desktop Entry]" and line.startswith("Exec="):
            line = "Exec=" + desktop_argument(str(executable)) + " %U\n"
            replaced = True
        result.append(line)
    if not replaced:
        raise ValueError("Missing desktop entry command")
    return "".join(result)


def atomic_write(path, contents, mode=0o600):
    descriptor, name = tempfile.mkstemp(prefix=path.name + ".tmp-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(contents)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(name, mode)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def install(source_desktop, launcher_source, home, data_home, state_home):
    executable = home / ".local/bin/chatgpt-maximized"
    desktop = data_home / "applications/chatgpt.desktop"
    if executable.exists() or executable.is_symlink():
        if not executable.is_symlink() or executable.resolve() != launcher_source.resolve():
            raise ValueError("Launcher destination already in use")
    if desktop.is_symlink():
        raise ValueError("Desktop destination is a symbolic link")
    original = desktop.read_bytes() if desktop.exists() else None
    contents = original.decode() if original is not None else source_desktop.read_text()
    updated = rewrite_desktop(contents, executable).encode()
    executable.parent.mkdir(parents=True, exist_ok=True)
    desktop.parent.mkdir(parents=True, exist_ok=True)
    if not executable.is_symlink():
        executable.symlink_to(launcher_source.resolve())
    if updated != original:
        if original is not None:
            backup = state_home / "dotfiles/chatgpt.desktop.before-maximized-launcher"
            backup.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            atomic_write(backup, original)
        atomic_write(desktop, updated, mode=0o644)
    return desktop.parent


def main():
    source = Path("/usr/share/applications/chatgpt.desktop")
    if sys.platform != "linux" or not source.is_file() or not Path("/usr/bin/chatgpt").is_file():
        print("chatgpt-maximized: Linux アプリが未導入のため設定を省きます。")
        return 0
    home = Path.home()
    try:
        applications = install(
            source,
            Path(__file__).resolve().with_name("chatgpt-maximized.py"),
            home,
            Path(os.environ.get("XDG_DATA_HOME", str(home / ".local/share"))),
            Path(os.environ.get("XDG_STATE_HOME", str(home / ".local/state"))),
        )
        if shutil.which("update-desktop-database"):
            subprocess.run(["update-desktop-database", str(applications)], check=True)
    except (OSError, ValueError, subprocess.CalledProcessError):
        print("chatgpt-maximized: 設定に失敗しました。既存の配置先を確認してください。", file=sys.stderr)
        return 1
    print("chatgpt-maximized: アプリアイコンの起動先を設定しました。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
