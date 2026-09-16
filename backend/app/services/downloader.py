"""下载任务管理器：队列、子进程、进度解析、取消。

纯逻辑模块：不依赖 FastAPI，可独立 import 使用（与旧版 downloader.py
的独立性原则一致）。事件通过回调推送，由上层（HTTP/SSE）决定如何转发。
"""

import os
import queue
import re
import subprocess
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_OUTPUT_TEMPLATE = "%(title)s [%(id)s].%(ext)s"
STREAM_FILE_RE = re.compile(r"\.f\d+(\.[A-Za-z0-9]+)$")  # 合并前中间流（.f137.mp4 等）

PROGRESS_RE = re.compile(
    r"\[download\]\s+([\d.]+)%\s+of\s+(?:~?\S+).*?"
    r"(?:at\s+([\d.]+[KMG]?i?B/s))?\s*(?:ETA\s+([\d:]+))?"
)
DESTINATION_RE = re.compile(r"(?:Destination|Renaming|Already downloaded|Merging formats in)\s*:\s*(.+)")
MERGE_RE = re.compile(r'Merging formats into\s+"([^"]+)"')  # 现版 yt-dlp：[Merger] Merging formats into "路径"
ALREADY_RE = re.compile(r"\[download\]\s+(.+?)\s+has already been downloaded")
FINISH_RE = re.compile(r"(has already been downloaded|Merging formats|Deleting original|Estimated download size)")
EXTRACT_URL_RE = re.compile(r"Extracting URL:\s*(\S+)")


@dataclass
class Job:
    id: str
    urls: list
    argv: list                       # 不含 yt-dlp 可执行名、不含 URL
    status: str = "queued"           # queued|running|paused|done|error|canceled
    meta: dict = field(default_factory=dict)  # 前端查询信息缓存 {url: {title, thumbnail}}，供历史记录用
    command_str: str = ""            # 真实执行的完整命令展示（含 -o 与 URL）
    progress: float = 0.0
    speed: str = ""
    eta: str = ""
    filepath: str = ""
    files: list = field(default_factory=list)   # 全部产物文件（多视频/合并前后的各路径）
    file_urls: list = field(default_factory=list)  # 与 files 平行：每个产物归属的 URL（按 Extracting URL 行跟踪）
    current_url: str = ""                        # 当前正在处理的 URL（解析行时维护，不序列化）
    error: str = ""
    ended_at: float = 0.0
    lines: deque = field(default_factory=lambda: deque(maxlen=500))
    created_at: float = field(default_factory=time.time)
    process: subprocess.Popen | None = field(default=None, repr=False)
    events: "queue.Queue[tuple]" = field(default_factory=queue.Queue, repr=False)

    def push(self, kind: str, payload):
        self.events.put((kind, payload))

    def to_dict(self):
        return {k: v for k, v in {
            "id": self.id, "urls": self.urls, "argv": self.argv,
            "status": self.status, "progress": self.progress,
            "speed": self.speed, "eta": self.eta, "filepath": self.filepath,
            "files": list(self.files), "file_urls": list(self.file_urls), "meta": self.meta,
            "error": self.error, "created_at": self.created_at,
            "command": self.command_str or ("yt-dlp " + " ".join(self.argv + self.urls)),
        }.items()}


