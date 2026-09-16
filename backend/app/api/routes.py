"""HTTP 路由层：薄封装，只做参数提取与调用 services。"""

import asyncio
import json
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel

from ..services import ffmpeg as ffsvc, history, imageproxy, metadata, options as optsvc, runtime, store, update as updsvc
from ..services.downloader import DownloadManager

router = APIRouter(prefix="/api")

_manager: DownloadManager | None = None


def get_manager() -> DownloadManager:
    global _manager
    if _manager is None:
        cfg = store.get_config()
        out = cfg["download_dir"]
        # 相对路径基于项目根目录解析（routes.py 位于 <root>/backend/app/api/）
        out = out if Path(out).is_absolute() else str((Path(__file__).resolve().parents[3] / out))
        _manager = DownloadManager(out_dir=out)
    return _manager


def rebuild_manager():
    global _manager
    _manager = None


# ---- 选项注册表 ----

@router.get("/options")
def get_options():
    return optsvc.load_registry()


# ---- 配置 ----

@router.get("/config")
def get_cfg():
    return dict(store.get_config(), ffmpeg=ffsvc.detect(),
                js_runtime=runtime.js_runtime(), browsers=runtime.browsers())


class ConfigIn(BaseModel):
    download_dir: str | None = None
    language: str | None = None
    filename_template: str | None = None


@router.put("/config")
def put_cfg(body: ConfigIn):
    before = store.get_config()
    try:
        cfg = store.save_config(body.model_dump(exclude_none=True))
    except ValueError as e:  # 路径类字段非法（相对路径/含 ..）
        raise HTTPException(400, str(e))
    # 仅下载目录变化才重建管理器（切换语言等不得清空内存中的任务列表）
    if body.download_dir is not None and body.download_dir != before.get("download_dir"):
        rebuild_manager()
    return cfg


# ---- ffmpeg 探测与自动安装 ----

@router.get("/ffmpeg/status")
def ffmpeg_status():
    return ffsvc.status()


@router.post("/ffmpeg/install")
def ffmpeg_install():
    return ffsvc.start_install()


# ---- 元数据查询 ----

@router.get("/formats")
def get_formats(url: str):
    try:
        return metadata.fetch_info(url.strip())
    except RuntimeError as e:
        raise HTTPException(400, str(e))
    except TimeoutError:
        raise HTTPException(504, "查询超时")
    except json.JSONDecodeError:
        raise HTTPException(502, "yt-dlp 返回了无法解析的数据")


# ---- 目录浏览（供下载路径选择对话框，支持局域网共享挂载点/网盘） ----

def _fs_roots() -> list:
    """结构化快捷位置：kind=home/root/drive/net，展示文本由前端按语言本地化。"""
    roots = [{"kind": "home", "name": "", "path": os.path.expanduser("~")},
             {"kind": "root", "name": "/", "path": "/"}]
    if os.name == "nt":
        import string
        for letter in string.ascii_uppercase:
            drive = f"{letter}:\\"
            if os.path.isdir(drive):
                roots.append({"kind": "drive", "name": drive, "path": drive})
        return roots
    net_fs = {"cifs", "smbfs", "nfs", "nfs4", "sshfs", "fuse.sshfs"}
    try:
        with open("/proc/mounts") as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 3 and (parts[2] in net_fs or "gvfs" in parts[2]):
                    mnt = parts[1].replace("\\040", " ")
                    roots.append({"kind": "net", "name": mnt, "path": mnt})
    except OSError:
        pass
    import glob
    for gvfs in glob.glob("/run/user/*/gvfs"):
        for entry in os.scandir(gvfs):
            if entry.is_dir():
                roots.append({"kind": "net", "name": entry.name, "path": entry.path})
    return roots


@router.get("/fs/list")
def fs_list(path: str = ""):
    p = os.path.abspath(os.path.expanduser(path or "~"))
    if not os.path.isdir(p):
        raise HTTPException(400, f"不是有效目录: {p}")
    try:
        dirs = sorted((e.name for e in os.scandir(p) if e.is_dir() and not e.name.startswith(".")))
    except OSError as e:
        raise HTTPException(400, str(e))
    parent = os.path.dirname(p.rstrip(os.sep)) or None
    # 子目录完整路径由后端用 os.path.join 拼接（Windows 反斜杠/Unix 正斜杠自动正确）
    entries = [{"name": n, "path": os.path.join(p, n)} for n in dirs[:500]]
    return {"path": p, "parent": parent if parent != p else None, "dirs": entries, "roots": _fs_roots()}


