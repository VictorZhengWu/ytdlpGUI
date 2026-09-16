"""缩略图代理：以同源 Referer 取回视频缩略图，绕过 B 站等站点的防盗链。

纯逻辑模块。安全约束（SSRF 防护，全程强制）：
- 仅 http/https，禁带 userinfo、非标准端口；
- 域名解析结果必须全部为公网地址（拒绝环回/私有/链路本地/保留，防 rebinding）；
- 重定向逐跳复验；
- 响应 Content-Type 必须 image/*，大小上限 5MB。
"""

import ipaddress
import socket
import urllib.request
from urllib.parse import urlparse

MAX_BYTES = 5 * 1024 * 1024


def assert_public_http_url(url: str) -> None:
    """校验图片 URL：协议/host/端口/解析后 IP 边界。不合法抛 ValueError。"""
    u = urlparse(url)
    if u.scheme not in ("http", "https") or not u.hostname:
        raise ValueError("仅允许 http/https 图片地址")
    if u.username or u.password or u.port not in (None, 80, 443):
        raise ValueError("不允许的地址形式")
    port = 443 if u.scheme == "https" else 80
    ips = {ai[4][0] for ai in socket.getaddrinfo(u.hostname, port, proto=socket.IPPROTO_TCP)}
    for ip in ips:
        if not ipaddress.ip_address(ip.split("%")[0]).is_global:
            raise ValueError(f"非公网地址被拒绝: {u.hostname}")


class _ValidatingRedirect(urllib.request.HTTPRedirectHandler):
    """重定向逐跳复验，防止图片 URL 302 跳向内网/任意目标。"""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        assert_public_http_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_image(url: str, timeout: float = 10) -> tuple:
    """取回缩略图，返回 (bytes, content_type)。任何违规抛 ValueError。"""
    assert_public_http_url(url)
    u = urlparse(url)
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (ytdlpGUI thumbnail proxy)",
        "Referer": f"{u.scheme}://{u.netloc}/",  # 同源 Referer 过防盗链
    })
    with urllib.request.build_opener(_ValidatingRedirect).open(req, timeout=timeout) as resp:
        ctype = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        if not ctype.startswith("image/"):
            raise ValueError(f"非图片响应: {ctype or 'unknown'}")
        data = resp.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise ValueError("图片超过 5MB 上限")
        return data, ctype
