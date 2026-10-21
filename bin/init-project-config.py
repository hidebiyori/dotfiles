#!/usr/bin/env python3
"""Preview or create missing repository configuration; preserve existing files."""

import argparse
from pathlib import Path
import sys


SOURCE = Path(__file__).resolve().parents[1] / "src/project-presets/common/templates"


class ConfigError(Exception):
    pass


def plan(project):
    if not project.is_dir():
        raise ConfigError("対象には既存のディレクトリを指定してください")
    templates = {name: name for name in (".editorconfig", ".gitattributes")}
    changes = []
    kept = []
    for name, source in templates.items():
        path = project / name
        for parent in path.relative_to(project).parents:
            current = project / parent
            if current.is_symlink() or (current.exists() and not current.is_dir()):
                raise ConfigError(f"{parent}: 通常のディレクトリが必要です")
        if path.is_symlink() or path.is_file():
            kept.append(name)
        elif path.exists():
            raise ConfigError(f"{name}: ファイル以外の配置があります")
        else:
            changes.append((path, (SOURCE / source).read_bytes()))
    return changes, kept


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path, help="初期設定を追加するリポジトリ")
    parser.add_argument("--write", action="store_true", help="存在しない設定だけを作成する")
    args = parser.parse_args()
    try:
        project = args.project.expanduser().resolve()
        changes, kept = plan(project)
        for path, contents in changes:
            if args.write:
                path.parent.mkdir(parents=True, exist_ok=True)
                # Exclusive creation also preserves files created after planning.
                with path.open("xb") as stream:
                    stream.write(contents)
            print(f"CREATE {path.relative_to(project)}")
        for name in kept:
            print(f"KEEP {name} (既存の設定を維持)")
        if changes and not args.write:
            print("プレビューのみ。反映するには --write を指定してください")
        return 0
    except (OSError, RuntimeError, ConfigError) as error:
        message = str(error) if isinstance(error, ConfigError) else type(error).__name__
        print(f"ERROR: {message}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
