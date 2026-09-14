@echo off
rem ytdlpGUI 启动脚本（Windows）：创建 venv、安装依赖、启动服务并打开浏览器
cd /d %~dp0
if not exist .venv (
  python -m venv .venv
  .venv\Scripts\pip -q install -r backend\requirements.txt
)
set PORT=8765
start "" /b cmd /c "timeout /t 2 >nul & start http://127.0.0.1:%PORT%"
.venv\Scripts\python -m uvicorn backend.app.main:app --host 127.0.0.1 --port %PORT%
