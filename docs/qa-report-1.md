# ytdlpGUI「All Options（全部选项）」功能测试报告

- 报告编号：QA-1
- 测试日期：2026-09-13 ～ 2026-09-14
- 测试人：QA（自动化脚本 + 代码评审，未使用浏览器、未重启服务、未修改任何代码）
- 被测版本：本地服务 http://127.0.0.1:8765（进程 2026-09-13 21:52 启动）；本地 yt-dlp 2026.08.19（.venv）
- 测试计划：`docs/qa-plan.md`（用例编号 TC-xx 与本报告对应）

## 一、总结

| 指标 | 数值 |
|---|---|
| 执行断言/用例 | 76 项（另有 94 条 example 全量回归、46 个互斥组全量复算） |
| 通过 | 62 项，通过率 **81.6%** |
| 中文 example 可用率 | 91 条（剔除 3 条环境因素）中 84 条可用，**92.3%** |
| 发现问题 | **20 个**：P0 × 1，P1 × 5，P2 × 5，P3 × 9 |

整体评价：注册表完备性（250/250 flag、metavar/短选项判定）与安全校验（白名单、注入防护 11 项全过）质量很高；命令构建的主干路径正确。主要风险集中在三处：**多值选项拼装会把取值泄漏为 URL**、**前端互斥组的极性算法在别名指向未注册 no- 名时失效**、**history_path 的目录/文件语义不匹配可在当前代码上杀死整个下载队列**。

> 环境说明（影响个别结论的归因）：服务进程于 09-13 21:52 启动，而 `backend/app/services/{downloader,history,store}.py` 于当日 23:18 被修改，**运行中进程加载的是旧版这三文件**；`options.py`、`routes.py`、注册表与中文层先于进程启动，API 层结论均有效。BUG-01 的「队列死亡」在当前磁盘代码上以独立进程实证（见复现步骤），并非臆测。

## 二、问题清单

### P0（1 个）

#### BUG-01 history_path 前后端语义不匹配：历史永不记录、DELETE 500，当前代码会杀死下载队列

- 模块：`backend/app/services/history.py` × `frontend/js/quick.js`（`__historypath` dir 控件）× `backend/app/services/downloader.py`
- 复现：
  1. 常用面板「历史日志路径」是**目录选择器**（quick.js `widget: "dir"`），选择后 PUT config `{"history_path":"/home/victor"}`（当前 config 即此状态）；
  2. `history._history_path()` 把它当**文件路径**：`GET /api/history` 永远返回 `[]`（open 目录 → OSError → 吞掉）；
  3. `DELETE /api/history` → **HTTP 500**（已在运行服务实测：`IsADirectoryError: [Errno 21] Is a directory: '/home/victor'`）；
  4. 当前磁盘代码独立进程实测：`DownloadManager.submit()` 第 1 个任务正常终态后 `history.record()` 抛 `IsADirectoryError`，`_worker` 线程死亡（`_run` 无 try/except），**第 2 个任务永久停留 queued，无非主线程存活**。
- 实际 vs 预期：预期选目录后历史写入该目录；实际历史功能整体失效，重启服务后（加载 23:18 版代码）任一任务完成即令整个下载队列永久卡死。
- 建议：① 统一语义——`history_path` 为目录时拼接 `<dir>/history.json`，或把前端控件改为文件路径输入；② `record()`/`clear()` 包裹 try/except，历史写失败不得影响任务与工作线程；③ `_worker` 对 `_run` 加异常保护。

### P1（5 个）

#### BUG-02 多值选项拼装泄漏：`--flag v1 v2` 中 v2 沦为位置参数（URL）

- 模块：`backend/app/services/options.py` `build_args()`（`argv.extend(values)` 分支）
- 复现：`POST /api/jobs {"urls":["https://example.com/notexist"],"options":{"--add-headers":"Referer:https://a.com,User-Agent:X"}}`，返回 `command`：
  `yt-dlp --add-headers Referer:https://a.com User-Agent:X https://example.com/notexist`
  本地 yt-dlp 实证：`--match-filters 'duration<600' 'notaurl2'` 会输出 `[generic] Extracting URL: notaurl2`（append 类选项每次只取 1 个值，第 2 个 token 被当 URL）。
