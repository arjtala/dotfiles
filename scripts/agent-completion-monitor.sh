#!/bin/bash

# Agent completion monitor script
# This script can be used to monitor and notify when AI agents complete tasks

# Configuration
NOTIFICATION_SCRIPT="$HOME/.local/bin/agent-notification.sh"
LOG_FILE="$HOME/.local/share/agent-completions.log"

# Function to send notification
send_notification() {
    local agent_name="$1"
    local task_description="$2"
    
    if [ -x "$NOTIFICATION_SCRIPT" ]; then
        "$NOTIFICATION_SCRIPT" "$agent_name" "$task_description"
    else
        echo "Notification script not found: $NOTIFICATION_SCRIPT"
        # Fallback to basic terminal output
        echo "🔔 $agent_name completed: $task_description"
    fi
}

# Function to monitor a process and notify when it completes
monitor_process() {
    local pid="$1"
    local agent_name="$2"
    local task_description="$3"
    
    if [ -z "$pid" ] || [ -z "$agent_name" ]; then
        echo "Usage: monitor_process <PID> <AgentName> [TaskDescription]"
        return 1
    fi
    
    # Wait for process to complete
    while kill -0 "$pid" 2>/dev/null; do
        sleep 1
    done
    
    # Process has completed, send notification
    send_notification "$agent_name" "$task_description"
}

# Function to create a wrapper that automatically notifies on completion
create_agent_wrapper() {
    local agent_command="$1"
    local agent_name="$2"
    
    if [ -z "$agent_command" ] || [ -z "$agent_name" ]; then
        echo "Usage: create_agent_wrapper \"command\" \"AgentName\""
        return 1
    fi
    
    # Create a temporary script that runs the command and notifies on completion
    local temp_script=$(mktemp)
    cat > "$temp_script" << EOF
#!/bin/bash
# Auto-generated agent wrapper for $agent_name

echo "Starting $agent_name..."
"$agent_command"
exit_code=\$?

if [ \$exit_code -eq 0 ]; then
    echo "$agent_name completed successfully"
    $NOTIFICATION_SCRIPT "$agent_name" "Task completed successfully"
else
    echo "$agent_name failed with exit code \$exit_code"
    $NOTIFICATION_SCRIPT "$agent_name" "Task failed with exit code \$exit_code"
fi

# Clean up
rm -f "$temp_script"
EOF
    
    chmod +x "$temp_script"
    echo "$temp_script"
}

# Main script logic
case "${1:-help}" in
    monitor)
        monitor_process "$2" "$3" "$4"
        ;;
    wrapper)
        create_agent_wrapper "$2" "$3"
        ;;
    notify)
        send_notification "$2" "$3"
        ;;
    *)
        echo "Agent Completion Monitor"
        echo "Usage:"
        echo "  $0 monitor <PID> <AgentName> [TaskDescription]     - Monitor a running process"
        echo "  $0 wrapper \"command\" \"AgentName\"              - Create wrapper script for agent"
        echo "  $0 notify \"AgentName\" \"TaskDescription\"         - Send notification directly"
        echo ""
        echo "Example:"
        echo "  $0 notify \"Claude\" \"Code review completed\""
        ;;
esac