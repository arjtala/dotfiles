# Agent Notification System

This system provides notifications when AI agents (Claude, Kosmonot, Pi, etc.) complete their tasks.

## Features

- Desktop notifications using `notify-send`
- Tmux integration for terminal-based notifications
- Sketchybar integration for status bar indicators
- Logging of agent completions to a file
- Sound alerts when available

## Setup

Run the setup script to install all components:

```bash
./setup-agent-notifications.sh
```

## Usage

### Direct Notification
```bash
agent-notification.sh "Agent Name" "Task Description"
```

### Run Command with Notification
```bash
run-agent-with-notification.sh "Agent Name" "Task Description" "command to run"
```

### Manual Testing
You can test the notification system by running:
```bash
agent-notification.sh "Test Agent" "This is a test notification"
```

## Integration

The system integrates with your existing tmux and sketchybar configurations:

- **Tmux**: Notifications are sent via desktop notifications or tmux status line
- **Sketchybar**: Shows agent completion status in the right-side bar
- **Logging**: All completions are logged to `~/.local/share/agent-completions.log`

## Components

1. `agent-notification.sh` - Core notification script
2. `run-agent-with-notification.sh` - Wrapper to run commands and notify on completion
3. `setup-agent-notifications.sh` - Installation script
4. Sketchybar plugin for agent status indicator