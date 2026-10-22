#!/usr/bin/env bash

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

function setApt()
{
  sudo apt update
  local packages=(screen ca-certificates curl gh unzip)
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
