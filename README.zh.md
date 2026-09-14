# ytdlpGUI

**English ([README.md](README.md)) · [中文](README.zh.md) · [日本語](README.ja.md) · [한국어](README.ko.md)**

yt-dlp 的跨平台图形前端（Web / Linux / Windows），覆盖 yt-dlp 全部命令行选项，采用"界面与功能严格分离"架构，为将来 macOS / iOS / Android 客户端预留同一套后端 API。

## 功能特性

- **双模式界面**：默认精简模式（标题栏 + 链接输入 + 下载队列，纯净 `yt-dlp <url>` 下载）；「⚙ 高级」展开完整设置
- **全部选项**：yt-dlp 全部选项（含手工补充的隐藏选项），按官方分类分栏，中文说明 + 使用示例 + 悬浮提示，支持搜索
- **互斥治理**：51 组三态互斥组（默认/开/关）+ 30 对自动清除互斥，前后端共享元数据，服务端强制校验
- **下载管理**：多 URL 任务队列、实时进度/速度/ETA/日志（SSE）、取消任务、文件路径实时上报
- **信息查询**：浮动窗口展示标题/时长/格式表，点击行即选用 `-f`，多链接逐条查询带 ↑↓ 导航
- **下载历史**：链接/标题/路径/时间/成败全记录，可清空，日志路径可设
- **目录选择**：服务器端目录浏览对话框，支持局域网共享/网盘挂载点（Windows 盘符/UNC）
- **四语界面**：中文 / English / 日本語 / 한국어，全部软编码（`frontend/js/i18n/*.json`）
- **预设系统**：选项组合保存/加载/删除，保存即校验
- **安全**：选项白名单 + 取值校验，阻止参数注入；默认仅监听 127.0.0.1

## 架构

```
frontend/   纯静态 HTML/CSS/JS（零构建，可嵌入任意 WebView）
backend/    FastAPI 服务（纯逻辑，可独立 import）
  api/          HTTP 路由层（薄）
  services/     downloader / options / metadata / history / store
  data/         options_registry.json（由 yt_dlp.options 内省生成）
docs/       SDD 文档 + 两轮 QA 报告（123 条 UI 用例 + 27 项修复记录）
scripts/    generate_registry.py / run_checks.sh / regress_examples.py
```

选项注册表由 `scripts/generate_registry.py` 从 yt-dlp 源码（`yt_dlp/options.py`）内省生成——flag/参数个数/可重复性/互斥关系全部数据驱动。升级 yt-dlp 后重跑脚本即可适配，`--check` 模式可做漂移检测。

## 快速开始

```bash
# Linux / macOS
./run.sh                    # 自动建 venv、装依赖、开浏览器
./run.sh --lan              # 局域网模式（0.0.0.0，手机/其它电脑可访问）
```

```bat
:: Windows（源码运行）
run.bat
```

手动方式：`python -m uvicorn backend.app.main:app --port 8765` → 浏览器打开 http://127.0.0.1:8765
API 文档（OpenAPI）：http://127.0.0.1:8765/docs

## 构建 Windows .exe

**方式一（推荐）**：装好 Python 3.10+ 后双击或执行

```bat
build_windows.bat
```

产物为单文件 `dist\ytdlpgui.exe`——无控制台窗口、双击即用、自动打开浏览器界面。配置/预设/下载记录保存在 exe 同级 `data\` 目录，拷贝 exe 即可分发。

**方式二（手动）**：

```bat
python -m venv .venv
.venv\Scripts\pip install -r backend\requirements.txt pyinstaller
.venv\Scripts\pyinstaller --clean ytdlpgui.spec
```

说明：`ytdlpgui.spec` 中 `console=False`（无黑框）；排错时改为 `True` 重新打包即可看到日志。exe 内置当前版本的注册表/前端资源，升级 yt-dlp 需重新打包或改用源码运行。

## 开发质量套件

改代码或升级 yt-dlp 后运行 `scripts/run_checks.sh`（三步全过才算绿）：

1. 注册表漂移检测——yt-dlp 实际选项与 registry 不一致时报警；
2. 互斥元数据与命令构建结构断言（双侧非空/对称/multi/nargs/冲突拒绝）；
3. 中文示例全量回归（经 build_args + yt-dlp --simulate 实证，96 条）。

发布前三分钟人工快检：页面正常启动 →「全部选项」三态组 ≥40 → 切英文后全页无中文残留。

## 已知设计取舍

- URL 输入接受 http(s)、`ytsearch` 前缀与不含冒号的裸域名；其它 scheme/搜索前缀拒绝（安全面考虑）
- `--alias` / `--replace-in-metadata` / `--print-to-file` 为多参数选项，单输入框空格分隔表达（各段空格限制见界面提示）
- 界面隐藏纯 CLI 查询型选项（`--help`/`--dump-json` 等），白名单仍受理以兼容旧预设

## 将来扩展（macOS / iOS / Android）

后端 `services/` 不依赖任何 Web 框架类型，可整体移植；前端为无构建静态资源，可直接用 WKWebView / WebView / Android WebView 加载，或以 Tauri / Capacitor 封装。

## 文档

- 设计与任务：`docs/design.md`、`docs/tasks.md`（v1 至今全记录）
- QA：`docs/qa-report-1.md`（数据/逻辑层）、`docs/qa-ui-plan.md` + `docs/qa-ui-report.md`（UI 层 123 用例）

## 旧版

旧版（tkinter，仅 Windows、仅基础下载）见仓库 `ytdlpGUI@7c93372`。
