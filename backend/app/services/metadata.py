"""元数据查询：yt-dlp -J --skip-download。纯逻辑模块。"""

import json
import subprocess
from shutil import which
import sys


def _cmd():
    exe = which("yt-dlp")
    return [exe] if exe else [sys.executable, "-m", "yt_dlp"]


def fetch_info(url: str, timeout: int = 60) -> dict:
    """返回精简的视频信息：标题、时长、上传者、格式列表、字幕数量等。"""
    try:
        proc = subprocess.run(_cmd() + ["-J", "--no-warnings", "--skip-download", url],
                              capture_output=True, text=True, timeout=timeout, errors="replace")
    except subprocess.TimeoutExpired:
        raise TimeoutError(f"查询超时（>{timeout}s）")
    if proc.returncode != 0:
        err = "\n".join(l for l in proc.stderr.splitlines() if l.startswith("ERROR"))[:500]
        raise RuntimeError(err or f"yt-dlp 退出码 {proc.returncode}")
    info = json.loads(proc.stdout)
    if "entries" in info:  # 播放列表
        entries = info["entries"][:50]
        return {
            "type": "playlist", "title": info.get("title", ""),
            "count": info.get("playlist_count", len(entries)),
            "entries": [{"title": e.get("title"), "id": e.get("id"), "duration": e.get("duration"),
                         "url": e.get("webpage_url")} for e in entries if e],
        }
    formats = [{
        "format_id": f.get("format_id"), "ext": f.get("ext"),
        "resolution": f.get("resolution") or "",
        "fps": f.get("fps"), "vcodec": f.get("vcodec", ""),
        "acodec": f.get("acodec", ""), "filesize": f.get("filesize") or f.get("filesize_approx"),
        "note": f.get("format_note", ""),
    } for f in (info.get("formats") or []) if f.get("format_id")]
    return {
        "type": "video", "title": info.get("title", ""),
        "duration": info.get("duration"), "uploader": info.get("uploader", ""),
        "webpage_url": info.get("webpage_url", url),
        "thumbnail": info.get("thumbnail"), "formats": formats,
    }
