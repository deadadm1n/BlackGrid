#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_ROOT="$(dirname "$ROOT")"
INSTALL_NAME="$(basename "$INSTALL_ROOT")"
SAFE_NAME="$(printf '%s' "$INSTALL_NAME" | tr -cs 'A-Za-z0-9_.-' '-' | sed 's/^-//; s/-$//')"
SESSION="${WATCHDOG_TMUX_SESSION:-blackgrid-${SAFE_NAME:-server}}"
STOP_COMMAND="${WATCHDOG_STOP_COMMAND:-wrapper stop}"

if ! command -v tmux >/dev/null 2>&1; then
    echo "tmux is required to stop a detached WatchDog session."
    exit 1
fi

if ! tmux has-session -t "$SESSION" 2>/dev/null; then
    echo "No WatchDog tmux session named '$SESSION' is running."
    exit 0
fi

echo "Sending '$STOP_COMMAND' to WatchDog tmux session '$SESSION'."
tmux send-keys -t "$SESSION" "$STOP_COMMAND" Enter

echo "Attach with ./attach.sh to watch shutdown, or wait a few seconds and check tmux ls."
