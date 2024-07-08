# emacs M-x shell
if [[ "dumb" == $TERM ]] ; then
  alias l='cat'
  alias less='cat'
  alias m='cat'
  alias more='cat'
  export PAGER=cat
  export TERM=xterm-256color
  unsetopt zle
  unsetopt prompt_cr
  unsetopt prompt_subst
  unsetopt zle
  PS1='$ '
  return
else
  autoload zmv
  export LC_ALL=en_US.UTF-8
  export LANG=en_US.UTF-8
  export LANGUAGE=en_US.UTF-8
fi

if [[ "$HOST" == *"ip-10-0-1-5"* ]];
then
	if [ -d "$HOME/.local/share/info" ]; then export INFOPATH=$HOME/.local/share/info; fi
fi
if [[ "$HOST" == *"facebook"* ]];
then
  export TERMINAL=xterm-256color
  export TERM=xterm-256color
  if [[ -t 1 ]]; then  echo "Loading FB specific settings..."; fi
	if [[ -z "${LOCAL_ADMIN_SCRIPTS}" ]]; then LOCAL_ADMIN_SCRIPTS="/usr/facebook/ops/rc/"; fi
    local fb_master_zshrc="${LOCAL_ADMIN_SCRIPTS}/master.zshrc"
    local fb_prompt_file="${LOCAL_ADMIN_SCRIPTS}/scm-prompt"
    if [ -f "$fb_master_zshrc" ]; then source "$fb_master_zshrc"; fi
    if [ -f "$fb_prompt_file" ]; then source "$fb_prompt_file"; fi
  if [[ -t 1 ]]; then echo "Setting proxy alias..."; fi
  alias with-proxy='env http_proxy=fwdproxy:8080 https_proxy=fwdproxy:8080 no_proxy=.fbcdn.net,.facebook.com,.thefacebook.com,.tfbnw.net,.fb.com,.fburl.com,.facebook.net,.sb.fbsbx.com,localhost RSYNC_PROXY=fwdproxy:8080 HTTP_PROXY=http://fwdproxy:8080 HTTPS_PROXY=http://fwdproxy:8080';
else
    if [[ -t 1 ]]; then  echo "Loading local settings..."; fi
set -g @prefix_highlight_fg 'white' # default is 'colour231'
	if [ -d "$HOME/.local/homebrew/Cellar/libgccjit/13.1.0" ]; then
		LDFLAGS="-L$HOME/.local/homebrew/Cellar/libgccjit/13.1.0/lib";
		CPPFLAGS="-I$HOME/.local/homebrew/Cellar/libgccjit/13.1.0/include";
	fi
	if [ -d "/Applications/Emacs.app/" ]; then export PATH="/Applications/Emacs.app/Contents/MacOS:$PATH"; fi
	if [ -d "/usr/local/opt/curl" ]; then export PATH="/usr/local/opt/curl/bin:$PATH"; fi
	if [ -d "$HOME/.rubies/ruby-3.1.2/" ]; then	export PATH="$HOME/.rubies/ruby-3.1.2/bin:$PATH"; fi
	if [ -d "$HOME/Library/Python/3.10/bin" ]; then export PATH="$PATH:$HOME/Library/Python/3.10/bin"; fi
	if [ -d "$HOME/Library/Python/3.9/bin" ]; then export PATH="$PATH:$HOME/Library/Python/3.9/bin"; fi
	if [ -d "/usr/local/opt" ]; then 
		PATH="/usr/local/opt/findutils/libexec/gnubin:$PATH";
		LDFLAGS="-L/usr/local/opt/curl/lib";
		CPPFLAGS="-I/usr/local/opt/curl/include";
		PKG_CONFIG_PATH="/usr/local/opt/curl/lib/pkgconfig";
	fi
	if [ -d "/usr/local/opt/grep/libexec/gnubin" ]; then PATH="/usr/local/opt/grep/libexec/gnubin:$PATH"; fi
fi
if [ -d "$HOME/.cargo" ]; then
	source "$HOME/.cargo/env";
fi
if [ -d "$HOME/.local/bin" ]; then export PATH="$HOME/.local/bin:$PATH"; fi
if [ -d "/usr/local/sbin" ]; then export PATH="/usr/local/sbin:$PATH"; fi
if type brew &> /dev/null; then
	export DYLD_LIBRARY_PATH="$(brew --prefix sqlite)/lib:/usr/lib";
	LDFLAGS="-L$(brew --prefix sqlite)/lib"
	CPPFLAGS="-I$(brew --prefix sqlite)/include"
	export PKG_CONFIG_PATH="$(brew --prefix sqlite)/lib/pkgconfig"
    export PATH="$(brew --prefix sqlite)/bin:$PATH";
fi 
if [ -d "$HOME/.local/homebrew" ]; then
	# export PATH=$(echo "$PATH" | tr ":" "\n" | grep -v '/opt/homebrew/bin' | xargs | tr ' ' ':');
    export PATH="$HOME/.local/homebrew/bin:$HOME/.local/homebrew/sbin:${PATH}";
fi
if [ -d "$HOME/.local/conda/bin" ]; then
	export PATH="$HOME/.local/conda/bin:${PATH}";
fi
if [ -d "/opt/anaconda3/bin" ]; then
	export PATH="/opt/anaconda3/bin:${PATH}";
fi
if [ -d "/usr/local/cuda/bin" ]; then
		export PATH="/usr/local/cuda/bin:${PATH}";
fi
