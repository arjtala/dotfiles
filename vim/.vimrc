set nocompatible              " required
filetype off                  " required

set rtp+=~/.vim/bundle/Vundle.vim
call vundle#begin()

Plugin 'VundleVim/Vundle.vim'
Plugin 'jnurmine/Zenburn'
Plugin 'altercation/vim-colors-solarized'
Plugin 'klen/python-mode'
Plugin 'junegunn/fzf'
Plugin 'junegunn/fzf.vim'
Plugin 'airblade/vim-gitgutter'
Plugin 'editorconfig/editorconfig-vim'
Plugin 'itchyny/lightline.vim'
Plugin 'scrooloose/nerdtree'
Plugin 'terryma/vim-multiple-cursors'
Plugin 'tpope/vim-eunuch'
Plugin 'tpope/vim-surround'
Plugin 'w0rp/ale'
Plugin 'mileszs/ack.vim'

" use Ag with ack.vim
let g:ackprg = 'ag --nogroup --nocolor --column'

call vundle#end()            " required
filetype plugin indent on    " required

autocmd! bufwritepost ~/.zshrc	!source ~/.zshrc
set nocp
set nu
"execute pathogen#infect()
filetype on
set bg=dark

let python_highlight_all=1
syntax on

filetype plugin indent on
set showmode
set nu
set ai
set sc
set noincsearch
set noexpandtab
set backspace=indent,eol,start
syntax on

let mapleader=" "
set hidden
set history=10000
filetype indent on
filetype plugin on
set linebreak
set nowrap
set tabstop=2
set shiftwidth=2
set expandtab
set smartindent
set autoindent
set nohlsearch
set showmatch
set laststatus=2
set noshowmode
set undofile
set undodir=~/.vim/undodir
set viminfo='10,\"100,:20,%,n~/.viminfo
set nobackup
set whichwrap=b,s,<,>,[,]
set laststatus=2
let g:powerline_pycmd = 'py3'
let g:airline#extensions#tabline#enabled = 1
let g:airline#extensions#tabline#formatter = 'default'
:noremap <leader>u :w<Home>silent <End> !urlview<CR>

function! ResCur()
  if line("'\"") <= line("$")
    normal! g`"
    return 1
  endif
endfunction

set guifont=ProggyCleanTT\ 12
filetype plugin indent on
set nocompatible
colo delek
colors zenburn
"set term=builtin_ansi
syntax on
set showmode
set backup
set backupdir=/private/tmp
set dir=/private/tmp
set number
set hlsearch


filetype off 
set laststatus=0
set encoding=utf8
set modeline
filetype plugin on
"set mouse=a

"    "
" ui "
"    "
"if &t_Co < 256
set t_Co=256
set guicursor=a:blinkon0
"set nu!                    " line numbering
set smartindent

set ruler         " show the cursor position all the time
set showcmd       " display incomplete commands

" statusline
"set cmdheight=0    " command line height
set ruler           " show cursor position in status line
set showmode        " show mode in status line
set showcmd         " show partial commands in status line
" fileformat, encoding, type, buffer num, RO/HELP/PREVIEW, mod flag, filepath; spacer;  line pos, line/total, percentage
set statusline=%{&ff}\ \%{&fenc}\ \b%1.3n\ \%#StatusFTP#\%Y\ \%#StatusRO#\%R\ \%#StatusHLP#\%H\ \%#StatusPRV#\%W\ \%#StatusModFlag#\%M\ \%#StatusLine#\%f\%=\%1.7c\ \%1.7l/%L\ \%p%%

set expandtab
set tabstop=4       " set tab keys to 2 spaces
set shiftwidth=4
" set autoindent     " set noautoindent to prevent vim from
                     " inserting unwanted indents when pasting
" backspace
set bs=2

" tab key in visual mode
vmap <tab> >gv
vmap <S-tab> <gv

"                     "
" searching & history "
"                     "
set hlsearch          " highlight all search results
set incsearch         " increment search
set ignorecase        " case-insensitive search; opposite noignorecase
set smartcase         " uppercase causes case-sensitive search
set wrapscan          " searches wrap back to the top of file

set nobackup          " don't create backup files
set noswapfile        " don't create swap file

set history=50        " keep 50 lines of command line history
set incsearch         " do incremental searching

map <C-f> :FufFile /home/bohoomil/<CR>

set tags+=ftags


"      "
" misc "
"      "
syntax enable
syntax on
