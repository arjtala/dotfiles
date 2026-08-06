# dotfiles

Personal config for macOS and Linux. Each tool's keybindings live in its own
README:

| Tool | README |
| --- | --- |
| AeroSpace (macOS tiling WM) | [aerospace/README.md](aerospace/README.md) |
| sway (Linux/Wayland tiling WM) | [sway/README.md](sway/README.md) |
| i3 (Linux/X11 tiling WM) | [i3/README.md](i3/README.md) |
| tmux | [tmux/README.md](tmux/README.md) |
| Emacs | [emacs/.config/emacs/README.md](emacs/.config/emacs/README.md) (submodule) |

AeroSpace, sway, and i3 share the same window-management scheme so muscle
memory carries across platforms — see each file for the small deltas.

## New machine setup

```sh
git clone --recurse-submodules git@github.com:arjtala/dotfiles.git ~/dotfiles
cd ~/dotfiles
```

The recursive clone requires GitHub SSH access because the Emacs submodule is
private.

For an existing checkout, initialize any missing dependencies with:

```sh
git submodule sync --recursive
git submodule update --init --recursive
```

**macOS:**

```sh
brew bundle install --file=~/dotfiles/Brewfile
```

**Fedora / Arch:** no one-shot equivalent — install per-tool deps listed in
each README's `## Dependencies` section.

**Everywhere, still needed:**

- `oh-my-zsh` (clone it directly so its installer does not replace `.zshrc`):
  `git clone https://github.com/ohmyzsh/ohmyzsh.git ~/.oh-my-zsh`
- Symlink the packages needed on this machine with GNU Stow, for example:
  `stow --target="$HOME" zsh tmux ghostty`.
  The repository's `.stowrc` supplies common ignore rules when Stow traverses
  package directories. Stow may fold an entire source directory into one
  symlink, in which case files already inside it remain visible. Use
  `stow --restow <packages...>` after changing the selected packages.
- In tmux: `<prefix> I` to install plugins.

The legacy Vim config uses Vundle, which is not a tracked submodule. To use it:

```sh
git clone https://github.com/VundleVim/Vundle.vim.git ~/.vim/bundle/Vundle.vim
vim +PluginInstall +qall
```
