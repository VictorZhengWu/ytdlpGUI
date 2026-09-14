#!/usr/bin/env python3
"""互斥元数据与命令构建的结构断言（run_checks 的组成部分）。

覆盖：
1. conflicts.groups 全部双侧非空、成员在白名单内
2. conflicts.mixed 成对且双向对称
3. build_args 关键行为断言（multi 重复拼装 / nargs 拆分 / 冲突拒绝 / 布尔语义）
退出码非 0 即失败。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.services import options as o  # noqa: E402

failures = []


def check(name, cond):
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        failures.append(name)


c = o.compute_conflicts()
flags = set(o.FLAG_INDEX)

check("groups 非空", len(c["groups"]) > 40)
check("groups 双侧非空", all(g["on"] and g["off"] for g in c["groups"]))
check("groups 成员均在白名单", all(f in flags for g in c["groups"] for f in g["on"] + g["off"]))
check("mixed 成对", all(len(p) == 2 for p in c["mixed"]))
check("mixed 在白名单", all(a in flags and b in flags for a, b in c["mixed"]))
check("skip 组极性正确",
      any(set(g["on"]) == {"--skip-unavailable-fragments"} and set(g["off"]) == {"--abort-on-unavailable-fragments"}
          for g in c["groups"]))
check("ignore-errors 组极性正确",
      any(set(g["on"]) == {"--ignore-errors", "--no-abort-on-error"} and set(g["off"]) == {"--abort-on-error"}
          for g in c["groups"]))
check("ipv4/ipv6 互斥", any(set(p) == {"--force-ipv4", "--force-ipv6"} for p in c["mixed"]))

# build_args 行为断言
check("multi 重复拼装",
      o.build_args({"--match-filters": "a,!is_live"}) == ["--match-filters", "a", "--match-filters", "!is_live"])
check("nargs 拆分", o.build_args({"--replace-in-metadata": "title Intro 前言"})
      == ["--replace-in-metadata", "title", "Intro", "前言"])
check("nargs 引号剥除", o.build_args({"--alias": 'get-audio "-x"'}) == ["--alias", "get-audio", "-x"])
check("布尔 false 剔除", o.build_args({"--simulate": False, "--quiet": True}) == ["--quiet"])


def rejects(opts):
    try:
        o.build_args(opts)
        return False
    except o.OptionsError:
        return True


check("三态组两侧冲突拒绝", rejects({"--yes-playlist": True, "--no-playlist": True}))
check("mixed 两端冲突拒绝", rejects({"--force-ipv4": True, "--force-ipv6": True}))
check("sponsorblock 冲突拒绝", rejects({"--no-sponsorblock": True, "--sponsorblock-mark": "all"}))
check("未知选项拒绝", rejects({"--no-such-flag": True}))
check("多值单选项拒绝", rejects({"--proxy": ["a", "b"]}))

print(f"\n{len(failures)} failed" if failures else "\nall checks passed")
sys.exit(1 if failures else 0)
