@echo off
rem 在 Windows 上构建 ytdlpgui.exe（需已安装 Python 3.10+）
cd /d %~dp0
if not exist .venv (
  python -m venv .venv
  .venv\Scripts\pip -q install -r backend\requirements.txt pyinstaller
) else (
  .venv\Scripts\pip -q install pyinstaller
)
.venv\Scripts\pyinstaller --clean ytdlpgui.spec
echo.
echo 构建完成: dist\ytdlpgui.exe
pause
