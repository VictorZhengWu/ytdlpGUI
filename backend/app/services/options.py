"""选项校验、yt-dlp 命令行构建与互斥元数据计算。

注册表由 scripts/generate_registry.py 从 yt_dlp/options.py 内省生成，
multi/nargs/dest/action/hidden 均为数据驱动；本模块只保留三张小型语义表：
SURFACE_HIDDEN（要展示的隐藏选项）、POLARITY_FIX（dest 内极性特例）、
EXTRA_MIXED（无共享 dest 的语义冲突对）。

纯逻辑模块：不依赖 FastAPI / GUI，可独立 import 与单测。
"""

import json
import os
import re
from pathlib import Path

REGISTRY_PATH = Path(__file__).resolve().parent.parent / "data" / "options_registry.json"
# PyInstaller 打包模式：资源随 YTDLPGUI_ROOT 解包
if os.environ.get("YTDLPGUI_ROOT"):
    REGISTRY_PATH = Path(os.environ["YTDLPGUI_ROOT"]) / "backend/app/data/options_registry.json"

ZH_PATH = REGISTRY_PATH.parent / "options_zh.json"

# 隐藏但要展示的选项（yt-dlp SUPPRESS_HELP 但对 GUI 用户有用）
SURFACE_HIDDEN = {
    "--playlist-reverse", "--no-playlist-reverse",
    "--playlist-start", "--playlist-end",
    "--user-agent", "--referer",
    "--geo-bypass", "--no-geo-bypass",
}

# dest 内极性特例：action 推导不准的选项（const 为语义值/None）
POLARITY_FIX = {
    "--no-abort-on-error": "on",     # const='only_download'：继续下载，属"忽略错误"侧
    "--no-geo-bypass": "off",        # const='never'
    "--no-force-overwrites": "off",  # const=None
}

# 界面隐藏的 CLI 信息/查询/调试型选项（白名单仍受理，兼容旧预设；--simulate/--quiet 等
# 输出控制类保留展示）
UI_HIDE = {
    "-h", "--help", "--version", "-U", "--update", "--list-extractors",
    "--extractor-descriptions", "--list-thumbnails", "--list-subs", "--list-formats",
    "--dump-json", "--dump-single-json", "--print", "--print-to-file",
    "--dump-pages", "--write-pages", "--print-traffic", "--list-impersonate-targets",
    "--ap-list-mso", "--test", "--you-tube-print-sig-code", "--youtube-print-sig-code",
}

# 无共享 dest 的语义冲突对（设一端应清除另一端）
EXTRA_MIXED = [
    ("--no-sponsorblock", "--sponsorblock-mark"),
    ("--no-sponsorblock", "--sponsorblock-remove"),
]

# 同 dest 但成员是"二选一替代"而非开关（不构成三态组，仅互斥）
ALTERNATIVE_DESTS = {"source_address"}  # --force-ipv4 / --force-ipv6

# 多参数选项的拆分方式（nargs 本身来自注册表）
NARGS_SPLIT = {"--alias": "lsplit", "--print-to-file": "rsplit"}

VALUE_RE = re.compile(r"^[\w,.:%\-+/\\\[\](){}<>=?&;#@~*'\"\s!|^]*$")


class OptionsError(ValueError):
    pass


def _load_raw() -> dict:
    with open(REGISTRY_PATH, encoding="utf-8") as f:
        return json.load(f)


