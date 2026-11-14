#!/usr/bin/env bash
# Startup script for HydroVision FastAPI backend server
set -e

# Default to mock mode if not specified
export HYDRO_MODE=${HYDRO_MODE:-mock}
HOST=${HOST:-0.0.0.0}
PORT=${PORT:-8000}

echo "=================================================="
echo " Starting HydroVision Backend Server"
echo " Mode: $HYDRO_MODE"
echo " Host: $HOST:$PORT"
echo " Documentation: http://localhost:$PORT/docs"
echo "=================================================="

exec uvicorn backend.app:app --host "$HOST" --port "$PORT" --reload

