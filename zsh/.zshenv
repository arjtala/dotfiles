autoload zmv
export TERM=xterm-256color
export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8
export LANGUAGE=en_US.UTF-8
if [[ ! -v FB ]]; then
	export PATH=$PATH:$HOME/Library/Python/3.7/bin
	PATH="/usr/local/opt/findutils/libexec/gnubin:$PATH"
	PATH="/usr/local/opt/curl/bin:$PATH"
	LDFLAGS="-L/usr/local/opt/curl/lib"
	CPPFLAGS="-I/usr/local/opt/curl/include"
	PKG_CONFIG_PATH="/usr/local/opt/curl/lib/pkgconfig"
	source "$HOME/.cargo/env"
	export PATH="/usr/local/opt/curl/bin:$PATH"
    export PATH="$HOME/.local/homebrew/bin:$HOME/.local/homebrew/sbin:$PATH"
	PATH="/usr/local/opt/grep/libexec/gnubin:$PATH"
fi
PATH=$HOME/.local/bin:$PATH
export PATH="/usr/local/sbin:$PATH"
export PATH="/usr/local/opt/llvm/bin:$PATH"
export PATH="/usr/local/opt/binutils/bin:$PATH"
