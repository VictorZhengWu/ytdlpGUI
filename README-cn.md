# yt-dlp GUI 视频下载器

[English](README.md)

## 项目简介

本项目为 [yt-dlp](https://github.com/yt-dlp/yt-dlp) 命令行视频下载工具的 Windows GUI 封装程序。用户只需在界面中粘贴视频链接，点击"下载"按钮即可完成视频下载，无需记忆命令行参数。支持中英文界面切换，支持通过设置对话框自定义下载目录和日志目录。

## 目录

- [项目简介](#项目简介)
- [程序设计思路](#程序设计思路)
  - [分层架构](#分层架构)
  - [关键技术决策](#关键技术决策)
- [文件结构](#文件结构)
- [模块说明](#模块说明)
  - [main.py — 程序入口](#mainpy--程序入口)
  - [gui.py — GUI 界面模块](#guipy--gui-界面模块)
  - [downloader.py — 下载核心模块](#downloaderpy--下载核心模块)
  - [logger.py — 日志记录模块](#loggerpy--日志记录模块)
  - [config.json — 配置文件](#configjson--配置文件)
- [使用方法](#使用方法)
  - [环境要求](#环境要求)
  - [运行程序](#运行程序)
  - [操作步骤](#操作步骤)
  - [语言切换](#语言切换)
  - [设置功能](#设置功能)
- [downloader.py 作为独立模块使用](#downloaderpy-作为独立模块使用)
- [注意事项](#注意事项)

## 程序设计思路

### 分层架构

程序采用**界面与功能分离**的三层架构设计：

```
┌─────────────────────────────────────┐
│   gui.py  (界面层)                   │  GUI 交互 + 设置对话框 + 多语言
└──────────┬──────────────────────────┘
           │ 调用
┌──────────▼──────────────────────────┐
│   downloader.py (核心层)             │  完全独立，无 GUI 依赖
│   logger.py    (日志层)              │  完全独立，无 GUI 依赖
└──────────┬──────────────────────────┘
           │ 调用
┌──────────▼──────────────────────────┐
│   core/yt-dlp.exe                   │  外部命令行工具
└─────────────────────────────────────┘
```

**核心设计原则**：
- `downloader.py` 不依赖任何 GUI 库（tkinter/PyQt 等），可作为独立模块被任何 Python 程序直接 `import` 使用
- `logger.py` 同样完全独立，不依赖 GUI 库
- 用户配置通过 `config.json` 持久化，启动时自动加载
- 多语言支持通过 `TRANSLATIONS` 翻译字典实现，切换语言时即时刷新所有界面文本

### 关键技术决策

| 决策项 | 方案 | 理由 |
|--------|------|------|
| GUI 库 | tkinter | Python 内置，零额外依赖 |
| 下载方式 | subprocess.Popen 调用 yt-dlp.exe | 直接使用提供的二进制文件 |
| 实时进度 | Popen + readline() + --newline | 逐行解析进度百分比 |
| 多线程 | threading.Thread | 防止下载过程中界面卡死 |
| 编码处理 | 自动检测系统编码 + errors='replace' | 兼容 Windows 中文环境 |
| 数据传递 | dataclass (DownloadResult) | 结构化返回值，无需第三方库 |
| 播放列表处理 | 截断 URL 中 "&" 之后的内容 | 模拟 CMD 命令行行为，与用户直接在 CMD 中运行 yt-dlp 的结果完全一致 |
| 日志排序 | 新日志插入文件最前面 | 最新的日志记录始终在最前面，方便查看 |
| 配置持久化 | config.json (JSON) | 轻量、可读、Python 标准库支持 |
| GUI 线程安全 | root.after() 调度到主线程 | tkinter 所有 GUI 操作必须在主线程执行 |
| 多语言 | TRANSLATIONS 字典 + t(key) 方法 | 零依赖，运行时即时切换，覆盖所有界面文本 |

## 文件结构

```
ytdlpGUI/
├── main.py          # 程序入口，加载配置，创建主窗口并启动主循环
├── gui.py           # GUI 界面模块（下载/设置按钮、语言切换、设置对话框、进度条）
├── downloader.py    # 下载核心模块（独立，无 GUI 依赖）
├── logger.py        # 日志记录模块（独立，无 GUI 依赖）
├── config.json      # 用户配置文件（下载目录、日志目录、界面语言）
├── README.md        # 英文说明文档
├── README-cn.md     # 中文说明文档
├── flow-en.md       # Mermaid 程序设计流程图（英文）
├── flow-cn.md       # Mermaid 程序设计流程图（中文）
├── tasks-en.md      # 任务清单（英文）
├── tasks-cn.md      # 任务清单（中文）
├── core/            # yt-dlp 及配套工具
│   ├── yt-dlp.exe
│   ├── ffmpeg.exe
│   ├── ffprobe.exe
│   └── ...
├── downloads/       # 视频下载存放目录（自动创建，可自定义）
└── logs/            # 日志文件存放目录（自动创建，可自定义）
```

## 模块说明

### main.py — 程序入口
- 加载 `config.json` 配置文件（不存在则使用默认值）
- 创建 tkinter 主窗口
- 创建 App 实例（传入配置字典）
- 启动 tkinter 主事件循环

### gui.py — GUI 界面模块
- `App` 类：管理主窗口界面和用户交互
- 包含 URL 输入框、"下载"按钮、"设置"按钮、语言选择下拉框、进度条、状态标签
- 输入框支持右键弹出菜单（粘贴、复制、清空）
- 下载在后台线程执行，不阻塞界面
- 进度条实时显示下载百分比（确定模式）或处理中动画（不确定模式）
- 下载完成后弹出成功/失败提示对话框
- 设置对话框支持自定义下载目录和日志目录，保存到 config.json
- 多语言支持：通过下拉框切换中文/英文，所有界面文本即时切换

### downloader.py — 下载核心模块
- `VideoDownloader` 类：封装 yt-dlp 调用逻辑
- `DownloadResult` 数据类：结构化返回下载结果
- 支持自定义 yt-dlp 路径、ffmpeg 路径和输出目录
- 截断 URL 中 `&` 之后的内容，模拟 Windows CMD 命令行行为
- 使用 Popen + readline() 实时解析下载进度
- `update_output_dir()` 方法支持运行时更改输出目录
- **完全不依赖任何 GUI 库**

### logger.py — 日志记录模块
- `Logger` 类：管理日志文件的创建和写入
- 按日期自动创建日志文件（如 `2026-03-28.log`）
- 支持 SUCCESS / ERROR / INFO 三种日志级别
- 日志按时间倒序排列，最新的日志记录始终在文件最前面
- `update_log_dir()` 方法支持运行时更改日志目录
- **完全不依赖任何 GUI 库**

### config.json — 配置文件
- JSON 格式，包含 `download_dir`、`log_dir` 和 `language` 三个键
- 默认值：`"downloads"`、`"logs"`、`"zh"`
- 程序启动时自动加载，设置对话框保存或语言切换时自动写入

## 使用方法

### 环境要求

- **操作系统**：Windows 7 及以上
- **Python**：Python 3.8 及以上
- **无额外依赖**：仅使用 Python 标准库（tkinter、subprocess、threading 等）

### 运行程序

```bash
python main.py
```

### 操作步骤

1. 运行程序后出现主窗口
2. 在文本输入框中粘贴视频链接（如 `https://www.youtube.com/watch?v=fnblCGXJqC8`）
3. 点击"下载"按钮（或按回车键）
4. 等待下载完成，弹出提示对话框
5. 下载的视频保存在 `downloads/` 目录下（默认，可通过设置修改）

### 语言切换

1. 在主窗口右上角找到语言选择下拉框
2. 点击下拉框，选择需要的语言（🇨🇳 中文 / 🇺🇸 English）
3. 界面所有文本立即切换为所选语言，包括按钮、菜单、状态提示和对话框
4. 语言设置自动保存到 config.json，下次启动时保持上次选择的语言

### 设置功能

1. 点击主窗口中的"设置"按钮
2. 在设置对话框中修改下载目录或日志目录
3. 可点击"浏览..."按钮通过目录选择器选择路径
4. 点击"保存"保存设置（配置写入 `config.json`，下次启动自动加载）
5. 点击"取消"放弃修改

## downloader.py 作为独立模块使用

`downloader.py` 可被任何 Python 程序直接调用：

```python
from downloader import VideoDownloader

# 使用默认配置（自动检测 core/ 目录）
dl = VideoDownloader()
result = dl.download("https://www.youtube.com/watch?v=xxx")

if result.success:
    print(f"下载成功: {result.video_path}")
else:
    print(f"下载失败: {result.error}")

# 自定义配置
dl = VideoDownloader(
    ytdlp_path="C:/tools/yt-dlp.exe",  # 自定义 yt-dlp 路径
    ffmpeg_path="C:/tools/",            # 自定义 ffmpeg 目录
    output_dir="C:/videos/"             # 自定义输出目录
)
result = dl.download("https://www.youtube.com/watch?v=xxx")

# 带进度回调
def on_progress(percent):
    if percent < 0:
        print("正在处理/合并...")
    else:
        print(f"下载进度: {percent:.1f}%")

result = dl.download("https://www.youtube.com/watch?v=xxx", progress_callback=on_progress)

# 运行时更新输出目录
dl.update_output_dir("D:/new_downloads")

# DownloadResult 数据类字段说明
# result.success   : bool   - 是否下载成功
# result.message   : str    - 结果描述
# result.output    : str    - yt-dlp 完整输出
# result.video_path: str    - 视频文件路径（成功时）
# result.error     : str    - 错误信息（失败时）
```

## 注意事项

1. 确保 `core/` 目录下有 `yt-dlp.exe` 和 `ffmpeg.exe`
2. 如果下载失败并出现 403 错误，可能是 yt-dlp 版本过旧，运行 `core\yt-dlp.exe --update` 更新
3. 下载的视频默认保存在程序目录下的 `downloads/` 文件夹，可通过设置对话框修改
4. 日志文件保存在 `logs/` 目录下，按日期命名，最新日志在最前面，可通过设置对话框修改
5. 程序使用系统默认编码读取 yt-dlp 输出，兼容中文 Windows 环境
6. 程序会自动截断 URL 中 `&` 之后的内容，模拟 Windows CMD 命令行行为，确保与用户在 CMD 中直接运行 yt-dlp 的下载结果一致
7. 设置保存到 `config.json` 文件，删除该文件将恢复所有默认配置（包括语言设置）
8. 日志内容始终使用英文，不受界面语言切换影响
9. 语言下拉框中的语言名称始终以本地语言显示（如"中文"始终显示为"中文"，不随界面语言变化）
