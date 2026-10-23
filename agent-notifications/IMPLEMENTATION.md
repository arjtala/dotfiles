# Agent Notification System Implementation

## Overview

This implementation provides a sophisticated agent notification system that integrates with your Sway/Wayland environment, tmux, and sketchybar. It features:

1. **Visual Status Indicators** in sketchybar:
   - 🟏 Sleeping: No agents running or recently completed
   - ⏳ Working: Agent currently processing tasks
   - 🔔 Waiting: Agent has completed and is waiting for your attention

2. **Detailed Popup Information**: Clicking the icon shows a popup with:
   - Running agents
   - Recent completions
   - Task descriptions

3. **Multi-environment Support**:
   - Desktop notifications (Linux)
   - Tmux status line notifications
   - Terminal output fallbacks

## How It Works

### Agent Tracking
- When an agent process starts, it creates a PID file in `~/.local/share/agent-pids/`
- The PID file contains the task description
- When the process completes, the PID file is removed and a completion log entry is created

### Status Detection Logic
1. **Working**: If any PID files exist and their processes are still running
2. **Waiting**: If no processes are running but recent completions (within 5 minutes) exist
3. **Sleeping**: If no processes are running and no recent completions exist

### Sketchybar Integration
The sketchybar plugin automatically:
- Updates the icon based on current agent status
- Shows detailed information in popups when clicked
- Uses appropriate visual indicators for each state

## Usage Examples

### Starting an Agent with Notification
```bash
# Method 1: Use wrapper script (recommended)
run-agent-with-notification.sh "Claude" "Code review" "claude-cli --prompt 'Review this code' < input.txt"

# Method 2: Manual monitoring
my_agent_command &
PID=$!
agent-monitor.sh monitor $PID "Claude" "Code review"
```

### Checking Agent Status
```bash
# Check current status
agent-monitor.sh status

# View detailed information  
agent-monitor.sh info

# List all agents and completions
agent-monitor.sh list
```

## Visual States

| State | Icon | Description |
|-------|------|-------------|
| Sleeping | 😴 | No agents running or recently completed |
| Working | ⏳ | Agent currently processing tasks |
| Waiting | 🔔 | Agent completed and waiting for attention |

## Configuration

The system automatically:
- Creates required directories (`~/.local/share/agent-pids/`, `~/.local/share/agent-completions.log`)
- Uses `notify-send` for desktop notifications (Linux)
- Falls back to terminal output when needed
- Integrates with existing tmux and sketchybar configurations

## Testing

Run the test scripts to verify everything works:
```bash
./test-agent-status.sh
./test-sketchybar-agent.sh
```

The system is designed to be robust and will automatically adapt to your environment while providing consistent behavior across different scenarios.