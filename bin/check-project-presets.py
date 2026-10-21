#!/usr/bin/env python3
"""Check explicitly selected Next.js repositories sequentially, without writes."""

import argparse
import json
from pathlib import Path
import subprocess
import sys


SYNC = Path(__file__).resolve().with_name("sync-project-presets.py")


def selected_projects(arguments, projects_file):
    projects = list(arguments)
    if projects_file:
        source = projects_file.expanduser().resolve()
        entries = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(entries, list) or any(
                not isinstance(entry, str) or not entry.strip() for entry in entries):
            raise ValueError("invalid project list")
        for entry in entries:
            path = Path(entry).expanduser()
            projects.append(path if path.is_absolute() else source.parent / path)
    if not projects:
        raise ValueError("no projects")
    return projects


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("projects", nargs="*", type=Path, help="確認する Next.js リポジトリ")
    parser.add_argument("--projects-file", type=Path, help="対象パスの JSON 配列を保存したローカルファイル")
    args = parser.parse_args()
    try:
        projects = selected_projects(args.projects, args.projects_file)
    except (OSError, ValueError, RuntimeError):
        print("ERROR: 対象パス、またはパス文字列の JSON 配列を指定してください", file=sys.stderr)
        return 2

    counts = [0, 0, 0]
    seen = set()
    for supplied in projects:
        try:
            project = supplied.expanduser().resolve()
            if project in seen:
                continue
            seen.add(project)
            result = subprocess.run(
                [sys.executable, "-B", str(SYNC), str(project), "--check"],
                capture_output=True, timeout=30)
            code = result.returncode if result.returncode in (0, 1) else 2
        except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired):
            code = 2
        counts[code] += 1
        label = json.dumps(supplied.name, ensure_ascii=False)
        status = ("OK", "UPDATE", "ERROR")[code]
        message = ("同期済み", "未同期", "確認できません。対象と単体の --check を確認してください")[code]
        # Do not forward child output: config contents and absolute paths stay private.
        print(f"{status} {label}: {message}")
    print(f"確認: {sum(counts)}件（同期済み {counts[0]} / 未同期 {counts[1]} / エラー {counts[2]}）")
    return 2 if counts[2] else 1 if counts[1] else 0


if __name__ == "__main__":
    sys.exit(main())
