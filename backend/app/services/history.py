"""下载历史记录：持久化 JSON，供 /api/history 查询与清空。纯逻辑模块。

设计约束：
- 历史写失败绝不能影响下载任务本身——record()/clear() 全部 try/except 静默降级（仅打 stderr 日志）；
- 历史文件固定为数据目录下的 history.json（v3.5 安全加固：移除可配置 history_path，
  杜绝经配置注入的任意路径写入面，也彻底消除目录/文件语义歧义类缺陷——原 BUG-01 温床）。
"""

import json
import sys
import threading
import time
from pathlib import Path

from .store import DATA_DIR

_lock = threading.Lock()
MAX_ENTRIES = 5000
HISTORY_FILE = DATA_DIR / "history.json"


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


def _entries_for(job: dict) -> list:
    """把一个任务拆成历史条目：多 URL 任务按产物归属分段，每个 URL 一条；
    单 URL / 无法分段（file_urls 缺失或全空）时整任务一条。"""
    files = job.get("files") or ([job["filepath"]] if job.get("filepath") else [])
    file_urls = (job.get("file_urls") or [])[:len(files)]
    urls = job.get("urls", [])

    base = {
        "time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(job.get("ended_at") or time.time())),
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
                     filepath=seg_files[-1] if seg_files else "")
                for u, seg_files in segments]

    return [dict(base, urls=urls, titles=[Path(f).name for f in files],
                 filepath=files[-1] if files else "")]


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
