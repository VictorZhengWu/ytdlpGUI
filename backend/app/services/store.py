"""配置与预设持久化（JSON 文件）。纯逻辑模块。"""

import json
import os
import threading
from pathlib import Path

# 打包模式下数据写入 exe 旁的可写目录（YTDLPGUI_DATA_DIR）
if os.environ.get("YTDLPGUI_DATA_DIR"):
    DATA_DIR = Path(os.environ["YTDLPGUI_DATA_DIR"])
else:
    DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

_lock = threading.Lock()


def _read(path: Path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default()


# ---- 应用配置 ----

CONFIG_PATH = DATA_DIR / "config.json"
# history_path 已移除（v3.5 安全加固：历史固定写数据目录，见 services/history.py）
DEFAULT_CONFIG = {"download_dir": "downloads", "language": "en",
                  "filename_template": "%(title)s [%(id)s].%(ext)s"}

def get_config() -> dict:
    cfg = DEFAULT_CONFIG.copy()
    cfg.update(_read(CONFIG_PATH, dict))
    return cfg

def _user_path(v: str) -> str:
    """用户配置的 download_dir 必须为绝对路径且不含 ..
    ——该项会传导给 yt-dlp 作为输出目录，禁止相对/穿越路径。"""
    p = Path(v)
    if not p.is_absolute() or ".." in p.parts:
        raise ValueError(f"illegal path: {v!r}")
    return str(p)

def _filename_template(v: str) -> str:
    """输出文件名模板：只允许文件名成分（yt-dlp %(field)s 语法），
    禁分隔符/../盘符——防止模板把产物写到输出目录之外。
    空串视为恢复默认模板（清空输入框=重置，而非报错）。"""
    v = (v or "").strip()
    if not v:
        return DEFAULT_CONFIG["filename_template"]
    if "/" in v or "\\" in v or ".." in v or ":" in v:
        raise ValueError("illegal filename template")
    return v


def save_config(cfg: dict) -> dict:
    cur = get_config()
    incoming = {k: v for k, v in cfg.items() if k in DEFAULT_CONFIG}
    if incoming.get("download_dir"):
        incoming["download_dir"] = _user_path(incoming["download_dir"])
    if "filename_template" in incoming:
        incoming["filename_template"] = _filename_template(incoming["filename_template"])
    cur.update(incoming)
    cfg_path = CONFIG_PATH.resolve()
    if not cfg_path.is_relative_to(DATA_DIR.resolve()):  # 禁 ../ 穿越
        raise ValueError("config path escapes data dir")
    with _lock:
        cfg_path.write_text(json.dumps(cur, ensure_ascii=False, indent=2), encoding="utf-8")
    return cur


# ---- 选项预设 ----

PRESETS_PATH = DATA_DIR / "presets.json"

def get_presets() -> dict:
    return _read(PRESETS_PATH, dict)

def save_preset(name: str, options: dict) -> dict:
    name = name.strip()
    if not name or "/" in name or "\\" in name or ".." in name:
        raise ValueError("预设名称不合法")
    presets = get_presets()
    presets[name] = options
    presets_path = PRESETS_PATH.resolve()
    if not presets_path.is_relative_to(DATA_DIR.resolve()):  # 禁 ../ 穿越
        raise ValueError("presets path escapes data dir")
    with _lock:
        presets_path.write_text(json.dumps(presets, ensure_ascii=False, indent=2), encoding="utf-8")
    return presets

def delete_preset(name: str) -> dict:
    presets = get_presets()
    presets.pop(name, None)
    presets_path = PRESETS_PATH.resolve()
    if not presets_path.is_relative_to(DATA_DIR.resolve()):  # 禁 ../ 穿越
        raise ValueError("presets path escapes data dir")
    with _lock:
        presets_path.write_text(json.dumps(presets, ensure_ascii=False, indent=2), encoding="utf-8")
    return presets
