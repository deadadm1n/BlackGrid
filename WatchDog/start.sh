#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SESSION="${WATCHDOG_TMUX_SESSION:-watchdog}"

cd "$ROOT"

if ! command -v tmux >/dev/null 2>&1; then
    echo "tmux is required so WatchDog can keep running after you disconnect."
    echo "Install it on Ubuntu with:"
    echo "  sudo apt update && sudo apt install -y tmux"
    exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 was not found. Install Python or create .venv first."
    echo "On Ubuntu:"
    echo "  sudo apt update && sudo apt install -y python3 python3-venv python3-pip"
    exit 1
fi

if [[ ! -x "$ROOT/.venv/bin/python" ]]; then
    echo "Creating WatchDog Python virtual environment."
    python3 -m venv "$ROOT/.venv"
fi

PYTHON="$ROOT/.venv/bin/python"

if ! "$PYTHON" - <<'PY' >/dev/null 2>&1
import aiohttp
import discord
import psutil
import requests
import yaml
PY
then
    echo "Installing WatchDog Python requirements."
    "$PYTHON" -m pip install --upgrade pip
    "$PYTHON" -m pip install -r "$ROOT/requirements.txt"
fi

mkdir -p "$ROOT/logs" "$ROOT/state"

if tmux has-session -t "$SESSION" 2>/dev/null; then
    echo "WatchDog tmux session '$SESSION' is already running."
    echo "Attaching now. Detach safely with: Ctrl-b then d"
    exec tmux attach-session -t "$SESSION"
fi

echo "Starting WatchDog in tmux session '$SESSION'."
echo "Detach safely with: Ctrl-b then d"
echo "Reconnect later with: ./start.sh"

export WATCHDOG_ROOT="$ROOT"
export WATCHDOG_PYTHON="$PYTHON"

exec tmux new-session -s "$SESSION" \
    'cd "$WATCHDOG_ROOT" && "$WATCHDOG_PYTHON" main.py; code=$?; echo; echo "WatchDog exited with code $code."; echo "Press Enter to close this tmux window."; read -r; exit "$code"'
