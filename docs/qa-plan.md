# ytdlpGUI「All Options（全部选项）」功能测试计划

- 测试人：QA（自动化 + 代码评审）
- 日期：2026-09-06
- 被测服务：http://127.0.0.1:8765（运行中，不重启）
- 被测对象：
  - `GET /api/options` 选项注册表（生成器 `scripts/generate_registry.py`，数据 `backend/app/data/options_registry.json` + `options_zh.json`）
  - `POST /api/jobs` 选项校验与命令构建（`backend/app/services/options.py` 的 `build_args/sanitize_value/validate_urls`）
  - 前端互斥逻辑 `frontend/js/app.js` 的 `buildConflicts/makeOptionControl/setGroupSide/setOption`
  - 常用面板 `frontend/js/quick.js`（引用的 flag 合法性）
- 参照基准：本地 yt-dlp 2026.08.19 `--help`（250 个长选项）+ 官方 README（USAGE AND OPTIONS / FORMAT SELECTION / FILTERING FORMATS）
- 测试 URL：`https://example.com/notexist`（generic 提取器快速 404 失败，不产生下载物）

## 测试范围与优先级

| 模块 | 优先级 | 说明 |
|---|---|---|
| A 注册表完备性 | P0 | 全部选项功能的数据地基 |
| B 命令构建正确性 | P0 | flag→argv 转换是核心链路 |
| C 安全校验 | P0 | 白名单/注入防护 |
| D 语义正确性抽查 | P1 | 复杂取值格式（DATE/FILTER/SPEC/-f/-S） |
| E 前端互斥逻辑 | P1 | 代码评审 + 算法复算（Node） |
| F 中文说明层 | P2 | 30 条抽查，语义与示例合法性 |
| G 端到端冒烟 | P1 | 真实小文件下载一次，测后清理 |

## 用例清单

### A. 注册表完备性（脚本化比对 help 与 /api/options）

| 编号 | 目的 | 方法 | 预期 |
|---|---|---|---|
| TC-01 | flag 无缺失/多余 | 解析 `--help` 全部选项行与 /api/options 全部 flag 集合比对 | 250 个长选项一一对应；短选项 30 个一致 |
| TC-02 | metavar 判定 | 对照 help 选项行第 3 词与注册表 metavar；重点：含下划线占位（ITEM_SPEC/NETRC_CMD）、带括号占位（BROWSER[+KEYRING]…）、多值选项（--alias/--print-to-file/--replace-in-metadata 多个占位词） | 取值型/开关型无误判；多占位词不应被吞进 description 或漏掉第 2/3 个取值 |
| TC-03 | 分节结构 | 注册表 section 列表 vs help 分节 | 无把节说明行误判为选项；Preset Aliases 空节不渲染 |
| TC-04 | multi 标记 | MULTI_FLAGS 与 help 中"can be used multiple times"的选项集合比对 | 所有可多次使用的选项都能表达多值；不可多次使用的不误拆 |

### B. 命令构建正确性（POST /api/jobs 的 command 字段断言 + 直接 import build_args 批量断言）

| 编号 | 目的 | 方法 | 预期 |
|---|---|---|---|
| TC-10 | 布尔型 true | options={"--verbose": true} | command 含 `--verbose`，无多余取值 |
| TC-11 | 取值型字符串 | {"--format": "mp4"} | `--format mp4` |
| TC-12 | 短选项键 | {"-f": "bv*+ba/b", "-S": "res:1080"} | 展开为 `--format`/`--format-sort` |
| TC-13 | 多值拼装 | MULTI_FLAGS 传逗号串与数组（如 --add-headers / --match-filter 两个值） | 每个取值独立跟在自己的 flag 后（`--flag v1 --flag v2`），不得把 v2 泄漏为位置参数（URL） |
| TC-14 | 数值类型 | {"--socket-timeout": 30, "--age-limit": 18.5} | 转字符串拼入 |
| TC-15 | 空值 | 取值型传 ""/"  "/[]，布尔传 false，取值型传 true | 400 且错误信息明确 |
| TC-16 | 非法取值类型 | 传嵌套 dict / null | 400 |
| TC-17 | 示例全量回归 | 把 zh 层全部非空 example 逐个注入对应 flag 构建 job，跑 yt-dlp --simulate 校验是否被接受 | 全部 example 构建的命令可被 yt-dlp 正常解析 |

### C. 安全校验

