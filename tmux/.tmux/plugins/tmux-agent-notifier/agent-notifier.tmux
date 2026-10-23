# tmux agent notifier plugin
# Integrates with tmux to provide agent completion notifications

# Set up a function that can be called from within tmux
set -g @tmux_agent_notify '
    run-shell -b "
        if [ -n \"$1\" ] && [ -x \"$HOME/.local/bin/agent-notification.sh\" ]; then
            $HOME/.local/bin/agent-notification.sh \"$1\" \"$2\"
        fi
    "
'

# Add a key binding to manually trigger agent notification
bind-key C-a run-shell "$HOME/.local/bin/agent-notification.sh 'Test Agent' 'Manual test notification'"