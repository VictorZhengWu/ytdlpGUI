"""ytdlpgui.exe 入口：启动本地服务并打开浏览器。

源码运行: python launcher.py
打包后（PyInstaller onefile）: ytdlpgui.exe 双击即用
"""

import os
import sys
import threading
import webbrowser
from pathlib import Path

PORT = int(os.environ.get("YTDLPGUI_PORT", "8765"))
HOST = "127.0.0.1"


def prepare_env():
    if getattr(sys, "frozen", False):
        # PyInstaller 解包目录（只读资源）
        os.environ["YTDLPGUI_ROOT"] = getattr(sys, "_MEIPASS", ".")
        # 可写数据目录：exe 同级的 data/（配置、预设、下载记录）
        writable = Path(sys.executable).parent / "data"
        writable.mkdir(exist_ok=True)
        os.environ["YTDLPGUI_DATA_DIR"] = str(writable)


def open_browser():
    threading.Timer(1.5, lambda: webbrowser.open(f"http://{HOST}:{PORT}")).start()


def main():
    prepare_env()
    # 窗口模式（exe console=False / pythonw）下 sys.stdout/stderr 为 None，
    # uvicorn 日志 formatter 调 stdout.isatty() 会直接崩溃——补一个可写的空流
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")
    # 无控制台/重定向下 stdout 编码随系统代码页（如 cp1252），非 ASCII 消息会炸启动——统一容错
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    if os.environ.get("YTDLPGUI_NO_BROWSER") != "1":
        open_browser()
    import uvicorn
    from backend.app.main import app
    print(f"ytdlpgui running at http://{HOST}:{PORT}  (close this program to exit)")
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")


if __name__ == "__main__":
    main()
