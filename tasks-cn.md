# yt-dlp GUI 程序 — 任务清单

## 一、程序总体要求

1. 基于 Python 3 + tkinter 开发 Windows 平台 GUI 程序
2. 界面包含：一个文本输入框（粘贴视频链接）+ 一个"下载"按钮 + 一个"设置"按钮 + 语言选择下拉框
3. 界面参考 `UI.jpg`
4. 下载功能与界面功能严格分离，`downloader.py` 不依赖任何 GUI 库，可作为独立模块被其它程序 import 调用
5. 下载的视频存放在当前目录的 `downloads/` 子目录下（可通过设置自定义）
6. 用日志文件记录下载成功或失败状况
7. 下载中出现问题需报错并给出错误提示
8. 下载完成后给出完成提示
9. 程序代码需有详细注释（功能块注释 + 尽可能每行注释）
10. 用 Mermaid 格式文件单独保存程序设计流程图
11. 提供 `README.md` 总结程序设计思路和使用方法
12. 仅下载单个视频文件，即使 URL 中包含播放列表参数（如 `&list=...`），也只下载目标视频
13. 日志按时间倒序排列，最新的日志记录始终在日志文件的最前面
14. 支持通过设置对话框自定义下载目录和日志目录，配置持久化到 `config.json`
15. 支持中英文界面切换，语言选择通过下拉框操作，选择后所有界面文本即时切换，语言设置持久化到 `config.json`

---

## 二、项目文件结构

```
ytdlpGUI/
├── main.py          # 程序入口（加载配置，创建窗口，启动主循环）
├── gui.py           # GUI 界面模块（下载/设置按钮、语言切换、设置对话框、进度条）
├── downloader.py    # 下载核心模块（独立，无 GUI 依赖）
├── logger.py        # 日志记录模块（独立，无 GUI 依赖）
├── config.json      # 用户配置文件（下载目录、日志目录、界面语言）
├── flow.md          # Mermaid 流程图
├── README.md        # 项目说明文档
├── tasks.md         # 本文件
├── core/            # yt-dlp 及配套工具（已有）
│   ├── yt-dlp.exe
│   ├── ffmpeg.exe
│   ├── ffprobe.exe
│   └── ...
├── downloads/       # 视频下载存放目录（运行时自动创建，可自定义）
└── logs/            # 日志文件存放目录（运行时自动创建，可自定义）
```

---

## 三、子任务清单

### 任务 1：下载核心模块 `downloader.py`

- [x] 定义 `DownloadResult` 数据类（success / message / output / video_path / error）
- [x] 实现 `VideoDownloader` 类
  - [x] `__init__(self, ytdlp_path, ffmpeg_path, output_dir)` — 初始化路径，支持自定义和自动检测
  - [x] `validate_url(self, url)` — URL 基本格式校验（非空、含协议头）
  - [x] `download(self, url, output_dir=None, progress_callback=None)` — 核心下载方法
    - [x] 拼接 yt-dlp.exe 完整路径（`core/yt-dlp.exe`）
    - [x] 构建 subprocess 命令参数（路径、ffmpeg 位置、输出目录、URL、--newline）
    - [x] 使用 Popen + readline() 实时读取输出，解析进度百分比
    - [x] 截断 URL 中 "&" 之后的内容，模拟 Windows CMD 命令行行为
    - [x] 1 小时超时定时器
    - [x] 返回 `DownloadResult` 结构化结果
  - [x] `update_output_dir(self, new_dir)` — 运行时更新下载目录
  - [x] `_parse_progress(self, line, progress_callback)` — 解析进度信息
  - [x] `_extract_video_path(self, stdout, save_dir)` — 提取视频文件路径
- [x] 确保本模块不 import 任何 GUI 库（tkinter / PyQt 等）
- [x] 确保可被其它 Python 程序直接 `from downloader import VideoDownloader` 使用

### 任务 2：日志记录模块 `logger.py`

- [x] 实现 `Logger` 类
  - [x] `__init__(self, log_dir)` — 创建日志目录，以日期命名日志文件（如 `2026-03-28.log`）
  - [x] `log(self, level, message)` — 写入时间戳 + 级别 + 消息（新日志插入文件最前面，按时间倒序）
  - [x] `log_success(self, url, details)` — 记录下载成功信息
  - [x] `log_error(self, url, error_msg)` — 记录下载失败信息 + 错误详情
  - [x] `log_info(self, message)` — 记录一般信息
  - [x] `update_log_dir(self, new_dir)` — 运行时更新日志目录
- [x] 日志按时间倒序排列，最新的日志记录始终在文件最前面

### 任务 3：GUI 界面模块 `gui.py`

