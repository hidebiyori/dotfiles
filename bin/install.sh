#!/bin/bash
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../lib/install" && pwd)/load.sh" || { return 1 2>/dev/null || exit 1; }

function main()
{
  setOptions
  detectPlatform
  syncConfiguration

  if [[ "${uname}" == *Darwin* ]]; then
    setBrew
    setMacPackages
    setMacDesktopApps
    setMise
  else
    setApt
    sudo apt install -y python3-venv
    setMise
    if ! isWsl; then
      setJapanese
      setVisualStudioCode
      setCodexDesktop
    fi
  fi

  applyPlatformSettings
  bash "${PJ_ROOT}/bin/setup-skill-python.sh"
  setMiseTools
  if [[ "${INSTALL_FLUTTER:-0}" == "1" ]]; then
    setFlutter
  fi
  echo "Success: 初期セットアップが完了しました。"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  runUpdatedCommand install.sh "$@"
fi