- 实际 vs 预期：预期多值选项输出 `--flag v1 --flag v2`；实际第 2 个取值被 yt-dlp 当作待下载 URL，轻则任务报错，配合 `--ignore-errors` 时会真的去下载该"值"，且前端命令预览显示的是 `--add-headers a,b` 与实际不符。影响全部 6 个生效的 MULTI_FLAGS（逗号串或数组均触发）。
- 建议：multi 选项按 `flag v1 flag v2` 重复 flag 拼装。

#### BUG-03 前端互斥组极性错误：两组「开」按钮静默无效，预设应用会翻到反侧

- 模块：`frontend/js/app.js` `buildConflicts()` 的 `sideOf()` 极性推导
- 复现（算法已忠实移植并在真实注册表上复算，46 组全量）：当别名指向**未注册的 no- 名**（如 `--skip-unavailable-fragments (Alias: --no-abort-on-unavailable-fragments)`）时，两个成员极性都推导为 "off"，产生 on 侧为空的组：
  - `{--skip-unavailable-fragments, --abort-on-unavailable-fragments}`（on=[]）
  - `{--allow-dynamic-mpd, --ignore-dynamic-mpd}`（on=[]）
- 实际 vs 预期：点「开」时 `setGroupSide(g,"on")` 因 `g.on.length===0` 什么都不写入，但 UI 高亮"开"、命令预览无变化——用户以为已启用；预期 on/off 两侧各至少一个 flag。代码评审推论（未在浏览器实测）：`applyPresetOptions` 对这些组恒走 "off" 分支，预设含 `--ignore-dynamic-mpd` 时实际置位的是 `g.off[0]`＝`--allow-dynamic-mpd`（反义）。
- 建议：极性判断回退为「组内语义名」判断——正名（非 no- 前缀）即 on 侧；`setGroupSide` 对空侧应防御并告警。

#### BUG-04 常用面板「倒序下载播放列表」勾选后下载必然 400

- 模块：`frontend/js/quick.js` 第 53 行引用 `--playlist-reverse`
- 复现：勾选该复选框 → 下载 → `POST /api/jobs` 返回 400 `未知或不支持的选项: --playlist-reverse`（已实测）。
- 原因：`--playlist-reverse` 在 yt-dlp 中是 `optparse.SUPPRESS_HELP` 隐藏选项（options.py:1087），不出现在 `--help`，注册表（由 --help 生成）因此不含它，后端白名单拒绝。
- 实际 vs 预期：预期勾选后倒序下载；实际常用面板该功能 100% 不可用，且错误弹窗文案与用户操作对不上。
- 建议：快捷面板改为组合合法选项实现，或注册表补充手工维护的白名单补充层（hidden-but-supported 列表）。

#### BUG-05 MULTI_FLAGS 含两个死条目，真实的 --match-filters/--downloader-args 多值被静默丢弃

- 模块：`backend/app/services/options.py` `MULTI_FLAGS`
- 复现：`MULTI_FLAGS` 写的是 `--match-filter`（单数）与 `--external-downloader-args`（别名），而注册表里的真实 flag 是 `--match-filters`（复数）与 `--downloader-args` → 两个条目永远匹配不上。实测 `build_args({"--match-filters":["a","b"]})` → `['--match-filters','a']`，**b 被静默丢弃**（非 multi 只取 `values[0]`）。
- 实际 vs 预期：预期 OR 语义的多个过滤器全部生效（yt-dlp 官方用法）；实际只剩第一个，无任何报错。
- 建议：修正为真实 flag 名；非 multi 选项收到多值时应报错而非静默截断。

#### BUG-06 取值白名单拒绝 yt-dlp 文档语法字符 `!`、`|`、`^`，README 官方示例无法提交

