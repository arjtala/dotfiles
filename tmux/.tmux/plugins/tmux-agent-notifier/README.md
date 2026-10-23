# Tmux Agent Notifier

This plugin provides integration for AI agent notifications within tmux.

## Features

- Integration with desktop notifications
- Tmux status line feedback
- Simple command to trigger notifications

## Usage

Add this to your tmux configuration:

```bash
# Enable agent notifier
set -g @agent_notifier_enabled on
```

Then you can use the following commands in tmux:

1. `tmux-agent-complete "AgentName" "TaskDescription"` - Send notification
2. `C-a C-n` - Test notification (bound to Ctrl-a, then Ctrl-n)

## Configuration

- `@agent_notifier_script`: Path to notification script (default: `$HOME/.local/bin/agent-notification.sh`)