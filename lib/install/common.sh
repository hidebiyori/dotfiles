#!/usr/bin/env bash

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

function detectPlatform()
{
  uname="$(uname -a)"
  if [[ "${uname}" != *Darwin* && "${uname}" != *Linux* ]]; then
    echo 'Mac または apt を使う Linux / WSL で実行してください。' >&2
    return 1
  fi
}

function runUpdatedCommand()
{
  local entrypoint="${1:?}"
  shift
  setOptions
  detectPlatform
  setGitRepository "${PJ_URL}"
  # Source the fetched entry point in a fresh shell without running its bootstrap twice.
  exec bash -c 'source "$1" || exit; shift; main "$@"' bash "${PJ_ROOT}/bin/${entrypoint}" "$@"
}

function syncConfiguration()
{
  setDirectories
  setSymbolicLink "${PJ_ROOT}/src" "${HOME}"
  setCodexInstructions
}

function applyPlatformSettings()
{
  if [[ "${uname}" == *Darwin* ]]; then
    setScreencapture
  elif isWsl; then
    setWslIntegration
  else
    setLink
    python3 "${PJ_ROOT}/bin/setup-chatgpt-maximized.py"
  fi
}

function isWsl()
{
  local kernel="${uname:-$(uname -a)}"
  [[ "${kernel}" == *Linux* ]] &&
    [[ -n "${WSL_DISTRO_NAME:-}" || -n "${WSL_INTEROP:-}" || "${kernel}" == *[Mm]icrosoft* || "${kernel}" == *WSL* ]]
}

function gitRepositoryIdentity()
{
  local repositoryUrl="${1:?}"
  case "${repositoryUrl}" in
    https://*)
      repositoryUrl="${repositoryUrl%%[?#]*}"
      repositoryUrl="${repositoryUrl#https://}"
      local authority="${repositoryUrl%%/*}"
      repositoryUrl="https://${authority##*@}${repositoryUrl#"${authority}"}"
      ;;
    git@github.com:*) repositoryUrl="https://github.com/${repositoryUrl#git@github.com:}" ;;
    ssh://git@github.com/*) repositoryUrl="https://github.com/${repositoryUrl#ssh://git@github.com/}" ;;
  esac
  if [[ "${repositoryUrl}" == https://github.com/* ]]; then
    repositoryUrl="${repositoryUrl%.git}"
  fi
  printf '%s' "${repositoryUrl}"
}

function setGitRepository()
{
  local repositoryUrl="${1:?}"
  local repositoryName="${repositoryUrl##*/}"
  repositoryName="${repositoryName%.git}"
  local targetPath="${2:-${GIT_ROOT}/${repositoryName}}"

  if [[ -e "${targetPath}" || -L "${targetPath}" ]]; then
    local checkoutRoot targetRoot
    if [[ ! -d "${targetPath}" ]] ||
       ! checkoutRoot="$(git -C "${targetPath}" rev-parse --show-toplevel 2>/dev/null)"; then
      echo 'Git: 指定先は既存のチェックアウトではありません。変更せず停止します。' >&2
      return 1
    fi
    targetRoot="$(cd -- "${targetPath}" && pwd -P)" || return
    checkoutRoot="$(cd -- "${checkoutRoot}" && pwd -P)" || return
    if [[ "${checkoutRoot}" != "${targetRoot}" ]]; then
      echo 'Git: 指定先はチェックアウトのルートではありません。変更せず停止します。' >&2
      return 1
    fi
    local originUrl
    if ! originUrl="$(git -C "${targetPath}" config --get remote.origin.url 2>/dev/null)" ||
       [[ -z "${originUrl}" ]]; then
      echo 'Git: origin を確認できないため更新を停止します。' >&2
      return 1
    fi
    if [[ "$(gitRepositoryIdentity "${originUrl}")" != "$(gitRepositoryIdentity "${repositoryUrl}")" ]]; then
      echo 'Git: origin が想定したリポジトリと異なるため、変更せず停止します。' >&2
      return 1
    fi
    if [[ "${repositoryUrl}" == https://* && "${originUrl}" == https://* ]]; then
      local originRepository="${originUrl%%[?#]*}"
      originRepository="${originRepository#https://}"
      local originAuthority="${originRepository%%/*}"
      originRepository="https://${originAuthority##*@}${originRepository#"${originAuthority}"}"
      if [[ "${originRepository}" != "${originUrl}" ]]; then
        git -C "${targetPath}" remote set-url origin "${originRepository}"
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
      if [[ -d "${dstPath}" && ! -L "${dstPath}" ]]; then
        echo "${dstPath}: 設定ファイルの配置先にディレクトリがあるため停止します。" >&2
        return 1
      fi
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

function findMise()
{
  if command -v mise >/dev/null 2>&1; then
    return
  elif [ -x "${HOME}/.local/bin/mise" ]; then
    export PATH="${HOME}/.local/bin:${PATH}"
    return
  fi
  return 1
}

function setMise()
{
  if findMise; then
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
