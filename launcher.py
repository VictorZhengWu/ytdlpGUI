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


def _pick_port(preferred: int, tries: int = 10) -> int:
    """桌面应用允许多开/与其它实例共存：首选端口被占则顺延（8765→8766…）。"""
    import socket
    for port in range(preferred, preferred + tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex((HOST, port)) != 0:  # 连不上 = 没人监听 = 可用
                return port
    raise RuntimeError(f"no free port in {preferred}..{preferred + tries - 1}")


def prepare_env():
    if getattr(sys, "frozen", False):
        # PyInstaller 解包目录（只读资源）
        os.environ["YTDLPGUI_ROOT"] = getattr(sys, "_MEIPASS", ".")
        # 可写数据目录：exe 同级的 data/（配置、预设、下载记录）
        writable = Path(sys.executable).parent / "data"
        writable.mkdir(exist_ok=True)
        os.environ["YTDLPGUI_DATA_DIR"] = str(writable)


def open_browser(port: int = PORT):
    threading.Timer(1.5, lambda: webbrowser.open(f"http://{HOST}:{port}")).start()


def _wait_server_up(port: int, timeout: float = 8.0):
    import time, urllib.request
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"http://{HOST}:{port}/", timeout=1)
            return True
        except OSError:
            time.sleep(0.15)
    return False


def _centered_pos(width: int, height: int):
    """主显示器（原点屏）工作区居中坐标；pywebview 不指定坐标时窗口可能落在副屏。
    取不到（非 Windows/异常）返回 None 交给系统默认放置。"""
    try:
        import ctypes
        user32 = ctypes.windll.user32
        user32.SetProcessDPIAware()
        return max(0, (user32.GetSystemMetrics(0) - width) // 2), \
               max(0, (user32.GetSystemMetrics(1) - height) // 3)
    except Exception:
        return None


def run_native_window():
    """原生桌面窗口模式：pywebview + 系统 WebView（Windows 为 Edge WebView2）。
    后端跑在同一进程内的子线程；关闭窗口即退出整个程序。"""
    import threading
    import webview

    import uvicorn
    from backend.app.main import app

    port = _pick_port(PORT)  # 已有实例占用 8765 时自动顺延
    server = uvicorn.Server(uvicorn.Config(app, host=HOST, port=port, log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    if not _wait_server_up(port):
        raise RuntimeError("backend failed to start")

    kwargs = dict(width=1280, height=820, min_size=(960, 600))
    pos = _centered_pos(1280, 820)
    if pos:
        kwargs["x"], kwargs["y"] = pos
    webview.create_window("ytdlpGUI", f"http://{HOST}:{port}/", **kwargs)
    webview.start()  # 阻塞到窗口关闭（GUI 主线程要求）
    server.should_exit = True


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
        try:
            run_native_window()  # 首选：独立桌面应用窗口
            return
        except Exception as e:
            print(f"native window unavailable ({e!r}); falling back to browser")
        import uvicorn
        from backend.app.main import app
        port = _pick_port(PORT)
        open_browser(port)
        print(f"ytdlpgui running at http://{HOST}:{port}  (close this program to exit)")
        uvicorn.run(app, host=HOST, port=port, log_level="warning")
    else:
        import uvicorn
        from backend.app.main import app
        print(f"ytdlpgui running at http://{HOST}:{PORT}  (close this program to exit)")
        uvicorn.run(app, host=HOST, port=PORT, log_level="warning")


if __name__ == "__main__":
    main()