- 模块：`backend/app/services/options.py` `VALUE_RE`
- 复现（全部实测 400「取值不合法」）：
  - `--match-filters "!is_live"` —— README 的**第一个官方示例**（`!field` 否定语法）；
  - `--remove-chapters "Intro|Outro"` —— 正则「或」的正确写法；
  - `--match-filters "title~=cats|dogs"`、`"^Intro"`。
- 实际 vs 预期：预期过滤器/章节正则类选项支持其文档语法；实际这些字符整体被拒，`--match-filters` 的否定过滤、`--remove-chapters`/`--download-sections` 的正则或逻辑均无法表达。
- 建议：VALUE_RE 增加 `!|^`（白名单本身无 shell 注入风险——subprocess 列表模式、值以 `-` 开头已单独拦截）；或对正则类选项放宽校验。

### P2（5 个）

#### BUG-07 多参数选项 `--alias` / `--print-to-file` / `--replace-in-metadata` 无法经 GUI/API 正确表达

- 复现（yt-dlp 实测）：三者分别需要 2/2/3 个取值，API 只能传 1 个：
  - `--print-to-file "title:titles.txt"` → URL 被吞作 FILE 参数 → `error: You must provide at least one URL`
  - `--replace-in-metadata 'title "a" "b"'` → `error: option requires 3 arguments`
  - `--alias 'get-audio "-x"'` → 吞 URL 同上
- 附带缺陷：注册表 description 吞入了第二 metavar 词（`--alias` 描述以 "OPTIONS" 开头、`--print-to-file` 以 "FILE" 开头、`--replace-in-metadata` 以 "REGEX REPLACE" 开头）。
- 建议：注册表增加 `nargs` 元数据，多参数选项前端渲染多输入框；短期内建议在 GUI 隐藏或标注这三项。

#### BUG-08 `--break-match-filters` 中文说明语义颠倒

- options_zh.json：「同过滤器，但遇到**匹配**视频时停止整个下载」。yt-dlp 原文：**stops the download process when a video is rejected**（视频**被过滤拒绝**时中止）。实际效果与说明完全相反，会误导用户构建错误任务。（example `title*=预告` 语法本身合法，`*=` 为 contains 算子，已验证。）

#### BUG-09 `--download-sections` 中文示例 `*intro` 是非法语法

- 复现：`yt-dlp --download-sections '*intro' --simulate <url>` → `error: invalid --download-sections time range "*intro". Must be of the form "*start-end"`。`*` 前缀表示时间区间（如 `*10:15-inf`），章节正则应为 `intro`；中文说明又写的是「标题匹配正则的章节」，说明与示例互相矛盾。建议示例改为 `intro` 或 `*0:30-1:00`。

#### BUG-10 漏网互斥：4 组语义冲突对可同时置位

- 46 组复算 + 语义排查确认以下冲突对前端无任何互斥（可同时进入命令，yt-dlp 按后者覆盖，实际效果取决于用户点击顺序）：
  1. `--no-playlist` ↔ `--yes-playlist`（yt-dlp 官方互斥对）
  2. `--no-sponsorblock` ↔ `--sponsorblock-mark` / `--sponsorblock-remove`（README 明言前者关闭后两者；且 sponsorblock-remove 在常用面板）
  3. `--no-overwrites` ↔ `--force-overwrites`（覆盖行为相反）
  4. `--force-ipv4` ↔ `--force-ipv6`
- 建议：在 buildConflicts 增加手工冲突表（与 BUG-04 的手工层共用）。

#### BUG-11 MULTI_FLAGS 覆盖率 8/20：12 个可多次使用的选项只能给单值

- help 明示 "can be used multiple times" 的 20 个选项中仅 8 个在 MULTI_FLAGS；缺失：`--download-sections`、`--retry-sleep`、`--downloader`、`--downloader-args`、`--remove-chapters`、`--replace-in-metadata`、`--exec`、`--use-postprocessor`、`--remote-components`、`--color`、`--alias`、`-t/--preset-alias`。后果：如 `--download-sections` 无法一次下载多个片段（yt-dlp 需重复 flag）。修复 BUG-02 时应一并按 yt_dlp options.py 的 action='append' 全量补齐。

