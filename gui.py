"""
GUI 界面模块 (gui.py)
=====================
功能：提供 yt-dlp 视频下载器的图形用户界面。
      界面包含一个文本输入框（用于输入视频链接）、一个"下载"按钮、一个"设置"按钮、
      一个语言选择下拉框和一个进度条。
      输入框支持右键弹出菜单（粘贴、复制、清空）。
      点击"下载"按钮后，在后台线程中调用 downloader 模块执行下载任务，
      下载过程中进度条实时显示下载进度百分比。
      下载完成后弹出提示对话框通知用户结果。
      下载过程中按钮被禁用，防止用户重复点击。
      点击"设置"按钮打开设置对话框，可自定义下载目录和日志目录，
      设置保存到 config.json 文件中，下次启动时自动加载。
      支持中英文界面切换，语言选择保存到 config.json 中。
"""

import os  # 导入操作系统接口模块
import json  # 导入 JSON 模块，用于保存和读取配置文件
import threading  # 导入线程模块，用于在后台线程中执行下载任务，避免界面卡死
import tkinter as tk  # 导入 tkinter 模块并简写为 tk，用于创建 GUI 窗口和控件
from tkinter import messagebox, ttk, filedialog  # 导入消息对话框、ttk 控件和文件对话框模块

# 导入项目内的自定义模块
from downloader import VideoDownloader  # 导入视频下载器类，用于执行视频下载
from logger import Logger  # 导入日志记录器类，用于记录下载日志


# ---- 多语言翻译字典 ----
# 每个语言键（"zh" / "en"）下包含所有界面文本的翻译
TRANSLATIONS = {
    "zh": {
        # 窗口标题
        "title": "yt-dlp 视频下载器",
        # URL 输入区域
        "url_label": "视频链接：",
        # 按钮
        "download_btn": "下载",
        "downloading_btn": "下载中...",
        "settings_btn": "设置",
        # 右键菜单
        "paste": "粘贴",
        "copy": "复制",
        "clear": "清空",
        # 状态提示
        "status_downloading": "正在下载中，请稍候...",
        "status_processing": "正在处理视频（合并/转码）...",
        "status_complete": "下载完成！",
        "status_failed": "下载失败",
        "progress_format": "正在下载... {:.1f}%",
        # 警告对话框
        "warning_title": "提示",
        "warning_empty_url": "请输入视频链接！",
        # 下载成功对话框
        "success_title": "下载完成",
        "success_message": "视频下载成功！\n\n保存路径: {}",
        # 下载失败对话框
        "error_title": "下载失败",
        "error_message": "视频下载失败！\n\n错误信息: {}",
        # 设置对话框
        "settings_title": "设置",
        "download_dir_label": "下载目录：",
        "log_dir_label": "日志目录：",
        "browse_btn": "浏览...",
        "save_btn": "保存",
        "cancel_btn": "取消",
        "browse_download_title": "选择下载目录",
        "browse_log_title": "选择日志目录",
        "warning_empty_download_dir": "下载目录不能为空！",
        "warning_empty_log_dir": "日志目录不能为空！",
        "config_error_title": "错误",
        "config_save_error": "保存配置文件失败：{}",
        # 帮助菜单
        "help_menu": "帮助",
        "help_flow": "流程图",
        "help_readme": "说明文档",
        "help_open_error_title": "错误",
        "help_open_error": "无法打开文件：{}",
    },
    "en": {
        # Window title
        "title": "yt-dlp Video Downloader",
        # URL input area
        "url_label": "Video URL:",
        # Buttons
        "download_btn": "Download",
        "downloading_btn": "Downloading...",
        "settings_btn": "Settings",
        # Context menu
        "paste": "Paste",
        "copy": "Copy",
        "clear": "Clear",
        # Status messages
        "status_downloading": "Downloading, please wait...",
        "status_processing": "Processing video (merging/encoding)...",
        "status_complete": "Download complete!",
        "status_failed": "Download failed",
        "progress_format": "Downloading... {:.1f}%",
        # Warning dialog
        "warning_title": "Warning",
        "warning_empty_url": "Please enter a video URL!",
        # Success dialog
        "success_title": "Download Complete",
        "success_message": "Video downloaded successfully!\n\nSaved to: {}",
        # Error dialog
        "error_title": "Download Failed",
        "error_message": "Video download failed!\n\nError: {}",
        # Settings dialog
        "settings_title": "Settings",
        "download_dir_label": "Download Directory:",
        "log_dir_label": "Log Directory:",
        "browse_btn": "Browse...",
        "save_btn": "Save",
        "cancel_btn": "Cancel",
        "browse_download_title": "Select Download Directory",
        "browse_log_title": "Select Log Directory",
        "warning_empty_download_dir": "Download directory cannot be empty!",
        "warning_empty_log_dir": "Log directory cannot be empty!",
        "config_error_title": "Error",
        "config_save_error": "Failed to save configuration: {}",
        # Help menu
        "help_menu": "Help",
        "help_flow": "Flow Diagram",
        "help_readme": "README",
        "help_open_error_title": "Error",
        "help_open_error": "Cannot open file: {}",
    },
}

# 语言选项列表：(语言代码, 显示文本)
# 显示文本使用国旗 emoji + 本地语言名称，始终以各自语言显示（国际惯例）
LANG_OPTIONS = [
    ("zh", "\U0001F1E8\U0001F1F3 中文"),  # 🇨🇳 中文
    ("en", "\U0001F1FA\U0001F1F8 English"),  # 🇺🇸 English
]


