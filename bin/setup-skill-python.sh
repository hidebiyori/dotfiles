#!/usr/bin/env bash
# Shared Python dependencies for Codex skill helpers, separate from project environments.
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
skill_env="${HOME}/.local/share/codex-skill-python"
requirements="${script_dir}/requirements-skill-python.txt"

if [ ! -x "${skill_env}/bin/python" ]; then
  if [ -e "${skill_env}" ]; then
    echo "既存の ${skill_env} に Python がありません。内容を確認してください。" >&2
    exit 1
  fi
  if ! command -v python3 >/dev/null 2>&1; then
    echo "Python 3 を先に導入してください（macOS: brew install python）。" >&2
    exit 1
  fi
  if ! python3 -c 'import venv, ensurepip' >/dev/null 2>&1; then
    echo "venv / ensurepip が必要です（Debian・Ubuntu: sudo apt install python3-venv）。" >&2
    exit 1
  fi
  python3 -m venv "${skill_env}"
fi

if ! "${skill_env}/bin/python" -c 'import yaml; assert yaml.__version__ == "6.0.3"' >/dev/null 2>&1; then
  "${skill_env}/bin/python" -m pip install --disable-pip-version-check -r "${requirements}"
fi
"${skill_env}/bin/python" -c 'import sys, yaml; print(f"Skill Python: {sys.executable} (PyYAML {yaml.__version__})")'
