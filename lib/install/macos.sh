#!/usr/bin/env bash

function findBrew()
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
  command -v brew >/dev/null 2>&1
}

function setBrew()
{
  if ! findBrew; then
    # https://docs.brew.sh/Installation
    local targetPath="${HOME}/.config/brew"

    mkdir -p "${targetPath}"
    curl -L https://github.com/Homebrew/brew/tarball/master | tar xz --strip 1 -C "${targetPath}"
    export PATH="${targetPath}/bin:${PATH}"
    if ! brew doctor; then
      echo "Homebrew の導入は完了しました。brew doctor の案内を確認してください。" >&2
    fi
  fi
}

function setMacPackages()
{
  local package
  for package in bash-completion git jq pstree gh python; do
    brew list --formula --versions "${package}" >/dev/null 2>&1 || brew install "${package}"
  done
  if ! brew list --cask --versions google-japanese-ime >/dev/null 2>&1 &&
     [[ ! -d '/Library/Input Methods/GoogleJapaneseInput.app' &&
        ! -d "${HOME}/Library/Input Methods/GoogleJapaneseInput.app" ]]; then
    brew install --cask google-japanese-ime
  fi
}

function setMacDesktopApps()
{
  local cask appPath
  local casks=(chatgpt google-chrome visual-studio-code)
  for cask in "${casks[@]}"; do
    if brew list --cask --versions "${cask}" >/dev/null 2>&1; then
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

function upgradeMacPackages()
{
  if ! findBrew; then
    echo 'Homebrew が見つかりません。初期セットアップを先に実行してください。' >&2
    return 1
  fi
  brew update
  brew upgrade --formula
  local cask
  for cask in chatgpt google-chrome visual-studio-code google-japanese-ime; do
    if brew list --cask --versions "${cask}" >/dev/null 2>&1; then
      brew upgrade --cask --greedy --no-quit "${cask}"
    fi
  done
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
