#!/bin/bash

# Test script for agent status functionality

echo "Testing Agent Status System"
echo "==========================="

# Test basic notification
echo "1. Testing basic notification..."
./agent-notification.sh "Test Agent" "This is a test notification"

echo ""
echo "2. Testing agent monitor status..."
./agent-monitor.sh status

echo ""
echo "3. Testing agent monitor info..."
./agent-monitor.sh info

echo ""
echo "4. Testing agent list..."
./agent-monitor.sh list

echo ""
echo "Agent status system tests complete!"