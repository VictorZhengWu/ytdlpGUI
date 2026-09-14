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
    if os.environ.get("YTDLPGUI_NO_BROWSER") != "1":
        open_browser()
    import uvicorn
    from backend.app.main import app
    print(f"ytdlpGUI 已启动: http://{HOST}:{PORT}  （关闭本程序即退出）")
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")


if __name__ == "__main__":
    main()