class App:
    """
    GUI 应用程序类
    ==============
    功能：创建和管理 yt-dlp 视频下载器的主界面窗口。
          包含 URL 输入框、下载按钮、设置按钮、语言选择下拉框、进度条和状态提示标签。
          输入框支持右键弹出菜单（粘贴、复制、清空）。
          处理用户的下载请求，在后台线程中执行下载任务。
          下载过程中进度条实时显示下载进度。
          下载完成后根据结果显示成功或失败的提示对话框。
          支持通过设置对话框自定义下载目录和日志目录。
          支持中英文界面切换，语言设置持久化到 config.json。

    使用示例：
        root = tk.Tk()       # 创建 tkinter 主窗口
        app = App(root)      # 创建应用实例
        root.mainloop()      # 启动主循环
    """

    def __init__(self, root, config=None):
        """
        初始化 GUI 应用程序界面
        ========================
        功能：创建并布局所有界面控件，包括输入框、按钮、语言下拉框、进度条和状态标签。
              同时初始化下载器和日志记录器实例。
              根据传入的 config 字典配置下载目录、日志目录和界面语言。

        参数：
            root (tk.Tk): tkinter 的主窗口对象
            config (dict, optional): 配置字典，包含 download_dir、log_dir 和 language 键
        """
        # 保存主窗口对象的引用
        self.root = root  # 将传入的 Tk 根窗口保存为实例属性

        # 保存配置字典（如果未传入则使用空字典，后续使用默认值）
        self.config = config or {}  # 如果 config 为 None 则使用空字典

        # 获取项目根目录（gui.py 所在目录）
        self.base_dir = os.path.dirname(os.path.abspath(__file__))  # 获取脚本文件的绝对路径所在目录

        # ---- 语言设置 ----
        # 从配置中读取语言代码，默认为中文 "zh"
        self.current_lang = self.config.get("language", "zh")  # 获取语言设置，默认中文

        # ---- 下载状态跟踪 ----
        # 用于在切换语言时正确更新界面文本
        self._downloading = False  # 是否正在下载中
        self._processing = False  # 是否处于合并/处理阶段
        self._last_percent = 0.0  # 最近一次的下载进度百分比
        self._last_result_success = None  # 最近一次下载结果（True=成功, False=失败, None=无结果）

        # 从配置中获取下载目录和日志目录，未配置时使用默认值
        download_dir = self.config.get("download_dir", "downloads")  # 获取下载目录，默认 downloads
        log_dir = self.config.get("log_dir", "logs")  # 获取日志目录，默认 logs

        # 初始化视频下载器（传入配置的输出目录）
        self.downloader = VideoDownloader(output_dir=download_dir)  # 创建 VideoDownloader 实例

        # 初始化日志记录器（传入配置的日志目录）
        self.logger = Logger(log_dir=log_dir)  # 创建 Logger 实例

        # 记录程序启动日志（英文）
        self.logger.log_info("yt-dlp GUI application started")  # 写入启动信息到日志文件

        # ---- 窗口基本设置 ----
        # 设置窗口标题（使用当前语言）
        self.root.title(self.t("title"))  # 设置窗口标题栏显示的文本

        # 设置窗口大小（宽 x 高），并禁止调整窗口大小
        self.root.geometry("600x280")  # 600x280，包含进度条的空间
        self.root.resizable(False, False)  # 禁止用户调整窗口大小（宽和高均不可调）

        # 将窗口居中显示在屏幕上
        self._center_window(600, 280)  # 调用居中显示的辅助方法

        # ---- 创建菜单栏 ----
        self.menubar = tk.Menu(root)  # 创建菜单栏对象

        # 创建"帮助"菜单
        self.help_menu = tk.Menu(self.menubar, tearoff=0, font=("Microsoft YaHei", 10))  # 创建帮助子菜单
        self.help_menu.add_command(label=self.t("help_flow"), command=lambda: self._open_help_file("flow"))  # 流程图菜单项
        self.help_menu.add_command(label=self.t("help_readme"), command=lambda: self._open_help_file("readme"))  # 说明文档菜单项
        self.menubar.add_cascade(label=self.t("help_menu"), menu=self.help_menu)  # 将帮助菜单添加到菜单栏

        # 将菜单栏设置到主窗口
        root.config(menu=self.menubar)  # 设置窗口的菜单栏

        # ---- 创建界面控件 ----
        # 创建主容器框架，用于集中放置所有控件，设置内边距
        self.main_frame = tk.Frame(root, padx=20, pady=20)  # 创建框架，设置水平和垂直内边距各 20 像素
        self.main_frame.pack(fill=tk.BOTH, expand=True)  # 将框架放入窗口，填充所有空间

        # 创建 URL 输入提示标签（保存为实例属性，以便切换语言时更新）
        self.url_label = tk.Label(self.main_frame, text=self.t("url_label"), font=("Microsoft YaHei", 11))  # 创建标签控件
        self.url_label.pack(anchor=tk.W, pady=(0, 5))  # 将标签放入框架，左对齐，底部间距 5 像素

        # 创建 URL 输入框
        self.url_entry = tk.Entry(self.main_frame, font=("Microsoft YaHei", 11), width=50)  # 创建文本输入框
        self.url_entry.pack(fill=tk.X, pady=(0, 10))  # 将输入框放入框架，水平填充，底部间距 10 像素

        # 绑定回车键到下载功能（用户按回车也可以开始下载）
        self.url_entry.bind("<Return>", lambda event: self.on_download())  # 绑定 Enter 键事件

        # ---- 创建右键弹出菜单（粘贴、复制、清空） ----
        self.context_menu = tk.Menu(root, tearoff=0, font=("Microsoft YaHei", 10))  # 创建右键菜单
        self.context_menu.add_command(label=self.t("paste"), command=self._paste)  # 添加粘贴菜单项
        self.context_menu.add_command(label=self.t("copy"), command=self._copy)  # 添加复制菜单项
        self.context_menu.add_separator()  # 添加分隔线
        self.context_menu.add_command(label=self.t("clear"), command=self._clear)  # 添加清空菜单项
        self.url_entry.bind("<Button-3>", self._show_context_menu)  # 绑定右键点击事件到输入框

        # ---- 创建按钮框架（水平排列下载按钮、设置按钮和语言选择下拉框） ----
        self.btn_frame = tk.Frame(self.main_frame)  # 创建按钮容器框架
        self.btn_frame.pack(fill=tk.X, pady=(0, 10))  # 将按钮框架放入主框架，水平填充

        # 创建下载按钮
        self.download_btn = tk.Button(  # 创建下载按钮
            self.btn_frame,  # 父容器为按钮框架
            text=self.t("download_btn"),  # 按钮文本（使用当前语言）
            font=("Microsoft YaHei", 11),  # 字体：微软雅黑、11号
            command=self.on_download,  # 点击时调用下载方法
            width=10  # 按钮宽度为 10 个字符
        )
        self.download_btn.pack(side=tk.LEFT)  # 将下载按钮放在按钮框架左侧

        # 创建设置按钮
        self.settings_btn = tk.Button(  # 创建设置按钮
            self.btn_frame,  # 父容器为按钮框架
            text=self.t("settings_btn"),  # 按钮文本（使用当前语言）
            font=("Microsoft YaHei", 11),  # 字体：微软雅黑、11号
            command=self._open_settings,  # 点击时打开设置对话框
            width=10  # 按钮宽度为 10 个字符
        )
        self.settings_btn.pack(side=tk.LEFT, padx=(10, 0))  # 设置按钮放在下载按钮右侧，间距 10 像素

        # ---- 创建语言选择下拉框 ----
        # 构建下拉框的选项显示文本列表
        lang_display_values = [display for _, display in LANG_OPTIONS]  # 提取所有语言的显示文本

        # 创建语言字符串变量，设置为当前语言的显示文本
        self.lang_var = tk.StringVar()  # 创建字符串变量
        for code, display in LANG_OPTIONS:  # 遍历所有语言选项
            if code == self.current_lang:  # 如果是当前语言
                self.lang_var.set(display)  # 设置为当前语言的显示文本
                break  # 找到后跳出循环

        # 创建语言选择下拉框（只读模式，用户只能从列表中选择）
        self.lang_combo = ttk.Combobox(  # 创建 ttk 下拉框
            self.btn_frame,  # 父容器为按钮框架
            textvariable=self.lang_var,  # 绑定字符串变量
            values=lang_display_values,  # 下拉选项列表
            state="readonly",  # 只读模式（不允许手动输入）
            width=16,  # 宽度足以显示国旗+文字
            font=("Microsoft YaHei", 10)  # 字体
        )
        self.lang_combo.pack(side=tk.RIGHT)  # 将下拉框放在按钮框架右侧
        # 绑定下拉框选择变更事件
        self.lang_combo.bind("<<ComboboxSelected>>", self._on_language_change)  # 用户选择语言时触发

        # ---- 创建进度条 ----
        self.progress_bar = ttk.Progressbar(  # 创建 ttk 风格进度条控件
            self.main_frame,  # 父容器为主框架
            mode="determinate",  # 确定进度模式（显示具体百分比）
            maximum=100,  # 最大值为 100
            length=500  # 进度条长度为 500 像素
        )
        self.progress_bar.pack(fill=tk.X, pady=(5, 0))  # 将进度条放入框架，水平填充

        # 创建状态提示标签（初始为空文本，下载过程中会更新）
        self.status_label = tk.Label(  # 创建标签控件
            self.main_frame,  # 父容器为主框架
            text="",  # 初始文本为空
            font=("Microsoft YaHei", 9),  # 字体：微软雅黑、9号
            fg="#666666"  # 文字颜色为灰色
        )
        self.status_label.pack(anchor=tk.W, pady=(5, 0))  # 将标签放入框架，左对齐

        # 记录界面初始化完成的日志（英文）
        self.logger.log_info("GUI interface initialized")  # 写入界面初始化完成信息

    # ---- 多语言辅助方法 ----

    def t(self, key):
        """
        获取翻译文本
        ============
        功能：根据当前语言和键名，从翻译字典中获取对应的界面文本。
              如果当前语言中没有该键，则回退到中文；如果中文也没有，则返回键名本身。

        参数：
            key (str): 翻译键名

        返回：
            str: 对应语言的翻译文本
        """
        # 从当前语言的翻译字典中获取文本
        if self.current_lang in TRANSLATIONS:  # 如果当前语言存在于翻译字典中
            text = TRANSLATIONS[self.current_lang].get(key)  # 尝试获取翻译文本
            if text is not None:  # 如果找到了翻译
                return text  # 返回翻译文本
        # 回退到中文翻译
        fallback = TRANSLATIONS.get("zh", {}).get(key)  # 尝试从中文翻译中获取
        if fallback is not None:  # 如果中文翻译存在
            return fallback  # 返回中文翻译
        # 最终回退：返回键名本身
        return key  # 返回键名作为兜底

    def _on_language_change(self, event):
        """
        语言选择变更事件处理
        ====================
        功能：当用户从下拉框中选择新的语言时触发。
              更新当前语言代码，刷新界面所有文本，
              将语言设置保存到 config.json，并记录日志。
        """
        # 获取用户选择的显示文本
        selected_display = self.lang_var.get()  # 获取下拉框当前选中的文本

        # 根据显示文本查找对应的语言代码
        new_lang = self.current_lang  # 默认保持当前语言
        for code, display in LANG_OPTIONS:  # 遍历所有语言选项
            if display == selected_display:  # 如果显示文本匹配
                new_lang = code  # 获取对应的语言代码
                break  # 找到后跳出循环

        # 如果语言没有变化，不需要做任何操作
        if new_lang == self.current_lang:  # 判断新旧语言是否相同
            return  # 相同则直接返回

        # 更新当前语言
        self.current_lang = new_lang  # 更新实例的语言代码属性

        # 刷新界面所有文本
        self._refresh_ui()  # 调用界面刷新方法

        # 将语言设置保存到配置字典
        self.config["language"] = new_lang  # 更新配置中的语言设置

        # 立即将配置写入 config.json 文件
        self._save_config()  # 调用配置保存方法

        # 记录语言变更日志（英文）
        self.logger.log_info(f"Language changed to: {new_lang}")  # 写入语言变更日志

    def _refresh_ui(self):
        """
        刷新界面所有文本
        ================
        功能：根据当前语言更新界面中所有控件的文本内容。
              包括窗口标题、标签、按钮、右键菜单和状态提示。
              下载过程中切换语言时，会根据当前下载状态显示正确的翻译文本。
        """
        # 更新窗口标题
        self.root.title(self.t("title"))  # 设置窗口标题为当前语言

        # 更新 URL 输入提示标签
        self.url_label.config(text=self.t("url_label"))  # 更新标签文本

        # 更新按钮文本（根据当前是否正在下载显示不同文本）
        if self._downloading:  # 如果正在下载中
            self.download_btn.config(text=self.t("downloading_btn"))  # 显示"下载中..."文本
        else:  # 如果不在下载中
            self.download_btn.config(text=self.t("download_btn"))  # 显示正常"下载"文本

        # 更新设置按钮文本
        self.settings_btn.config(text=self.t("settings_btn"))  # 更新设置按钮文本

        # 更新右键菜单项文本
        self.context_menu.entryconfig(0, label=self.t("paste"))  # 更新粘贴菜单项
        self.context_menu.entryconfig(1, label=self.t("copy"))  # 更新复制菜单项
        self.context_menu.entryconfig(3, label=self.t("clear"))  # 更新清空菜单项（索引3因为索引2是分隔线）

        # 根据下载状态更新状态标签文本
        if self._downloading:  # 如果正在下载中
            if self._processing:  # 如果处于合并/处理阶段
                self.status_label.config(text=self.t("status_processing"), fg="#FF9800")  # 显示处理中提示
            else:  # 如果处于正常下载阶段
                self.status_label.config(  # 显示下载进度百分比
                    text=self.t("progress_format").format(self._last_percent),  # 格式化进度文本
                    fg="#FF9800"  # 橙色
                )
        elif self._last_result_success is True:  # 如果最近一次下载成功
            self.status_label.config(text=self.t("status_complete"), fg="#4CAF50")  # 显示成功提示（绿色）
        elif self._last_result_success is False:  # 如果最近一次下载失败
            self.status_label.config(text=self.t("status_failed"), fg="#F44336")  # 显示失败提示（红色）

        # 更新帮助菜单项文本
        self.help_menu.entryconfig(0, label=self.t("help_flow"))  # 更新流程图菜单项
        self.help_menu.entryconfig(1, label=self.t("help_readme"))  # 更新说明文档菜单项
        # 菜单栏上的级联菜单无法直接用 entryconfig 修改 label，需删除后重新添加
        self.menubar.delete(0, tk.END)  # 删除菜单栏上所有级联项（不影响子菜单对象）
        self.menubar.add_cascade(label=self.t("help_menu"), menu=self.help_menu)  # 重新添加帮助菜单

    def _open_help_file(self, name):
        """
        打开帮助文档文件
        ================
        功能：根据当前界面语言选择对应版本的 Markdown 文件并打开。
              英文界面打开 -en 版本，中文界面打开 -cn 版本。
              优先使用系统默认的 Markdown 阅览器打开；
              如果系统没有关联 .md 文件的阅览器，则以纯文本模式（记事本）打开。

        参数：
            name (str): 文件基本名称，"flow" 或 "readme"
        """
        # 根据文件类型和当前语言确定文件名
        # README 特殊处理：英文版为 README.md（GitHub 默认首页），中文版为 README-cn.md
        # flow/tasks 文件保持原名格式：xxx-cn.md / xxx-en.md
        if name == "readme":  # README 文件使用特殊命名规则
            filename = "README-cn.md" if self.current_lang == "zh" else "README.md"  # 根据语言选择 README 文件
        else:  # 其它文档文件（如 flow）使用标准后缀命名
            suffix = "-cn" if self.current_lang == "zh" else "-en"  # 选择语言后缀
            filename = f"{name.lower()}{suffix}.md"  # 构造文件名

        # 拼接文件的完整绝对路径
        file_path = os.path.join(self.base_dir, filename)  # 获取绝对路径

        # 检查文件是否存在
        if not os.path.exists(file_path):  # 如果文件不存在
            messagebox.showerror(  # 弹出错误提示
                self.t("help_open_error_title"),  # 标题
                self.t("help_open_error").format(filename),  # 消息
            )
            return  # 直接返回

        try:  # 尝试用系统默认程序打开文件
            # os.startfile() 是 Windows 专用方法，使用 Windows Shell 关联打开文件
            # 如果系统安装了 Markdown 阅览器（如 Typora、VSCode 等），会使用该阅览器打开
            os.startfile(file_path)  # 使用默认关联程序打开
        except OSError:  # 如果系统没有关联 .md 文件的程序（startfile 失败）
            try:  # 回退方案：使用记事本以纯文本模式打开
                os.startfile(file_path, "open")  # 尝试以"打开"操作启动
            except OSError:  # 如果仍然失败
                # 最终回退：直接调用 notepad.exe 打开
                import subprocess  # 导入子进程模块
                subprocess.Popen(["notepad", file_path])  # 用记事本打开

    def _save_config(self):
        """
        保存配置到 config.json 文件
        ============================
        功能：将当前内存中的配置字典写入 config.json 文件。
              此方法可被多处调用（语言切换时、设置对话框保存时），
              避免重复的文件写入代码。
        """
        # 拼接配置文件路径
        config_path = os.path.join(self.base_dir, "config.json")  # 拼接完整路径
        try:  # 尝试写入配置文件
            with open(config_path, "w", encoding="utf-8") as f:  # 以写入模式打开
                json.dump(self.config, f, indent=4, ensure_ascii=False)  # 写入 JSON（缩进4空格，保留中文）
        except IOError:  # 捕获文件写入错误
            pass  # 静默忽略（语言切换时不应弹窗打断用户）

    def _center_window(self, width, height):
        """
        将窗口居中显示在屏幕上
        =======================
        功能：计算窗口在屏幕上的居中位置，并设置窗口的几何属性。
              使窗口在启动时显示在屏幕正中央。

        参数：
            width (int): 窗口的宽度（像素）
            height (int): 窗口的高度（像素）
        """
        # 获取屏幕的宽度和高度（像素）
        screen_width = self.root.winfo_screenwidth()  # 获取屏幕总宽度
        screen_height = self.root.winfo_screenheight()  # 获取屏幕总高度

        # 计算窗口左上角的 x 和 y 坐标，使窗口居中
        x = (screen_width - width) // 2  # 水平居中：(屏幕宽 - 窗口宽) / 2
        y = (screen_height - height) // 2  # 垂直居中：(屏幕高 - 窗口高) / 2

        # 设置窗口的几何属性（位置和大小）
        self.root.geometry(f"{width}x{height}+{x}+{y}")  # 格式：宽x高+x偏移+y偏移

    # ---- 右键菜单相关方法 ----

    def _show_context_menu(self, event):
        """
        显示右键弹出菜单
        ==================
        功能：在输入框上点击鼠标右键时，在鼠标位置弹出上下文菜单。
              菜单包含"粘贴"、"复制"和"清空"三个操作选项。

        参数：
            event: tkinter 鼠标事件对象
        """
        try:  # 尝试显示菜单
            self.context_menu.tk_popup(event.x_root, event.y_root)  # 在鼠标右键点击位置弹出菜单
        finally:  # 确保菜单最终被取消聚焦
            self.context_menu.grab_release()  # 释放菜单的鼠标抓取

    def _paste(self):
        """
        粘贴操作
        ========
        功能：将系统剪贴板中的文本内容粘贴到输入框中。
              用于替代手动 Ctrl+V 操作。
        """
        try:  # 尝试获取剪贴板内容
            clipboard_content = self.root.clipboard_get()  # 从系统剪贴板获取文本
            self.url_entry.insert(tk.INSERT, clipboard_content)  # 在光标位置插入剪贴板内容
        except tk.TclError:  # 如果剪贴板为空或不可读取
            pass  # 忽略异常，不做任何操作

    def _copy(self):
        """
        复制操作
        ========
        功能：将输入框中选中的文本复制到系统剪贴板。
              用于替代手动 Ctrl+C 操作。
        """
        try:  # 尝试获取选中的文本
            selected_text = self.url_entry.selection_get()  # 获取输入框中被选中的文本
            if selected_text:  # 如果有文本被选中
                self.root.clipboard_clear()  # 清空系统剪贴板
                self.root.clipboard_append(selected_text)  # 将选中的文本追加到剪贴板
        except tk.TclError:  # 如果没有选中的文本
            pass  # 忽略异常

    def _clear(self):
        """
        清空操作
        ========
        功能：清空输入框中的所有文本内容，同时清空状态提示标签和重置状态跟踪。
        """
        self.url_entry.delete(0, tk.END)  # 删除从位置 0 到末尾的所有文本
        self.status_label.config(text="")  # 同时清空状态提示标签
        self._last_result_success = None  # 重置下载结果状态

    # ---- 设置对话框相关方法 ----

    def _open_settings(self):
        """
        打开设置对话框
        ==============
        功能：创建一个 Toplevel 窗口作为设置对话框，允许用户自定义下载目录和日志目录。
              对话框包含两个目录路径输入框，每个输入框旁边有"浏览..."按钮用于选择目录。
              底部有"保存"和"取消"按钮。
              所有文本使用当前选择的语言显示。
              点击"保存"时，更新下载器和日志记录器的目录，并将配置写入 config.json。
        """
        # 创建设置对话框窗口
        settings_win = tk.Toplevel(self.root)  # 创建 Toplevel 子窗口
        settings_win.title(self.t("settings_title"))  # 设置对话框标题（使用当前语言）
        settings_win.geometry("500x220")  # 设置对话框大小
        settings_win.resizable(False, False)  # 禁止调整对话框大小
        settings_win.transient(self.root)  # 设置为父窗口的临时窗口（始终在父窗口前面）
        settings_win.grab_set()  # 捕获所有输入事件（模态对话框，阻止操作主窗口）

        # 将对话框居中显示在主窗口上方
        settings_win.update_idletasks()  # 更新窗口以获取准确尺寸
        main_x = self.root.winfo_x()  # 获取主窗口的 x 坐标
        main_y = self.root.winfo_y()  # 获取主窗口的 y 坐标
        main_w = self.root.winfo_width()  # 获取主窗口的宽度
        main_h = self.root.winfo_height()  # 获取主窗口的高度
        dlg_x = main_x + (main_w - 500) // 2  # 计算对话框 x 坐标使居中
        dlg_y = main_y + (main_h - 220) // 2  # 计算对话框 y 坐标使居中
        settings_win.geometry(f"+{dlg_x}+{dlg_y}")  # 设置对话框位置

        # 创建对话框内部框架，带内边距
        dlg_frame = tk.Frame(settings_win, padx=20, pady=20)  # 创建内边距 20 像素的框架
        dlg_frame.pack(fill=tk.BOTH, expand=True)  # 填充对话框空间

        # ---- 下载目录设置行 ----
        dl_label = tk.Label(dlg_frame, text=self.t("download_dir_label"), font=("Microsoft YaHei", 10))  # 创建标签
        dl_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 10))  # 放在第 0 行第 0 列

        # 下载目录输入框，初始值从配置获取
        dl_var = tk.StringVar(value=self.config.get("download_dir", "downloads"))  # 创建字符串变量
        dl_entry = tk.Entry(dlg_frame, textvariable=dl_var, font=("Microsoft YaHei", 10), width=35)  # 创建输入框
        dl_entry.grid(row=0, column=1, padx=(5, 5), pady=(0, 10), sticky=tk.EW)  # 放在第 0 行第 1 列

        # 下载目录"浏览..."按钮
        def browse_download_dir():  # 定义浏览下载目录的回调函数
            selected = filedialog.askdirectory(  # 弹出目录选择对话框
                title=self.t("browse_download_title"),  # 对话框标题（使用当前语言）
                initialdir=os.path.join(self.base_dir, dl_var.get())  # 初始目录
            )
            if selected:  # 如果用户选择了目录（未取消）
                dl_var.set(selected)  # 将选择的路径设置到输入框

        dl_browse_btn = tk.Button(  # 创建浏览按钮
            dlg_frame,  # 父容器
            text=self.t("browse_btn"),  # 按钮文本（使用当前语言）
            font=("Microsoft YaHei", 9),  # 字体
            command=browse_download_dir  # 点击时调用浏览回调
        )
        dl_browse_btn.grid(row=0, column=2, pady=(0, 10))  # 放在第 0 行第 2 列

        # ---- 日志目录设置行 ----
        log_label = tk.Label(dlg_frame, text=self.t("log_dir_label"), font=("Microsoft YaHei", 10))  # 创建标签
        log_label.grid(row=1, column=0, sticky=tk.W, pady=(0, 10))  # 放在第 1 行第 0 列

        # 日志目录输入框，初始值从配置获取
        log_var = tk.StringVar(value=self.config.get("log_dir", "logs"))  # 创建字符串变量
        log_entry = tk.Entry(dlg_frame, textvariable=log_var, font=("Microsoft YaHei", 10), width=35)  # 创建输入框
        log_entry.grid(row=1, column=1, padx=(5, 5), pady=(0, 10), sticky=tk.EW)  # 放在第 1 行第 1 列

        # 日志目录"浏览..."按钮
        def browse_log_dir():  # 定义浏览日志目录的回调函数
            selected = filedialog.askdirectory(  # 弹出目录选择对话框
                title=self.t("browse_log_title"),  # 对话框标题（使用当前语言）
                initialdir=os.path.join(self.base_dir, log_var.get())  # 初始目录
            )
            if selected:  # 如果用户选择了目录（未取消）
                log_var.set(selected)  # 将选择的路径设置到输入框

        log_browse_btn = tk.Button(  # 创建浏览按钮
            dlg_frame,  # 父容器
            text=self.t("browse_btn"),  # 按钮文本（使用当前语言）
            font=("Microsoft YaHei", 9),  # 字体
            command=browse_log_dir  # 点击时调用浏览回调
        )
        log_browse_btn.grid(row=1, column=2, pady=(0, 10))  # 放在第 1 行第 2 列

        # 配置网格列的权重，使第 1 列（输入框）可以水平拉伸
        dlg_frame.columnconfigure(1, weight=1)  # 第 1 列权重为 1，可拉伸

        # ---- 底部按钮框架 ----
        btn_frame = tk.Frame(dlg_frame)  # 创建底部按钮容器
        btn_frame.grid(row=2, column=0, columnspan=3, pady=(10, 0))  # 放在第 2 行，跨 3 列

        def save_settings():  # 定义保存设置的回调函数
            """保存设置：更新下载器和日志记录器的目录，写入 config.json"""
            new_download_dir = dl_var.get().strip()  # 获取下载目录输入框的值并去空格
            new_log_dir = log_var.get().strip()  # 获取日志目录输入框的值并去空格

            # 校验：目录路径不能为空
            if not new_download_dir:  # 如果下载目录为空
                messagebox.showwarning(  # 弹出警告
                    self.t("warning_title"),  # 标题（使用当前语言）
                    self.t("warning_empty_download_dir"),  # 消息（使用当前语言）
                    parent=settings_win  # 父窗口为设置对话框
                )
                return  # 不保存，直接返回
            if not new_log_dir:  # 如果日志目录为空
                messagebox.showwarning(  # 弹出警告
                    self.t("warning_title"),  # 标题（使用当前语言）
                    self.t("warning_empty_log_dir"),  # 消息（使用当前语言）
                    parent=settings_win  # 父窗口为设置对话框
                )
                return  # 不保存，直接返回

            # 更新下载器的输出目录
            self.downloader.update_output_dir(new_download_dir)  # 调用下载器方法更新目录

            # 更新日志记录器的目录
            self.logger.update_log_dir(new_log_dir)  # 调用日志记录器方法更新目录

            # 更新内存中的配置字典
            self.config["download_dir"] = new_download_dir  # 更新配置中的下载目录
            self.config["log_dir"] = new_log_dir  # 更新配置中的日志目录

            # 将配置写入 config.json 文件
            config_path = os.path.join(self.base_dir, "config.json")  # 拼接配置文件路径
            try:  # 尝试写入配置文件
                with open(config_path, "w", encoding="utf-8") as f:  # 以写入模式打开
                    json.dump(self.config, f, indent=4, ensure_ascii=False)  # 写入 JSON
            except IOError as e:  # 捕获文件写入错误
                messagebox.showerror(  # 弹出错误提示
                    self.t("config_error_title"),  # 标题（使用当前语言）
                    self.t("config_save_error").format(e),  # 消息（使用当前语言）
                    parent=settings_win  # 父窗口
                )
                return  # 不关闭对话框

            # 记录设置变更日志（英文）
            self.logger.log_info(f"Settings updated - download_dir: {new_download_dir}, log_dir: {new_log_dir}")

            # 关闭设置对话框
            settings_win.destroy()  # 销毁对话框窗口

        # 创建保存按钮
        save_btn = tk.Button(  # 创建保存按钮
            btn_frame,  # 父容器
            text=self.t("save_btn"),  # 按钮文本（使用当前语言）
            font=("Microsoft YaHei", 10),  # 字体
            command=save_settings,  # 点击时调用保存回调
            width=8  # 按钮宽度
        )
        save_btn.pack(side=tk.LEFT, padx=(0, 10))  # 放在左侧

        # 创建取消按钮
        cancel_btn = tk.Button(  # 创建取消按钮
            btn_frame,  # 父容器
            text=self.t("cancel_btn"),  # 按钮文本（使用当前语言）
            font=("Microsoft YaHei", 10),  # 字体
            command=settings_win.destroy,  # 点击时关闭对话框
            width=8  # 按钮宽度
        )
        cancel_btn.pack(side=tk.LEFT)  # 放在保存按钮右侧

    # ---- 下载相关方法 ----

    def on_download(self):
        """
        下载按钮点击事件处理函数
        ========================
        功能：当用户点击"下载"按钮或按回车键时触发。
              获取输入框中的 URL，进行基本验证后，
              禁用下载按钮，重置进度条，启动后台线程执行下载任务。
              下载完成后由后台线程回调恢复界面状态。
        """
        # 获取输入框中的 URL 文本
        url = self.url_entry.get()  # 从 Entry 控件中获取用户输入的文本

        # 校验 URL 是否为空
        if not url or not url.strip():  # 如果 URL 为空或仅含空白字符
            messagebox.showwarning(self.t("warning_title"), self.t("warning_empty_url"))  # 弹出警告对话框
            return  # 提前返回，不执行后续下载操作

        # 重置进度条为初始状态
        self.progress_bar.stop()  # 停止可能正在运行的不确定模式动画
        self.progress_bar.configure(value=0, mode="determinate")  # 重置为 0%，确定进度模式

        # 设置下载状态跟踪
        self._downloading = True  # 标记为下载中
        self._processing = False  # 重置处理状态
        self._last_percent = 0.0  # 重置进度百分比
        self._last_result_success = None  # 重置下载结果

        # 更新状态标签，提示用户正在下载
        self.status_label.config(text=self.t("status_downloading"), fg="#FF9800")  # 更新状态文本为橙色

        # 禁用下载按钮、设置按钮和输入框，防止下载过程中用户重复操作
        self.download_btn.config(state=tk.DISABLED, text=self.t("downloading_btn"))  # 禁用按钮并更改文字
        self.settings_btn.config(state=tk.DISABLED)  # 禁用设置按钮
        self.url_entry.config(state=tk.DISABLED)  # 禁用输入框

        # 记录用户发起下载请求的日志（英文）
        self.logger.log_info(f"Download requested: {url}")  # 写入下载请求日志

        # 创建后台线程执行下载任务
        download_thread = threading.Thread(  # 创建新的线程对象
            target=self._do_download,  # 线程执行的目标函数
            args=(url,),  # 传递给目标函数的参数（URL）
            daemon=True  # 设置为守护线程（主程序退出时线程自动终止）
        )
        download_thread.start()  # 启动后台线程，开始执行下载任务

    def _do_download(self, url):
        """
        在后台线程中执行下载任务
        ========================
        功能：在工作线程中调用 VideoDownloader 执行实际的视频下载。
              传入 progress_callback 函数，实时报告下载进度百分比。
              下载完成后，通过 root.after() 方法将界面更新操作
              调度回主线程执行（tkinter 的 GUI 操作必须在主线程中进行）。

        参数：
            url (str): 要下载的视频 URL
        """
        # 定义进度回调闭包：在工作线程中接收进度值，通过 root.after() 调度到主线程更新进度条
        def progress_callback(percent):  # 进度回调函数（闭包，可访问 self）
            if percent < 0:  # percent < 0 表示进入不确定模式（合并/处理阶段）
                self.root.after(0, lambda: self._set_progress_indeterminate())  # 调度到主线程切换为不确定模式
            else:  # percent >= 0 表示正常下载进度百分比
                self.root.after(0, lambda p=percent: self._update_progress(p))  # 调度到主线程更新进度条值

        # 调用下载器执行下载，并传入进度回调函数
        result = self.downloader.download(url, progress_callback=progress_callback)  # 传入进度回调

        # 记录下载结果到日志
        if result.success:  # 如果下载成功
            self.logger.log_success(url, result.video_path)  # 记录成功日志（含视频路径）
        else:  # 如果下载失败
            self.logger.log_error(url, result.error)  # 记录失败日志（含错误信息）

        # 使用 root.after() 将界面更新操作调度回主线程执行
        self.root.after(0, self._on_download_complete, result)  # 在主线程中调用回调函数

    def _update_progress(self, percent):
        """
        在主线程中更新进度条的值（确定模式）
        ======================================
        功能：将进度条设置为指定的百分比值，并更新状态标签显示百分比文字。

        参数：
            percent (float): 下载进度百分比 (0.0 ~ 100.0)
        """
        # 更新下载状态跟踪
        self._processing = False  # 确定模式表示正在下载，非处理阶段
        self._last_percent = percent  # 记录当前进度百分比

        self.progress_bar.stop()  # 停止可能正在运行的不确定模式动画
        self.progress_bar.configure(value=percent, mode="determinate")  # 设置进度条值和确定模式
        self.status_label.config(text=self.t("progress_format").format(percent), fg="#FF9800")  # 更新状态标签

    def _set_progress_indeterminate(self):
        """
        在主线程中将进度条设置为不确定模式
        ======================================
        功能：切换进度条为不确定模式（脉冲滚动动画），
              用于合并/处理等无法确定具体进度的阶段。
        """
        # 更新下载状态跟踪
        self._processing = True  # 标记为处理阶段

        self.progress_bar.configure(mode="indeterminate")  # 切换为不确定模式
        self.progress_bar.start(15)  # 启动脉冲动画，每 15 毫秒移动一次
        self.status_label.config(text=self.t("status_processing"), fg="#FF9800")  # 更新状态标签

    def _on_download_complete(self, result):
        """
        下载完成后的界面更新回调
        ========================
        功能：在主线程中执行下载完成后的界面更新操作。
              重置进度条为初始状态，恢复按钮和输入框的可用状态。
              根据下载结果显示成功或失败的提示对话框。

        参数：
            result (DownloadResult): 下载结果对象
        """
        # 更新下载状态跟踪
        self._downloading = False  # 标记下载结束
        self._processing = False  # 标记处理结束

        # 重置进度条为初始状态
        self.progress_bar.stop()  # 停止不确定模式的脉冲动画
        self.progress_bar.configure(value=0, mode="determinate")  # 重置为 0%，确定模式

        # 恢复下载按钮、设置按钮和输入框的可用状态
        self.download_btn.config(state=tk.NORMAL, text=self.t("download_btn"))  # 恢复下载按钮
        self.settings_btn.config(state=tk.NORMAL)  # 恢复设置按钮
        self.url_entry.config(state=tk.NORMAL)  # 恢复输入框

        # 根据下载结果更新界面和弹出提示
        if result.success:  # 如果下载成功
            # 更新状态标签为成功信息（绿色）
            self._last_result_success = True  # 记录下载成功
            self.status_label.config(text=self.t("status_complete"), fg="#4CAF50")  # 绿色成功提示
            # 弹出成功提示对话框
            messagebox.showinfo(  # 弹出信息对话框
                self.t("success_title"),  # 标题（使用当前语言）
                self.t("success_message").format(result.video_path)  # 消息（使用当前语言）
            )
        else:  # 如果下载失败
            # 更新状态标签为失败信息（红色）
            self._last_result_success = False  # 记录下载失败
            self.status_label.config(text=self.t("status_failed"), fg="#F44336")  # 红色失败提示
            # 弹出错误提示对话框
            messagebox.showerror(  # 弹出错误对话框
                self.t("error_title"),  # 标题（使用当前语言）
                self.t("error_message").format(result.error)  # 消息（使用当前语言）
            )
