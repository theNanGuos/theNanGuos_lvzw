#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$ROOT_DIR/frontend"

BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_HOST="${FRONTEND_HOST:-127.0.0.1}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  if [[ -n "$FRONTEND_PID" ]] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
    kill "$FRONTEND_PID" 2>/dev/null || true
  fi
  if [[ -n "$BACKEND_PID" ]] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi
}

trap cleanup EXIT INT TERM

command -v uv >/dev/null 2>&1 || {
  echo "缺少 uv，请先安装 uv 后再运行。"
  exit 1
}

command -v npm >/dev/null 2>&1 || {
  echo "缺少 npm，请先安装 Node.js/npm 后再运行。"
  exit 1
}

cd "$ROOT_DIR"

if [[ ! -d ".venv" ]]; then
  echo "未找到 .venv，正在同步 Python 依赖..."
  uv sync
fi

if [[ ! -d "$FRONTEND_DIR/node_modules" ]]; then
  echo "未找到 frontend/node_modules，正在安装前端依赖..."
  npm --prefix "$FRONTEND_DIR" install
fi

echo "启动后端: http://$BACKEND_HOST:$BACKEND_PORT"
uv run uvicorn app.api:app --reload --host "$BACKEND_HOST" --port "$BACKEND_PORT" &
BACKEND_PID="$!"

echo "启动前端: http://$FRONTEND_HOST:$FRONTEND_PORT"
npm --prefix "$FRONTEND_DIR" run dev -- --host "$FRONTEND_HOST" --port "$FRONTEND_PORT" &
FRONTEND_PID="$!"

echo "开发服务已启动。按 Ctrl+C 停止。"
wait -n "$BACKEND_PID" "$FRONTEND_PID"
