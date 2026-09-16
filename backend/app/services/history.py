"""下载历史记录：持久化 JSON，供 /api/history 查询与清空。纯逻辑模块。

设计约束：
- 历史写失败绝不能影响下载任务本身——record()/clear() 全部 try/except 静默降级（仅打 stderr 日志）；
- 历史文件固定为数据目录下的 history.json（v3.5 安全加固：移除可配置 history_path，
  杜绝经配置注入的任意路径写入面，也彻底消除目录/文件语义歧义类缺陷——原 BUG-01 温床）。
"""

import json
import re
import sys
import threading
import time
import uuid
from pathlib import Path

from .store import DATA_DIR

_lock = threading.Lock()
MAX_ENTRIES = 5000
HISTORY_FILE = DATA_DIR / "history.json"
VIDEOID_SUFFIX_RE = re.compile(r"\s*\[[^\]]*\]$")  # 文件名词干里的 " [videoid]" 后缀


def _load() -> list:
    try:
        with open(HISTORY_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError, ValueError):
        return []


def _save(entries: list) -> None:
    """写入固定路径：数据目录/history.json。resolve 校验禁止 ../ 穿越。"""
    out = HISTORY_FILE.resolve()
    if not out.is_relative_to(DATA_DIR.resolve()):  # 禁 ../ 穿越
        raise ValueError(f"unsafe history path: {out}")
    out.write_text(json.dumps(entries[-MAX_ENTRIES:], ensure_ascii=False, indent=1),
                   encoding="utf-8")


def _meta_for(meta: dict, url: str) -> dict:
    """按 URL 取前端提交的查询缓存（容忍提取规范化后的形态差异）。"""
    if not meta:
        return {}
    hit = meta.get(url)
    if hit:
        return hit
    for k, v in meta.items():
        if k and (k in url or url in k):
            return v
    return {}


def _entry_title(meta: dict, url: str, files: list) -> str:
    m = _meta_for(meta, url)
    if m.get("title"):
        return m["title"]
    if files:
        stem = Path(files[-1]).stem
        return VIDEOID_SUFFIX_RE.sub("", stem) or stem
    return url


def _entries_for(job: dict) -> list:
    """把一个任务拆成历史条目：多 URL 任务按产物归属分段，每个 URL 一条；
    单 URL / 无法分段（file_urls 缺失或全空）时整任务一条。
    条目含 id/title/thumbnail（title 与缩略图来自前端查询缓存 meta）。"""
    files = job.get("files") or ([job["filepath"]] if job.get("filepath") else [])
    file_urls = (job.get("file_urls") or [])[:len(files)]
    urls = job.get("urls", [])
    meta = job.get("meta") or {}

    base = {
        "time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(job.get("ended_at") or time.time())),
        "id": uuid.uuid4().hex[:10],
        "status": job.get("status", ""),
        "error": (job.get("error") or "")[:300],
        "command": job.get("command", ""),
    }

    # 分段条件：多个输入 URL 且产物归属齐全（同一 URL 的连续产物并为一段）
    if len(urls) > 1 and file_urls and all(file_urls):
        segments: list = []
        for f, u in zip(files, file_urls):
            if segments and segments[-1][0] == u:
                segments[-1][1].append(f)
            else:
                segments.append([u, [f]])
        return [dict(base, urls=[u], titles=[Path(f).name for f in seg_files],
                     filepath=seg_files[-1] if seg_files else "",
                     title=_entry_title(meta, u, seg_files),
                     thumbnail=(_meta_for(meta, u) or {}).get("thumbnail", ""))
                for u, seg_files in segments]

    return [dict(base, urls=urls, titles=[Path(f).name for f in files],
                 filepath=files[-1] if files else "",
                 title=_entry_title(meta, urls[0] if urls else "", files),
                 thumbnail=(_meta_for(meta, urls[0] if urls else "") or {}).get("thumbnail", ""))]


def record(job: dict):
    """任务终态时调用：记录下载历史条目。失败只记日志，绝不抛出。"""
    try:
        entries = _entries_for(job)
        with _lock:
            _save(_load() + entries)
    except Exception as e:  # 历史失败不影响下载
        print(f"[history] record failed: {e!r}", file=sys.stderr)


def list_entries(limit: int = 300) -> list:
    try:
        with _lock:
            entries = _load()
        return list(reversed(entries))[:limit]
    except Exception as e:
        print(f"[history] list failed: {e!r}", file=sys.stderr)
        return []


def clear():
    try:
        with _lock:
            _save([])
    except Exception as e:
        print(f"[history] clear failed: {e!r}", file=sys.stderr)


def delete_entry(entry_id: str) -> bool:
    """单条删除。"""
    try:
        with _lock:
            entries = [e for e in _load() if e.get("id") != entry_id]
            _save(entries)
        return True
    except Exception as e:
        print(f"[history] delete failed: {e!r}", file=sys.stderr)
        return False


def open_path(filepath: str, reveal: bool = False) -> None:
    """打开历史产物文件（reveal=False）或在文件管理器中定位（reveal=True）。
    安全约束：filepath 必须是历史条目已登记且磁盘上存在的文件——防任意路径启动。"""
    import os
    import subprocess
    if not any(e.get("filepath") == filepath for e in _load()):
        raise ValueError("path not in history")
    p = Path(filepath)
    if not p.is_file():
        raise ValueError("file missing")
    if sys.platform == "win32":
        if reveal:
            subprocess.run(["explorer", "/select,", str(p)], check=False)
        else:
            os.startfile(str(p))  # Windows 专属 API
    else:
        subprocess.run(["xdg-open", str(p.parent if reveal else p)], check=False)

