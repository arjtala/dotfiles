export ZSH="$HOME/.oh-my-zsh"
ZSH_THEME="powerlevel10k/powerlevel10k"
plugins=(git virtualenv bazel)
source $ZSH/oh-my-zsh.sh
source $HOME/.purepower
source $HOME/.aliases
POWERLEVEL10k_MODE='nerdfont-complete'
POWERLEVEL10k_LEFT_PROMPT_ELEMENTS=(dir vcs newline status ssh)
POWERLEVEL10k_RIGHT_PROMPT_ELEMENTS=(status virtualenv aws)
POWERLEVEL10k_PROMPT_ADD_NEWLINE=true
