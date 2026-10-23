#!/bin/bash

# Advanced Agent Status plugin for SketchyBar
# Shows agent states with visual indicators and detailed popup

# Configuration
AGENT_PID_DIR="$HOME/.local/share/agent-pids"
LOG_FILE="$HOME/.local/share/agent-completions.log"

# Default state - no agents running
if [ "$SENDER" = "mouse.exited.global" ]; then
    sketchybar --set "$NAME" popup.drawing=off
    exit 0
fi

# Function to get agent status
get_agent_status() {
    local status="sleeping"
    local count=0
    
    # Check for running agents
    if [ -d "$AGENT_PID_DIR" ]; then
        for pid_file in "$AGENT_PID_DIR"/*.pid; do
            if [ -f "$pid_file" ]; then
                local pid=$(basename "$pid_file" | sed 's/.*_\([0-9]*\)\.pid/\1/')
                if kill -0 "$pid" 2>/dev/null; then
                    status="working"
                    count=$((count + 1))
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

# Function to generate popup content
generate_popup() {
    local popup_content=""
    
    # Show running agents
    if [ -d "$AGENT_PID_DIR" ]; then
        local has_running=false
        for pid_file in "$AGENT_PID_DIR"/*.pid; do
            if [ -f "$pid_file" ]; then
                local pid=$(basename "$pid_file" | sed 's/.*_\([0-9]*\)\.pid/\1/')
                local agent_name=$(basename "$pid_file" | sed 's/_.*//')
                local task_desc=$(cat "$pid_file" 2>/dev/null || echo "Running")
                
                if kill -0 "$pid" 2>/dev/null; then
                    popup_content="$popup_content<toolTip>⏳ $agent_name: $task_desc</toolTip>\n"
                    has_running=true
                fi
            fi
        done
        
        if [ "$has_running" = true ]; then
            popup_content="$popup_content<toolTip>--- Running Agents ---</toolTip>\n"
        fi
    fi
    
    # Show recent completions (waiting state)
    if [ -f "$LOG_FILE" ]; then
        local count=0
        while IFS= read -r line && [ "$count" -lt 5 ]; do
            if [ -n "$line" ]; then
                popup_content="$popup_content<toolTip>✅ $line</toolTip>\n"
                count=$((count + 1))
            fi
        done < <(tail -n 20 "$LOG_FILE" | tac)
    fi
    
    # If no agents, show message
    if [ -z "$popup_content" ]; then
        popup_content="<toolTip>No active or recent agents</toolTip>"
    fi
    
    echo "$popup_content"
}

# Main logic
AGENT_STATUS=$(get_agent_status)

case "$AGENT_STATUS" in
    working)
        sketchybar --set "$NAME" icon="⏳" label.drawing=off tooltip="Agents are working..."
        ;;
    waiting)
        sketchybar --set "$NAME" icon="🔔" label.drawing=off tooltip="Agent(s) completed, waiting for your attention"
        ;;
    sleeping)
        sketchybar --set "$NAME" icon="😴" label.drawing=off tooltip="No active agents"
        ;;
esac

# Set up popup content
POPUP_CONTENT=$(generate_popup)
sketchybar --set "$NAME" popup.content="$POPUP_CONTENT"