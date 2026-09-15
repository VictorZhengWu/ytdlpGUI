"""下载历史记录：持久化 JSON，供 /api/history 查询与清空。纯逻辑模块。

设计约束：历史写失败绝不能影响下载任务本身——record()/clear() 全部
try/except 静默降级（仅打 stderr 日志）。
"""

import json
import sys
import threading
import time
from pathlib import Path

_lock = threading.Lock()
MAX_ENTRIES = 5000


def _history_path() -> Path:
    """history_path 语义为「目录」：为空用默认；指向目录时拼 history.json；
    指向文件（历史遗留配置）则按文件用。任何异常回退默认路径。"""
    from .store import get_config, DATA_DIR
    default = DATA_DIR / "history.json"
    try:
        p = Path(get_config().get("history_path") or "")
        if not str(p) or str(p) == ".":
            return default
        if p.is_dir():
            return p / "history.json"
        return p
    except Exception:
        return default


def _load(path: Path) -> list:
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError, ValueError):
        return []


def _save(path: Path, entries: list):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(entries[-MAX_ENTRIES:], f, ensure_ascii=False, indent=1)


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
            p = _history_path()
            entries = _load(p) + entries
            _save(p, entries)
    except Exception as e:  # 历史失败不影响下载
        print(f"[history] record failed: {e!r}", file=sys.stderr)


def list_entries(limit: int = 300) -> list:
    try:
        with _lock:
            entries = _load(_history_path())
        return list(reversed(entries))[:limit]
    except Exception as e:
        print(f"[history] list failed: {e!r}", file=sys.stderr)
        return []


def clear():
    try:
        with _lock:
            _save(_history_path(), [])
    except Exception as e:
        print(f"[history] clear failed: {e!r}", file=sys.stderr)
