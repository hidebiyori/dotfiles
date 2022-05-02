""" Common """
scriptencoding utf-8
set nocompatible

filetype plugin indent on
syntax on

if has('clipboard')
  set clipboard=unnamed,autoselect,html
endif

let mySessionFile = "${HOME}/.vim/session"

set noerrorbells
set visualbell t_vb=
set tabpagemax=100
set history=1000
set autoread
set hidden

set backup
set writebackup
set backupdir=${HOME}/.vim/backup//

set swapfile
set directory=${HOME}/.vim/swap//

set undofile
set undodir=${HOME}/.vim/undo//
set undolevels=2000

set encoding=utf-8
set fileencodings=utf-8,euc-jp,iso-2022-jp,cp932
set ambiwidth=double

set backspace=indent,eol,start
set whichwrap=b,s,h,l,<,>,[,],~
set nrformats=bin,hex

set nomodeline
set expandtab
set tabstop=2
set shiftwidth=2
set autoindent
set smartindent

set hlsearch
set ignorecase
set smartcase
set incsearch
set wrapscan
set nofoldenable

set title
set number
set ruler
set showtabline=2
set laststatus=2
set statusline=%<\ %f\ %y%{'['.(&fenc!=''?&fenc:&enc).']['.&ff.']'}%r%w%m%=%l,%c%V%5P
set wildmenu
set shellslash
set cmdheight=1
set showcmd
set showmode
set showmatch
set cursorline
set nocursorcolumn
set list
set listchars=tab:^=
set helplang=ja
set display=lastline

nnoremap <C-n> gt
nnoremap <C-p> gT

nnoremap qq :qa<CR>
nnoremap <C-m><C-m> :execute('mksession!' . mySessionFile)<CR>
nnoremap <C-m><C-s> :execute('source' . mySessionFile)<CR>

nnoremap <C-l> o<C-R>=expand('%:p')<CR><ESC>

nnoremap n nzz
nnoremap N Nzz

vnoremap <silent> * "vy/\V<C-r>=substitute(escape(@v,'\/'),"\n",'\\n','g')<CR><CR>

inoremap <C-c> <ESC>

augroup disableAutoFormat
  autocmd!
  autocmd BufEnter * setlocal textwidth=0
  autocmd BufEnter * setlocal formatoptions=
augroup END

augroup enableAutoJumpLastCursor
  autocmd!
  autocmd BufReadPost *
  \ if line("'\"") > 0 && line("'\"") <= line("$") |
  \   exe "normal! g'\"" |
  \ endif
augroup END

augroup enableAutoReloadVimrc
  autocmd!
  autocmd BufWritePost *vimrc source ${MYVIMRC} | set foldmethod=marker
  autocmd BufWritePost *gvimrc if has('gui_running') source ${MYGVIMRC}
augroup END

augroup enableAutoSaveSession
  autocmd!
  autocmd VimLeave * execute('mksession!' . mySessionFile)
  "autocmd VimEnter * execute('source' . mySessionFile)
augroup END

colorscheme koehler