class DownloadManager:
    """单工作线程顺序执行队列中的任务。"""

    def __init__(self, yt_dlp_cmd=None, out_dir=None):
        self.yt_dlp_cmd = yt_dlp_cmd or self._detect_cmd()
        self.out_dir = out_dir or os.path.join(os.getcwd(), "downloads")
        self.jobs: dict[str, Job] = {}
        self._order: deque[str] = deque()
        self._lock = threading.Lock()
        self._wakeup = threading.Event()
        threading.Thread(target=self._worker, daemon=True).start()

    @staticmethod
    def _detect_cmd():
        # venv / PATH 中有可执行 yt-dlp 则用之，否则回退 python -m yt_dlp
        from shutil import which
        exe = which("yt-dlp")
        if exe:
            return [exe]
        import sys
        return [sys.executable, "-m", "yt_dlp"]

    # ---- 对外接口 ----

    def submit(self, urls: list, argv: list, meta: dict | None = None) -> Job:
        job = Job(id=uuid.uuid4().hex[:12], urls=urls, argv=argv, meta=meta or {})
        with self._lock:
            self.jobs[job.id] = job
            self._order.append(job.id)
        self._wakeup.set()
        return job

    def pause(self, job_id: str) -> bool:
        """暂停：终止子进程但保留 .part 断点，任务可 resume 续传。"""
        job = self.jobs.get(job_id)
        if not job:
            return False
        if job.status == "running" and job.process:
            job.status = "paused"  # 先置状态：_run 退出分支据此跳过 error/历史记录
            try:
                job.process.terminate()
            except OSError:
                pass
            return True
        if job.status == "queued":
            job.status = "paused"
            job.push("status", job.status)
            return True
        return False

    def _requeue(self, job: Job) -> None:
        job.status, job.error = "queued", ""
        with self._lock:
            self._order.append(job.id)
        self._wakeup.set()
        job.push("status", job.status)

    def resume(self, job_id: str) -> bool:
        """继续已暂停任务：同 argv 重新入队，yt-dlp 默认续传 .part。"""
        job = self.jobs.get(job_id)
        if not job or job.status != "paused":
            return False
        self._requeue(job)
        return True

    def retry(self, job_id: str) -> bool:
        """重试失败/已取消任务：同 argv 重新入队。"""
        job = self.jobs.get(job_id)
        if not job or job.status not in ("error", "canceled"):
            return False
        job.progress = 0.0
        self._requeue(job)
        return True

    def cancel(self, job_id: str) -> bool:
        job = self.jobs.get(job_id)
        if not job:
            return False
        if job.process and job.status == "running":
            job.status = "canceled"
            try:
                job.process.terminate()
            except OSError:
                pass
        elif job.status in ("queued", "paused"):
            job.status = "canceled"
            job.push("status", job.status)
        return True

    def prune(self, max_age: float = 3600 * 24):
        cutoff = time.time() - max_age
        with self._lock:
            for jid in [j for j, job in self.jobs.items()
                        if job.status in ("done", "error", "canceled") and job.created_at < cutoff]:
                del self.jobs[jid]
                try:
                    self._order.remove(jid)
                except ValueError:
                    pass

    # ---- 内部实现 ----

    def _worker(self):
        while True:
            self._wakeup.wait()
            self._wakeup.clear()
            while True:
                with self._lock:
                    if not self._order:
                        break
                    job_id = self._order.popleft()
                job = self.jobs.get(job_id)
                if not job or job.status in ("canceled", "paused"):
                    continue
                try:
                    self._run(job)
                except Exception as e:  # 单任务异常不得杀死队列工作线程
                    import sys
                    job.status, job.error, job.ended_at = "error", f"internal error: {e!r}", time.time()
                    job.push("status", job.status)
                    print(f"[downloader] job {job_id} crashed: {e!r}", file=sys.stderr)

    def _run(self, job: Job):
        from . import history  # 延迟导入避免环
        from .ffmpeg import env_with_ffmpeg
        from .store import get_config
        tpl = get_config().get("filename_template") or DEFAULT_OUTPUT_TEMPLATE
        cmd = self.yt_dlp_cmd + ["-o", os.path.join(self.out_dir, tpl)] + job.argv + job.urls
        job.command_str = "yt-dlp " + " ".join(cmd[len(self.yt_dlp_cmd):])
        job.status = "running"
        job.push("status", job.status)
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    text=True, bufsize=1, errors="replace",
                                    env=env_with_ffmpeg())
        except OSError as e:
            job.status, job.error, job.ended_at = "error", str(e), time.time()
            job.push("status", job.status)
            history.record(job.to_dict())
            return
        job.process = proc
        for line in proc.stdout:
            line = line.rstrip()
            if not line:
                continue
            job.lines.append(line)
            job.push("log", line)
            self._parse_line(job, line)
        code = proc.wait()
        job.process = None
        job.ended_at = time.time()
        if job.status in ("canceled", "paused"):
            job.push("status", job.status)
        elif code == 0:
            job.status, job.progress = "done", 100.0
            self._cleanup_stream_leftovers(job)
            job.push("status", job.status)
        else:
            job.status = "error"
            job.error = next((l for l in reversed(job.lines) if l.lower().startswith("error") or "ERROR:" in l), f"exit code {code}")
            job.push("status", job.status)
        if job.status in ("done", "error", "canceled"):
            history.record(job.to_dict())

    def _cleanup_stream_leftovers(self, job: Job):
        """合并成功后的兜底清理：删除同词干的 .fNNN.* 中间流残留
        （yt-dlp 通常自删；未删尽时避免用户看到成对的无声/无画文件）。"""
        root = Path(self.out_dir).resolve()
        for f in list(job.files):
            m = STREAM_FILE_RE.search(f)
            if not m:
                continue
            final = f[:m.start()] + m.group(1)
            try:
                fp = Path(f)
                if fp.is_file() and Path(final).is_file():
                    rp = fp.resolve()
                    if rp.is_relative_to(root):  # 禁 ../ 穿越
                        rp.unlink()
                        job.files.remove(f)
            except OSError:
                pass

    @staticmethod
    def _parse_line(job: Job, line: str):
        m = PROGRESS_RE.search(line)
        if m:
            try:
                job.progress = float(m.group(1))
            except ValueError:
                pass
            job.speed = m.group(2) or job.speed
            job.eta = m.group(3) or job.eta
            job.push("progress", {"progress": job.progress, "speed": job.speed, "eta": job.eta})
        e = EXTRACT_URL_RE.search(line)  # yt-dlp 每处理一个 URL 前输出（分段归属依据）
        if e:
            job.current_url = e.group(1)
            return
        d = DESTINATION_RE.search(line) or MERGE_RE.search(line)
        if d:
            job.filepath = d.group(1).strip()
            job.files.append(job.filepath)
            job.file_urls.append(job.current_url)
            job.push("file", job.filepath)  # 产物路径实时下发（任务卡显示）
        else:
            a = ALREADY_RE.search(line)  # 已下载过：路径前置无冒号，单独匹配
            if a:
                job.filepath = a.group(1).strip()
                job.files.append(job.filepath)
                job.file_urls.append(job.current_url)
                job.push("file", job.filepath)