### P3（9 个）

| 编号 | 问题 | 复现/证据 | 建议 |
|---|---|---|---|
| BUG-12 | `--compat-options` example `"list"` 非法 | yt-dlp 实测 `error: wrong OPTS for --compat-options: list` | 改为 `all` 或删除 |
| BUG-13 | `--remove-chapters` example `"Intro,Outro"` 语义误导 | 单值是**一个**正则（字面匹配"Intro,Outro"），正确写法 `Intro\|Outro` 又被 BUG-06 拦截 | 改 example 并放宽 `\|` |
| BUG-14 | example 混入中文提示词，复制即错 | `--update-to`："stable@latest **或** nightly"；`--audio-quality`："0 **或** 320K"（作 placeholder 直接进命令会报错） | example 只放可复制值 |
| BUG-15 | 布尔选项传 `false` 静默视为开启 | `build_args({"--simulate": False})` → `--simulate`（值被忽略，metavar=None 不走 sanitize） | 布尔型收到显式 false 应报错或剔除该 flag |
| BUG-16 | URL 校验不一致 | `"javascript:alert(1)"`（无 `://`）通过 validate_urls（实测放行）；URL 内空格亦放行，运行期才失败 | 无 `://` 时要求纯路径或直接拒绝；拒绝含空白 |
| BUG-17 | `--write-auto-subs` 中文「（机翻）」不准确 | 自动字幕是语音识别（ASR）生成，非机器翻译；quick.js 同文案 | 改为「自动生成（语音识别）」 |
| BUG-18 | job.command 展示与真实执行不一致 | to_dict 只拼 `argv+urls`，实际执行还会注入 `-o <download_dir>/%(title)s [%(id)s].%(ext)s`（e2e 实测文件名带 `[id]`，command 无 `-o`） | command 含完整 argv |
| BUG-19 | HIDDEN_FLAGS 死代码 | `--help/--version/--list-extractors/--simulate/--dump-json` 等 CLI 信息型选项定义了隐藏集合但全项目无引用，GUI 全部展示；勾选 `--list-extractors` 类选项任务"成功"但无下载物 | 落实隐藏或标注「CLI 查询类」 |
| BUG-20 | 依赖型选项无提示，单用即失败 | `--max-sleep-interval "10"` 单用 yt-dlp 报 `min sleep interval must be specified`；`--username` 单用触发交互式密码提示（子进程 stdin 关闭 → EOFError） | 依赖提示/组合校验；GUI 场景提示必须同时填 `--password` |

## 三、改进建议（非缺陷，按价值排序）

1. **注册表生成器改为从 `yt_dlp/options.py` 提取元数据**（flag/alias/action=append/nargs/SUPPRESS_HELP），根治 metavar 判定、multi 标记、隐藏选项三类问题（BUG-02/04/05/07/11 的共同根源），也免于 help 文案改版造成的脆弱正则。
2. **服务端做语义冲突校验**：目前互斥完全依赖前端（buildConflicts），API 层可同时提交 `--yes-playlist` + `--no-playlist` 等；将互斥/冲突元数据放入 /api/options 输出，前后端共享一份逻辑。
3. **预设保存时校验**：`POST /api/presets` 接受任意 options dict 原样存储（实测可存未知 flag，应用时才静默跳过）；保存时应走一遍 build_args 白名单校验。
4. **前端命令预览统一走后端**：预览是前端自行拼的（multi/布尔/-o 均与实际有偏差），可加一个 dry-run 端点返回真实 command。
5. **为 `--exec`/`--netrc-cmd` 增加风险提示**：二者天然接受任意命令（VALUE_RE 放行 `;` 等属预期行为，subprocess 列表模式无 shell 注入），但 GUI 无任何警示。
6. **example 纳入 CI 回归**：本次 94 条 example 全量实证脚本（build_args → yt-dlp --simulate）可直接作为回归用例，防止示例随 yt-dlp 升级失效。

