"""
程序入口模块 (main.py)
======================
功能：yt-dlp GUI 视频下载器的程序启动入口。
      加载配置文件（config.json），创建 tkinter 主窗口，
      初始化 GUI 应用程序并启动主事件循环。
      本文件是整个程序的启动点，用户通过运行本文件来启动程序。

使用方法：
    在命令行中执行：python main.py
"""

import os  # 导入操作系统接口模块，用于路径拼接
import json  # 导入 JSON 模块，用于读取和写入配置文件
import tkinter as tk  # 导入 tkinter 模块并简写为 tk，用于创建 GUI 主窗口
from gui import App  # 从 gui 模块中导入 App 类，即应用程序的主界面


# 程序默认配置（当 config.json 不存在或读取失败时使用此默认值）
DEFAULT_CONFIG = {  # 默认配置字典
    "download_dir": "downloads",  # 视频下载目录，默认为项目根目录下的 downloads/
    "log_dir": "logs",  # 日志文件目录，默认为项目根目录下的 logs/
    "language": "zh"  # 界面语言，默认为中文（"zh"=中文, "en"=英文）
}


def load_config():
    """
    加载配置文件
    ============
    功能：从项目根目录的 config.json 文件中读取用户配置。
          如果文件不存在或格式错误，则返回默认配置。
          配置文件中保存了用户自定义的下载目录和日志目录路径。

    返回：
        dict: 配置字典，包含 download_dir 和 log_dir 键
    """
    # 获取 config.json 的完整路径（与 main.py 同目录）
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")  # 拼接配置文件路径

    # 检查配置文件是否存在
    if not os.path.exists(config_path):  # 如果配置文件不存在
        return DEFAULT_CONFIG.copy()  # 返回默认配置的副本

    try:  # 尝试读取并解析配置文件
        with open(config_path, "r", encoding="utf-8") as f:  # 以 UTF-8 编码打开文件
            config = json.load(f)  # 解析 JSON 内容为字典
        # 确保配置字典中包含必要的键，缺失的使用默认值
        if "download_dir" not in config:  # 如果缺少 download_dir 键
            config["download_dir"] = DEFAULT_CONFIG["download_dir"]  # 使用默认下载目录
        if "log_dir" not in config:  # 如果缺少 log_dir 键
            config["log_dir"] = DEFAULT_CONFIG["log_dir"]  # 使用默认日志目录
        if "language" not in config:  # 如果缺少 language 键
            config["language"] = DEFAULT_CONFIG["language"]  # 使用默认语言（中文）
        return config  # 返回完整的配置字典
    except (json.JSONDecodeError, IOError):  # 捕获 JSON 解析错误和文件读取错误
        return DEFAULT_CONFIG.copy()  # 出错时返回默认配置的副本


def main():
    """
    主函数
    ======
    功能：程序的入口点。加载配置文件，创建 tkinter 主窗口和 GUI 应用程序实例，
          然后启动 tkinter 的主事件循环，等待用户交互。
          主循环会持续运行，直到用户关闭窗口。

    执行流程：
        1. 加载 config.json 配置文件
        2. 创建 tkinter 主窗口 (Tk 实例)
        3. 创建 App 实例（传入主窗口和配置参数）
        4. 启动 tkinter 主循环 (mainloop)
    """
    # 步骤1：加载配置文件（如果不存在则使用默认配置）
    config = load_config()  # 读取 config.json，获取用户自定义的目录路径

    # 步骤2：创建 tkinter 主窗口对象
    root = tk.Tk()  # 实例化 Tk 类，创建主窗口

    # 步骤3：创建应用程序实例，传入主窗口和配置参数
    app = App(root, config=config)  # 创建 App 实例，传入主窗口和配置字典

    # 步骤4：启动 tkinter 主事件循环
    # mainloop() 会持续监听事件（如鼠标点击、键盘输入等），直到窗口被关闭
    root.mainloop()  # 启动主循环，程序在此处阻塞，直到窗口关闭


# Python 的标准入口判断：仅当本文件被直接运行时才执行 main() 函数
# 如果本文件被其它模块 import，则不会自动执行 main()
if __name__ == "__main__":  # 检查当前文件是否作为主程序运行
    main()  # 调用主函数，启动程序
