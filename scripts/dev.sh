#!/usr/bin/env bash
# ==============================================================================
# HydroVision One-Command Development Launcher
# Starts both FastAPI Backend (port 8000) and Vite Frontend (port 5173)
# ==============================================================================
set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Default mode is mock unless explicitly overridden
export HYDRO_MODE="${HYDRO_MODE:-mock}"

echo "=================================================================="
echo " Starting HydroVision Development Environment"
echo " Engine Mode: $HYDRO_MODE"
echo " Root:        $REPO_ROOT"
echo "=================================================================="

# Locate virtual environment Python / Uvicorn
if [ -f "$REPO_ROOT/.venv/bin/uvicorn" ]; then
    UVICORN_BIN="$REPO_ROOT/.venv/bin/uvicorn"
elif command -v uvicorn >/dev/null 2>&1; then
    UVICORN_BIN="uvicorn"
else
    echo "ERROR: uvicorn not found. Please activate your virtualenv or run: pip install -r requirements.txt"
    exit 1
fi

# Cleanup child processes on exit (Ctrl+C / SIGINT / SIGTERM)
cleanup() {
    echo ""
    echo "Shutting down HydroVision development servers..."
    if [ -n "$BACKEND_PID" ]; then
        kill "$BACKEND_PID" 2>/dev/null || true
    fi
    if [ -n "$FRONTEND_PID" ]; then
        kill "$FRONTEND_PID" 2>/dev/null || true
    fi
    wait 2>/dev/null || true
    echo "All services stopped cleanly."
}
trap cleanup SIGINT SIGTERM EXIT

# 1. Start Backend in background
echo "[1/2] Starting FastAPI backend on http://localhost:8000..."
"$UVICORN_BIN" backend.app:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Wait briefly for backend port to bind
sleep 1.5

# 2. Start Frontend in background
echo "[2/2] Starting Vite frontend on http://localhost:5173..."
cd "$REPO_ROOT/frontend"
npm run dev -- --port 5173 &
FRONTEND_PID=$!

echo "=================================================================="
echo " HydroVision is Live!"
echo " • Frontend Dashboard: http://localhost:5173"
echo " • Backend API:        http://localhost:8000"
echo " • Swagger API Docs:   http://localhost:8000/docs"
echo " Press Ctrl+C to terminate both servers."
echo "=================================================================="

# Wait for both processes
wait "$BACKEND_PID" "$FRONTEND_PID"