## 四、测试覆盖说明

| 模块 | 用例 | 覆盖情况 |
|---|---|---|
| A 注册表完备性 | TC-01~04 | help 250 长选项 + 30 短选项脚本化逐项比对；metavar 特例（下划线 ITEM_SPEC/NETRC_CMD、括号 BROWSER[+KEYRING]、[CHANNEL]@[TAG] 等）逐一核验；multi 标记与 yt_dlp options.py 源码比对 |
| B 命令构建 | TC-10~17 | 21 项断言（直接 import build_args/sanitize_value，无副作用）；94 条中文 example 全量经 build_args 拼装后跑真实 yt-dlp --simulate |
| C 安全校验 | TC-20~24 | 11 项：未知/隐藏选项、`-` 开头值、反引号/`$()`/NUL/管道、URL 各非法形态，全部符合预期（白名单有效，subprocess 列表模式无 shell 注入面） |
| D 语义正确性 | TC-30~52 | 29 个复杂取值（DATE/FILTER/ITEM_SPEC/-f/-S/大小/区间/headers 等）实证，28 过 1 败（BUG-06） |
| E 前端互斥 | TC-60~65 | buildConflicts 忠实移植 Python 复算：46 组全量极性校验、14 对 mixed、成员≥3 组、漏网互斥语义排查；渲染/预设路径为代码评审 |
| F 中文说明层 | TC-70~71 | options_zh.json 全量（约 200 条）人工对照 help 审阅 + 94 条 example 机器实证；失败 10 条中 3 条为环境因素（~/yt-dlp.conf 不存在、video.info.json 不存在、impersonate 依赖缺失）已剔除 |
| G 端到端 | TC-80~82 | 真实下载 sample-5s.mp4 成功（done、100%、文件落盘）；/api/formats 正常；测后已删文件、还原 config（download_dir=/home/victor/share）、history 为空、presets 为空，项目 downloads/ 无残留 |

未覆盖/限制：浏览器 DOM 层交互（按任务要求未使用浏览器）——BUG-03 的 UI 表现、BUG-10 的双选操作均为算法复算 + 代码评审结论；SSE 事件流、取消、多任务并发不在本轮范围；运行中服务加载的 downloader/history/store 为 21:52 前版本，相关 API 现象（500）已在磁盘代码上复现归因。

## 附录 A：修复复验记录（2026-09-14）

原报告交付后，开发于 09-14 00:10-00:13 落盘了第一批/第二批修复并于 00:13:28 重启服务（进程 803689）。本附录为对新代码的全面复验结论（脚本复跑 + API 实测 + 内省比对）。

### 已验证修复（不再列为问题）

| 原编号 | 复验证据 |
|---|---|
| BUG-01 | `_history_path()` 目录语义 + record/clear 全 try/except + `_worker` 异常保护；实测 `DELETE /api/history` 200、`/home/victor/history.json` 正常写入；独立进程双任务验证队列存活 |
| BUG-02 | 重复拼装生效：API 实测 `--add-headers Referer:https://a.com --add-headers User-Agent:X`，无取值泄漏 |
| BUG-04 | EXTRA_OPTIONS（--playlist-reverse/--no-playlist-reverse）并入白名单与 "Additional Options" 节；API 受理；前端复算成正确三态组 {on: --playlist-reverse, off: --no-playlist-reverse} |
| BUG-05 | MULTI_FLAGS 修正为 `--match-filters` 真名，数组多值重复拼装（`!is_live` + `duration<600` 实测通过） |
| BUG-06 | VALUE_RE 增 `!|^`：`--match-filters '!is_live'`、`--remove-chapters 'Intro|Outro'` 均通过 |
| BUG-07 | NARGS 拆分（lsplit/rsplit/split）三件套全部实测通过 yt-dlp 参数校验（残留见 R-5） |
| BUG-08/12/13/17 | options_zh.json 文案/示例已修正（break-match-filters 语义、compat-options、remove-chapters、机翻→语音识别） |
| BUG-09 | example 改为合法区间语法（残留见 R-4） |
| BUG-15/16/18/19/20 | 布尔 false/None 剔除、URL 规则（javascript:/空白拒绝、ytsearch 前缀放行）、command 含 `-o` 完整命令（API 实测）、HIDDEN_FLAGS 接线并扩充（--console-title 未隐藏，正确）、依赖提示文案 |