- [x] 实现 `App` 类
  - [x] `__init__(self, root, config=None)` — 初始化窗口
    - [x] 设置窗口标题（根据当前语言）
    - [x] 设置窗口大小并居中显示
    - [x] 创建 URL 文本输入框（Entry）
    - [x] 创建"下载"按钮（Button）
    - [x] 创建"设置"按钮（Button）
    - [x] 创建语言选择下拉框（ttk.Combobox，国旗+文字）
    - [x] 创建进度条（ttk.Progressbar，支持确定/不确定模式）
    - [x] 创建状态提示标签（Label）
    - [x] 根据传入的 config 字典配置下载目录、日志目录和语言
  - [x] `t(self, key)` — 翻译辅助方法，根据当前语言获取界面文本
  - [x] `_refresh_ui(self)` — 切换语言后刷新所有界面文本
  - [x] `_on_language_change(self, event)` — 语言下拉框选择变更事件处理
    - [x] 更新 current_lang
    - [x] 调用 _refresh_ui 刷新界面
    - [x] 调用 _save_config 保存到 config.json
  - [x] `on_download(self)` — 下载按钮点击事件处理
    - [x] 获取输入框中的 URL
    - [x] 验证 URL 是否为空
    - [x] 禁用下载按钮和设置按钮（防止重复操作）
    - [x] 创建后台线程调用 `VideoDownloader.download()`
    - [x] 传入 progress_callback 实时更新进度条
  - [x] `_do_download(self, url)` — 后台线程执行下载
    - [x] 通过 root.after() 调度 GUI 更新到主线程
  - [x] `_on_download_complete(self, result)` — 下载完成回调
    - [x] 恢复按钮和输入框状态
    - [x] 根据结果显示成功/失败对话框
  - [x] `_open_settings(self)` — 设置对话框
    - [x] 创建 Toplevel 模态对话框，所有文本使用当前语言
    - [x] 下载目录输入框 + "浏览..." 按钮（filedialog.askdirectory）
    - [x] 日志目录输入框 + "浏览..." 按钮（filedialog.askdirectory）
    - [x] 保存按钮：更新下载器和日志记录器目录，写入 config.json
    - [x] 取消按钮：关闭对话框
  - [x] `_save_config(self)` — 保存配置到 config.json（可多处复用）
  - [x] 右键弹出菜单（粘贴、复制、清空，文本随语言切换）
  - [x] 进度条实时显示（百分比模式 + 不确定模式）
  - [x] 下载状态跟踪（_downloading / _processing / _last_percent）支持语言切换时正确更新

### 任务 4：多语言支持

- [x] 定义 `TRANSLATIONS` 翻译字典（zh / en 两种语言）
- [x] 定义 `LANG_OPTIONS` 语言选项列表（国旗 emoji + 本地语言名称）
- [x] 覆盖所有界面文本：窗口标题、标签、按钮、菜单、状态提示、对话框标题和内容
- [x] 语言下拉框使用 ttk.Combobox（只读模式）
- [x] 语言名称始终以本地语言显示（中文/English，不随界面语言变化）
- [x] 切换语言后立即刷新界面所有文本（包括下载状态文本）
- [x] 语言选择保存到 config.json（`language` 键），立即写入
- [x] 程序启动时从 config.json 加载语言设置

### 任务 5：程序入口 `main.py`

- [x] 加载 config.json 配置文件
- [x] DEFAULT_CONFIG 包含 language 键（默认 "zh"）
- [x] 创建 tkinter 主窗口
- [x] 初始化 `App`（传入配置字典）
- [x] 启动 tkinter 主循环（`mainloop()`）

### 任务 6：配置文件 `config.json`

- [x] JSON 格式，包含 download_dir、log_dir 和 language 键
- [x] 默认值：`"downloads"`、`"logs"`、`"zh"`
- [x] 程序启动时加载（不存在则使用默认值）
- [x] 设置对话框保存时写入
- [x] 语言切换时立即写入

### 任务 7：Mermaid 流程图 `flow.md`

- [x] 绘制程序整体执行流程图（含配置加载、语言设置、设置流程）
- [x] 绘制模块调用关系图
- [x] 绘制类结构关系图（含多语言相关属性和方法）
- [x] 绘制下载流程序列图（含 Popen + readline 循环）
- [x] 绘制设置流程序列图
- [x] 绘制语言切换流程序列图

### 任务 8：README.md 文档

- [x] 程序简介
- [x] 程序设计思路（分层架构说明）
- [x] 文件结构说明（含 config.json）
- [x] 使用方法
  - [x] 环境要求（Python 3 版本）
  - [x] 运行命令
  - [x] 操作步骤（含设置功能和语言切换说明）
- [x] `downloader.py` 作为独立模块被其它程序调用的示例代码
- [x] 配置文件说明（含 language 键）
- [x] 注意事项

### 任务 9：代码注释

- [x] 每个模块文件顶部添加文件功能说明注释
- [x] 每个类、函数添加功能说明注释
- [x] 尽可能每行代码后添加行内注释

---

## 四、关键设计决策（已确认）

| 决策项 | 方案 |
|--------|------|
| GUI 库 | tkinter（零额外依赖） |
| 下载与界面分离 | downloader.py 完全独立，无 GUI 依赖 |
| 多线程 | 下载在单独线程中执行，防止界面卡死 |
| 视频存放 | `downloads/` 子目录，运行时自动创建，可通过设置自定义 |
| 日志存放 | `logs/` 子目录，按日期命名，运行时自动创建，可通过设置自定义 |
| 日志排序 | 最新日志在文件最前面（时间倒序） |
| 日志语言 | 日志内容始终使用英文（不受界面语言切换影响） |
| yt-dlp 调用方式 | subprocess.Popen 调用 `core/yt-dlp.exe`，使用 readline() 逐行读取 |
| ffmpeg 路径 | 通过 `--ffmpeg-location` 参数指定 `core/` |
| 进度解析 | 使用 `--newline` 标志，Popen + readline() 逐行解析百分比 |
| 播放列表处理 | 截断 URL 中 "&" 之后的内容，模拟 CMD 命令行行为 |
| 编码处理 | 自动检测系统编码 + errors='replace'，兼容 Windows 中文环境 |
| 配置持久化 | config.json（JSON 格式），启动时加载，设置/语言切换时保存 |
| 进度条模式 | 下载百分比用 determinate 模式，合并/转码用 indeterminate 模式 |
| GUI 线程安全 | 所有 tkinter 操作通过 root.after() 调度到主线程 |
| 多语言方案 | TRANSLATIONS 字典 + t(key) 方法 + _refresh_ui() 刷新 |
| 语言选项显示 | 国旗 emoji + 本地语言名称（始终以本地语言显示，不随界面语言变化） |
| 语言持久化 | config.json 的 language 键，切换时立即保存 |
