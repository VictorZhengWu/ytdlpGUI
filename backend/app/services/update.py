"""应用内更新检查：查询 GitHub 最新 Release 与本地版本比对。

纯逻辑模块。安全约束（SSRF 防护）：仅 https、host 固定 api.github.com、
域名解析结果必须为公网地址——与 imageproxy 同一套硬约束。
"""

import ipaddress
import json
import socket
import urllib.request
from urllib.parse import urlparse

APP_VERSION = "3.7.0"
RELEASES_URL = "https://github.com/VictorZhengWu/ytdlpGUI/releases/latest"
_API = "https://api.github.com/repos/VictorZhengWu/ytdlpGUI/releases/latest"


def _assert_github(url: str) -> None:
    """仅放行 https + api.github.com（解析后必须公网）。"""
    u = urlparse(url)
    if u.scheme != "https" or u.hostname != "api.github.com":
        raise ValueError(f"blocked update source: {url!r}")
    ips = {ai[4][0] for ai in socket.getaddrinfo(u.hostname, 443, proto=socket.IPPROTO_TCP)}
    for ip in ips:
        if not ipaddress.ip_address(ip.split("%")[0]).is_global:
            raise ValueError(f"blocked non-public host: {u.hostname} -> {ip}")


def _ver_tuple(v: str) -> tuple:
    out = []
    for part in (v or "").lstrip("vV").split("."):
        num = ""
        for ch in part:
            if ch.isdigit():
                num += ch
            else:
                break
        out.append(int(num) if num else 0)
    return tuple(out[:3])


def check(timeout: float = 8) -> dict:
    """返回 {current, latest, has_update, url, error}。失败静默降级（不打扰启动）。"""
    result = {"current": APP_VERSION, "latest": "", "has_update": False,
              "url": RELEASES_URL, "error": ""}
    try:
        _assert_github(_API)
        req = urllib.request.Request(_API, headers={"User-Agent": f"ytdlpgui/{APP_VERSION}",
                                                    "Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        latest = (data.get("tag_name") or "").strip()
        if latest:
            result["latest"] = latest.lstrip("vV")
            result["has_update"] = _ver_tuple(latest) > _ver_tuple(APP_VERSION)
    except Exception as e:  # 更新检查失败不影响任何功能
        result["error"] = repr(e)[:120]
    return result
