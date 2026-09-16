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
        "note": f.get("format_note", ""), "language": f.get("language"),
    } for f in (info.get("formats") or []) if f.get("format_id")]
    return {
        "type": "video", "title": info.get("title", ""),
        "duration": info.get("duration"), "uploader": info.get("uploader", ""),
        "webpage_url": info.get("webpage_url", url),
        "thumbnail": info.get("thumbnail"), "formats": formats,
        "audio_tracks": _audio_tracks(formats),
        "subtitle_langs": _subtitle_langs(info),
    }


def _audio_tracks(formats: list) -> list:
    """多音轨语言（YouTube 多语配音等）：按 language 去重，每种语言取体积最大的纯音轨。
    返回 [{language, format_id}]；不足 2 种语言时返回空列表（界面不展示）。"""
    best: dict = {}
    for f in formats:
        lang = f.get("language")
        if not lang or not f.get("acodec") or f.get("vcodec") not in ("", None, "none"):
            continue  # 只看带语言标记的纯音轨
        size = f.get("filesize") or 0
        if lang not in best or size > best[lang]["size"]:
            best[lang] = {"language": lang, "format_id": f["format_id"], "size": size}
    tracks = [{"language": k, "format_id": v["format_id"]} for k, v in best.items()]
    return sorted(tracks, key=lambda t: t["language"]) if len(tracks) > 1 else []


_COMMON_LANGS = ("zh", "en", "ja", "ko", "yue", "es", "fr", "de", "pt", "ru",
                 "ar", "hi", "id", "th", "vi", "it")


def _lang_priority(lang: str) -> tuple:
    """常见语言排前（zh/en/ja/ko/yue…），其余按字母——避免自动字幕按字母序
    盲截断时把 aa/ab 之类冷门码留在列表而丢了用户要找的。"""
    for i, p in enumerate(_COMMON_LANGS):
        if lang == p or lang.startswith(p + "-") or lang.startswith(p + "_"):
            return (i, lang)
    return (len(_COMMON_LANGS), lang)


def _subtitle_langs(info: dict) -> list:
    """字幕语言：人工字幕在前，自动生成字幕（语音识别）以 auto: 前缀标记。"""
    manual = sorted((info.get("subtitles") or {}).keys())
    auto = sorted((info.get("automatic_captions") or {}).keys(),
                  key=lambda l: (_lang_priority(l),))
    out = list(manual)
    out += [f"auto:{l}" for l in auto if l not in manual][:20]  # 常见语言优先，截断
    return out[:40]
