#!/usr/bin/env bash
# ytdlpGUI 质量套件：改代码后 / 打包前运行，任一失败即退出非 0
#   1. 注册表漂移检测（yt-dlp 选项 vs 现有 registry）
#   2. 互斥元数据与命令构建结构断言
#   3. 92 条中文 example 全量回归（经 build_args + yt-dlp --simulate 实证）
set -e
cd "$(dirname "$0")/.."
PY=.venv/bin/python
[ -x "$PY" ] || PY=.venv/Scripts/python.exe
[ -x "$PY" ] || PY=python3

echo "=== 1/3 注册表漂移检测 ==="
"$PY" scripts/generate_registry.py --check
echo
echo "=== 2/3 互斥与命令构建断言 ==="
"$PY" scripts/test_conflicts.py
echo
echo "=== 3/3 example 全量回归 ==="
"$PY" scripts/regress_examples.py
echo
echo "全部通过 ✔"