### 复验发现的残留问题

| 编号 | 级别 | 问题 | 证据 | 建议 |
|---|---|---|---|---|
| R-1 | P1 | BUG-03 仅半修：no- 前缀兜底后，`{--skip-unavailable-fragments, --abort-on-unavailable-fragments}` 与 `{--allow-dynamic-mpd, --ignore-dynamic-mpd}` 两组 off 侧仍为空（两成员均无 no- 前缀，全部落入 on 侧）；「关」按钮被 setGroupSide 静默忽略（console.warn），「开」置位哪一个取决于 Set 插入序 | 新算法忠实复算，输出 `{'on': [两者], 'off': []}` | POLARITY_OVERRIDES 显式表（4 行）或以描述中 "(default)" 为锚定 on 侧 |
| R-2 | P2 | BUG-10 残留：mixed Map 一对多覆盖——`--no-sponsorblock → --sponsorblock-mark` 映射被 `→ --sponsorblock-remove` 覆盖；设置 --no-sponsorblock 只清 remove 不清 mark（反向清除正常） | 复算 `mixed.get('--no-sponsorblock') == '--sponsorblock-remove'`；app.js 源码 Map.set 顺序同理 | mixed 改为 `Map<flag, Set<flag>>`，setOption 清除时遍历集合 |
| R-3 | P2 | BUG-11 回归项：`--break-match-filters` 从 MULTI_FLAGS 丢失（yt_dlp options.py action='append'）；数组取值 400、逗号串无法表达 OR | `build_args({'--break-match-filters':['a','b']})` → 400「不支持多个取值」 | MULTI_FLAGS 补一行 `--break-match-filters` |
| R-4 | P3 | BUG-14 残留：--download-sections 新示例 `"intro 或 *0:30-1:00"` 混入中文「或」，复制后是合法但永不匹配的正则 | options_zh.json 实文 | 示例改为单一合法值（如 `intro`） |
| R-5 | P3 | NARGS --alias 保留字面引号：`get-audio "-x --audio-format mp3"` 拆分后 OPTIONS 含引号，定义可过、使用即 Usage error | 实测带引号定义+使用报错，无引号版本正常 | 拆分后 strip 外层引号（shlex 风格）或示例去引号；注意 regress 脚本仅验定义不验使用（盲区） |
| R-6 | P3 | URL 规则仅放行 `ytsearch` 前缀，`gvsearch2:python` 等 yt-dlp 文档化的 --default-search 前缀被拒 | `validate_urls(['gvsearch2:python'])` → 400 | 可接受则记录为设计取舍；或放行 `^[a-z0-9_]+search\d*:` 模式 |

### 回归工具基线

`scripts/regress_examples.py`（本报告交付物，92 条 example 全量实证）：修复后基线为 **通过 87 / 环境跳过 3 / 已知限制 2 / 失败 0，退出码 0**。R-4、R-5 修复后示例集合可能变化，基线随之更新。

### 终轮复测（2026-09-14 00:30 服务重启后，执行真实 app.js buildConflicts 源码 + API 实测）