def _load_zh() -> dict:
    try:
        with open(ZH_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


_RAW = _load_raw()
_ZH = _load_zh()

# 白名单索引：全部选项（含隐藏，兼容任意历史预设）
FLAG_INDEX: dict[str, dict] = {}
for _opt in [o for s in _RAW["sections"] for o in s["options"]]:
    FLAG_INDEX[_opt["flag"]] = _opt
    if _opt["short"]:
        FLAG_INDEX[_opt["short"]] = _opt


def load_registry() -> dict:
    """界面用注册表：合并中文层，过滤隐藏项（SURFACE_HIDDEN 除外），附互斥元数据。"""
    sections = []
    for sec in _RAW["sections"]:
        opts = []
        for o in sec["options"]:
            if (o["hidden"] and o["flag"] not in SURFACE_HIDDEN) or o["flag"] in UI_HIDE:
                continue
            o = dict(o)
            extra = _ZH.get(o["flag"], {})
            o["zh"] = extra.get("zh", "")
            o["example"] = extra.get("example", "")
            if o.get("nargs") and o["nargs"] > 1:
                o["nargs"] = o["nargs"]
            opts.append(o)
        if opts:
            sections.append({"name": sec["name"], "options": opts})
    return {"source": _RAW["source"], "sections": sections, "conflicts": compute_conflicts()}


# ---------- 互斥元数据（数据驱动：按 dest 分组 + 三张小表） ----------

def compute_conflicts() -> dict:
    """返回 {groups: [{id,on,off}], mixed: [[a,b],...]}，前后端共享同一份（模块级缓存）。"""
    global _CONFLICTS
    if _CONFLICTS is not None:
        return _CONFLICTS
    by_dest: dict[str, list] = {}
    for o in FLAG_INDEX.values():
        if o["kind"] != "bool" or not o.get("dest") or o["dest"] == "_":
            continue
        by_dest.setdefault(o["dest"], []).append(o)

    def side(o) -> str:
        if o["flag"] in POLARITY_FIX:
            return POLARITY_FIX[o["flag"]]
        return "off" if o["action"] == "store_false" else "on"

    groups, mixed = [], []
    for dest, opts in by_dest.items():
        flags = sorted({o["flag"] for o in opts})
        if dest in ALTERNATIVE_DESTS:
            for i in range(len(flags)):
                for j in range(i + 1, len(flags)):
                    mixed.append([flags[i], flags[j]])
            continue
        if len(flags) < 2:
            continue
        on = [f for f in flags if side(FLAG_INDEX[f]) == "on"]
        off = [f for f in flags if side(FLAG_INDEX[f]) == "off"]
        if on and off:
            groups.append({"id": "g" + str(len(groups)), "on": on, "off": off})
        else:
            print(f"[conflicts] 警告: dest={dest} 组极性未定: {flags}", file=os.sys.stderr)

    # 值型与同 dest 布尔型互斥（--X 与 --no-X）
    for o in FLAG_INDEX.values():
        if o["kind"] != "value" or not o.get("dest"):
            continue
        for b in by_dest.get(o["dest"], []):
            pair = sorted([o["flag"], b["flag"]])
            if pair not in mixed:
                mixed.append(pair)
    for a, b in EXTRA_MIXED:
        pair = sorted([a, b])
        if pair not in mixed:
            mixed.append(pair)
    _CONFLICTS = {"groups": groups, "mixed": mixed}
    return _CONFLICTS


_CONFLICTS = None


def validate_conflicts(options: dict):
    """提交期冲突校验：三态组两侧同时置位 / 互斥对两端同时出现 → 报错。
    键先经 FLAG_INDEX 归一化为长名（-4 → --force-ipv4），防止短选项绕过。"""
    norm = {}
    for k, v in options.items():
        opt = FLAG_INDEX.get(k)
        if not opt:
            raise OptionsError(f"未知或不支持的选项: {k}")
        norm[opt["flag"]] = v
    conflicts = compute_conflicts()
    for g in conflicts["groups"]:
        ons = [f for f in g["on"] if norm.get(f) not in (None, False)]
        offs = [f for f in g["off"] if norm.get(f) not in (None, False)]
        if ons and offs:
            raise OptionsError(f"互斥选项同时启用: {', '.join(ons)} 与 {', '.join(offs)}")
    for a, b in conflicts["mixed"]:
        if norm.get(a) not in (None, False) and norm.get(b) not in (None, False):
            raise OptionsError(f"互斥选项同时启用: {a} 与 {b}")


# ---------- 命令构建 ----------

def sanitize_value(flag: str, value) -> list[str]:
    """把单个用户输入值规范化为该选项的命令行取值列表。"""
    if value is None or value is True:
        return []
    if value is False:
        raise OptionsError(f"{flag} 不接受布尔值")
    if isinstance(value, (int, float)):
        return [str(value)]
    if isinstance(value, str):
        values = [value] if not FLAG_INDEX[flag]["multi"] else [v for v in value.split(",")]
    elif isinstance(value, list):
        values = [str(v) for v in value]
    else:
        raise OptionsError(f"{flag} 取值类型不合法")
    for v in values:
        v = v.strip()
        if not v:
            continue
        if v.startswith("-") or "\x00" in v or not VALUE_RE.match(v):
            raise OptionsError(f"{flag} 取值不合法: {v!r}")
    return [v.strip() for v in values if v.strip()]


def build_args(options: dict) -> list[str]:
    """把 {flag: value} 字典构建为 yt-dlp 参数列表（白名单 + 冲突校验）。"""
    validate_conflicts(options)
    argv: list[str] = []
    for flag, value in options.items():
        if flag not in FLAG_INDEX:
            raise OptionsError(f"未知或不支持的选项: {flag}")
        opt = FLAG_INDEX[flag]
        if opt["kind"] == "bool":
            if value is False or value is None:
                continue
            if value is not True and value != "true":
                raise OptionsError(f"{flag} 是开关型选项，取值必须为布尔")
            argv.append(opt["flag"])
            continue
        values = sanitize_value(flag, value)
        if not values:
            raise OptionsError(f"{flag} 需要提供取值")
        nargs = opt.get("nargs") or 1
        if nargs > 1:
            if len(values) > 1:
                raise OptionsError(f"{opt['flag']} 需要 {nargs} 个以空格分隔的取值（合为一个输入）")
            text = values[0]
            mode = NARGS_SPLIT.get(opt["flag"], "split")
            tokens = text.rsplit(None, nargs - 1) if mode == "rsplit" else \
                text.split(None, nargs - 1) if mode == "lsplit" else text.split()
            tokens = [tk for tk in tokens if tk]
            if len(tokens) != nargs:
                raise OptionsError(f"{opt['flag']} 需要 {nargs} 个以空格分隔的取值，当前 {len(tokens)} 个")
            # 剥去外层引号（GUI 单输入框场景，用户按 shell 习惯加引号）
            tokens = [tk[1:-1] if len(tk) > 1 and tk[0] == tk[-1] and tk[0] in "\"'" else tk for tk in tokens]
            argv.append(opt["flag"])
            argv.extend(tokens)
        elif opt["multi"]:
            # append 型：重复拼装 --flag v1 --flag v2（不能连排，否则后续值会被当作 URL）
            for v in values:
                argv.extend([opt["flag"], v])
        else:
            if len(values) > 1:
                raise OptionsError(f"{opt['flag']} 不支持多个取值（收到 {len(values)} 个）")
            argv.extend([opt["flag"], values[0]])
    return argv


def validate_urls(urls: list) -> list[str]:
    result = []
    for u in urls:
        u = str(u).strip()
        if not u or u.startswith("-") or any(c.isspace() for c in u):
            raise OptionsError(f"URL 不合法: {u!r}")
        if "://" in u and not u.startswith(("http://", "https://")):
            raise OptionsError(f"URL 不合法: {u!r}")
        if ":" in u and "://" not in u and not u.startswith("ytsearch"):
            raise OptionsError(f"URL 不合法: {u!r}")
        result.append(u)
    if not result:
        raise OptionsError("至少提供一个 URL")
    return result
