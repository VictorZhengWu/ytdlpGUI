# 需求规格（Requirements）

## 1. 背景

ytdlpGUI 旧版（commit 7c93372）基于 Python tkinter，仅支持 Windows，只有"输入 URL → 下载"的最小功能。
新版目标：跨 **Web / Linux / Windows** 运行，覆盖 **yt-dlp 全部命令行选项**，并为将来 macOS / iOS / Android 客户端预留扩展点。

## 2. 功能需求

### FR-1 选项全覆盖
- 程序内提供 yt-dlp `--help` 所列全部选项（250 项，17 个分类），分类沿用 yt-dlp 官方分节（General / Network / Video Selection / … / Extractor）。
- 选项注册表由脚本 `scripts/generate_registry.py` 从 `yt-dlp --help` 自动生成（`backend/app/data/options_registry.json`），升级 yt-dlp 后可重新生成，无需改代码。

### FR-2 下载核心
- 提交一个或多个 URL，按当前勾选/填写的选项组合构建 yt-dlp 命令行并执行。
- 实时进度（百分比、速度、ETA）与实时日志输出。
- 支持取消正在运行的任务。
- 支持多任务队列（顺序执行，避免并发抢占带宽）。

### FR-3 元数据查询
- 输入 URL 后可先查询视频信息（标题、时长、可用格式列表），辅助选择 `-f` 格式。

### FR-4 预设（Presets）
- 用户可将当前选项组合保存为命名预设，可加载、删除，持久化到本地 JSON。

### FR-5 命令预览
- 界面实时显示当前选项生成的完整 yt-dlp 命令行，便于学习与排错。

### FR-6 选项检索
- 提供选项搜索框（按 flag / 描述过滤），在 250 个选项中快速定位。

### FR-7 界面
- 中英文双语界面（沿用旧版 i18n 思路）。
- 下载目录可配置并持久化（config.json）。

### FR-8 跨平台运行
- Linux / Windows：`run.sh` / `run.bat` 启动本地服务并自动打开浏览器；亦支持纯服务器部署（Web 版，供局域网访问）。
- 后端与前端之间只通过 HTTP API + SSE 通信，未来 macOS/iOS/Android 客户端可直接复用同一后端 API 与前端静态资源（WebView 嵌入）。

## 3. 非功能需求

- **NFR-1 界面与功能严格分离**：前端不含任何业务逻辑（只做渲染与 API 调用）；后端不含任何界面代码（纯 REST/SSE 服务），downloader 服务可脱离 HTTP 层独立 import 使用（沿用旧版 downloader.py 的独立性原则）。
- **NFR-2 安全**：后端对用户提交的选项做白名单校验（只允许注册表内的 flag），阻止任意参数注入；URL 必须以 http(s) 或支持的前缀开头。
- **NFR-3 零构建前端**：纯 HTML/CSS/JS，无 node 构建链，便于嵌入各平台 WebView。
- **NFR-4 可测试**：核心服务（命令构建、进度解析）为纯函数/纯类，可单测。

## 4. 交付物

- `docs/` SDD 三件套（requirements / design / tasks）
- `backend/` FastAPI 服务 + 选项注册表数据
- `frontend/` 静态界面
- `run.sh` / `run.bat` / `README.md`
