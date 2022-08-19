autoload zmv
export TERM=xterm-256color
export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8
export LANGUAGE=en_US.UTF-8

if [[ "$HOST" == *"facebook"* ]];
then
  if [[ -t 1 ]]; then  echo "Loading FB specific settings..."; fi
  source /usr/facebook/ops/rc/master.zshrc;
  if [[ -t 1 ]]; then echo "Setting proxy alias..."; fi
  alias with-proxy='env http_proxy=fwdproxy:8080 https_proxy=fwdproxy:8080 no_proxy=.fbcdn.net,.facebook.com,.thefacebook.com,.tfbnw.net,.fb.com,.fburl.com,.facebook.net,.sb.fbsbx.com,localhost RSYNC_PROXY=fwdproxy:8080 HTTP_PROXY=http://fwdproxy:8080 HTTPS_PROXY=http://fwdproxy:8080';
else
    if [[ -t 1 ]]; then  echo "Loading local settings..."; fi
	if [ -d "/Applications/Emacs.app/Contents/MacOS/bin" ]; then
		export PATH="/Applications/Emacs.app/Contents/MacOS/bin:$PATH";
	fi
	export TERMINAL=kitty
	export PATH=$PATH:$HOME/Library/Python/3.7/bin;
	PATH="/usr/local/opt/findutils/libexec/gnubin:$PATH";
	PATH="/usr/local/opt/curl/bin:$PATH";
	LDFLAGS="-L/usr/local/opt/curl/lib";
	CPPFLAGS="-I/usr/local/opt/curl/include";
	PKG_CONFIG_PATH="/usr/local/opt/curl/lib/pkgconfig";
	source "$HOME/.cargo/env";
	export PATH="/usr/local/opt/curl/bin:$PATH";
    export PATH="$HOME/.local/homebrew/bin:$HOME/.local/homebrew/sbin:$PATH";
	PATH="/usr/local/opt/grep/libexec/gnubin:$PATH";
fi
PATH=$HOME/.local/bin:$PATH
export PATH="/usr/local/sbin:$PATH"
. "$HOME/.cargo/env"
