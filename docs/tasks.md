# 任务清单（Tasks）

| # | 任务 | 状态 |
|---|---|---|
| T1 | 生成全量选项注册表 `options_registry.json` | ✅ 完成（17 节 / 250 项） |
| T2 | SDD 文档：requirements / design / tasks | ✅ 完成 |
| T3 | 后端：`services/options.py` 白名单校验 + 命令构建 | ⬜ |
| T4 | 后端：`services/downloader.py` 任务管理器（队列/进程/进度解析/取消） | ⬜ |
| T5 | 后端：`services/metadata.py` `-J` 元数据与格式列表 | ⬜ |
| T6 | 后端：`services/presets.py` + `config.py` 持久化 | ⬜ |
| T7 | 后端：`api/routes.py` + `main.py`（含 SSE） | ⬜ |
| T8 | 前端：选项面板（动态 tab + 搜索 + 预设） | ⬜ |
| T9 | 前端：URL/信息查询/格式选择 | ⬜ |
| T10 | 前端：任务队列 + SSE 进度 + 日志 + 命令预览 | ⬜ |
| T11 | i18n zh/en | ⬜ |
| T12 | run.sh / run.bat / README | ⬜ |
| T13 | 端到端测试（API curl + 浏览器 GUI） | ⬜ |

## v2.1 更新（2026-09-06 第二轮）

| # | 任务 | 状态 |
|---|---|---|
| T14 | 全量选项中文说明与使用示例（options_zh.json，250/250 覆盖） | ✅ |
| T15 | 界面重构：暗色科技风主题（渐变/玻璃卡片/光晕/网格背景） | ✅ |
| T16 | "常用设置/全部选项"双模式渐进式选项界面 | ✅ |
| T17 | Windows .exe 打包（launcher.py + ytdlpgui.spec + build_windows.bat） | ✅（打包需在 Windows 上执行） |
| T18 | 新界面浏览器端到端验证（下载/搜索/中英文切换） | ✅ |

## v2.2 更新（第三轮 UI 交互重构）

| # | 任务 | 状态 |
|---|---|---|
| T19 | 下载路径移入常用设置 + 服务器目录浏览对话框（/api/fs/list） | ✅ |
| T20 | 中文界面下 17 个选项分类标签自动中文化 | ✅ |
| T21 | 精简/高级双模式（默认精简：标题栏+URL+队列+进度；高级展开全部设置） | ✅ |
| T22 | 响应式布局（窄屏单列、隐藏英文描述、无横向溢出） | ✅ |

## v2.3 更新（第四轮）

| # | 任务 | 状态 |
|---|---|---|
| T23 | 目录选择支持局域网共享/网盘（roots 快捷入口：主目录/根/网络挂载） | ✅ |
| T24 | 窄屏滚动时顶栏与命令条固定（main 内部滚动） | ✅ |
| T25 | 命令预览可隐藏（⌨ 开关，localStorage 记忆） | ✅ |
| T26 | 下载历史（链接/标题/时间/成败，可清空，路径可设，/api/history） | ✅ |
| T27 | 界面语言软编码为 JSON 字典，新增日文/韩文 | ✅ |

## v2.4 更新（第五轮）

| # | 任务 | 状态 |
|---|---|---|
| T28 | 查询信息按钮仅高级模式显示；精简模式纯净下载（yt-dlp <url>，不带任何选项） | ✅ |
| T29 | 多链接逐条查询信息（上限 10 条，各自独立渲染/报错） | ✅ |

## v2.5 更新（第六轮）

| # | 任务 | 状态 |
|---|---|---|
| T30 | 精简模式隐藏命令预览条（仅高级模式显示） | ✅ |
| T31 | 查询结果 ↑↓ 快速定位导航（粘性导航条 + 位置指示 + 边界禁用） | ✅ |
| T32 | 修复宽屏下队列/历史盒内容被裁剪（flex 子项 min-height:0 收缩） | ✅ |
| T33 | 静态资源版本参数防缓存（css/js ?v=） | ✅ |

## v2.6 更新（第七轮）

| # | 任务 | 状态 |
|---|---|---|
| T34 | 修复低矮视口（约 ≤700px）队列/历史卡片被压扁：列内滚动 + 卡片保底高度 340px | ✅ |

## v2.7 更新（第八轮）

| # | 任务 | 状态 |
|---|---|---|
| T35 | 查询信息改为浮动窗口展示（非模态，居中悬浮），右上角 ↑↓ 导航 + 位置指示 + 关闭按钮 | ✅ |
| T36 | 浮动窗口内格式行仍可点击选用（联动 -f 与命令预览） | ✅ |

## v2.9 更新（第十轮）

| # | 任务 | 状态 |
|---|---|---|
| T37 | 全部选项面板：非中文界面隐藏中文说明行，英文描述为主文本；悬浮提示同步分语言 | ✅ |
| T38 | 常用面板多语言回退链修正（非中文语言缺失时回退英文而非中文） | ✅ |
| T39 | 目录快捷位置标签去后端硬编码中文（结构化 kind/name，前端按语言本地化） | ✅ |
| T40 | html lang 与 body data-lang 随语言更新 | ✅ |

## v2.10 更新（第十一轮）

