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
    git -C "${targetPath}" pull
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

    if isWsl && [[ "${srcPath}" == "${PJ_ROOT}/src/.sommelierrc" || "${srcPath}" == "${PJ_ROOT}/src/.config/Code" ]]; then
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

function setBrew()
{
  if which brew; then
    brew update
    brew upgrade
  else
    # https://docs.brew.sh/Installation
    local targetPath="${HOME}/.config/brew"

    mkdir -p "${targetPath}"
    curl -L https://github.com/Homebrew/brew/tarball/master | tar xz --strip 1 -C "${targetPath}"
    export PATH="${targetPath}/bin:${PATH}"
    brew install bash-completion git jq pstree
    brew install --cask google-chrome google-japanese-ime visual-studio-code
    brew doctor
  fi
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
  local packages=(screen)
  if isWsl; then
    packages+=(ca-certificates curl git vim)
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
  if which code; then
    :
  else
    curl -L "https://go.microsoft.com/fwlink/?LinkID=760868" -o vscode.deb
    sudo apt install ./vscode.deb
    rm vscode.deb
  fi
}

function setLink()
{
  local localPath="/mnt/chromeos/MyFiles"
  local drivePath="/mnt/chromeos/GoogleDrive/MyDrive"

  # required: Chrome OS Share with Linux
  ln -sfnv "${localPath}/Downloads" "${HOME}/"
  ln -sfnv "${drivePath}" "${HOME}/"
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
    if [[ -d "${HOME}/Downloads" && ! -L "${HOME}/Downloads" ]]; then
      echo "WSL: ~/Downloads は既存のディレクトリのため維持します。" >&2
    else
      ln -sfnv "${windowsDownloads}" "${HOME}/Downloads"
    fi
  else
    echo "WSL: Windows の Downloads にアクセスできないためリンク作成を省きます。" >&2
  fi

  if windowsAppData="$(wslpath -u "${windowsFolders%%$'\n'*}")" && [[ -d "${windowsAppData}" ]]; then
    local codeUser="${windowsAppData}/Code/User"
    mkdir -p "${codeUser}"
    cp "${PJ_ROOT}/src/.config/Code/User/settings.json" "${codeUser}/settings.json"
    cp "${PJ_ROOT}/src/.config/Code/User/keybindings.json" "${codeUser}/keybindings.json"
    echo "WSL: Windows 版 VS Code の既定プロファイル設定を反映しました。"
  else
    echo "WSL: Windows の AppData にアクセスできないため VS Code 設定の反映を省きます。" >&2
  fi
}

function setNode()
{
  # Keep the previous LTS policy; do not depend on interactive shell activation.
  mise use --global node@lts
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

function setFirebase()
{
  # https://firebase.google.com/docs/cli
  mise exec node@lts -- npm install -g firebase-tools

  # memo
  # firebase login --no-localhost
  # firebase projects:list
}

function main()
{
  setOptions
  uname="$(uname -a)"
  setDirectories
  setGitRepository "${PJ_URL}"
  setSymbolicLink "${PJ_ROOT}/src" "${HOME}"

  ### Mac ###
  if [[ "${uname}" =~ "Darwin" ]]; then
    setBrew
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
      setLink
      python3 "${PJ_ROOT}/bin/setup-chatgpt-maximized.py"
    fi


  fi


  ### Common ###
  bash "${PJ_ROOT}/bin/setup-skill-python.sh"
  setNode
  if [[ "${INSTALL_FLUTTER:-0}" == "1" ]]; then
    setFlutter
  fi
  setFirebase
  echo "Success: ${0}"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
