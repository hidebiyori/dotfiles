#!/usr/bin/env bash

function upgradeWindowsApps()
{
  if ! command -v powershell.exe >/dev/null 2>&1 || ! command -v wslpath >/dev/null 2>&1; then
    echo 'Windows アプリを更新できません。WSL の Windows 実行ファイル連携を確認してください。' >&2
    return 1
  fi
  local windowsScript
  windowsScript="$(wslpath -w "${PJ_ROOT}/bin/upgrade-windows.ps1")" || return
  powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "${windowsScript}"
}

function setWslIntegration()
{
  echo "WSL: Windows 版 VS Code と WSL 拡張、Windows 側の日本語入力を使用します。"
  if ! command -v powershell.exe >/dev/null 2>&1 || ! command -v wslpath >/dev/null 2>&1; then
    echo "WSL: Windows 連携を利用できないため Downloads と VS Code 設定の反映を省きます。README.md を参照してください。" >&2
    return
  fi

  local windowsFolders
  if ! windowsFolders="$(powershell.exe -NoLogo -NoProfile -NonInteractive -Command '
    $ErrorActionPreference = "Stop"
    [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
    [Environment]::GetFolderPath("ApplicationData")
    (New-Object -ComObject Shell.Application).NameSpace("shell:Downloads").Self.Path
  ')"; then
    echo "WSL: Windows のフォルダ取得に失敗したため Downloads と VS Code 設定の反映を省きます。" >&2
    return
  fi
  windowsFolders="${windowsFolders//$'\r'/}"
  if [[ "${windowsFolders}" != *$'\n'* ]]; then
    echo "WSL: Windows のフォルダ情報が不足しているため連携設定を省きます。" >&2
    return
  fi

  local windowsAppData windowsDownloads
  if windowsDownloads="$(wslpath -u "${windowsFolders#*$'\n'}")" && [[ -d "${windowsDownloads}" ]]; then
    setDirectoryLink "${windowsDownloads}" "${HOME}/Downloads"
  else
    echo "WSL: Windows の Downloads にアクセスできないためリンク作成を省きます。" >&2
  fi

  if windowsAppData="$(wslpath -u "${windowsFolders%%$'\n'*}")" && [[ -d "${windowsAppData}" ]]; then
    local codeUser="${windowsAppData}/Code/User"
    mkdir -p "${codeUser}"
    copyFileIfChanged "${PJ_ROOT}/src/.config/Code/User/settings.json" "${codeUser}/settings.json"
    copyFileIfChanged "${PJ_ROOT}/src/.config/Code/User/keybindings.json" "${codeUser}/keybindings.json"
    echo "WSL: Windows 版 VS Code の既定プロファイル設定を反映しました。"
  else
    echo "WSL: Windows の AppData にアクセスできないため VS Code 設定の反映を省きます。" >&2
  fi
}
