### Common ###
export FIGNORE=".svn:.git"
export PAGER="less -+S -M"
export EDITOR="vim"

export HISTSIZE="50000"
export HISTFILESIZE="50000"
export HISTCONTROL="ignoreboth"
export HISTIGNORE="[hrw]:ls:exit"
export HISTTIMEFORMAT="%Y-%m-%d %T "

shopt -s histappend
shopt -s histreedit
shopt -s histverify
shopt -s cmdhist
shopt -s lithist

function __dotfiles_set_history_prompt()
{
  local historyCommands='history -a; history -c; history -r;'
  local prompt="${PROMPT_COMMAND-}" existing
  # Collapse the prefixes added by earlier reloads without changing custom hooks.
  while [[ "${prompt}" == "${historyCommands}"* ]]; do
    prompt="${prompt#"${historyCommands}"}"
    prompt="${prompt# }"
  done
  # Scalar assignment also preserves the other entries of an indexed array.
  PROMPT_COMMAND="${prompt}"
  for existing in "${PROMPT_COMMAND[@]}"; do
    if [[ "${existing}" == *"${historyCommands}"* ]]; then
      return
    fi
  done
  PROMPT_COMMAND="${historyCommands}${prompt:+ ${prompt}}"
}

if [ -s "${HOME}/.bash_history" ]; then
  __dotfiles_set_history_prompt
  export PROMPT_COMMAND
fi

GIT_PS1_SHOWDIRTYSTATE=1
GIT_PS1_SHOWSTASHSTATE=1
GIT_PS1_SHOWUNTRACKEDFILES=1
GIT_PS1_SHOWUPSTREAM="verbose"
if __git_ps1 > /dev/null 2>&1; then
  export PS1='\n\d \A$(__git_ps1)\n\u@\H:\w/\n\$ '
else
  export PS1='\n\d \A\n\u@\H:\w/\n\$ '
fi

export GIT_ROOT="${HOME}/git"
export AP1_ROOT="${GIT_ROOT}/app01-flutter"
export AP2_ROOT="${GIT_ROOT}/app02-nextjs"
export DOT_ROOT="${GIT_ROOT}/dotfiles"
export DOC_MAIN="${HOME}/var/0001-data/0001-hide/0001-soon"
alias r="source ${HOME}/.bash_profile"
alias u='bash "$GIT_ROOT/dotfiles/bin/update.sh" && r'
alias up='bash "$GIT_ROOT/dotfiles/bin/upgrade.sh" && r'
alias o="if [[ ! x${TERM} =~ xscreen ]]; then screen -U -D -R; fi"
alias a="cd ${AP1_ROOT}"
alias s="cd ${GIT_ROOT}/dotfiles"
alias d="cd ${GIT_ROOT}"
alias f="cd ${DOC_MAIN}"
alias h="history | tail -n 50"
alias l="ls -Al"
alias ll="l"
alias lt="ls -Altr"
alias vim="vim -vfp"
alias v="\
  vim \
  ${DOC_MAIN}/001-memo.txt \
  ${DOT_ROOT}/bin/install.sh \
  -c '2tabnext' \
  -c 'vsplit ${HOME}/.bash_profile' \
  -c 'split ${HOME}/.bashrc' \
  -c 'wincmd l' \
  -c 'split ${HOME}/.vimrc' \
  -c 'wincmd h' \
  -c 'tabfirst' \
  -c 'cd ${AP1_ROOT}' \
"
alias b="vim -S ${HOME}/.vim/session"

uname="$(uname -a)"


### Mac ###
if [[ "${uname}" =~ "Darwin" ]]; then
  alias ls="ls -G"

  # maximize a window
  printf '\e[9;1t'


### Linux ###
elif [[ "${uname}" =~ "Linux" ]]; then
  alias ls="ls --color"

  if [[ -n "${WSL_DISTRO_NAME:-}" || -n "${WSL_INTEROP:-}" || "${uname}" == *[Mm]icrosoft* ]]; then
    if [[ -z "${BROWSER:-}" && -x "${HOME}/bin/wsl-browser" ]] && command -v powershell.exe >/dev/null 2>&1; then
      export BROWSER="${HOME}/bin/wsl-browser"
    fi
  fi

  if [ -x /usr/bin/chromium ]; then
    export CHROME_EXECUTABLE=/usr/bin/chromium
  fi


fi


# Activate after Flutter PATH setup; skip missing mise and non-interactive shells.
if [[ $- == *i* ]]; then
  if command -v mise >/dev/null 2>&1; then
    eval "$(mise activate bash)"
  elif [ -x "${HOME}/.local/bin/mise" ]; then
    eval "$("${HOME}/.local/bin/mise" activate bash)"
  fi
fi

### Common ###
if [ "${PWD}" = "${HOME}" ]; then
  o
fi
