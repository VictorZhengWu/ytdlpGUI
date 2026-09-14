"""应用入口：装配路由与静态前端。
运行: uvicorn backend.app.main:app（源码） / ytdlpgui.exe（PyInstaller 打包）"""

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .api.routes import router

# 打包模式（YTDLPGUI_ROOT）下资源在 _MEIPASS 解包目录
_ROOT = Path(os.environ.get("YTDLPGUI_ROOT", Path(__file__).resolve().parents[2]))
FRONTEND_DIR = _ROOT / "frontend"

app = FastAPI(title="ytdlpGUI", version="2.1.0")
app.include_router(router)
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
