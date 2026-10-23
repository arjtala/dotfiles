#!/bin/bash

# Setup script to configure agent notifications for your environment

echo "Setting up agent notification system..."

# Create necessary directories
mkdir -p "$HOME/.local/bin"
mkdir -p "$HOME/.local/share"

# Copy notification scripts
cp "$HOME/dotfiles/scripts/agent-notification.sh" "$HOME/.local/bin/"
cp "$HOME/dotfiles/scripts/run-agent-with-notification.sh" "$HOME/.local/bin/"

chmod +x "$HOME/.local/bin/agent-notification.sh"
chmod +x "$HOME/dotfiles/scripts/run-agent-with-notification.sh"

# Create a simple test notification
echo "Agent notification system is ready!"
echo "To test: $HOME/.local/bin/agent-notification.sh 'Test Agent' 'This is a test notification'"

echo ""
echo "Usage examples:"
echo "1. Direct notification: agent-notification.sh 'Claude' 'Code review complete'"
echo "2. Run with notification: run-agent-with-notification.sh 'Claude' 'Code review' 'claude-cli --prompt \"Review this code\" < input.txt'"
echo ""
echo "Add to your shell profile to use with tmux:"
echo "export PATH=\"\$HOME/.local/bin:\$PATH\""