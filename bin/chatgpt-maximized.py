#!/usr/bin/python3
"""Restore maximized Codex/ChatGPT windows before starting the Linux app."""

import fcntl
import json
import math
import os
from pathlib import Path
import sys
import tempfile


WINDOW_KEY = "electron-main-window-bounds"
APP_LAUNCHER = Path("/usr/bin/chatgpt")


def app_is_running(app_binary):
    # Renderer processes also count: never change state while the app is alive.
    for process in Path("/proc").iterdir():
        if not process.name.isdecimal():
            continue
        try:
            if process.stat().st_uid == os.getuid():
                target = os.readlink(process / "exe")
                if Path(target.removesuffix(" (deleted)")) == app_binary:
                    return True
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
    return False


def atomic_write(path, contents):
    # State and its backup can contain private data; keep both user-readable only.
    descriptor, name = tempfile.mkstemp(prefix=path.name + ".tmp-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(contents)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def prepare_state(state_path, running):
    if running():
        return "app-running"
    state_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with state_path.with_name(".maximized-launcher.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if running():
            return "app-running"
        if state_path.is_symlink():
            raise ValueError("Symbolic state file")
        original = state_path.read_bytes() if state_path.exists() else None
        state = json.loads(original) if original is not None else {}
        if not isinstance(state, dict):
            raise ValueError("Invalid state object")
        bounds = state.get(WINDOW_KEY, {"x": 0, "y": 0, "width": 1000, "height": 800})
        if not isinstance(bounds, dict) or any(
            isinstance(bounds.get(key), bool)
            or not isinstance(bounds.get(key), (int, float))
            or not math.isfinite(bounds[key])
            for key in ("x", "y", "width", "height")
        ):
            raise ValueError("Invalid window bounds")
        if bounds.get("isMaximized") is True:
            return "already-maximized"
        bounds["isMaximized"] = True
        state[WINDOW_KEY] = bounds
        updated = (json.dumps(state, ensure_ascii=False, separators=(",", ":")) + "\n").encode()
        # Check again just before writing, including launches through other routes.
        if running():
            return "app-running"
        current = state_path.read_bytes() if state_path.exists() else None
        if current != original:
            return "state-changed"
        if original is not None:
            atomic_write(state_path.with_name(state_path.name + ".before-maximized-launcher"), original)
        atomic_write(state_path, updated)
        return "corrected"


def main(arguments=None):
    arguments = sys.argv[1:] if arguments is None else arguments
    prepare_only = arguments == ["--prepare-only"]
    if not APP_LAUNCHER.is_file():
        print("chatgpt-maximized: アプリが見つかりません。", file=sys.stderr)
        return 1
    app_binary = (APP_LAUNCHER.resolve().parent / "ChatGPT").resolve()
    codex_home = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex").expanduser()
    try:
        status = prepare_state(codex_home / ".codex-global-state.json", lambda: app_is_running(app_binary))
    except (OSError, ValueError):
        # Do not print exception text or any state values; still allow normal startup.
        print("chatgpt-maximized: 保存情報を変更できないため、補正を省きます。", file=sys.stderr)
        if prepare_only:
            return 1
    else:
        if prepare_only:
            print("chatgpt-maximized: " + status)
            return 0
    os.execv(str(APP_LAUNCHER), [str(APP_LAUNCHER), *arguments])


if __name__ == "__main__":
    sys.exit(main())
