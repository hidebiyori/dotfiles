#!/bin/bash
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../lib/install" && pwd)/load.sh" || { return 1 2>/dev/null || exit 1; }

function main()
{
  setOptions
  detectPlatform
  syncConfiguration
  applyPlatformSettings
  if ! findMise; then
    echo 'mise が見つかりません。初期セットアップを先に実行してください。' >&2
    return 1
  fi
  if [[ "${uname}" == *Darwin* ]]; then
    upgradeMacPackages
  else
    sudo apt update
    sudo apt upgrade
  fi
  mise upgrade --global --jobs 1 --no-prune
  if isWsl; then
    upgradeWindowsApps
  fi
  echo 'Success: 共通環境を更新しました。'
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
