"""ffmpeg 探测与（Windows）自动安装。纯逻辑模块：不依赖 Web 框架。

为什么不能只靠 shutil.which：PATH 环境变量在进程启动时固化，用户中途用
winget/choco 安装的 ffmpeg 写入的是注册表 PATH，运行中的服务进程看不到——
所以探测必须实时读注册表与常见安装位置（T66）。安装则是下载静态构建解压到
应用 data/bin，不改系统环境、无需管理员权限（T67）。
"""

import os
import shutil
import sys
import threading
import urllib.request
import zipfile
from pathlib import Path

from .store import DATA_DIR

# 静态构建固定发布地址（含 ffmpeg.exe + ffprobe.exe，免安装）
DOWNLOAD_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
BIN_DIR = DATA_DIR / "bin"

_state_lock = threading.Lock()
_state = {"installing": False, "phase": "", "progress": 0.0, "error": ""}


# ---- 探测 ----

def _candidate_dirs() -> list:
    """PATH 之外的候选目录：应用自带、winget/choco/scoop 链接位、注册表 PATH。"""
    dirs = [BIN_DIR]
    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA", "")
        if local:
            dirs.append(Path(local) / "Microsoft" / "WinGet" / "Links")
        dirs += [Path("C:/ProgramData/chocolatey/bin"),
                 Path(os.path.expanduser("~")) / "scoop" / "shims"]
        dirs += _registry_path_dirs()
    else:
        dirs += [Path("/usr/local/bin"), Path("/usr/bin"), Path("/opt/homebrew/bin")]
    return [d for d in dirs if d.is_dir()]


def _registry_path_dirs() -> list:
    """实时读注册表里的用户/系统 PATH（winget 等安装器写这里，运行中进程不感知）。"""
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


def detect() -> dict:
    """返回 {available, path, dir, source, os}。每次调用实时探测（供 /api/config）。"""
    exe = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"

    bundled = BIN_DIR / exe
    if bundled.is_file():
        return {"available": True, "path": str(bundled), "dir": str(BIN_DIR),
                "source": "bundled", "os": sys.platform}

    hit = shutil.which("ffmpeg")
    if hit:
        return {"available": True, "path": hit, "dir": os.path.dirname(hit),
                "source": "path", "os": sys.platform}

    reg_dirs = set(_registry_path_dirs())
    for d in _candidate_dirs():
        p = d / exe
        if p.is_file():
            return {"available": True, "path": str(p), "dir": str(d),
                    "source": "registry" if d in reg_dirs else "wellknown",
                    "os": sys.platform}

    return {"available": False, "path": "", "dir": "", "source": "none", "os": sys.platform}


def env_with_ffmpeg(env: dict | None = None) -> dict:
    """给 yt-dlp 子进程的环境变量：把检测到的 ffmpeg 目录前置到 PATH。
    检测目录不在进程 PATH（注册表/自带）时子进程才能看到 ffmpeg/ffprobe。"""
    e = dict(env or os.environ)
    info = detect()
    if info["available"] and info["dir"] and info["dir"] not in e.get("PATH", "").split(os.pathsep):
        e["PATH"] = info["dir"] + os.pathsep + e.get("PATH", "")
    return e


# ---- 自动安装（Windows） ----

def status() -> dict:
    with _state_lock:
        s = dict(_state)
    s["available"] = detect()["available"]
    return s


def start_install() -> dict:
    """启动后台安装线程。已在装/已装好时直接返回状态，不重复下载。"""
    with _state_lock:
        if _state["installing"]:
            return {"started": False, **_state}
        _state.update(installing=True, progress=0.0, error="")
    if sys.platform != "win32":
        with _state_lock:
            _state.update(installing=False, error="auto-install is Windows-only")
        return {"started": False, **_state}
    if detect()["available"]:
        with _state_lock:
            _state["installing"] = False
        return {"started": False, "already": True, **_state}
    threading.Thread(target=_install_worker, daemon=True).start()
    return {"started": True}


def _install_worker():
    try:
        _download_and_extract()
    except Exception as e:  # 安装失败不得影响服务
        with _state_lock:
            _state.update(installing=False, error=repr(e))
    else:
        with _state_lock:
            _state.update(installing=False, progress=1.0)


def _assert_safe_download_url(url: str):
    """下载源安全约束（SSRF 防护）：仅 https、host 固定白名单、DNS 解析结果
    必须为公网地址（拒绝环回/私有/链路本地/保留，防 rebinding）。"""
    import ipaddress
    import socket
    from urllib.parse import urlparse
    u = urlparse(url)
    if u.scheme != "https" or u.hostname not in ("www.gyan.dev", "gyan.dev"):
        raise RuntimeError(f"blocked download source: {url!r}")
    ips = {ai[4][0] for ai in socket.getaddrinfo(u.hostname, 443, proto=socket.IPPROTO_TCP)}
    for ip in ips:
        if not ipaddress.ip_address(ip.split("%")[0]).is_global:
            raise RuntimeError(f"blocked non-public download host: {u.hostname} -> {ip}")


class _ValidatingRedirect(urllib.request.HTTPRedirectHandler):
    """重定向逐跳复验，防止白名单域 302 跳向内网/任意目标。"""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _assert_safe_download_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _safe_member(want: str, names: list) -> str:
    """在压缩包内定位目标文件，拒绝含路径穿越的成员名（防御恶意/损坏的包）。"""
    for n in names:
        norm = n.replace("\\", "/").lstrip("/")
        if ".." in norm.split("/"):
            continue
        if norm.endswith("/" + want):
            return n
    raise RuntimeError(f"{want} not found in archive")


def _download_and_extract():
    BIN_DIR.mkdir(parents=True, exist_ok=True)
    bin_root = BIN_DIR.resolve()
    tmp_zip = (BIN_DIR / "ffmpeg_dl.zip").resolve()
    if not tmp_zip.is_relative_to(bin_root):  # 禁 ../ 穿越
        raise RuntimeError(f"unsafe temp path: {tmp_zip}")

    with _state_lock:
        _state["phase"] = "download"
    _assert_safe_download_url(DOWNLOAD_URL)
    req = urllib.request.Request(DOWNLOAD_URL, headers={"User-Agent": "ytdlpGUI"})
    buf = bytearray()
    with urllib.request.build_opener(_ValidatingRedirect).open(req, timeout=60) as resp:
        total = int(resp.headers.get("Content-Length") or 0)
        while True:
            chunk = resp.read(64 * 1024)
            if not chunk:
                break
            buf += chunk
            with _state_lock:
                _state["progress"] = round(len(buf) / total, 3) if total else 0.0
    tmp_zip.write_bytes(buf)  # 目标已 resolve+目录包含校验（见上），禁 ../ 穿越

    try:
        # 静态包根目录形如 ffmpeg-x.y-essentials_build/bin/*.exe；按文件名定位
        with _state_lock:
            _state["phase"] = "extract"
        with zipfile.ZipFile(tmp_zip) as z:
            names = z.namelist()
            for want in ("ffmpeg.exe", "ffprobe.exe"):
                hit = _safe_member(want, names)  # 拒绝含 .. 的成员名
                dst_path = (BIN_DIR / want).resolve()
                if not dst_path.is_relative_to(bin_root):  # 禁 ../ 穿越
                    raise RuntimeError(f"unsafe extract target: {dst_path}")
                dst_path.write_bytes(z.read(hit))
    finally:
        tmp_zip.unlink(missing_ok=True)
