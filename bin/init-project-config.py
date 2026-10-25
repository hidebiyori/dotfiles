#!/usr/bin/env python3
"""Preview or create missing repository configuration; preserve existing files."""

import argparse
import json
from pathlib import Path
import sys


SOURCE = Path(__file__).resolve().parents[1] / "src/project-presets/common/templates"


class ConfigError(Exception):
    pass


def check_parents(project, path):
    for parent in path.relative_to(project).parents:
        current = project / parent
        if current.is_symlink() or (current.exists() and not current.is_dir()):
            raise ConfigError(f"{parent}: 通常のディレクトリが必要です")


def plan(project, github_actions=False, node=False, python=False):
    if not project.is_dir():
        raise ConfigError("対象には既存のディレクトリを指定してください")
    templates = {name: name for name in (".editorconfig", ".gitattributes")}
    changes = []
    kept = []
    if python:
        # A separate uv.toml would hide an existing [tool.uv] configuration.
        if (project / "pyproject.toml").exists() or (project / "pyproject.toml").is_symlink():
            kept.append("pyproject.toml (tool.uv の exclude-newer を個別に確認)")
        else:
            templates["uv.toml"] = "uv.toml"
    if github_actions or node:
        check_parents(project, project / ".github/dependabot.yml")
        if (project / ".github/dependabot.yaml").exists() or (
                project / ".github/dependabot.yaml").is_symlink():
            kept.append(".github/dependabot.yaml")
        else:
            templates[".github/dependabot.yml"] = (
                "dependabot-npm.yml" if node else "dependabot-actions.yml")
    if node:
        templates[".npmrc"] = ".npmrc"
        check_parents(project, project / ".github/workflows/check.yml")
        try:
            package = json.loads((project / "package.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raise ConfigError("package.json: 読み取り可能な JSON が必要です") from None
        if not isinstance(package, dict):
            raise ConfigError("package.json: JSON オブジェクトが必要です")
        if not (project / "package-lock.json").is_file():
            raise ConfigError("--node: package-lock.json が必要です")
        workflows = project / ".github/workflows"
        if any(workflows.glob("*.yml")) or any(workflows.glob("*.yaml")):
            kept.append(".github/workflows")
        else:
            scripts = package.get("scripts", {})
            required = ["check", "test:ci", "build"]
            dependencies = {}
            for field in ("dependencies", "devDependencies"):
                section = package.get(field, {})
                if not isinstance(section, dict):
                    raise ConfigError(f"package.json: {field} はオブジェクトで指定してください")
                dependencies.update(section)
            if "typescript" in dependencies:
                required.append("typecheck")
            if not isinstance(scripts, dict) or any(
                    not isinstance(scripts.get(key), str) or not scripts[key].strip()
                    for key in required):
                raise ConfigError("--node: check / test:ci / build と、TypeScript 利用時は "
                                  "typecheck の npm scripts が必要です")
            templates[".github/workflows/check.yml"] = "node-check.yml"
        existing_mise = [name for name in ("mise.toml", ".mise.toml")
                         if (project / name).exists() or (project / name).is_symlink()]
        if existing_mise:
            kept.extend(existing_mise)
        else:
            templates["mise.toml"] = "mise-node.toml"
    for name, source in templates.items():
        path = project / name
        check_parents(project, path)
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
    profile = parser.add_mutually_exclusive_group()
    profile.add_argument("--github-actions", action="store_true",
                         help="GitHub Actions 用の Dependabot 設定も追加する")
    profile.add_argument("--node", action="store_true",
                         help="npm の3日待機・Dependabot・Node CI の設定も追加する")
    profile.add_argument("--python", action="store_true",
                         help="uv の3日待機設定も追加する (既存 pyproject.toml は維持)")
    args = parser.parse_args()
    try:
        project = args.project.expanduser().resolve()
        changes, kept = plan(project, args.github_actions, args.node, args.python)
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
