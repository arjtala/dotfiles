# Brewfile — macOS one-shot install.
#
# Usage:
#   brew bundle install --file=~/dotfiles/Brewfile
#
# After running, still needed:
#   - oh-my-zsh: git clone https://github.com/ohmyzsh/ohmyzsh.git ~/.oh-my-zsh
#   - submodules: git -C ~/dotfiles submodule sync --recursive
#                 git -C ~/dotfiles submodule update --init --recursive
#   - symlinks: cd ~/dotfiles && stow --target="$HOME" <packages...>

# Taps
tap "nikitabobko/tap"              # AeroSpace
tap "FelixKratz/formulae"          # SketchyBar

# Shell / terminal
brew "zsh"
brew "bash"                        # /opt/homebrew/bin/bash 5.x for scripts that need declare -g etc.
brew "fzf"
brew "stow"
brew "coreutils"                   # gls used by bash/.aliases
brew "gnu-sed"                     # gsed used by bash/.aliases

# tmux + plugin deps
brew "tmux"
brew "entr"                        # tmux-autoreload
brew "rust"                        # tmux-thumbs builds via cargo

# Build tooling (LSP, Emacs native-comp, etc.)
brew "cmake"
brew "libgccjit"
brew "sqlite"

# Python / Node toolchains commonly used by editor tooling
brew "node"
brew "pyright"                     # Emacs lsp-pyright
brew "ruff"                        # Python lint / format

# Core CLI upgrades
brew "ripgrep"
brew "fd"
brew "bat"
brew "eza"
brew "jq"
brew "git"
brew "gh"

# Status bar / dock stack
brew "sketchybar"

# Window manager + terminal
cask "nikitabobko/tap/aerospace"
cask "ghostty"

# Font
cask "font-jetbrains-mono-nerd-font"
cask "font-symbols-only-nerd-font"
