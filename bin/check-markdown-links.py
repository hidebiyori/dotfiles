#!/usr/bin/env python3
"""Check local Markdown links in Git-tracked files without network access."""

import argparse
import html
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit


LABEL = re.compile(r"\[((?:\\.|[^\[\]\\]|\[[^\[\]\n]*\])*)\]")
TAIL = re.compile(r"""\s*(?:(?:"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|\((?:\\.|[^)\\])*\))\s*)?\)""")


def blank(text):
    return "".join("\n" if char == "\n" else " " for char in text)


def prose(text):
    text = re.sub(r"<!--[\s\S]*?-->", lambda match: blank(match[0]), text)
    lines = []
    fence = None
    for line in text.splitlines(keepends=True):
        marker = re.match(r" {0,3}(`{3,}|~{3,})(.*)", line)
        if fence:
            lines.append(blank(line))
            if (marker and marker[1][0] == fence[0] and len(marker[1]) >= len(fence)
                    and not marker[2].strip()):
                fence = None
        elif marker:
            fence = marker[1]
            lines.append(blank(line))
        else:
            lines.append(line)
    text = "".join(lines)
    return re.sub(r"(?<![\\`])(`+)(?!`)[\s\S]*?(?<!`)\1(?!`)",
                  lambda match: blank(match[0]), text)


def destination(text, start):
    while start < len(text) and text[start].isspace():
        start += 1
    if start == len(text):
        return None
    if text[start] == "<":
        end = start + 1
        while end < len(text) and text[end] not in ">\n":
            end += 2 if text[end] == "\\" else 1
        return (text[start + 1:end], end + 1) if end < len(text) and text[end] == ">" else None
    end = start
    depth = 0
    while end < len(text):
        char = text[end]
        if char == "\\":
            end += 2
            continue
        if char.isspace() or (char == ")" and depth == 0):
            break
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        end += 1
    return (text[start:end], end) if depth == 0 else None


def reference(label):
    return " ".join(label.split()).casefold()


def links(text):
    text = prose(text)
    definitions = {}
    lines = []
    for line in text.splitlines(keepends=True):
        match = re.match(r" {0,3}\[([^\]\n]+)\]:[ \t]*", line)
        value = destination(line, match.end()) if match else None
        if value:
            definitions.setdefault(reference(match[1]), value[0])
            lines.append(blank(line))
        else:
            lines.append(line)
    text = "".join(lines)
    consumed = 0
    for match in LABEL.finditer(text):
        if match.start() < consumed:
            continue
        escapes = 0
        before = match.start() - 1
        while before >= 0 and text[before] == "\\":
            escapes += 1
            before -= 1
        if escapes % 2:
            continue
        end = match.end()
        line = text.count("\n", 0, match.start()) + 1
        if text[end:end + 1] == "(":
            value = destination(text, end + 1)
            tail = TAIL.match(text, value[1]) if value else None
            if tail:
                consumed = tail.end()
                yield line, value[0]
        elif text[end:end + 1] == "[":
            label = re.match(r"\[([^\]\n]*)\]", text[end:])
            if label:
                value = definitions.get(reference(label[1] or match[1]))
                if value is not None:
                    consumed = end + label.end()
                    yield line, value
                elif reference(match[1]) in definitions:
                    yield line, definitions[reference(match[1])]
        elif reference(match[1]) in definitions:
            yield line, definitions[reference(match[1])]


def local_path(value):
    value = html.unescape(re.sub(r"\\([\\`*{}\[\]()#+.!_<> -])", r"\1", value))
    if value.startswith(("/", "\\")) or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", value):
        return None
    path = unquote(urlsplit(value).path)
    return path or None


def check(root):
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z", "--", "*.md", "*.markdown"],
        capture_output=True, check=True)
    documents = checked = skipped = failures = errors = 0
    for name in result.stdout.split(b"\0"):
        if not name:
            continue
        relative = Path(os.fsdecode(name))
        source = root / relative
        label = json.dumps(relative.as_posix(), ensure_ascii=False)
        if source.is_symlink():
            skipped += 1
            continue
        try:
            text = source.read_text(encoding="utf-8-sig")
            documents += 1
            for line, value in links(text):
                target = local_path(value)
                if target is None:
                    continue
                checked += 1
                resolved = (source.parent / target).resolve()
                try:
                    resolved.relative_to(root)
                except ValueError:
                    failures += 1
                    print(f"{label}:{line}: リポジトリ外への相対リンクです")
                    continue
                if not resolved.exists():
                    failures += 1
                    # Destinations can contain credentials; never print their value.
                    print(f"{label}:{line}: リンクの参照先が存在しません")
        except (OSError, ValueError, RuntimeError):
            errors += 1
            print(f"{label}: 文書またはリンクを確認できません")
    print(f"Markdown {documents}文書 / 相対リンク {checked}件 / "
          f"問題 {failures}件 / 確認エラー {errors}件 / リンク文書の除外 {skipped}件")
    return 2 if errors else 1 if failures else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", nargs="?", type=Path, default=Path.cwd(),
                        help="確認する Git リポジトリ（既定: 現在のディレクトリ）")
    args = parser.parse_args()
    try:
        project = args.project.expanduser().resolve()
        result = subprocess.run(["git", "-C", str(project), "rev-parse", "--show-toplevel"],
                                capture_output=True, check=True)
        return check(Path(os.fsdecode(result.stdout).strip()).resolve())
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError):
        print("ERROR: 読み取り可能な Git リポジトリを指定してください", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