| 残留 | 状态 | 证据 |
|---|---|---|
| R-1 | ✅ 已关闭 | Node 直接执行 app.js 真实 buildConflicts 源码对 /api/options 断言：46 组双侧全部非空；skip 组 on=[--skip-unavailable-fragments]、mpd 组 on=[--allow-dynamic-mpd]；POLARITY_OVERRIDES 显式表生效，兜底降级为 tripwire（正确） |
| R-2 | ❌ **部分关闭，引入新 P1（NEW-1）** | 手工冲突表已正确改 Set：--no-sponsorblock → Set{mark, remove} 双向清除复算通过；但值型/--no-X 配对循环（app.js 第 116 行）仍用 `state.mixed.set(f, pos)` 写入**字符串**——28 个条目（14 对，含 --match-filters/--cookies/--exec/--download-archive 等）不是 Set，而 setOption 消费端已改为 `others.forEach(...)`，字符串无 forEach → **这 28 个 flag 首次置位即抛 TypeError**（对端不清除、高亮与命令预览不更新）。实测：`mixed 非 Set 条目数: 28`、`setOption forEach 将崩溃的 flag 数: 28`。一行修复：改为 `addMixed(f, pos); addMixed(pos, f);` |
| R-3 | ✅ 已关闭 | MULTI_FLAGS 已含 --break-match-filters；API 实测 `--break-match-filters a --break-match-filters b` 重复拼装正确 |
| R-4 | ✅ 已关闭 | --download-sections example 已改 "intro" |
| R-5 | ✅ 已关闭 | NARGS 拆分后剥外层引号：带引号/不带引号输入均产出 `['--alias','get-audio','-x --audio-format mp3']`；别名使用时实证正常（--get-audio 展开成功） |
| R-6 | ✅ 已关闭（附 2 条措辞建议，非阻塞） | README「已知设计取舍」两条与实现相符；建议：① 补充「不含冒号的裸域名（如 example.com）亦放行」；② 空格例外描述不准确——实际规则是 lsplit（--alias）仅首段不可含空格、rsplit（--print-to-file）仅末段（文件路径）不可含空格、split（--replace-in-metadata）三段均不可，现文案「--alias 第二参数除外」遗漏 --print-to-file 模板段可含空格 |

终轮回归：`scripts/regress_examples.py` 92 条 = 通过 87 + 环境 3 + 已知限制 2 + 失败 0，exit 0（--alias 属 PASS 类，LIMIT 仅为 --max-sleep-interval/--username 两项依赖型，脚本无需调整）。

**终轮结论：R-1/R-3/R-4/R-5/R-6 关闭；R-2 因第 116 行类型不一致遗留新 P1（NEW-1，一行修复），修复后建议仅复跑本节 Node 断言脚本（/tmp/qa_conflicts_final.js 逻辑：mixed 全量 Set 断言 + 46 组双侧非空断言）即可关闭全部问题。**

### 定稿确认（2026-09-14 00:43，app.js v=42）

NEW-1 修复核验（第 116 行已改 `addMixed(f, pos); addMixed(pos, f)`，Node 直跑真实源码对 /api/options 断言）：

- 46 组 on/off 双侧全部非空；skip 组 on=[--skip-unavailable-fragments]、mpd 组 on=[--allow-dynamic-mpd]、playlist-reverse 组极性正确；
- mixed 非 Set 条目数 0（全量 Set）；setOption forEach 崩溃 flag 数 0；
- README「已知设计取舍」两条措辞已修正（裸域名放行说明、lsplit/rsplit 空格方向描述、外层引号剥除），与实现一致；
- 后端本轮未改动（options.py 未变），example 回归基线（92 条 0 失败，exit 0）持续有效。

**最终结论：全部问题关闭（20 原始问题 + 6 残留 + NEW-1），本报告定稿。**

### 元数据工程验收复测（2026-09-14 11:10 服务重启后）

三方向重构（注册表内省化 / 冲突元数据后端统一 / run_checks 套件）独立复测结果：

