# ytdlpGUI 跨设备接力开发提示词（粘贴给另一台电脑上的 ZCode）

> 用法：在另一台电脑的项目目录下打开 ZCode，把本文件全文（从下一行开始）粘贴给它。

---

你是 ZCode，现在接手 ytdlpGUI 项目的继续开发。这个项目由两台电脑上的 ZCode 轮流接力开发（每天通过 GitHub 同步），你负责今天的开发时段。请先完整阅读以下内容再开始工作。

## 项目背景

ytdlpGUI 是 yt-dlp 的跨平台图形前端（Web / Linux / Windows），仓库 https://github.com/VictorZhengWu/ytdlpGUI ，默认分支 `v2`。核心设计：

- **界面与功能严格分离**：`frontend/` 纯静态 HTML/CSS/JS（零构建），`backend/` FastAPI（`services/` 层不依赖 Web 框架、可独立 import），两者只通过 REST + SSE 通信。将来 macOS/iOS/Android 客户端复用同一后端。
- **选项注册表是单一数据源**：`scripts/generate_registry.py` 从 yt-dlp 源码（`yt_dlp/options.py`）内省生成 `backend/app/data/options_registry.json`（flag/nargs/可重复性/互斥关系全部数据驱动）。升级 yt-dlp 后重跑该脚本即可，`--check` 模式做漂移检测。
- **互斥元数据前后端共享**：后端 `compute_conflicts()` 产出 51 组三态互斥 + 30 对 mixed，随 `/api/options` 下发；服务端在 `build_args()` 强制校验冲突；前端 `buildConflicts()` 只消费不推导。
- **四语界面软编码**：`frontend/js/i18n/{zh,en,ja,ko}.json`，默认英文。中文选项说明层在 `backend/app/data/options_zh.json`。
- **双模式 UI**：默认精简（纯 `yt-dlp <url>`），「⚙ 高级」展开全部选项/常用设置。
- 开发采用 SDD 模式（先写/更新 docs 文档再动代码），测试由"QA Agent 出题 + 主会话浏览器执行"的双角色流程完成，已闭环 27 个数据层缺陷 + 123 条 UI 用例。

## 必读资料（按顺序）

1. `README.md`——功能全貌、快速开始、Windows exe 构建、已知取舍
2. `docs/design.md`——架构与 API 契约
3. `docs/tasks.md`——v1 至今全部任务记录（看最后两节了解近期工作）
4. `docs/qa-report-1.md` 附录 A——历轮缺陷与修复的来龙去脉（避免踩同样的坑）
5. `docs/qa-ui-plan.md` + `docs/qa-ui-report.md`——123 条 UI 用例（改 UI 后的回归清单）

## 环境要点

- Python venv：`.venv/`（没有则 `./run.sh` 会自动创建并装依赖）
- 启动：`./run.sh`（本机 127.0.0.1:8765）或 `./run.sh --lan`（局域网）；改后端代码需重启服务
- 前端无构建，改 `frontend/js/*.js` 或 CSS 后：更新 `frontend/index.html` 里的 `?v=` 版本号和 `window.APP_VER`（同一步 bump，防浏览器缓存），刷新即可
- 运行时数据（`backend/app/data/config.json`、`presets.json`、`history.json`、`downloads/`）已 gitignore，不入库

## 开发规约（必须遵守）

1. **改代码前后端行为类逻辑**：先在 `docs/tasks.md` 追加条目（SDD），改完运行 `scripts/run_checks.sh`，三步全绿才算完成（漂移检测 / 结构断言 / 96 条示例回归）
2. **改前端 UI**：run_checks 之外必须做浏览器冒烟——页面正常启动、「全部选项」三态组 ≥40、切中文/英文无语言残留。这是历史事故区（曾因组渲染标记未复位导致整页假死）
3. **不要手工编辑** `options_registry.json`（重跑生成器覆盖）；元数据语义修正只动 `backend/app/services/options.py` 里的三张小表（SURFACE_HIDDEN / POLARITY_FIX / EXTRA_MIXED）
4. **提交规范**：小步提交，message 用英文祈使句（如 "Fix tri-state group loss after language switch"）；绝不提交 cookies/凭据/运行时数据
5. 遇到 yt-dlp 语义不确定时读 yt-dlp 源码或 README（`.venv` 里有完整包），不要猜

## 接力协作流程（与另一台电脑的 ZCode）

- **开工第一步**：`git pull origin v2`，然后读 `git log --oneline -10` 了解对方昨天做了什么；若 `docs/tasks.md` 有新条目，视为最高优先级上下文
- **收工前必做**：跑 `scripts/run_checks.sh` 确认全绿 → `git add -A && git commit` → `git push origin v2`。未推送的工作对下一棒不可见，等于丢失
- **并行冲突**：两台机器理论上是错峰工作，若 `git push` 被拒（远端有新提交），先 `git pull --rebase` 解决再推；`docs/tasks.md` 若冲突，两边条目都保留
- **交接信息**：有未尽事项/警告/待验证点，追加到 `docs/tasks.md` 新条目（标注"待下一棒"），这是两台电脑之间唯一的异步沟通渠道

## 当前待办候选（上一棒遗留的建议，非强制）

- 注册表元数据再前进一步：把 SURFACE_HIDDEN/POLARITY_FIX 缩为纯语义表或数据化
- 为 ja/ko 增加选项说明层（机制已就绪：仿照 options_zh.json 加 options_ja/ko.json）
- macOS 版启动脚本与打包（技术栈已预留）
- 把 run_checks.sh 挂 CI（GitHub Actions）

现在请从 `git pull` 和阅读资料开始，然后向我（用户）确认你已就绪，并复述你对接力流程的理解。
