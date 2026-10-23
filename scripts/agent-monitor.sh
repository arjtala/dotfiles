#!/bin/bash

# Advanced Agent Monitor Script for Sway/Sketchybar Integration
# Monitors agent processes and provides detailed state management

# Configuration
NOTIFICATION_SCRIPT="$HOME/.local/bin/agent-notification.sh"
LOG_FILE="$HOME/.local/share/agent-completions.log"
PID_FILE_DIR="$HOME/.local/share/agent-pids"

# Create directories
mkdir -p "$PID_FILE_DIR"
mkdir -p "$(dirname "$LOG_FILE")"

# Function to create a PID file for tracking
create_pid_file() {
    local agent_name="$1"
    local pid="$2"
    local task_desc="$3"
    
    if [ -z "$agent_name" ] || [ -z "$pid" ]; then
        return 1
    fi
    
    local pid_file="$PID_FILE_DIR/${agent_name}_$pid.pid"
    echo "$task_desc" > "$pid_file"
    echo "$pid_file"
}

# Function to clean up PID files
cleanup_pid_file() {
    local pid_file="$1"
    if [ -f "$pid_file" ]; then
        rm -f "$pid_file"
    fi
}

# Function to send notification
send_notification() {
    local agent_name="$1"
    local task_description="$2"
    local success="${3:-true}"
    
    if [ -x "$NOTIFICATION_SCRIPT" ]; then
        "$NOTIFICATION_SCRIPT" "$agent_name" "$task_description"
    else
        echo "Notification script not found: $NOTIFICATION_SCRIPT"
        # Fallback to basic output
        if [ "$success" = "true" ]; then
            echo "✅ $agent_name completed: $task_description"
        else
            echo "❌ $agent_name failed: $task_description"
        fi
    fi
}

# Function to monitor a process by PID
monitor_process() {
    local pid="$1"
    local agent_name="$2"
    local task_description="$3"
    
    if [ -z "$pid" ] || [ -z "$agent_name" ]; then
        echo "Usage: monitor_process <PID> <AgentName> [TaskDescription]"
        return 1
    fi
    
    local pid_file=$(create_pid_file "$agent_name" "$pid" "$task_description")
    
    # Wait for process to complete
    while kill -0 "$pid" 2>/dev/null; do
        sleep 1
    done
    
    # Process has completed, send notification
    local exit_code=0
    wait "$pid" 2>/dev/null
    exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        send_notification "$agent_name" "$task_description" "true"
        echo "$(date '+%Y-%m-%d %H:%M:%S') - SUCCESS: $agent_name completed '$task_description'" >> "$LOG_FILE"
    else
        send_notification "$agent_name" "Failed: $task_description (exit code: $exit_code)" "false"
        echo "$(date '+%Y-%m-%d %H:%M:%S') - FAILED: $agent_name failed '$task_description' with exit code $exit_code" >> "$LOG_FILE"
    fi
    
    # Cleanup
    cleanup_pid_file "$pid_file"
}

