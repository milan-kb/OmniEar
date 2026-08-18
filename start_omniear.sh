#!/bin/bash

set -e

PROJECT_DIR="$HOME/projects/omniear"
FRONTEND_DIR="$PROJECT_DIR/acoustic-insight-sentinel"

RELAY_PID=""
FRONTEND_PID=""
PIPELINE_PID=""

cleanup() {
    echo ""
    echo "🛑 Stopping OmniEar..."

    if [[ -n "$RELAY_PID" ]]; then
        kill -TERM -- "-$RELAY_PID" 2>/dev/null || true
    fi

    if [[ -n "$FRONTEND_PID" ]]; then
        kill -TERM -- "-$FRONTEND_PID" 2>/dev/null || true
    fi

    if [[ -n "$PIPELINE_PID" ]]; then
        kill -TERM -- "-$PIPELINE_PID" 2>/dev/null || true
    fi

    sleep 1

    echo "✅ OmniEar stopped."
}

# Clean up when Ctrl+C, terminal close, or script exit happens
trap cleanup EXIT
trap 'exit 130' INT TERM TSTP

cd "$PROJECT_DIR"

echo "🚀 Starting OmniEar..."
echo ""

# Python environment
source "$PROJECT_DIR/venv/bin/activate"

# ─────────────────────────────────────
# Relay server
# ─────────────────────────────────────

echo "📡 Starting relay server..."

setsid python relay_server.py &
RELAY_PID=$!

# ─────────────────────────────────────
# Frontend
# ─────────────────────────────────────

echo "🌐 Starting dashboard..."

cd "$FRONTEND_DIR"

setsid npm run dev &
FRONTEND_PID=$!

# ─────────────────────────────────────
# Detection pipeline
# ─────────────────────────────────────

echo "🧠 Starting OmniEar pipeline..."

cd "$PROJECT_DIR"

setsid python omniear_pipeline.py &
PIPELINE_PID=$!

# Give services a moment to start
sleep 2

echo ""
echo "========================================"
echo "          🎧 OMNIEAR RUNNING"
echo "========================================"
echo ""
echo "📡 Relay:      ws://localhost:8765"
echo "🧠 Pipeline:   PID $PIPELINE_PID"
echo "🌐 Dashboard:  http://localhost:5173"
echo ""
echo "========================================"
echo "Open the dashboard:"
echo "👉 http://localhost:5173"
echo "========================================"
echo ""
echo "Press Ctrl+C to stop everything."
echo ""

# Keep script alive
wait
