#!/usr/bin/env bash

set -e

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$PROJECT_DIR/acoustic-insight-sentinel"

RELAY_PID=""
FRONTEND_PID=""
PIPELINE_PID=""

cleanup() {
    echo
    echo "Stopping OmniEar..."
    for pid in "$RELAY_PID" "$FRONTEND_PID" "$PIPELINE_PID"; do
        if [[ -n "$pid" ]]; then
            kill -TERM -- "-$pid" 2>/dev/null || true
        fi
    done
    echo "OmniEar stopped."
}

trap cleanup EXIT
trap 'exit 130' INT TERM TSTP

if [[ ! -f "$PROJECT_DIR/venv/bin/activate" ]]; then
    echo "Missing venv. Create it and install requirements first."
    exit 1
fi
if [[ ! -d "$FRONTEND_DIR" ]]; then
    echo "Missing dashboard directory: $FRONTEND_DIR"
    exit 1
fi

cd "$PROJECT_DIR"
source "$PROJECT_DIR/venv/bin/activate"

echo "Starting relay server..."
setsid python relay_server.py &
RELAY_PID=$!

echo "Starting dashboard..."
cd "$FRONTEND_DIR"
setsid npm run dev &
FRONTEND_PID=$!

echo "Starting OmniEar pipeline..."
cd "$PROJECT_DIR"
setsid python omniear_pipeline.py &
PIPELINE_PID=$!

sleep 2
echo
echo "OmniEar is running"
echo "Dashboard: http://localhost:5173"
echo "Relay:     ws://localhost:8765"
echo "Press Ctrl+C to stop everything."

wait
