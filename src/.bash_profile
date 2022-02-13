### Common ###
export XDG_CONFIG_HOME="${HOME}/.config"

function load()
{
  local file="${1:?}"

  if [ -s "${file}" ]; then
    \source "${file}"
  fi
}

# disable <C-s>
stty stop undef

# set default permission directory: 755, file: 644
umask 0022

uname="$(uname -a)"


### Mac ###
if [[ "${uname}" =~ "Darwin" ]]; then
  load "/etc/bashrc"
  load "/usr/local/etc/bash_completion"
  export PATH="${HOME}/.config/brew/bin:${PATH}"


### Linux ###
elif [[ "${uname}" =~ "Linux" ]]; then
  :


fi


### Common ###
export NVM_DIR="${HOME}/.config/nvm"
load "${NVM_DIR}/nvm.sh"
load "${NVM_DIR}/bash_completion"

export PATH="${HOME}/.config/flutter/bin:${PATH}"

export PATH="${HOME}/bin:${PATH}"
load "${HOME}/.bashrc"