| 编号 | 目的 | 方法 | 预期 |
|---|---|---|---|
| TC-20 | 未知选项 | {"--definitely-not-real": true}、{"--playlist-reverse": true}（yt-dlp 隐藏选项，不在注册表） | 400「未知或不支持的选项」 |
| TC-21 | 注入：以 - 开头 | {"--format": "-verbose"}、URL "https://x.com -o /tmp/pwn" | 400 取值不合法 / URL 拒绝 |
| TC-22 | 注入：特殊字符 | 取值含反引号、$()、\|、\x00、中文混合 | 危险字符被 VALUE_RE 拒绝（400）；无害字符放行且命令拼装无 shell 解释（subprocess 列表模式） |
| TC-23 | URL 校验 | 空列表、"ftp://x"、"file:///etc/passwd"、"-h"、"javascript:alert(1)" | 400 |
| TC-24 | flag 名注入 | 键为 ""、"verbose"、"-h" | 400 未知选项 |

### D. 语义正确性抽查（20 个复杂选项，POST command 断言 + yt-dlp --simulate 实证）

TC-30..TC-49：--dateafter now-1month / --date 20240101；--match-filters "duration<600"、"like_count>?100 & description~='cats'"；--download-sections "*10:15-inf" 与 "intro"；--sponsorblock-remove sponsor,selfpromo；--cookies-from-browser chrome；--playlist-items "1,3-5" 与 "1:3,7,-5::2"；-S "res:1080,ext:mp4:m4a"；-f "bv*+ba/b"；--min-filesize 50k / --limit-rate 4.2M；--sub-langs "en.*,ja"；--extractor-args youtube:player_client=android；--add-headers Referer:https://example.com；--retry-sleep linear=1::2；--wait-for-video 10-30；--parse-metadata "title:(?P<n>.+) - .*"；--netrc-cmd "pass show yt-dlp"；--xff default；-o "%(title)s [%(id)s].%(ext)s"；--js-runtimes deno；--exec "echo {}"。
预期：API 接受、command 拼装与 yt-dlp 语义一致、yt-dlp --simulate 解析不报参数错。

### E. 前端互斥逻辑（代码评审 + 将 buildConflicts 移植到 Node 对真实注册表复算）

| 编号 | 目的 | 方法 | 预期 |
|---|---|---|---|
| TC-60 | --X/--no-X 三态组 | 复算输出全部分组 | 每组 on/off 两侧非空，极性正确（on 侧=开启该行为的 flag） |
| TC-61 | 别名并组 | --abort-on-error (Alias: --no-ignore-errors) 三成员组 | {--ignore-errors, --no-abort-on-error, --abort-on-error} 一组，on=[--ignore-errors, --no-abort-on-error] |
| TC-62 | 极性反转对 | --skip-unavailable-fragments/--abort-on-unavailable-fragments、--allow-dynamic-mpd/--ignore-dynamic-mpd（别名指向未注册的 no- 名） | on/off 两侧均非空，点「开」能真正写入选项 |
| TC-63 | 值型↔布尔 mixed | --match-filters ↔ --no-match-filters 等 | 设一端自动清另一端 |
| TC-64 | 漏网互斥排查 | 对照 README/语义：--no-playlist/--yes-playlist、--no-sponsorblock 与 --sponsorblock-mark/remove、--no-overwrites/--force-overwrites、-4/-6 | 语义冲突对不产生矛盾命令 |
| TC-65 | 渲染正确性 | 代码评审 makeOptionControl/buildOptionTabs/applyPresetOptions | 组只渲染一次；preset 应用正确回填三态 |

### F. 中文说明层抽查（30 条，options_zh.json 对照 README/help）

| 编号 | 目的 | 方法 | 预期 |
|---|---|---|---|
| TC-70 | 语义准确性 | 逐条对照 help 原文 | 中文表述与原文语义一致（重点 --break-match-filters：是「被拒绝时中止」不是「匹配时中止」） |
| TC-71 | 示例合法性 | 每个 example 实际送 yt-dlp --simulate 验证 | 示例可直接复制使用；与中文说明的语义一致（--download-sections 示例应为合法章节/时间区间语法） |

### G. 端到端

| 编号 | 目的 | 方法 | 预期 |
|---|---|---|---|
| TC-80 | 真实下载 | POST https://download.samplelib.com/mp4/sample-5s.mp4 | 任务 done、downloads/ 出现文件、进度/文件路径上报 |
| TC-81 | 元数据查询 | GET /api/formats?url=… | 200 且含 formats 数组 |
| TC-82 | 环境清理 | DELETE /api/history、删除下载物、还原 config | 测试后无残留 |

## 输出物

- `/home/victor/myCode/ytdlpGUI/docs/qa-report-1.md`：总结（通过率、严重问题数）、问题清单（编号/级别 P0-P3/复现/实际 vs 预期/修复建议）、改进建议、覆盖说明。
