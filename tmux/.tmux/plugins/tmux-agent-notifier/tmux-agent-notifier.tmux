# tmux-agent-notifier - Notify when AI agents complete tasks
# This plugin integrates with tmux to detect agent completion

# Set up a hook to monitor command completion in tmux panes
# We'll use a custom function that can be called when an agent finishes

# Create a function that can be used by scripts to notify of agent completion
set -g @agent_notifier_script "$HOME/.local/bin/agent-notification.sh"

# Add a command to manually trigger notifications (for testing)
bind-key C-n run-shell "echo 'Testing agent notification' && $HOME/.local/bin/agent-notification.sh 'Test Agent' 'This is a test notification'"

# Function to notify about agent completion
# This can be called from shell scripts when an agent finishes
# Usage: tmux-agent-complete "AgentName" "TaskDescription"
set -g @tmux_agent_complete_hook '
    run-shell -b "
        if [ -n \"$1\" ]; then
            $HOME/.local/bin/agent-notification.sh \"$1\" \"$2\"
        fi
    "
'

# Set up a way to track agent processes (can be extended)
set -g @agent_process_tracking on