#!/usr/bin/env python3
"""从 yt_dlp/options.py 内省生成选项注册表（取代解析 --help 文本的旧方案）。

元数据直接取自 optparse 定义：flag/短选项/metavar/nargs/action/callback/dest/const/
SUPPRESS_HELP，一次根治 metavar 判定、multi 标记、隐藏选项、互斥分组的来源问题。

用法:
    python scripts/generate_registry.py            # 生成到 backend/app/data/
    python scripts/generate_registry.py --check    # 漂移检测：与现有文件比对，不同则 exit 1
"""

import json
import sys
from pathlib import Path

import optparse

OUT = Path(__file__).resolve().parents[1] / "backend/app/data/options_registry.json"

# 逗号/列表语义的回调（单值内可逗号分隔，亦可重复 flag）
LIST_CALLBACKS = {"_list_from_options_callback", "_dict_from_options_callback", "_set_from_options_callback"}


def iter_options():
    from yt_dlp.options import create_parser
    parser = create_parser()
    for group in parser.option_groups:
        for o in group.option_list:
            if not o._long_opts:
                continue
            yield group.title or "Other", o
    for o in parser.option_list:  # 无分组的选项归入 General
        if o._long_opts:
            yield "General Options", o


def build_option(o):
    flag = o._long_opts[0]
    cb = getattr(o, "callback", None)
    cb_name = cb.__name__ if cb else None
    metavar = o.metavar
    action = o.action or "store"
    # 布尔型：无 metavar（不接收命令行取值）
    kind = "bool" if metavar is None else "value"
    help_text = o.help if isinstance(o.help, str) and o.help != optparse.SUPPRESS_HELP else ""
    return {
        "flag": flag,
        "short": o._short_opts[0] if o._short_opts else None,
        "metavar": metavar,
        "description": " ".join(help_text.split()),
        "kind": kind,
        "action": action,
        "callback": cb_name,
        "dest": o.dest,
        "nargs": o.nargs if isinstance(o.nargs, int) and o.nargs > 1 else None,
        "const": repr(o.const) if o.const is not None else None,
        # append 型或列表回调：可重复使用（GUI 逗号拆分 + 重复拼装）
        "multi": action == "append" or (cb_name in LIST_CALLBACKS),
        "hidden": o.help in (optparse.SUPPRESS_HELP, None) or not help_text,
    }


def build():
    sections = {}
    for title, o in iter_options():
        sections.setdefault(title, []).append(build_option(o))
    return {
        "source": "yt_dlp.options introspection",
        "sections": [{"name": k, "options": v} for k, v in sections.items()],
    }


def main():
    data = build()
    if "--check" in sys.argv:
        current = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
        if json.dumps(current, sort_keys=True) != json.dumps(data, sort_keys=True):
            print("注册表漂移：yt-dlp 选项与现有 registry 不一致，请重新生成", file=sys.stderr)
            return 1
        print("registry 无漂移")
        return 0
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    total = sum(len(s["options"]) for s in data["sections"])
    hidden = sum(1 for s in data["sections"] for o in s["options"] if o["hidden"])
    print(f"generated {len(data['sections'])} sections, {total} options ({hidden} hidden)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
