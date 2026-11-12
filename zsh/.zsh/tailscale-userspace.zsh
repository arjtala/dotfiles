# Tailscale in userspace mode: one terminal opts in to the tailnet; the others, and the rest of the
# system, keep the normal network. Nothing here touches system network settings.
#
#   tsu-up         start the userspace daemon (first time: `tsu up` prints a login URL)
#   tsu ARGS       the tailscale CLI for that daemon: tsu status, tsu up, tsu down
#   tsu-on         route this terminal's proxy-aware tools through it (ALL_PROXY, HTTP(S)_PROXY)
#   tsu-off        put this terminal's previous proxy settings back
#   tssh HOST ...  ssh to a tailnet host through it (`tailscale nc`, so the netcat flavour doesn't matter)
#   tsu-stop       stop the daemon
#
# macOS: Homebrew's tailscale, by full path, never the GUI app's /usr/local/bin/tailscale wrapper.
# Linux: the distro's tailscale/tailscaled (tailscaled is often in /usr/sbin, off a user's PATH). If the system
# tailscaled is running, the machine is already on the tailnet: tsu then talks to it, tssh is plain ssh, and
# tsu-up and tsu-on do nothing (TSU_USERSPACE=1 tsu-up still starts a separate userspace node).

_TSU_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/tailscale"
_TSU_SOCK="$_TSU_DIR/tailscaled.sock"
_TSU_SOCKS_PORT=1055
_TSU_HTTP_PORT=1056
_TSU_PROXY_VARS=(ALL_PROXY all_proxy HTTP_PROXY HTTPS_PROXY http_proxy https_proxy NO_PROXY no_proxy)

if [[ "$OSTYPE" == darwin* ]]; then
    for _tsu_d in /opt/homebrew/opt/tailscale/bin /usr/local/opt/tailscale/bin; do
        if [[ -x "$_tsu_d/tailscaled" ]]; then
            _TSU_CLI="$_tsu_d/tailscale"; _TSU_DAEMON="$_tsu_d/tailscaled"; break
        fi
    done
    unset _tsu_d
else
    _TSU_CLI="$(command -v tailscale 2>/dev/null)"
    _TSU_DAEMON="$(command -v tailscaled 2>/dev/null)"
    [[ -z "$_TSU_DAEMON" && -x /usr/sbin/tailscaled ]] && _TSU_DAEMON=/usr/sbin/tailscaled
fi

_tsu_running() {
    pgrep -f -- "--socket=$_TSU_SOCK" >/dev/null 2>&1
}

# Linux only: the system tailscaled (a TUN device; the whole machine is on the tailnet).
_tsu_system() {
    [[ "$OSTYPE" == linux* ]] && { [[ -S /var/run/tailscale/tailscaled.sock ]] || [[ -S /run/tailscale/tailscaled.sock ]]; }
}

tsu() {
    if [[ -z "$_TSU_CLI" || ! -x "$_TSU_CLI" ]]; then
        echo "tsu: tailscale CLI not found (macOS: brew install tailscale)" >&2
        return 127
    fi
    if ! _tsu_running && _tsu_system; then
        "$_TSU_CLI" "$@"  # no userspace daemon here: the system one
    else
        "$_TSU_CLI" --socket="$_TSU_SOCK" "$@"
    fi
}

tsu-up() {
    if [[ -z "$_TSU_DAEMON" || ! -x "$_TSU_DAEMON" ]]; then
        echo "tsu-up: tailscaled not found (macOS: brew install tailscale)" >&2
        return 127
    fi
    if ! _tsu_running && _tsu_system && [[ -z "$TSU_USERSPACE" ]]; then
        echo "tsu-up: the system tailscaled is running, so this machine is already on the tailnet; tsu uses it."
        echo "        (TSU_USERSPACE=1 tsu-up starts a separate userspace node anyway.)"
        return 0
    fi
    if ! _tsu_running; then
        mkdir -p "$_TSU_DIR"
        nohup "$_TSU_DAEMON" --tun=userspace-networking \
            --socks5-server="localhost:$_TSU_SOCKS_PORT" \
            --outbound-http-proxy-listen="localhost:$_TSU_HTTP_PORT" \
            --statedir="$_TSU_DIR" --socket="$_TSU_SOCK" >"$_TSU_DIR/tailscaled.log" 2>&1 &!
        local i
        for i in {1..50}; do [[ -S "$_TSU_SOCK" ]] && break; sleep 0.1; done
    fi
    tsu up "$@"  # the first time, this prints the login URL
}

tsu-stop() {
    pkill -f -- "--socket=$_TSU_SOCK" && echo "tsu: daemon stopped"
}

tsu-on() {
    [[ -n "$_TSU_ON" ]] && return 0
    if ! _tsu_running && _tsu_system; then
        echo "tsu-on: not needed: the system tailscaled already routes tailnet traffic for every terminal"
        return 0
    fi
    _tsu_running || echo "tsu-on: the daemon is not running (tsu-up)" >&2
    typeset -g _TSU_SAVED="$(typeset -p -- "${_TSU_PROXY_VARS[@]}" 2>/dev/null)"
    local socks="socks5h://localhost:$_TSU_SOCKS_PORT" http="http://localhost:$_TSU_HTTP_PORT"
    local keep="${NO_PROXY:-$no_proxy}"
    export ALL_PROXY="$socks" all_proxy="$socks"
    export HTTP_PROXY="$http" HTTPS_PROXY="$http" http_proxy="$http" https_proxy="$http"
    export NO_PROXY="${keep:+$keep,}localhost,127.0.0.1,::1" no_proxy="${keep:+$keep,}localhost,127.0.0.1,::1"
    typeset -g _TSU_ON=1
    echo "tsu: this terminal now uses the tailnet proxy (tsu-off to undo)"
}

tsu-off() {
    [[ -z "$_TSU_ON" ]] && return 0
    unset -- "${_TSU_PROXY_VARS[@]}"
    [[ -n "$_TSU_SAVED" ]] && eval "$_TSU_SAVED"  # restores whatever proxy settings were there before
    unset _TSU_ON _TSU_SAVED
    echo "tsu: proxy settings restored"
}

tssh() {
    if ! _tsu_running && _tsu_system; then
        ssh "$@"  # the system tailscaled routes it
    else
        ssh -o ProxyCommand="'$_TSU_CLI' --socket='$_TSU_SOCK' nc %h %p" "$@"
    fi
}
