
# [[ -o interactive ]] || exit 0

# Enable Powerlevel10k instant prompt. Should stay close to the top of ~/.zshrc.
# Initialization code that may require console input (password prompts, [y/n]
# confirmations, etc.) must go above this block; everything else may go below.
if [[ -r "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh" ]]; then
  source "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh"
fi

# If you come from bash you might have to change your $PATH.
# export PATH=$HOME/bin:/usr/local/bin:$PATH

# Path to your oh-my-zsh installation.
export ZSH="$HOME/.oh-my-zsh"

# Set name of the theme to load --- if set to "random", it will
# load a random theme each time oh-my-zsh is loaded, in which case,
# to know which specific one was loaded, run: echo $RANDOM_THEME
# See https://github.com/robbyrussell/oh-my-zsh/wiki/Themes
# ZSH_THEME="powerlevel10k/powerlevel10k"
# ZSH_THEME="half-life"
# ZSH_THEME="sonicradish"
ZSH_THEME="half-life"

# Set list of themes to pick from when loading at random
# Setting this variable when ZSH_THEME=random will cause zsh to load
# a theme from this variable instead of looking in ~/.oh-my-zsh/themes/
# If set to an empty array, this variable will have no effect.
# ZSH_THEME_RANDOM_CANDIDATES=( "robbyrussell" "agnoster" )

# Uncomment the following line to use case-sensitive completion.
# CASE_SENSITIVE="true"

# Uncomment the following line to use hyphen-insensitive completion.
# Case-sensitive completion must be off. _ and - will be interchangeable.
# HYPHEN_INSENSITIVE="true"

# Uncomment the following line to disable bi-weekly auto-update checks.
# DISABLE_AUTO_UPDATE="true"

# Uncomment the following line to automatically update without prompting.
# DISABLE_UPDATE_PROMPT="true"

# Uncomment the following line to change how often to auto-update (in days).
# export UPDATE_ZSH_DAYS=13

# Uncomment the following line if pasting URLs and other text is messed up.
# DISABLE_MAGIC_FUNCTIONS=true

# Uncomment the following line to disable colors in ls.
# DISABLE_LS_COLORS="true"

# Uncomment the following line to disable auto-setting terminal title.
# DISABLE_AUTO_TITLE="true"

# Uncomment the following line to enable command auto-correction.
# ENABLE_CORRECTION="true"

# Uncomment the following line to display red dots whilst waiting for completion.
# COMPLETION_WAITING_DOTS="true"

# Uncomment the following line if you want to disable marking untracked files
# under VCS as dirty. This makes repository status check for large repositories
# much, much faster.
# DISABLE_UNTRACKED_FILES_DIRTY="true"

# Uncomment the following line if you want to change the command execution time
# stamp shown in the history command output.
# You can set one of the optional three formats:
# "mm/dd/yyyy"|"dd.mm.yyyy"|"yyyy-mm-dd"
# or set a custom format using the strftime function format specifications,
# see 'man strftime' for details.
# HIST_STAMPS="mm/dd/yyyy"

# Would you like to use another custom folder than $ZSH/custom?
# ZSH_CUSTOM=/path/to/new-custom-folder

# Which plugins would you like to load?
# Standard plugins can be found in ~/.oh-my-zsh/plugins/*
# Custom plugins may be added to ~/.oh-my-zsh/custom/plugins/
# Example format: plugins=(rails git textmate ruby lighthouse)
# Add wisely, as too many plugins slow down shell startup.
plugins=(git mercurial)

