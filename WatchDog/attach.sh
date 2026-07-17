#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_ROOT="$(dirname "$ROOT")"
INSTALL_NAME="$(basename "$INSTALL_ROOT")"
SAFE_NAME="$(printf '%s' "$INSTALL_NAME" | tr -cs 'A-Za-z0-9_.-' '-' | sed 's/^-//; s/-$//')"
SESSION="${WATCHDOG_TMUX_SESSION:-blackgrid-${SAFE_NAME:-server}}"

if ! command -v tmux >/dev/null 2>&1; then
    echo "tmux is required to reattach to WatchDog."
    echo "Install it with: sudo apt update && sudo apt install -y tmux"
    exit 1
fi

if ! tmux has-session -t "$SESSION" 2>/dev/null; then
    echo "No WatchDog tmux session named '$SESSION' is running."
    echo "Start it with: ./start.sh or ../start-watchdog.sh"
    exit 1
fi

echo "Attaching to WatchDog tmux session '$SESSION'."
echo "Detach safely with: Ctrl-b then d"
exec tmux attach-session -t "$SESSION"