**通过项：**
- `run_checks.sh` 全套 exit 0：漂移检测无漂移、test_conflicts 17 项断言全过、example 回归 98 条（93 过/3 环境/2 已知限制/0 失败）；
- 独立按 dest 重算互斥（不复用 compute_conflicts）：51 组/30 对 mixed，与 /api/options 下发**集合级完全一致**，无极性未定被丢弃的 dest；ignore-errors 三成员组、skip、dynamic-mpd 极性全部正确（--abort-on-error 经 action=store_false 自然归 off 侧，无需人工表）；
- Node 直跑新 buildConflicts（纯消费 conflicts 字段）：51 组双侧非空、mixed 40 条全 Set、双向对称、setOption forEach 零崩溃；
- API 冲突校验：--yes-playlist+--no-playlist 与 --no-sponsorblock+--sponsorblock-remove 均 400；隐藏项白名单兼容旧预设（--dump-json/--exec-before-download 受理）；界面隐藏对（--cache-dir/--no-cache-dir）服务端仍校验；
- 注册表 vs --help 抽查 14 个易错项：metavar（含多词 "ALIASES OPTIONS"/"[WHEN:]FIELDS REGEX REPLACE" 完整保留，旧吞词问题结构性根除）、nargs（2/2/3）、multi（append+列表回调）全部与 optparse 一致；全量 metavar 无误判；322 项/72 隐藏与声明相符；SURFACE_HIDDEN 8 项带中文层。

**残留（验收未全过）：**

| 编号 | 级别 | 问题 | 证据 | 建议 |
|---|---|---|---|---|
| V-1 | P2 | **BUG-19 回归**：旧 UI 隐藏清单（HIDDEN_FLAGS，19 项）随手工表删除，新 hidden 仅来自 SUPPRESS_HELP，17 个 CLI 信息/查询型选项回流界面：--help/--version/--update/--list-extractors/--extractor-descriptions/--list-thumbnails/--list-subs/--list-formats/--dump-json/--dump-single-json/--print/--print-to-file/--dump-pages/--write-pages/--print-traffic/--list-impersonate-targets/--ap-list-mso | /api/options 逐一可见（17/19，-h/-U 为短键不计） | 恢复第四张小表 UI_SURFACE_HIDE（或将其并入 SURFACE_HIDDEN 语义的反向表），load_registry 过滤；白名单继续保留兼容 |
| V-2 | P3 | 短选项键绕过服务端冲突校验：`{"-4":true,"-6":true}` → 200，命令含 `--force-ipv4 --force-ipv6` | API 实测 | validate_conflicts 前将 options 键经 FLAG_INDEX 归一化为长名 |

**验收结论：方向 1/2/3 的核心目标全部达成且实现质量高（数据驱动彻底、前后端单一事实源、结构断言齐备）；遗留 V-1（P2 回归）/V-2（P3 绕过）两项，修复量约 10 行，修后建议复跑 run_checks.sh + 本节 Node 断言即可关闭。**

### 验收收尾（2026-09-14 11:24 服务重启后，V-1/V-2 修复确认）

- **V-1 已关闭**：UI_HIDE 表恢复（19 项 + --test + 两种 sig-code 拼写），/api/options 界面选项 258→241，17 项泄漏清单逐一复验 0 泄漏；--simulate/--quiet/--console-title/playlist-reverse 对/--user-agent/--referer/--playlist-start/--geo-bypass 共 9 项应保留项全部保留；白名单仍受理 --dump-json（旧预设兼容）；conflicts 元数据不受影响（51 组/30 对不变）。
- **V-2 已关闭**：validate_conflicts 入口经 FLAG_INDEX 归一化——`{"-4":true,"-6":true}` → 400「互斥选项同时启用: --force-ipv4 与 --force-ipv6」；短+长混写（-4 + --force-ipv6）同样 400；单 `-4` 正常输出 `--force-ipv4`；未知键提前 400；长名冲突路径回归正常。
- `run_checks.sh` 全套 exit 0（漂移无、17 断言全过、example 回归 96 条 = 91 过/3 环境/2 已知限制/0 失败；条数 98→96 系 --print/--print-to-file 转入 UI_HIDE 后其 example 不再进入界面注册表，符合预期）。

**最终验收结论：验收通过，定稿。** 累计问题账目：20 原始 + 6 残留（R-1~R-6）+ NEW-1 + V-1/V-2，全部关闭。
