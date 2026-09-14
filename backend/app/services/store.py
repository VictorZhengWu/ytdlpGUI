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
DEFAULT_CONFIG = {"download_dir": "downloads", "language": "en", "history_path": ""}

def get_config() -> dict:
    cfg = DEFAULT_CONFIG.copy()
    cfg.update(_read(CONFIG_PATH, dict))
    return cfg

def save_config(cfg: dict) -> dict:
    cur = get_config()
    cur.update({k: v for k, v in cfg.items() if k in DEFAULT_CONFIG})
    with _lock, open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cur, f, ensure_ascii=False, indent=2)
    return cur


# ---- 选项预设 ----

PRESETS_PATH = DATA_DIR / "presets.json"

def get_presets() -> dict:
    return _read(PRESETS_PATH, dict)

def save_preset(name: str, options: dict) -> dict:
    name = name.strip()
    if not name or "/" in name:
        raise ValueError("预设名称不合法")
    presets = get_presets()
    presets[name] = options
    with _lock, open(PRESETS_PATH, "w", encoding="utf-8") as f:
        json.dump(presets, f, ensure_ascii=False, indent=2)
    return presets

def delete_preset(name: str) -> dict:
    presets = get_presets()
    presets.pop(name, None)
    with _lock, open(PRESETS_PATH, "w", encoding="utf-8") as f:
        json.dump(presets, f, ensure_ascii=False, indent=2)
    return presets