# ---- 下载历史 ----

@router.get("/history")
def get_history():
    return history.list_entries()


@router.delete("/history")
def clear_history():
    history.clear()
    return {"ok": True}


@router.delete("/history/{entry_id}")
def delete_history_entry(entry_id: str):
    if not history.delete_entry(entry_id):
        raise HTTPException(500, "删除失败")
    return {"ok": True}


class HistoryOpenIn(BaseModel):
    filepath: str
    reveal: bool = False


@router.post("/history/open")
def open_history_file(body: HistoryOpenIn):
    try:
        history.open_path(body.filepath, body.reveal)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True}


# ---- 缩略图代理（防盗链 + SSRF 约束见 services/imageproxy.py） ----

@router.get("/proxy/image")
def proxy_image(url: str):
    try:
        data, ctype = imageproxy.fetch_image(url)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except OSError:
        raise HTTPException(502, "图片获取失败")
    return Response(content=data, media_type=ctype,
                    headers={"Cache-Control": "private, max-age=86400"})


# ---- 更新检查（SSRF 约束见 services/update.py） ----

@router.get("/update")
def check_update():
    return updsvc.check()


# ---- 下载任务 ----

class JobIn(BaseModel):
    urls: list[str]
    options: dict = {}
    meta: dict = {}  # 前端查询信息缓存 {url: {title, thumbnail}}，供历史卡片（后端不发起网络请求）


@router.post("/jobs")
def create_job(body: JobIn):
    try:
        urls = optsvc.validate_urls(body.urls)
        argv = optsvc.build_args(body.options)
    except optsvc.OptionsError as e:
        raise HTTPException(400, str(e))
    job = get_manager().submit(urls, argv, meta=body.meta)
    return job.to_dict()


@router.get("/jobs")
def list_jobs():
    return [j.to_dict() for j in sorted(get_manager().jobs.values(), key=lambda j: -j.created_at)]


@router.post("/jobs/{job_id}/cancel")
def cancel_job(job_id: str):
    if not get_manager().cancel(job_id):
        raise HTTPException(404, "任务不存在")
    return {"ok": True}


@router.post("/jobs/{job_id}/pause")
def pause_job(job_id: str):
    if not get_manager().pause(job_id):
        raise HTTPException(409, "任务当前状态不可暂停")
    return {"ok": True}


@router.post("/jobs/{job_id}/resume")
def resume_job(job_id: str):
    """继续（paused）或重试（error/canceled）：同 argv 重新入队，断点续传。"""
    mgr = get_manager()
    if not (mgr.resume(job_id) or mgr.retry(job_id)):
        raise HTTPException(409, "任务当前状态不可继续")
    return {"ok": True}


@router.get("/jobs/{job_id}/events")
async def job_events(job_id: str):
    mgr = get_manager()
    job = mgr.jobs.get(job_id)
    if not job:
        raise HTTPException(404, "任务不存在")
    # 重放历史日志，再跟随实时事件
    replay = [("log", l) for l in job.lines]

    async def gen():
        for ev in replay:
            yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps(('progress', {'progress': job.progress, 'speed': job.speed, 'eta': job.eta}), ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps(('status', job.status), ensure_ascii=False)}\n\n"
        while True:
            try:
                kind, payload = await asyncio.to_thread(job.events.get, timeout=30)
            except TimeoutError:
                yield ": keepalive\n\n"
                continue
            yield f"data: {json.dumps((kind, payload), ensure_ascii=False)}\n\n"
            if kind == "status" and payload in ("done", "error", "canceled", "paused"):
                break

    return StreamingResponse(gen(), media_type="text/event-stream")


# ---- 预设 ----

@router.get("/presets")
def list_presets():
    return store.get_presets()


class PresetIn(BaseModel):
    name: str
    options: dict


@router.post("/presets")
def create_preset(body: PresetIn):
    try:
        optsvc.build_args(body.options)  # 保存即校验：非法选项/取值不允许入库
    except optsvc.OptionsError as e:
        raise HTTPException(400, str(e))
    try:
        return store.save_preset(body.name, body.options)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.delete("/presets/{name}")
def remove_preset(name: str):
    return store.delete_preset(name)
