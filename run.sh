#!/usr/bin/env bash
# ytdlpGUI 启动脚本（Linux/macOS）：创建 venv、安装依赖、启动服务并打开浏览器
set -e
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  python3 -m venv .venv
  .venv/bin/pip -q install -r backend/requirements.txt
fi
PORT="${YTDLPGUI_PORT:-8765}"
# ./run.sh --lan 或 YTDLPGUI_HOST=0.0.0.0 ./run.sh 监听所有网卡（局域网可访问）
HOST="${YTDLPGUI_HOST:-127.0.0.1}"
if [ "$1" = "--lan" ]; then HOST="0.0.0.0"; fi
if [ "$HOST" = "0.0.0.0" ]; then echo "局域网模式: 本机局域网 IP 均可通过 $PORT 端口访问"; fi
if command -v xdg-open >/dev/null 2>&1; then (sleep 1.5; xdg-open "http://127.0.0.1:$PORT") & fi
exec .venv/bin/python -m uvicorn backend.app.main:app --host "$HOST" --port "$PORT"
