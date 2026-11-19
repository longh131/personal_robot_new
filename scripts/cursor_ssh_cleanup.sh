#!/usr/bin/env bash
# Kill leftover Cursor Remote SSH server. Run from a normal SSH/login, not from Cursor.
set -euo pipefail
echo "cursor-server / multiplex processes:"
pgrep -a -f '/\.cursor-server/' || echo "(none)"
pkill -u "$USER" -f '/\.cursor-server/.*/cursor-server' 2>/dev/null || true
pkill -u "$USER" -f '/\.cursor-server/bin/multiplex-server/' 2>/dev/null || true
pkill -u "$USER" -f '/\.cursor-server/.*/server-main.js' 2>/dev/null || true
sleep 1
pgrep -a -f '/\.cursor-server/' || echo "cleared"
rm -f "$HOME/.cursor-server/data/User/workspaceStorage/"*/vscode.lock 2>/dev/null || true
echo "locks removed (if any). reconnect Cursor once."
