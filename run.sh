#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Run in background, detach from terminal
nohup python3 main.py >/dev/null 2>&1 &
echo "Genshin Widget started (PID $!)."
