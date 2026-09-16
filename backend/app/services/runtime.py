"""运行环境探测：JS 运行时（YouTube 解析依赖）与已装浏览器（Cookie 来源）。

纯逻辑模块。与 ffmpeg.py 同模式：which → 注册表 PATH → 常见安装位，
每次调用实时探测——进程 PATH 固化后用户新装的运行时/浏览器也能被发现。
"""

import os
import shutil
import sys
from pathlib import Path


def _exe_dirs_from_registry() -> list:
    """实时读注册表 PATH（HKCU/HKLM），返回目录列表（仅 Windows）。"""
    if sys.platform != "win32":
        return []
    import winreg
    out = []
    for root, sub in [(winreg.HKEY_CURRENT_USER, "Environment"),
                      (winreg.HKEY_LOCAL_MACHINE,
                       r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment")]:
        try:
            with winreg.OpenKey(root, sub) as k:
                raw, _ = winreg.QueryValueEx(k, "Path")
        except OSError:
            continue
        for part in raw.split(";"):
            part = os.path.expandvars(part.strip())
            if part:
                out.append(Path(part))
    return out


def _find_exe(name: str, extra_dirs: list) -> str:
    """按 which → 注册表 PATH → 常见目录 查找可执行文件，返回路径或空串。"""
    hit = shutil.which(name)
    if hit:
        return hit
    exe = name + (".exe" if sys.platform == "win32" else "")
    for d in list(extra_dirs) + _exe_dirs_from_registry():
        p = Path(d) / exe
        if p.is_file():
            return str(p)
    return ""


def js_runtime() -> dict:
    """探测 JS 运行时（yt-dlp 优先级 deno > node；两者缺一时 YouTube 部分格式不可用）。
    返回 {available, name, path}。"""
    local = os.environ.get("LOCALAPPDATA", "")
    candidates = {
        "deno": [Path.home() / ".deno" / "bin"],
        "node": [Path("C:/Program Files/nodejs"), Path("C:/Program Files (x86)/nodejs"),
                 Path.home() / ".volta" / "bin", Path.home() / "scoop" / "shims"]
                + ([Path(local) / "Programs" / "nodejs",
                    Path(local) / "pnpm"] if local else []),
    }
    for name, dirs in candidates.items():
        hit = _find_exe(name, dirs)
        if hit:
            return {"available": True, "name": name, "path": hit}
    return {"available": False, "name": "", "path": ""}


_BROWSER_NAMES = {
    "chrome": ["chrome", "google-chrome", "google-chrome-stable"],
    "edge": ["msedge", "microsoft-edge"],
    "firefox": ["firefox"],
}
_BROWSER_DIRS = {  # Windows 固定安装位（PATH 外兜底）
    "chrome": ["C:/Program Files/Google/Chrome/Application",
               "C:/Program Files (x86)/Google/Chrome/Application"],
    "edge": ["C:/Program Files (x86)/Microsoft/Edge/Application",
             "C:/Program Files/Microsoft/Edge/Application"],
    "firefox": ["C:/Program Files/Mozilla Firefox"],
}


def browsers() -> list:
    """探测可用作 --cookies-from-browser 来源的浏览器（chrome > edge > firefox），
    返回浏览器键名列表，供前端组装 Cookie 选项。"""
    out = []
    for key in ("chrome", "edge", "firefox"):
        names = _BROWSER_NAMES[key]
        found = any(shutil.which(n) for n in names)
        if not found:
            for d in _BROWSER_DIRS.get(key, []):
                if any((Path(d) / (n + ".exe")).is_file() for n in names):
                    found = True
                    break
        if found:
            out.append(key)
    return out
