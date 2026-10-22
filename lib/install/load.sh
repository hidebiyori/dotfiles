#!/usr/bin/env bash
# Shared definitions only; sourcing this file does not run setup or upgrades.
DOTFILES_INSTALL_LIB="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "${DOTFILES_INSTALL_LIB}/common.sh" || return
source "${DOTFILES_INSTALL_LIB}/macos.sh" || return
source "${DOTFILES_INSTALL_LIB}/linux.sh" || return
source "${DOTFILES_INSTALL_LIB}/wsl.sh" || return
