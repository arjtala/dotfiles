#!/bin/bash

# Test script for sketchybar agent integration

echo "Testing Sketchybar Agent Integration"
echo "==================================="

# Create a fake running agent to test the status system
PID_FILE_DIR="$HOME/.local/share/agent-pids"
mkdir -p "$PID_FILE_DIR"

# Create a fake PID file for testing
echo "Test task description" > "$PID_FILE_DIR/TestAgent_12345.pid"

echo "Created test PID file: $PID_FILE_DIR/TestAgent_12345.pid"

# Test the agent status
echo ""
echo "Testing agent status:"
./agent-monitor.sh status

echo ""
echo "Testing agent info:"
./agent-monitor.sh info

# Clean up
rm -f "$PID_FILE_DIR/TestAgent_12345.pid"
echo ""
echo "Test completed. Cleaned up test files."