| # | 任务 | 状态 |
|---|---|---|
| T41 | 互斥选项治理：--X/--no-X 布尔对合并为三态控件（默认/开/关），共 46 组 | ✅ |
| T42 | 别名等价并组（含未注册反义名翻转，如 --abort-on-error ≡ --no-ignore-errors → 并入 ignore-errors 组） | ✅ |
| T43 | 值型 --X 与布尔 --no-X 混合互斥（设一端自动清除另一端并同步界面） | ✅ |
| T44 | 搜索/预设/清空适配互斥组；修复 /g 正则 lastIndex 跨选项残留 | ✅ |

## v3.0 更新（双角色 QA 迭代，Agent 协作）

| # | 任务 | 状态 |
|---|---|---|
| T45 | QA Agent 独立测试（README 对照 + API 黑盒 + 互斥复算，qa-plan/qa-report-1） | ✅ 发现 20 问题 |
| T46 | 首批修复 13 项（BUG-01~20 择要：history 语义/队列保护/multi 重复拼装/EXTRA_OPTIONS/VALUE_RE/nargs/布尔与 URL 校验/command 一致性/隐藏项/zh 修正） | ✅ Agent 复验 12/13 通过 |
| T47 | 残留修复 R-1~R-5（极性显式覆盖表/mixed 一对多集合/break-match-filters/example/引号剥离） | ✅ 回归 92 条 0 失败 |
| T48 | R-6 记为设计取舍（README 已知取舍节）；regress_examples.py 纳入回归 | ✅ |
| T49 | NEW-1（mixed 类型不一致，28 flag 置位崩溃）修复；Agent 终轮确认全部关闭，qa-report-1 定稿 | ✅ |

## v3.1 元数据工程（三方向落地）

| # | 任务 | 状态 |
|---|---|---|
| T50 | 方向1：generate_registry.py 重写为 yt_dlp/options.py 内省（322 选项含 72 隐藏；nargs/multi/dest/hidden 数据化） | ✅ |
| T51 | 方向2：冲突元数据后端统一计算（51 组三态 + 30 对互斥）进 /api/options；POST /api/jobs 服务端冲突校验；前端退役 union-find/别名解析/四张手工表 | ✅ |
| T52 | 方向3：scripts/run_checks.sh 质量套件（漂移检测 + test_conflicts.py 结构断言 + regress_examples.py） | ✅ |
| T53 | 新展示 SUPPRESS_HELP 有用选项（playlist-start/end、user-agent、referer、geo-bypass 等 8 个） | ✅ |
| T54 | Agent 验收复测：V-1（UI 隐藏清单回归）/V-2（短选项键绕过校验）修复并复验关闭；验收通过定稿 | ✅ |
| T55 | 修复 V-1 引发的启动崩溃：互斥组含界面隐藏成员时 flagMap 缺项抛 TypeError 致整页假死；组按可见性过滤 + boot 失败显示错误横幅 | ✅ |

## v3.2 UI 全面测试（双角色协作第二轮）

| # | 任务 | 状态 |
|---|---|---|
| T56 | Agent 设计 123 条 UI 用例（qa-ui-plan.md，11 模块含高危标注） | ✅ |
| T57 | 浏览器逐条执行 123 条：112 直接通过，执行中发现并修复 5 缺陷 | ✅ |
| T58 | D1 语言切换丢三态组 / D2 nargs=1 污染 / D3 配置 PUT 清任务列表 / D4 格式点击不回填 / D5 路径不上报 —— 全部修复并经 Agent 独立核验 | ✅ |
| T59 | Agent 判读定稿（qa-ui-report.md）：UI 测试通过；4 判读项裁定非阻塞 | ✅ |
| T60 | 补关 P3：already-downloaded 行路径解析（ALREADY_RE） | ✅ |

## v3.3 CI（第十二轮）

| # | 任务 | 状态 |
|---|---|---|
| T61 | run_checks.sh Windows venv 路径兼容（.venv/Scripts/python.exe），新机器开箱可用 | ✅ |
| T62 | GitHub Actions CI：push/PR 到 v2 触发质量套件三步（漂移检测/结构断言/96 条 example 回归），Ubuntu + Python 3.12；首跑 6a5cdee 全绿（1m26s） | ✅ |

## v3.4 用户实测三轮修复（第十三轮）

| # | 任务 | 状态 |
|---|---|---|
| T63 | 标签页标题随界面语言切换（i18n appTitle，applyI18n 设 document.title；index.html 静态标题改英文默认）；附带修复：切换语言时已有任务卡徽章/按钮文案重翻译（refreshJobs 只加新卡不更新旧卡） | ✅ |
| T64 | 多链接任务历史缺记录：Job.to_dict() 漏 files 字段（只记最后一个 filepath）；新增 file_urls 并行数组按「Extracting URL」行分段，多 URL 任务逐 URL 记一条历史；附带修复：MERGE_RE 匹配现版 yt-dlp「Merging formats into \"路径\"」，合并最终产物路径首次可被记录 | ✅ |
| T65 | 无 ffmpeg 时高画质下载产生分离的视频/音频两文件：/api/config 下发 ffmpeg_available，前端四语警告横幅（可关闭）；README 已知取舍补充说明。本机复现实证（yt-dlp 2026.08.19 无 ffmpeg + 无 JS 运行时 → YouTube 无预合并格式可回退） | ✅ |