# Function to get agent status for display
get_agent_status() {
    local status="sleeping"
    
    # Check for running agents
    if [ -d "$AGENT_PID_DIR" ]; then
        for pid_file in "$AGENT_PID_DIR"/*.pid; do
            if [ -f "$pid_file" ]; then
                local pid=$(basename "$pid_file" | sed 's/.*_\([0-9]*\)\.pid/\1/')
                if kill -0 "$pid" 2>/dev/null; then
                    status="working"
                    break
                fi
            fi
        done
    fi
    
    # If no running agents, check for recent completions (waiting state)
    if [ "$status" = "sleeping" ] && [ -f "$LOG_FILE" ]; then
        local last_completion=$(tail -n 1 "$LOG_FILE" 2>/dev/null)
        if [ -n "$last_completion" ]; then
            # Check if this completion was recent (within last 5 minutes)
            local completion_time=$(echo "$last_completion" | cut -d' ' -f1-2)
            local now_timestamp=$(date +%s)
            local completion_timestamp=$(date -d "$completion_time" +%s 2>/dev/null || echo 0)
            
            if [ "$completion_timestamp" != "0" ]; then
                local time_diff=$((now_timestamp - completion_timestamp))
                if [ "$time_diff" -lt 300 ]; then  # Less than 5 minutes ago
                    status="waiting"
                fi
            fi
        fi
    fi
    
    echo "$status"
}

# Function to get detailed agent information
get_agent_info() {
    local output=""
    
    # Show running agents
    if [ -d "$AGENT_PID_DIR" ]; then
        local has_running=false
        for pid_file in "$AGENT_PID_DIR"/*.pid; do
            if [ -f "$pid_file" ]; then
                local pid=$(basename "$pid_file" | sed 's/.*_\([0-9]*\)\.pid/\1/')
                local agent_name=$(basename "$pid_file" | sed 's/_.*//')
                local task_desc=$(cat "$pid_file" 2>/dev/null || echo "Running")
                
                if kill -0 "$pid" 2>/dev/null; then
                    output="$output<toolTip>⏳ $agent_name: $task_desc</toolTip>\n"
                    has_running=true
                fi
            fi
        done
        
        if [ "$has_running" = true ]; then
            output="$output<toolTip>--- Running Agents ---</toolTip>\n"
        fi
    fi
    
    # Show recent completions (waiting state)
    if [ -f "$LOG_FILE" ]; then
        local count=0
        while IFS= read -r line && [ "$count" -lt 5 ]; do
            if [ -n "$line" ]; then
                output="$output<toolTip>✅ $line</toolTip>\n"
                count=$((count + 1))
            fi
        done < <(tail -n 20 "$LOG_FILE" | tac)
    fi
    
    echo -e "$output"
}

# Function to list all agents
list_agents() {
    echo "Agent Status Report:"
    echo "==================="
    
    # Check for running agents
    local running_count=0
    if [ -d "$AGENT_PID_DIR" ]; then
        for pid_file in "$AGENT_PID_DIR"/*.pid; do
            if [ -f "$pid_file" ]; then
                local pid=$(basename "$pid_file" | sed 's/.*_\([0-9]*\)\.pid/\1/')
                local agent_name=$(basename "$pid_file" | sed 's/_.*//')
                local task_desc=$(cat "$pid_file" 2>/dev/null || echo "Running")
                
                if kill -0 "$pid" 2>/dev/null; then
                    echo "⏳ $agent_name (PID: $pid) - $task_desc"
                    running_count=$((running_count + 1))
                fi
            fi
        done
    fi
    
    # Show recent completions
    if [ -f "$LOG_FILE" ]; then
        echo ""
        echo "Recent Completions:"
        echo "------------------"
        tail -n 5 "$LOG_FILE" 2>/dev/null || echo "No completions recorded."
    fi
    
    if [ "$running_count" -eq 0 ] && [ ! -f "$LOG_FILE" ]; then
        echo "No agents currently running or completed recently."
    fi
}

# Main script logic
case "${1:-help}" in
    monitor)
        monitor_process "$2" "$3" "$4"
        ;;
    status)
        get_agent_status
        ;;
    info)
        get_agent_info
        ;;
    list)
        list_agents
        ;;
    recent)
        if [ -f "$LOG_FILE" ]; then
            tail -n 10 "$LOG_FILE"
        else
            echo "No completions recorded yet."
        fi
        ;;
    notify)
        send_notification "$2" "$3" "$4"
        ;;
    *)
        echo "Agent Monitor - Advanced Agent Completion Notifier"
        echo ""
        echo "Usage:"
        echo "  $0 monitor <PID> <AgentName> [TaskDescription]     - Monitor a running process"
        echo "  $0 status                                           - Get current agent status"
        echo "  $0 info                                             - Get detailed agent information"
        echo "  $0 list                                             - List all agents and completions"
        echo "  $0 recent                                           - Show recent completions"
        echo "  $0 notify \"AgentName\" \"TaskDescription\" [success]   - Send notification directly"
        echo ""
        echo "Status values:"
        echo "  sleeping - No agents running or recently completed"
        echo "  working  - Agent is currently processing"
        echo "  waiting  - Agent has completed and is waiting for attention"
        ;;
esac