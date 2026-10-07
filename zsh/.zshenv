# Prefer the active Homebrew installation, including in Emacs shell buffers.
if command -v brew >/dev/null 2>&1 && brew_prefix="$(brew --prefix 2>/dev/null)"; then
  export PATH="$brew_prefix/bin:$PATH"
fi
unset brew_prefix

# Work-only config lives in a private repo cloned to ~/.config/work.
# Keep the UUIDs in sync with my/apple-work-machine-uuids in
# emacs/.config/emacs/my-machine.el.
apple_work_machine_uuids=(93B3CC6E-3CEE-5FDE-A086-8C46BE01A8C6)
if [[ "$OSTYPE" == darwin* && -r "$HOME/.config/work/zsh/work.zsh" ]]; then
  machine_uuid="$(/usr/sbin/ioreg -rd1 -c IOPlatformExpertDevice 2>/dev/null |
    awk -F'"' '/IOPlatformUUID/ { print toupper($4) }')"
  if [[ -n "$machine_uuid" ]] && (( ${apple_work_machine_uuids[(Ie)$machine_uuid]} )); then
    source "$HOME/.config/work/zsh/work.zsh"
  fi
fi
unset apple_work_machine_uuids machine_uuid

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
if [[ -t 1 ]]; then  echo "Loading local settings..."; fi
if [ -d "$HOME/.local/homebrew/Cellar/libgccjit/13.1.0" ]; then
    export LDFLAGS="-L$HOME/.local/homebrew/Cellar/libgccjit/13.1.0/lib";
    export CPPFLAGS="-I$HOME/.local/homebrew/Cellar/libgccjit/13.1.0/include";
fi
if [ -d "/Applications/Emacs.app/" ]; then export PATH="/Applications/Emacs.app/Contents/MacOS:$PATH"; fi
if [ -d "/usr/local/opt/curl" ]; then export PATH="/usr/local/opt/curl/bin:$PATH"; fi
if [ -d "/opt/homebrew/opt/ruby" ]; then export PATH="/opt/homebrew/opt/ruby/bin:$PATH"; fi
if command -v ruby >/dev/null 2>&1; then
    gem_bindir="$(ruby -rrubygems -e 'print Gem.bindir' 2>/dev/null)"
    if [ -n "$gem_bindir" ]; then export PATH="$gem_bindir:$PATH"; fi
    unset gem_bindir
fi
if [ -d "$HOME/.rubies/ruby-3.1.2/" ]; then	export PATH="$HOME/.rubies/ruby-3.1.2/bin:$PATH"; fi
if [ -d "$HOME/Library/Python/3.10/bin" ]; then export PATH="$PATH:$HOME/Library/Python/3.10/bin"; fi
if [ -d "$HOME/Library/Python/3.9/bin" ]; then export PATH="$PATH:$HOME/Library/Python/3.9/bin"; fi
if [ -d "/usr/local/opt" ]; then
    PATH="/usr/local/opt/findutils/libexec/gnubin:$PATH";
    export LDFLAGS="-L/usr/local/opt/curl/lib";
    export CPPFLAGS="-I/usr/local/opt/curl/include";
    export PKG_CONFIG_PATH="/usr/local/opt/curl/lib/pkgconfig";
fi
if [ -d "/usr/local/opt/grep/libexec/gnubin" ]; then PATH="/usr/local/opt/grep/libexec/gnubin:$PATH"; fi
. "$HOME/.cargo/env"
