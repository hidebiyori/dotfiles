#!/bin/bash
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../lib/install" && pwd)/load.sh" || { return 1 2>/dev/null || exit 1; }

function main()
{
  setOptions
  detectPlatform
  syncConfiguration
  applyPlatformSettings
  echo 'Success: 設定を同期しました。ツールの更新は up で実行できます。'
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
