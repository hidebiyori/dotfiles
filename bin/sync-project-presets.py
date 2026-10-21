#!/usr/bin/env python3
"""Copy reviewed Next.js presets into a project without runtime dotfiles links."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile


SOURCE = Path(__file__).resolve().parents[1] / "src/project-presets/nextjs"
DESTINATION = Path("config/presets/nextjs")
PRESETS = ("biome-next.json", "tsconfig-next.json")
MANIFEST = "manifest.json"


class PresetError(Exception):
    pass


def digest(contents):
    return hashlib.sha256(contents).hexdigest()


def read_json(path):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise PresetError(f"{path.name}: 読み取り可能な JSON が必要です") from None
    if not isinstance(value, dict):
        raise PresetError(f"{path.name}: JSON オブジェクトが必要です")
    return value


def check_destination(project):
    current = project
    for part in DESTINATION.parts:
        current = current / part
        if current.is_symlink() or (current.exists() and not current.is_dir()):
            raise PresetError(f"{current.relative_to(project)}: 通常のディレクトリが必要です")
    for name in (*PRESETS, MANIFEST):
        path = current / name
        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise PresetError(f"{path.relative_to(project)}: 通常のファイルが必要です")


def atomic_write(path, contents):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".preset-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(contents)
        os.chmod(temporary, 0o644)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def plan(project, initialize):
    package = read_json(project / "package.json")
    dependencies = {}
    for field in ("dependencies", "devDependencies"):
        section = package.get(field, {})
        if not isinstance(section, dict):
            raise PresetError(f"package.json: {field} はオブジェクトで指定してください")
        dependencies.update(section)
    if "next" not in dependencies:
        raise PresetError("package.json: Next.js プロジェクトを指定してください")

    check_destination(project)
    destination = project / DESTINATION
    recorded = {}
    manifest_path = destination / MANIFEST
    if manifest_path.exists():
        manifest = read_json(manifest_path)
        recorded = manifest.get("files")
        if (manifest.get("formatVersion") != 1 or manifest.get("profile") != "nextjs"
                or not isinstance(recorded, dict) or set(recorded) != set(PRESETS)
                or any(not isinstance(value, str) for value in recorded.values())):
            raise PresetError("manifest.json: 対応していない管理情報です")

    changes = []
    hashes = {}
    for name in PRESETS:
        read_json(SOURCE / name)
        contents = (SOURCE / name).read_bytes()
        hashes[name] = digest(contents)
        path = destination / name
        if path.exists():
            previous = path.read_bytes()
            if previous == contents:
                continue
            if digest(previous) != recorded.get(name):
                raise PresetError(
                    f"{path.relative_to(project)}: 独自の変更があります。"
                    "プロジェクト直下の設定へ移してから同期してください")
        changes.append((path, contents))

    metadata = {"formatVersion": 1, "profile": "nextjs", "files": hashes}
    contents = (json.dumps(metadata, indent=2) + "\n").encode("utf-8")
    if not manifest_path.exists() or manifest_path.read_bytes() != contents:
        changes.append((manifest_path, contents))

    kept = []
    if initialize:
        templates = ["biome.json", ".editorconfig", "mise.toml"]
        if "typescript" in dependencies:
            templates.append("tsconfig.json")
        for name in templates:
            alternatives = {
                "biome.json": ("biome.json", "biome.jsonc"),
                "mise.toml": ("mise.toml", ".mise.toml"),
            }.get(name, (name,))
            existing = [project / item for item in alternatives
                        if (project / item).exists() or (project / item).is_symlink()]
            if existing:
                kept.extend(path.name for path in existing)
            else:
                changes.append((project / name, (SOURCE / "templates" / name).read_bytes()))
    return changes, kept


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path, help="対象 Next.js プロジェクトのディレクトリ")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true", help="表示した管理対象ファイルを更新する")
    mode.add_argument("--check", action="store_true", help="未同期なら終了コード 1 を返す")
    parser.add_argument("--init", action="store_true", help="存在しないルート設定だけ作成する")
    args = parser.parse_args()
    project = args.project.expanduser().resolve()
    try:
        changes, kept = plan(project, args.init)
        for path, contents in changes:
            action = "UPDATE" if path.exists() else "CREATE"
            if args.write:
                atomic_write(path, contents)
            print(f"{action} {path.relative_to(project)}")
        for name in kept:
            print(f"KEEP {name} (既存の設定を維持。継承設定は docs/project-presets.md を参照)")
        if not changes:
            print("共通プリセットは同期済みです")
        elif not args.write and not args.check:
            print("プレビューのみ。反映するには --write を指定してください")
        return 1 if args.check and changes else 0
    except (OSError, PresetError) as error:
        # OS errors may contain private absolute paths; report only the error kind.
        message = str(error) if isinstance(error, PresetError) else type(error).__name__
        print(f"ERROR: {message}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
