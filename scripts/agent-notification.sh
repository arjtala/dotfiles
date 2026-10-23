#!/bin/bash

# Agent completion notification script
# Works with tmux, sway/sketchybar, and desktop notifications

AGENT_NAME="$1"
TASK_DESCRIPTION="$2"

# Validate input
if [ -z "$AGENT_NAME" ]; then
    echo "Usage: $0 \"Agent Name\" \"Task Description\"" >&2
    exit 1
fi

# Log the completion
LOG_FILE="$HOME/.local/share/agent-completions.log"
mkdir -p "$(dirname "$LOG_FILE")"
echo "$(date '+%Y-%m-%d %H:%M:%S') - $AGENT_NAME: $TASK_DESCRIPTION" >> "$LOG_FILE"

# Determine the best notification method based on environment
NOTIFICATION_METHOD="none"

# Check if we're in tmux
if [ -n "$TMUX" ]; then
    NOTIFICATION_METHOD="tmux"
elif [ -n "$SSH_CLIENT" ] || [ -n "$SSH_TTY" ]; then
    # SSH session - might be remote
    NOTIFICATION_METHOD="terminal"
else
    # Check for desktop environment
    if command -v notify-send &> /dev/null; then
        NOTIFICATION_METHOD="desktop"
    elif command -v osascript &> /dev/null && [ "$(uname)" = "Darwin" ]; then
        NOTIFICATION_METHOD="macos"
    else
        NOTIFICATION_METHOD="terminal"
    fi
fi

# Send notification based on method
case "$NOTIFICATION_METHOD" in
    desktop)
        # Desktop notification using notify-send (Linux)
        notify-send \
            -a "AI Agent" \
            -u normal \
            -t 5000 \
            "$AGENT_NAME Completed" \
            "$TASK_DESCRIPTION"
        ;;
    macos)
        # macOS notification
        osascript -e "display notification \"$TASK_DESCRIPTION\" with title \"$AGENT_NAME Completed\""
        ;;
    tmux)
        # Tmux status line notification
        if command -v tmux &> /dev/null; then
            tmux display-message -p "🔔 $AGENT_NAME: $TASK_DESCRIPTION"
        else
            echo "🔔 $AGENT_NAME completed: $TASK_DESCRIPTION"
        fi
        ;;
    terminal)
        # Terminal output only
        echo "🔔 $AGENT_NAME completed: $TASK_DESCRIPTION"
        ;;
esac

# Play sound if available (for desktop environments)
if command -v paplay &> /dev/null; then
    # Try to play a notification sound
    paplay /usr/share/sounds/freedesktop/stereo/complete.oga 2>/dev/null || true
elif command -v afplay &> /dev/null && [ "$(uname)" = "Darwin" ]; then
    # macOS fallback (if running on macOS)
    afplay /System/Library/Sounds/Ping.aiff 2>/dev/null || true
fi

# Print to stdout for logging
echo "🔔 Notification: $AGENT_NAME completed - $TASK_DESCRIPTION"