#!/usr/bin/env python3
"""options_zh.json example 全量回归。

对注册表（含中文说明层合并后的 example）的每条非空示例：
  1. 经后端 build_args 构建参数 —— 与 GUI 提交完全同一条代码路径；
  2. 用本地 yt-dlp --simulate 实证：命令可被解析、取值不泄漏为位置参数（URL）。

用法: python3 scripts/regress_examples.py [-v]
退出码: 存在 FAIL 时为 1，否则为 0（可直接用于 CI / 修复后验证）。
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.services.options import OptionsError, build_args, load_registry  # noqa: E402

URL = "https://example.com/notexist"

# 环境依赖型失败：取决于本机文件/可选依赖是否存在，不算产品缺陷，标记 SKIP。
# 修复引入新 example 时若需新增豁免，请附原因。
KNOWN_ENV = {
    "--config-locations": "示例指向的文件在本机不存在（路径型示例）",
    "--load-info-json": "示例指向的 info.json 在本机不存在（路径型示例）",
    "--impersonate": "本机未安装 curl_cffi 客户端伪装依赖",
}

# 已知产品限制（经评审接受，非回归）：单选项示例在 yt-dlp 侧必然失败，
# 修复决策为「仅中文说明提示，不做硬校验」（原 BUG-20）。
KNOWN_LIMITATION = {
    "--max-sleep-interval": "yt-dlp 要求必须与 --sleep-interval 同时使用，单示例无法独立成功",
    "--username": "yt-dlp 缺少 --password 时进入交互式提示，无终端环境必然 EOF",
}


def yt_dlp_cmd() -> list:
    venv = ROOT / ".venv" / "bin" / "python"
    return [str(venv), "-m", "yt_dlp"] if venv.exists() else [sys.executable, "-m", "yt_dlp"]


def run_case(flag: str, example: str) -> tuple:
    """返回 (状态, 说明)。状态: OK | FAIL。"""
    try:
        argv = build_args({flag: example})
    except OptionsError as e:
        return "FAIL", f"后端拒绝: {e}"
    cmd = yt_dlp_cmd() + ["--ignore-config", "--simulate"] + argv + [URL]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        return "FAIL", "yt-dlp 执行超时"
    out = r.stdout + r.stderr
    low = out.lower()
    # optparse 参数级错误（usage/error:）——业务性错误以 "ERROR:" 开头，不算失败
    if ("usage" in low or re.search(r"error:", low)) and "ERROR:" not in out:
        return "FAIL", (out.strip().splitlines() or ["?"])[-1]
    # 多值泄漏检测：取值被 yt-dlp 当作 URL 提取
    for line in out.splitlines():
        if "Extracting URL:" in line:
            got = line.split("Extracting URL:", 1)[1].strip()
            if got != URL and URL not in got:
                return "FAIL", f"取值泄漏为位置参数: {line.strip()}"
    if r.returncode == 0 and not out.strip():
        return "FAIL", "yt-dlp 无输出（异常）"
    return "OK", ""


def main() -> None:
    ap = argparse.ArgumentParser(description="options_zh.json example 全量回归")
    ap.add_argument("-v", "--verbose", action="store_true", help="逐条打印 PASS")
    args = ap.parse_args()

    reg = load_registry()
    examples = [(o["flag"], o["example"])
                for s in reg["sections"] for o in s["options"] if o.get("example")]

    ok = skip = limit = fail = 0
    for flag, ex in examples:
        status, msg = run_case(flag, ex)
        if status == "FAIL" and flag in KNOWN_ENV:
            status, msg = "SKIP", KNOWN_ENV[flag]
        elif status == "FAIL" and flag in KNOWN_LIMITATION:
            status, msg = "LIMIT", KNOWN_LIMITATION[flag]
        if status == "OK":
            ok += 1
            if args.verbose:
                print(f"PASS  {flag:<30} {ex}")
        elif status == "SKIP":
            skip += 1
            print(f"SKIP  {flag:<30} {msg}")
        elif status == "LIMIT":
            limit += 1
            print(f"LIMIT {flag:<30} {msg}")
        else:
            fail += 1
            print(f"FAIL  {flag:<30} example={ex!r}\n        {msg}")

    total = ok + skip + limit + fail
    rate = (ok / (ok + fail) * 100) if (ok + fail) else 100.0
    print(f"\nexample 回归: 共 {total} 条 | 通过 {ok} | 跳过 {skip}（环境因素） | "
          f"已知限制 {limit} | 失败 {fail} | 通过率(剔跳过/限制) {rate:.1f}%")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
