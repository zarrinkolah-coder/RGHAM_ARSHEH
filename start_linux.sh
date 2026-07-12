#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
export RAGHAM_HOST="${RAGHAM_HOST:-0.0.0.0}"
export RAGHAM_PORT="${RAGHAM_PORT:-8080}"
exec python3 server.py
