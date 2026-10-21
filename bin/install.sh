#!/bin/bash
### Common ###
GIT_ROOT="${HOME}/git"
ORG_NAME=hidebiyori
PJ_NAME=dotfiles
PJ_ROOT="${GIT_ROOT}/${PJ_NAME}"
PJ_URL="https://github.com/${ORG_NAME}/${PJ_NAME}.git"

function setOptions()
{
  # Do not trace credentials read from an existing Git configuration.
  set +x
  set -euo pipefail
}

function setDirectories()
{
  mkdir -p "${HOME}"/{.config,.vim/{backup,swap,undo},bin,var,tmp,old}
}

function isWsl()
{
  local kernel="${uname:-$(uname -a)}"
  [[ "${kernel}" == *Linux* ]] &&
    [[ -n "${WSL_DISTRO_NAME:-}" || -n "${WSL_INTEROP:-}" || "${kernel}" == *[Mm]icrosoft* || "${kernel}" == *WSL* ]]
}

function setGitRepository()
{
  local repositoryUrl="${1:?}"
  local repositoryName="$(echo ${repositoryUrl##*/} | sed 's/.git//g')"
  local targetPath="${2:-${GIT_ROOT}/${repositoryName}}"

  if [ -d "${targetPath}" ]; then
    local originUrl
    originUrl="$(git -C "${targetPath}" config --get remote.origin.url || true)"
    if [[ "${repositoryUrl}" == https://* && "${originUrl}" == https://* ]]; then
      local originRepository="${originUrl%%[?#]*}"
      originRepository="${originRepository#https://}"
      originRepository="https://${originRepository##*@}"
      if [[ "${originRepository}" == "${repositoryUrl}" && "${originUrl}" != "${repositoryUrl}" ]]; then
        git -C "${targetPath}" remote set-url origin "${repositoryUrl}"
      fi
    fi
    git -C "${targetPath}" pull --ff-only
  else
    git clone "${repositoryUrl}" "${targetPath}"
  fi
}

function setSymbolicLink()
{
  local srcRoot="${1:?}"
  local dstRoot="${2:?}"

  ls -A "${srcRoot}" | while read file; do
    [[ "${file}" == ".git" ]] && continue
    [[ "${file}" == ".DS_Store" ]] && continue

    local srcPath="${srcRoot}/${file}"
    local dstPath="${dstRoot}/${file}"

    # Project presets are copied explicitly into each repository, not HOME.
    [[ "${srcPath}" == "${PJ_ROOT}/src/project-presets" ]] && continue

    if isWsl && [[ "${srcPath}" == "${PJ_ROOT}/src/.sommelierrc" || "${srcPath}" == "${PJ_ROOT}/src/.config/Code" ]]; then
      continue
    fi

    # A manually linked directory already exposes the source tree. Recursing
    # into it would replace source files with links to themselves.
    if [[ "${srcPath}" -ef "${dstPath}" ]]; then
      continue
    fi

    if [ -d "${srcPath}" ]; then
      mkdir -p "${dstPath}"
      setSymbolicLink "${srcPath}" "${dstPath}"
    else
      ln -sfnv "${srcPath}" "${dstPath}"
    fi
  done
}

function setDirectoryLink()
{
  local target="${1:?}" destination="${2:?}"
  if [[ -L "${destination}" ]]; then
    if [[ "$(readlink "${destination}")" == "${target}" || "${target}" -ef "${destination}" ]]; then
      return
    fi
  elif [[ -e "${destination}" ]]; then
    echo "${destination}: 既存のディレクトリまたはファイルのため維持します。" >&2
    return
  fi
  ln -sfnv "${target}" "${destination}"
}

function copyFileIfChanged()
{
  local source="${1:?}" destination="${2:?}"
  if [[ "${source}" -ef "${destination}" ]] || cmp -s "${source}" "${destination}"; then
    return
  fi
  if [[ -d "${destination}" ]]; then
    echo "${destination}: ファイルのコピー先にディレクトリがあるため停止します。" >&2
    return 1
  fi
  cp "${source}" "${destination}"
}

function setCodexInstructions()
{
  local codexHome="${CODEX_HOME:-}"
  if [[ -z "${codexHome}" ]] && isWsl; then
    if ! command -v powershell.exe >/dev/null 2>&1 || ! command -v wslpath >/dev/null 2>&1; then
      echo 'WSL: Windows 側の Codex 共通指示を配置できません。CODEX_HOME を指定してください。' >&2
      return
    fi
    local windowsCodexHome
    windowsCodexHome="$(powershell.exe -NoProfile -NonInteractive -Command '
      $ErrorActionPreference = "Stop"
      [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
      if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $env:USERPROFILE ".codex" }
    ')" || return
    windowsCodexHome="${windowsCodexHome//$'\r'/}"
    codexHome="$(wslpath -u "${windowsCodexHome}")" || return
  fi
  [[ -n "${codexHome}" ]] || return 0
  if [[ "${codexHome}" != /* ]]; then
    echo 'CODEX_HOME は実行環境の絶対パスで指定してください。' >&2
    return 1
  fi
  mkdir -p "${codexHome}"
  # Copy for Windows apps as well: Linux symlinks on /mnt/c are not portable.
  copyFileIfChanged "${PJ_ROOT}/src/.codex/AGENTS.md" "${codexHome}/AGENTS.md"
}

function setBrew()
{
  # A previous child process may have installed brew without changing the
  # caller's PATH. Reuse that installation on the next invocation.
  local brewPath
  if ! command -v brew >/dev/null 2>&1; then
    for brewPath in "${HOME}/.config/brew/bin" /opt/homebrew/bin /usr/local/bin; do
      if [[ -x "${brewPath}/brew" ]]; then
        export PATH="${brewPath}:${PATH}"
        break
      fi
    done
  fi
  if command -v brew >/dev/null 2>&1; then
    brew update
    brew upgrade
  else
    # https://docs.brew.sh/Installation
    local targetPath="${HOME}/.config/brew"

    mkdir -p "${targetPath}"
    curl -L https://github.com/Homebrew/brew/tarball/master | tar xz --strip 1 -C "${targetPath}"
    export PATH="${targetPath}/bin:${PATH}"
    brew install bash-completion git jq pstree
    brew install --cask google-japanese-ime
    if ! brew doctor; then
      echo "Homebrew の導入は完了しました。brew doctor の案内を確認してください。" >&2
    fi
  fi
}

function setMacDesktopApps()
{
  local cask appPath
  local casks=(chatgpt google-chrome visual-studio-code)
  for cask in "${casks[@]}"; do
    if brew list --cask --versions "${cask}" >/dev/null 2>&1; then
      if [[ "${UPGRADE_DESKTOP_APPS:-0}" == "1" ]]; then
        brew upgrade --cask --greedy "${cask}"
      fi
      continue
    fi
    case "${cask}" in
      chatgpt) appPath="ChatGPT.app" ;;
      google-chrome) appPath="Google Chrome.app" ;;
      visual-studio-code) appPath="Visual Studio Code.app" ;;
    esac
    if [[ -d "/Applications/${appPath}" || -d "${HOME}/Applications/${appPath}" ]]; then
      echo "${appPath}: 既存のアプリを維持します。Homebrew 管理への変更は手動で行ってください。"
      continue
    fi
    brew install --cask "${cask}"
  done
}

function verifyDesktopDeb()
{
  local debPath="${1:?}" package="${2:?}" architecture="${3:?}" expectedSha256="${4:-}"
  if [[ "$(dpkg-deb --field "${debPath}" Package)" != "${package}" ||
        "$(dpkg-deb --field "${debPath}" Architecture)" != "${architecture}" ]]; then
    echo "${package}: パッケージの名前またはアーキテクチャが異なります。導入を中止します。" >&2
    return 1
  fi
  if [[ -n "${expectedSha256}" ]]; then
    local actualSha256
    actualSha256="$(sha256sum < "${debPath}")" || return
    if [[ "${actualSha256%% *}" != "${expectedSha256}" ]]; then
      echo "${package}: SHA256 が配布元の値と一致しません。導入を中止します。" >&2
      return 1
    fi
  fi
}

function installDesktopDeb()
{
  local package="${1:?}"
  local architecture="${2:?}"
  local packageUrl="${3:?}"
  local expectedSha256="${4:-}"
  local cacheRoot="${XDG_CACHE_HOME:-${HOME}/.cache}/dotfiles"
  local cachedDeb="${cacheRoot}/${package}_${architecture}.deb"
  local downloadedDeb="${cachedDeb}.part"
  mkdir -p "${cacheRoot}" || return
  if [[ ! -f "${cachedDeb}" ]]; then
    curl --fail --location --proto '=https' --tlsv1.2 \
      --user-agent 'dotfiles-desktop-setup/1.0 (+https://github.com/hidebiyori/dotfiles)' \
      --output "${downloadedDeb}" "${packageUrl}" || return
    verifyDesktopDeb "${downloadedDeb}" "${package}" "${architecture}" "${expectedSha256}" || return
    mv "${downloadedDeb}" "${cachedDeb}" || return
  fi
  verifyDesktopDeb "${cachedDeb}" "${package}" "${architecture}" "${expectedSha256}" || return
  sudo apt install "${cachedDeb}"
}

function getDesktopLinuxRelease()
{
  (. /etc/os-release; printf '%s:%s' "${ID}" "${VERSION_ID}")
}

function setCodexDesktop()
{
  local packageStatus queryExit=0
  packageStatus="$(dpkg-query -W -f='${Status}' chatgpt 2>/dev/null)" || queryExit=$?
  if (( queryExit > 1 )); then
    echo "Codex / ChatGPT: パッケージの導入状態を確認できません。導入を中止します。" >&2
    return 1
  fi
  if [[ "${packageStatus}" == 'install ok installed' ]]; then
    return
  fi
  local osVersion architecture
  osVersion="$(getDesktopLinuxRelease)"
  case "${osVersion}" in
    debian:13|ubuntu:24.04|ubuntu:26.04) ;;
    *)
      echo "Codex / ChatGPT: 新規導入は公式対象の Debian 13 / Ubuntu 24.04・26.04 に限ります。README.md を参照してください。" >&2
      return 1
      ;;
  esac
  architecture="$(dpkg --print-architecture)"
  case "${architecture}" in
    amd64|arm64) ;;
    *) echo "Codex / ChatGPT: 対応パッケージのないアーキテクチャです。" >&2; return 1 ;;
  esac
  installDesktopDeb chatgpt "${architecture}" \
    "https://persistent.oaistatic.com/codex-app-prod/linux/deb/latest/chatgpt_${architecture}.deb"
}

function setMise()
{
  if command -v mise >/dev/null 2>&1; then
    return
  elif [ -x "${HOME}/.local/bin/mise" ]; then
    export PATH="${HOME}/.local/bin:${PATH}"
    return
  fi

  if [[ "${uname}" =~ "Darwin" ]]; then
    brew install mise
  elif [[ "${uname}" =~ "Linux" ]]; then
    sudo apt update
    sudo apt install -y extrepo
    sudo extrepo enable mise
    sudo apt update
    sudo apt install -y mise
  else
    echo "mise: この OS では README.md の手動導入手順を参照してください。" >&2
    return 1
  fi
}

function setScreencapture()
{
  defaults write com.apple.screencapture location "${HOME}/Downloads"
  defaults write com.apple.screencapture name "s"
  defaults write com.apple.screencapture include-date -bool true
  defaults write com.apple.screencapture type png
  defaults read com.apple.screencapture
  # defaults delete com.apple.screencapture
}

function setApt()
{
  sudo apt update
  sudo apt upgrade
  local packages=(screen ca-certificates curl gh)
  if isWsl; then
    packages+=(git vim)
  fi
  sudo apt install "${packages[@]}"
}

function setJapanese()
{
  if which fcitx-autostart; then
    :
  else
    sudo apt install fcitx-mozc
    fcitx-autostart
    fcitx-configtool

    # memo
    # restart terminal
    # select "+", unselect "Only Show Current Language", Search "Mozc"
    # select "Global Config"
  fi
}

function setVisualStudioCode()
{
  if command -v code >/dev/null 2>&1; then
    return
  fi
  local architecture platform
  architecture="$(dpkg --print-architecture)"
  case "${architecture}" in
    amd64) platform=x64 ;;
    arm64) platform=arm64 ;;
    *) echo "VS Code: 対応パッケージのないアーキテクチャです。" >&2; return 1 ;;
  esac
  local cacheRoot="${XDG_CACHE_HOME:-${HOME}/.cache}/dotfiles"
  local metadata="${cacheRoot}/code_${architecture}.json"
  local metadataInput="${metadata}"
  mkdir -p "${cacheRoot}" || return
  if [[ ! -f "${metadata}" ]]; then
    metadataInput="${metadata}.part"
    curl --fail --location --proto '=https' --tlsv1.2 \
      --user-agent 'dotfiles-desktop-setup/1.0 (+https://github.com/hidebiyori/dotfiles)' \
      --output "${metadataInput}" "https://update.code.visualstudio.com/api/update/linux-deb-${platform}/stable/latest" || return
  fi
  local releaseInfo codeVersion codeSha256
  releaseInfo="$(python3 - "${metadataInput}" <<'PY'
import json
from pathlib import Path
import re
import sys
try:
    metadata = json.loads(Path(sys.argv[1]).read_text())
    version = metadata['productVersion']
    checksum = metadata['sha256hash']
    if not isinstance(version, str) or not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', version):
        raise ValueError('invalid product version')
    if not isinstance(checksum, str) or not re.fullmatch(r'[a-fA-F0-9]{64}', checksum):
        raise ValueError('invalid SHA256')
except (OSError, ValueError, KeyError, AssertionError, TypeError):
    sys.exit('VS Code: invalid version or SHA256 metadata; no package installed.')
print(version + '\t' + checksum.lower())
PY
)" || return
  IFS=$'\t' read -r codeVersion codeSha256 <<< "${releaseInfo}"
  if [[ "${metadataInput}" != "${metadata}" ]]; then
    mv "${metadataInput}" "${metadata}" || return
    sleep 1
  fi
  installDesktopDeb code "${architecture}" \
    "https://update.code.visualstudio.com/${codeVersion}/linux-deb-${platform}/stable" "${codeSha256}"
}

function setLink()
{
  local localPath="/mnt/chromeos/MyFiles"
  local drivePath="/mnt/chromeos/GoogleDrive/MyDrive"

  # required: Chrome OS Share with Linux
  setDirectoryLink "${localPath}/Downloads" "${HOME}/Downloads"
  setDirectoryLink "${drivePath}" "${HOME}/MyDrive"
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

function setMiseTools()
{
  # Read the linked global config without rewriting it or loading a project config.
  mise install --cd "${HOME}" --jobs 1
}

function setFlutter()
{
  # https://flutter.dev/docs/get-started/install/linux
  local targetPath="${HOME}/.config/flutter"
  export PATH="${targetPath}/bin:${PATH}"

  setGitRepository "https://github.com/flutter/flutter.git" "${targetPath}"
  flutter channel stable
  flutter precache
  flutter doctor
}

function main()
{
  setOptions
  uname="$(uname -a)"
  setDirectories
  setGitRepository "${PJ_URL}"
  setSymbolicLink "${PJ_ROOT}/src" "${HOME}"
  setCodexInstructions

  ### Mac ###
  if [[ "${uname}" =~ "Darwin" ]]; then
    setBrew
    brew list --versions gh >/dev/null 2>&1 || brew install gh
    setMacDesktopApps
    brew list --versions python >/dev/null 2>&1 || brew install python
    setScreencapture
    setMise


  ### Linux ###
  elif [[ "${uname}" =~ "Linux" ]]; then
    setApt
    sudo apt install -y python3-venv
    setMise
    if isWsl; then
      setWslIntegration
    else
      setJapanese
      setVisualStudioCode
      setCodexDesktop
      setLink
      python3 "${PJ_ROOT}/bin/setup-chatgpt-maximized.py"
    fi


  fi


  ### Common ###
  bash "${PJ_ROOT}/bin/setup-skill-python.sh"
  setMiseTools
  if [[ "${INSTALL_FLUTTER:-0}" == "1" ]]; then
    setFlutter
  fi
  echo "Success: ${0}"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