export ZSH_DISABLE_COMPFIX=true
fpath=(${fpath:#/usr/share/zsh/site-functions})
[[ -r "$ZSH/oh-my-zsh.sh" ]] && source "$ZSH/oh-my-zsh.sh"

# User configuration

# export MANPATH="/usr/local/man:$MANPATH"

# You may need to manually set your language environment
export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8

# Preferred editor for local and remote sessions
# if [[ -n $SSH_CONNECTION ]]; then
#   export EDITOR='vim'
# else
#   export EDITOR='mvim'
# fi

# Compilation flags
# export ARCHFLAGS="-arch x86_64"

# Set personal aliases, overriding those provided by oh-my-zsh libs,
# plugins, and themes. Aliases can be placed here, though oh-my-zsh
# users are encouraged to define aliases within the ZSH_CUSTOM folder.
# For a full list of active aliases, run `alias`.
#
# Example aliases
# alias zshconfig="mate ~/.zshrc"
# alias ohmyzsh="mate ~/.oh-my-zsh"
# source $HOME/.purepower
# POWERLEVEL10k_MODE='nerdfont-complete'
# POWERLEVEL10k_LEFT_PROMPT_ELEMENTS=(dir vcs status ssh)
# POWERLEVEL9K_LEFT_PROMPT_ELEMENTS=(dir vcs status ssh)
# POWERLEVEL10k_RIGHT_PROMPT_ELEMENTS=(status)
# POWERLEVEL9K_RIGHT_PROMPT_ELEMENTS=(status)
# POWERLEVEL10k_PROMPT_ADD_NEWLINE=true
# POWERLEVEL9K_VCS_BACKENDS=(git hg)

# To customize prompt, run `p10k configure` or edit ~/.p10k.zsh.
[[ ! -f ~/.p10k.zsh ]] || source ~/.p10k.zsh

if [ -d "$HOME/.zsh/pure" ]; then
    fpath+=($HOME/.zsh/pure);
    autoload -U promptinit;
    promptinit;
    prompt pure
fi

if [ -d "$CONDA_PREFIX" ]; then export DYLD_LIBRARY_PATH="$CONDA_PREFIX/lib:$DYLD_LIBRARY_PATH"; fi
if [ -d "/usr/local/opt/curl/bin" ]; then export PATH="/usr/local/opt/curl/bin:$PATH"; fi
# opam configuration
[[ ! -r "$HOME/.opam/opam-init/init.zsh" ]] || source "$HOME/.opam/opam-init/init.zsh" > /dev/null 2>&1
if [ -f "$HOME/.fzf.zsh" ]; then source "$HOME/.fzf.zsh"; fi

# Copy input to clipboard using OSC 52 (limit 74994 bytes)
clip() { # limit copy to 74994 bytes (OSC 52 limit)
  input_data=$(cat)
  encoded_data=$(printf '%s' "$input_data" | base64 | tr -d '\n')
  printf "\033]52;c;%s\a" "$encoded_data"
}

# Linux-only: Wayland/Sway env (stale sockets after sway restart, wlroots cursor fix)
if [[ "$OSTYPE" == linux-gnu* ]]; then
    if [ -n "$TMUX" ]; then
        local _runtime_dir="${XDG_RUNTIME_DIR:-/run/user/$UID}"
        export SWAYSOCK=$( (setopt nonomatch; ls -t "$_runtime_dir"/sway-ipc.*.sock 2>/dev/null | head -1) )
        local _wd=$( (setopt nonomatch; ls "$_runtime_dir"/wayland-* 2>/dev/null | grep -v lock | head -1) )
        if [ -n "$_wd" ]; then export WAYLAND_DISPLAY=$(basename "$_wd"); fi
    fi
    export WLR_NO_HARDWARE_CURSORS=1
fi
# PATH setup (kept before conda init so conda can prepend correctly)
if [ -r "$HOME/.cargo/env" ]; then
	source "$HOME/.cargo/env";
fi
if [ -d "/usr/local/sbin" ]; then export PATH="/usr/local/sbin:$PATH"; fi
if [ -d "/opt/homebrew" ]; then
    export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:${PATH}";
fi
if [ -d "/opt/homebrew/opt/libiconv" ]; then
	 export PATH="/opt/homebrew/opt/libiconv/bin:${PATH}";
fi
if [ -d "$HOME/.local/homebrew" ]; then
    export PATH="$HOME/.local/homebrew/bin:$HOME/.local/homebrew/sbin:${PATH}";
fi
if type brew &> /dev/null; then
	typeset sqlite_prefix
	if sqlite_prefix="$(brew --prefix sqlite 2>/dev/null)"; then
		export DYLD_LIBRARY_PATH="$sqlite_prefix/lib:/usr/lib";
		export LDFLAGS="-L$sqlite_prefix/lib"
		export CPPFLAGS="-I$sqlite_prefix/include"
		export PKG_CONFIG_PATH="$sqlite_prefix/lib/pkgconfig"
		export PATH="$sqlite_prefix/bin:$PATH";
	fi
	unset sqlite_prefix
fi
if [ -d "$HOME/.local/conda/bin" ]; then
	export PATH="$HOME/.local/conda/bin:${PATH}";
fi
if [ -d "/opt/conda/bin" ]; then
	export PATH="/opt/conda/bin:${PATH}";
fi
if [ -f "/opt/conda/etc/profile.d/conda.sh" ]; then
	. "/opt/conda/etc/profile.d/conda.sh"
fi
if [ -d "/opt/anaconda3/bin" ]; then
	export PATH="/opt/anaconda3/bin:${PATH}";
fi
if [ -d "$HOME/.local/homebrew/anaconda3" ]; then
	export PATH="$HOME/.local/homebrew/anaconda3/bin:${PATH}";
fi
if [ -d "/usr/local/cuda/bin" ]; then
	export PATH="/usr/local/cuda/bin:${PATH}";
fi
if [ -d "$HOME/.local/bin" ]; then export PATH="$HOME/.local/bin:$PATH"; fi

# >>> conda initialize >>>
# !! Contents within this block are managed by 'conda init' !!
if [ -f "$HOME/miniforge3/bin/conda" ]; then
    __conda_setup="$("$HOME/miniforge3/bin/conda" 'shell.zsh' 'hook' 2> /dev/null)"
    if [ $? -eq 0 ]; then
        eval "$__conda_setup"
    else
        if [ -f "$HOME/miniforge3/etc/profile.d/conda.sh" ]; then
            . "$HOME/miniforge3/etc/profile.d/conda.sh"
        else
            export PATH="$HOME/miniforge3/bin:$PATH"
        fi
    fi
elif [ -f "/usr/bin/conda" ]; then
    __conda_setup="$('/usr/bin/conda' 'shell.zsh' 'hook' 2> /dev/null)"
    if [ $? -eq 0 ]; then
        eval "$__conda_setup"
    else
        if [ -f "/etc/profile.d/conda.sh" ]; then
            . "/etc/profile.d/conda.sh"
        else
            export PATH="/usr/bin:$PATH"
        fi
    fi
fi
unset __conda_setup
# <<< conda initialize <<<

# Fix for system conda: env bins are placed mid-PATH (replacing /usr/bin)
# instead of being prepended. Wrap conda to move the env bin to the front.
if (( $+functions[conda] )); then
    functions[__wrapped_conda]=$functions[conda]
    conda() {
        __wrapped_conda "$@"
        local ret=$?
        if [[ -n "$CONDA_PREFIX" && "$CONDA_PREFIX" != "/usr" && -d "$CONDA_PREFIX/bin" && "$PATH" != "$CONDA_PREFIX/bin:"* ]]; then
            local conda_bin="$CONDA_PREFIX/bin"
            PATH=":$PATH:"
            PATH="${PATH//":$conda_bin:"/":"}"
            PATH="${PATH#:}"
            PATH="${PATH%:}"
            export PATH="$conda_bin:$PATH"
        fi
        return $ret
    }
fi
