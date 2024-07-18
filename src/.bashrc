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
if [ -s "${HOME}/.bash_history" ]; then
  export PROMPT_COMMAND="history -a; history -c; history -r; ${PROMPT_COMMAND}"
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
export DOC_MAIN="${HOME}/var/0000-soon"
alias r="source ${HOME}/.bash_profile"
alias u="${GIT_ROOT}/dotfiles/bin/install.sh && r"
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
alias n="updateFlutter; updateFirebaseFunctions"

function updateFlutter()
{
  pushd "${AP1_ROOT}"
  flutter upgrade
  flutter pub outdated
  flutter pub upgrade --major-versions
  version=$(cat ${FLUTTER_DIR}/version)
  perl -i -ple "s/(flutter-version: )'.+'/\1'${version}'/g" .github/workflows/*
  git ci -m 'update flutter' pubspec.lock .github
  popd
}
export -f updateFlutter

function updateFirebaseFunctions()
{
  pushd "${AP1_ROOT}/functions"
  npx -p npm-check-updates -c 'ncu -u'
  npm install
  git ci -m 'update firebase functions' package.json package-lock.json
  popd
}
export -f updateFirebaseFunctions

uname="$(uname -a)"


### Mac ###
if [[ "${uname}" =~ "Darwin" ]]; then
  alias ls="ls -G"

  # maximize a window
  printf '\e[9;1t'


### Linux ###
elif [[ "${uname}" =~ "Linux" ]]; then
  alias ls="ls --color"

  # required: sudo apt install chromium
  export CHROME_EXECUTABLE=/usr/bin/chromium


fi


### Common ###
if [ "${PWD}" = "${HOME}" ]; then
  o
fi
