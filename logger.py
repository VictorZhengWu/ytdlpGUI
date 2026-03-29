"""
日志记录模块 (logger.py)
========================
功能：提供日志记录功能，将下载过程中的成功和失败信息写入日志文件。
      日志文件按日期命名，存放在 logs/ 目录下。
      本模块不依赖任何 GUI 库，可被任何 Python 程序独立调用。
"""

import os  # 导入操作系统接口模块，用于路径操作和目录创建
from datetime import datetime  # 导入日期时间模块，用于获取当前时间戳和日期


class Logger:
    """
    日志记录器类
    ============
    功能：管理日志文件的创建和写入，支持不同级别的日志记录。
          每次程序运行时，会自动创建以当前日期命名的日志文件。
          日志文件存放在指定的日志目录下（默认为 logs/）。

    使用示例：
        logger = Logger()                    # 创建日志记录器，默认日志目录为 logs/
        logger.log_success(url, "下载完成")   # 记录成功日志
        logger.log_error(url, "网络超时")     # 记录错误日志
    """

    def __init__(self, log_dir="logs"):
        """
        初始化日志记录器
        ================
        功能：创建日志目录（如不存在），并设置日志文件路径。
              日志文件以当前日期命名，格式为 YYYY-MM-DD.log。

        参数：
            log_dir (str): 日志文件存放的目录路径，默认为 "logs"
        """
        # 获取当前 Python 脚本所在的目录（即项目根目录）
        self.base_dir = os.path.dirname(os.path.abspath(__file__))  # 获取脚本文件的绝对路径所在目录

        # 拼接完整的日志目录路径（项目根目录/logs）
        self.log_dir = os.path.join(self.base_dir, log_dir)  # 将基础目录和日志子目录拼接为完整路径

        # 如果日志目录不存在，则创建它
        if not os.path.exists(self.log_dir):  # 检查日志目录是否存在
            os.makedirs(self.log_dir)  # 递归创建日志目录（包括父目录）

        # 获取当前日期，格式为 YYYY-MM-DD
        today = datetime.now().strftime("%Y-%m-%d")  # 将当前日期格式化为字符串

        # 拼接日志文件的完整路径（logs/YYYY-MM-DD.log）
        self.log_file = os.path.join(self.log_dir, f"{today}.log")  # 将日志目录和文件名拼接为完整路径

    def update_log_dir(self, new_dir):
        """
        更新日志文件的存放目录
        =======================
        功能：在运行时动态更改日志保存目录（例如用户通过设置界面修改）。
              更新后，后续的日志将写入新目录下以当前日期命名的新日志文件。
              如果新目录不存在会自动创建。

        参数：
            new_dir (str): 新的日志目录路径（可以是相对路径或绝对路径）
        """
        # 如果传入的是相对路径，则基于项目根目录拼接为绝对路径
        if not os.path.isabs(new_dir):  # 判断是否为绝对路径
            new_dir = os.path.join(self.base_dir, new_dir)  # 拼接为绝对路径

        # 更新日志目录属性
        self.log_dir = new_dir  # 将日志目录设置为新路径

        # 如果新目录不存在则自动创建
        if not os.path.exists(self.log_dir):  # 检查新目录是否存在
            os.makedirs(self.log_dir)  # 递归创建新目录

        # 更新日志文件路径为新目录下以当前日期命名的文件
        today = datetime.now().strftime("%Y-%m-%d")  # 获取当前日期字符串
        self.log_file = os.path.join(self.log_dir, f"{today}.log")  # 拼接新的日志文件完整路径

    def log(self, level, message):
        """
        写入一条日志记录
        ================
        功能：将带时间戳和级别的日志消息写入日志文件的最前面（最新的日志在文件顶部）。
              每条日志的格式为：[YYYY-MM-DD HH:MM:SS] [LEVEL] message
              新日志始终插入文件开头，按时间倒序排列，方便查看最新记录。

        参数：
            level (str): 日志级别，如 "INFO"、"SUCCESS"、"ERROR"
            message (str): 日志消息内容
        """
        # 获取当前时间，格式为 YYYY-MM-DD HH:MM:SS
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # 格式化当前时间为可读字符串

        # 拼接完整的日志行：[时间戳] [级别] 消息内容
        log_line = f"[{timestamp}] [{level}] {message}\n"  # 使用 f-string 拼接日志行并换行

        # 读取现有日志文件的内容（如果文件存在）
        existing_content = ""  # 初始化变量用于保存已有日志内容
        if os.path.exists(self.log_file):  # 检查日志文件是否已存在
            with open(self.log_file, "r", encoding="utf-8") as f:  # 以只读模式打开文件
                existing_content = f.read()  # 读取全部已有内容

        # 将新日志行插入到文件最前面（新日志在前，旧日志在后）
        with open(self.log_file, "w", encoding="utf-8") as f:  # 以写入模式打开文件（会覆盖原文件）
            f.write(log_line)  # 先写入新的日志行
            f.write(existing_content)  # 再写入之前的所有旧日志内容

    def log_success(self, url, details=""):
        """
        记录下载成功日志
        ================
        功能：将视频下载成功的消息写入日志文件，包括视频 URL 和详细信息。

        参数：
            url (str): 成功下载的视频 URL
            details (str): 额外的详细信息，如文件路径等，默认为空字符串
        """
        # 拼接成功日志消息：URL + 详细信息
        message = f"Download succeeded | URL: {url}"  # 构建包含 URL 的基本消息（英文）
        if details:  # 如果有额外的详细信息
            message += f" | Details: {details}"  # 将详细信息追加到消息末尾（英文）

        # 调用通用日志方法，级别为 "SUCCESS"
        self.log("SUCCESS", message)  # 写入成功级别的日志

    def log_error(self, url, error_msg):
        """
        记录下载失败日志
        ================
        功能：将视频下载失败的消息写入日志文件，包括视频 URL 和错误信息。

        参数：
            url (str): 下载失败的视频 URL
            error_msg (str): 错误详情信息
        """
        # 拼接错误日志消息：URL + 错误信息
        message = f"Download failed | URL: {url} | Error: {error_msg}"  # 构建包含 URL 和错误信息的消息（英文）

        # 调用通用日志方法，级别为 "ERROR"
        self.log("ERROR", message)  # 写入错误级别的日志

    def log_info(self, message):
        """
        记录一般信息日志
        ================
        功能：将一般性的程序运行信息写入日志文件。

        参数：
            message (str): 信息内容
        """
        # 调用通用日志方法，级别为 "INFO"
        self.log("INFO", message)  # 写入信息级别的日志
