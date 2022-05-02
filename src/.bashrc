### Common ###
export FIGNORE=".svn:.git"
export PAGER="less -+S -M"
export EDITOR="vim"

export HISTSIZE="5000"
export HISTFILESIZE="5000"
export HISTCONTROL="ignoreboth"
export HISTIGNORE="?:exit"
export HISTTIMEFORMAT="%Y-%m-%d %T "

shopt -s histappend
shopt -s histreedit
shopt -s histverify
shopt -s cmdhist
shopt -s lithist
export PROMPT_COMMAND="history -a; history -c; history -r; ${PROMPT_COMMAND}"

GIT_PS1_SHOWDIRTYSTATE=1
GIT_PS1_SHOWSTASHSTATE=1
GIT_PS1_SHOWUNTRACKEDFILES=1
GIT_PS1_SHOWUPSTREAM="verbose"
if __git_ps1 > /dev/null 2>&1; then
  export PS1='\n\d \A$(__git_ps1)\n\u@\H:\w/\n\$ '
else
  export PS1='\n\d \A\n\u@\H:\w/\n\$ '
fi

GIT_ROOT="${HOME}/git"
APP_ROOT="${GIT_ROOT}/hidebiyori-app"
alias r="source ${HOME}/.bash_profile"
alias u="${GIT_ROOT}/dotfiles/bin/install.sh && r"
alias o="if [[ ! x${TERM} =~ xscreen ]]; then screen -U -D -R; fi"
alias a="cd ${APP_ROOT}"
alias s="cd ${GIT_ROOT}/dotfiles"
alias d="cd ${GIT_ROOT}"
alias f="cd ${HOME}/var/000-docs"
alias h="history | tail -n 50"
alias l="ls -Al"
alias ll="l"
alias lt="ls -Altr"
alias vim="vim -vfp"
alias v="\
  vim \
  ${HOME}/var/000-docs/001-memo.txt \
  ${GIT_ROOT}/dotfiles/bin/install.sh \
  -c '2tabnext' \
  -c 'vsplit ${HOME}/.bash_profile' \
  -c 'split ${HOME}/.bashrc' \
  -c 'wincmd l' \
  -c 'split ${HOME}/.vimrc' \
  -c 'wincmd h' \
  -c 'tabfirst' \
  -c 'cd ${GIT_ROOT}/hidebiyori-app' \
"
alias b="vim -S ${HOME}/.vim/session"
alias n="updateFlutter; updateFirebaseFunctions"

function updateFlutter()
{
  pushd "${APP_ROOT}"
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
  pushd "${APP_ROOT}/functions"
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
  a
fi
