#!/bin/bash
### Common ###
GIT_ROOT="${HOME}/git"
ORG_NAME=hidebiyori
PJ_NAME=dotfiles
PJ_ROOT="${GIT_ROOT}/${PJ_NAME}"
PJ_URL="https://${GH_TOKEN}${GH_TOKEN:+@}github.com/${ORG_NAME}/${PJ_NAME}.git"

function setOptions()
{
  set -xeuo pipefail
}

function setDirectories()
{
  mkdir -p "${HOME}"/{.config,.vim/{backup,swap,undo},bin,var,tmp,old}
}

function setGitRepository()
{
  local repositoryUrl="${1:?}"
  local repositoryName="$(echo ${repositoryUrl##*/} | sed 's/.git//g')"
  local targetPath="${2:-${GIT_ROOT}/${repositoryName}}"

  if [ -d "${targetPath}" ]; then
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
  sudo apt install screen
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

setOptions
setDirectories
setGitRepository "${PJ_URL}"
setSymbolicLink "${PJ_ROOT}/src" "${HOME}"

uname="$(uname -a)"


### Mac ###
if [[ "${uname}" =~ "Darwin" ]]; then
  setBrew
  setScreencapture
  setMise


### Linux ###
elif [[ "${uname}" =~ "Linux" ]]; then
  setApt
  setMise
  setJapanese
  setVisualStudioCode
  setLink


fi


### Common ###
setNode
if [[ "${INSTALL_FLUTTER:-0}" == "1" ]]; then
  setFlutter
fi
setFirebase
echo "Success: ${0}"
