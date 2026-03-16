#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
DIST_DIR="$SCRIPT_DIR/dist"

if ! command -v node &>/dev/null; then
    echo "[ERROR] node not found. Install Node.js 18+ first."
    exit 1
fi

echo "[1/3] Installing frontend dependencies..."
cd "$FRONTEND_DIR"
npm ci --silent

echo "[2/3] Building frontend..."
npm run build

echo "[3/3] Done. Output: $DIST_DIR"
ls -lh "$DIST_DIR"/assets/
