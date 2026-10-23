#!/bin/bash

# Wrapper script to run AI agents and notify when they complete
# Usage: ./run-agent-with-notification.sh "Agent Name" "Task Description" "command to run"

if [ $# -lt 3 ]; then
    echo "Usage: $0 \"Agent Name\" \"Task Description\" \"command to run\""
    echo ""
    echo "Example:"
    echo "  $0 \"Claude\" \"Code review\" \"claude-cli --prompt 'Review this code' < input.txt\""
    exit 1
fi

AGENT_NAME="$1"
TASK_DESCRIPTION="$2"
COMMAND="$3"

echo "Starting $AGENT_NAME for: $TASK_DESCRIPTION"
echo "Command: $COMMAND"

# Run the command in background and capture its PID
eval "$COMMAND" &
PID=$!

echo "Process started with PID: $PID"

# Wait for completion
wait $PID
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ $AGENT_NAME completed successfully"
    # Send notification
    if [ -x "$HOME/.local/bin/agent-notification.sh" ]; then
        "$HOME/.local/bin/agent-notification.sh" "$AGENT_NAME" "$TASK_DESCRIPTION"
    else
        echo "⚠️  Notification script not found, but task completed"
    fi
else
    echo "❌ $AGENT_NAME failed with exit code: $EXIT_CODE"
    if [ -x "$HOME/.local/bin/agent-notification.sh" ]; then
        "$HOME/.local/bin/agent-notification.sh" "$AGENT_NAME" "Failed: $TASK_DESCRIPTION (exit code: $EXIT_CODE)"
    fi
fi

exit $EXIT_CODE