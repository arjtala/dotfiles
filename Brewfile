# Brewfile — macOS one-shot install.
#
# Usage:
#   brew bundle install --file=~/dotfiles/Brewfile
#
# After running, still needed:
#   - oh-my-zsh: sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"
#   - pure prompt: clone into ~/dotfiles/zsh/.zsh/pure (already expected by .zshrc)
#   - TPM (tmux plugin manager): git clone https://github.com/tmux-plugins/tpm ~/.tmux/plugins/tpm
#   - Symlink configs into $HOME (ad-hoc per file/dir — see each app's README)

# Taps
tap "nikitabobko/tap"              # AeroSpace
tap "FelixKratz/formulae"          # SketchyBar

# Shell / terminal
brew "zsh"
brew "bash"                        # /opt/homebrew/bin/bash 5.x for scripts that need declare -g etc.
brew "fzf"

# tmux + plugin deps
brew "tmux"
brew "entr"                        # tmux-autoreload
brew "rust"                        # tmux-thumbs builds via cargo

# Build tooling (LSP, Emacs native-comp, etc.)
brew "cmake"
brew "libgccjit"

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
