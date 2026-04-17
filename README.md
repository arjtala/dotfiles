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
git clone --recurse-submodules <this-repo> ~/dotfiles
cd ~/dotfiles
```

**macOS:**

```sh
brew bundle install --file=~/dotfiles/Brewfile
```

**Fedora / Arch:** no one-shot equivalent — install per-tool deps listed in
each README's `## Dependencies` section.

**Everywhere, still needed:**

- `oh-my-zsh`:
  `sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"`
- Pure prompt (cloned into a path `.zshrc` already expects):
  `git clone https://github.com/sindresorhus/pure.git ~/dotfiles/zsh/.zsh/pure`
- TPM (tmux plugin manager):
  `git clone https://github.com/tmux-plugins/tpm ~/.tmux/plugins/tpm`
- Symlink configs into `$HOME` (ad-hoc — each file/dir points back into this
  repo; e.g. `ln -s ~/dotfiles/tmux/.tmux.conf ~/.tmux.conf`).
- In tmux: `<prefix> I` to install plugins.
