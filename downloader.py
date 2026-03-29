"""
下载核心模块 (downloader.py)
============================
功能：封装 yt-dlp 命令行工具的调用，提供视频下载功能。
      本模块是完全独立的，不依赖任何 GUI 库（tkinter / PyQt 等），
      可被任何 Python 程序直接 import 使用。

使用示例：
    from downloader import VideoDownloader

    dl = VideoDownloader()                                    # 使用默认配置
    result = dl.download("https://www.youtube.com/watch?v=xxx")  # 下载视频
    if result.success:
        print(f"下载完成: {result.video_path}")
    else:
        print(f"下载失败: {result.error}")
"""

import os  # 导入操作系统接口模块，用于路径拼接和目录操作
import subprocess  # 导入子进程模块，用于调用外部命令行程序
import re  # 导入正则表达式模块，用于 URL 格式校验和进度百分比提取
import locale  # 导入区域设置模块，用于获取系统默认编码
import threading  # 导入线程模块，用于实现下载超时定时器
from dataclasses import dataclass  # 导入数据类装饰器，用于定义结构化的返回结果


@dataclass
class DownloadResult:
    """
    下载结果数据类
    ==============
    功能：以结构化的方式保存视频下载的结果信息。
          使用 Python 内置的 dataclass 装饰器，无需第三方依赖。

    属性：
        success (bool): 下载是否成功，True=成功，False=失败
        message (str): 下载结果的简要描述信息（如"下载成功"或"下载失败: xxx"）
        output (str): yt-dlp 命令的完整标准输出和标准错误输出
        video_path (str): 下载成功后的视频文件完整路径，失败时为空字符串
        error (str): 下载失败时的错误信息，成功时为空字符串
    """
    success: bool = False  # 下载是否成功，默认为 False
    message: str = ""  # 结果描述消息，默认为空字符串
    output: str = ""  # yt-dlp 的完整输出内容，默认为空字符串
    video_path: str = ""  # 下载后的视频文件路径，默认为空字符串
    error: str = ""  # 错误信息，默认为空字符串


class VideoDownloader:
    """
    视频下载器类
    ============
    功能：封装 yt-dlp 命令行工具，提供简洁的 Python 接口进行视频下载。
          支持自定义 yt-dlp 路径、ffmpeg 路径和输出目录。
          本类不依赖任何 GUI 库，可作为独立模块被其它程序调用。

    使用示例：
        # 方式一：使用默认配置（自动检测 core/ 目录）
        dl = VideoDownloader()
        result = dl.download("https://www.youtube.com/watch?v=xxx")

        # 方式二：自定义路径
        dl = VideoDownloader(
            ytdlp_path="C:/tools/yt-dlp.exe",
            ffmpeg_path="C:/tools/",
            output_dir="C:/videos/"
        )
        result = dl.download("https://www.youtube.com/watch?v=xxx")
    """

    def __init__(self, ytdlp_path=None, ffmpeg_path=None, output_dir=None):
        """
        初始化视频下载器
        ================
        功能：设置 yt-dlp 和 ffmpeg 的路径，以及视频输出目录。
              如果未指定路径，则自动检测程序同级 core/ 目录下的工具。

        参数：
            ytdlp_path (str, optional): yt-dlp.exe 的完整路径，默认为 None（自动检测）
            ffmpeg_path (str, optional): ffmpeg 所在目录路径，默认为 None（自动检测）
            output_dir (str, optional): 视频下载的输出目录，默认为 None（使用 downloads/）
        """
        # 获取当前 Python 脚本所在的目录（即项目根目录）
        self.base_dir = os.path.dirname(os.path.abspath(__file__))  # 获取脚本文件的绝对路径所在目录

        # 设置 yt-dlp.exe 的路径
        if ytdlp_path:  # 如果调用者提供了自定义的 yt-dlp 路径
            self.ytdlp_path = ytdlp_path  # 使用调用者提供的路径
        else:  # 如果未提供，则自动检测 core/ 目录
            self.ytdlp_path = os.path.join(self.base_dir, "core", "yt-dlp.exe")  # 拼接默认路径

        # 设置 ffmpeg 所在目录的路径
        if ffmpeg_path:  # 如果调用者提供了自定义的 ffmpeg 路径
            self.ffmpeg_path = ffmpeg_path  # 使用调用者提供的路径
        else:  # 如果未提供，则自动检测 core/ 目录
            self.ffmpeg_path = os.path.join(self.base_dir, "core")  # 拼接默认的 ffmpeg 目录

        # 设置视频下载的输出目录
        if output_dir:  # 如果调用者提供了自定义的输出目录
            self.output_dir = output_dir  # 使用调用者提供的目录
        else:  # 如果未提供，则使用默认的 downloads/ 目录
            self.output_dir = os.path.join(self.base_dir, "downloads")  # 拼接默认输出目录

        # 确保输出目录存在（如果不存在则自动创建）
        if not os.path.exists(self.output_dir):  # 检查输出目录是否存在
            os.makedirs(self.output_dir)  # 递归创建输出目录

    def update_output_dir(self, new_dir):
        """
        更新视频下载的输出目录
        =======================
        功能：在运行时动态更改视频保存目录（例如用户通过设置界面修改）。
              如果新目录不存在会自动创建。

        参数：
            new_dir (str): 新的输出目录路径（可以是相对路径或绝对路径）
        """
        # 如果传入的是相对路径，则基于项目根目录拼接为绝对路径
        if not os.path.isabs(new_dir):  # 判断是否为绝对路径
            new_dir = os.path.join(self.base_dir, new_dir)  # 拼接为绝对路径

        # 更新实例属性为新目录
        self.output_dir = new_dir  # 将输出目录设置为新路径

        # 如果新目录不存在则自动创建
        if not os.path.exists(self.output_dir):  # 检查新目录是否存在
            os.makedirs(self.output_dir)  # 递归创建新目录

    def validate_url(self, url):
        """
        校验 URL 格式
        =============
        功能：对用户输入的 URL 进行基本格式校验。
              检查 URL 是否非空，是否以 http:// 或 https:// 开头。
              注意：本方法仅做基本格式校验，不验证 URL 是否真实可访问。

        参数：
            url (str): 待校验的视频 URL 字符串

        返回：
            tuple: (is_valid, error_message)
                   - is_valid (bool): URL 是否合法
                   - error_message (str): 如果不合法，返回错误描述；合法时为空字符串
        """
        # 检查 URL 是否为 None 或去除空格后为空字符串
        if not url or not url.strip():  # 判断 URL 是否为空或仅含空白字符
            return False, "URL 不能为空"  # 返回校验失败及错误信息

        # 去除 URL 首尾的空白字符
        url = url.strip()  # 使用 strip() 去除首尾空格、换行等

        # 使用正则表达式检查 URL 是否以 http:// 或 https:// 开头
        url_pattern = r'^https?://'  # 正则表达式：以 http:// 或 https:// 开头
        if not re.match(url_pattern, url):  # 如果 URL 不匹配正则表达式
            return False, "URL 格式不正确，必须以 http:// 或 https:// 开头"  # 返回校验失败及错误信息

        # 所有校验通过，返回成功
        return True, ""  # 返回校验成功，无错误信息

    def download(self, url, output_dir=None, progress_callback=None):
        """
        下载视频
        ========
        功能：调用 yt-dlp 命令行工具下载指定 URL 的视频。
              使用 Popen 实时读取 yt-dlp 输出，解析下载进度百分比，
              通过 progress_callback 回调函数实时报告进度。
              下载完成后返回结构化的 DownloadResult 对象。

        参数：
            url (str): 视频页面的 URL 地址
            output_dir (str, optional): 本次下载的临时输出目录，默认为 None（使用初始化时的目录）
            progress_callback (callable, optional): 进度回调函数，接收一个 float 参数 (0.0-100.0)
                                                  传入 -1 时表示进入不确定模式（如合并/处理阶段）

        返回：
            DownloadResult: 包含下载结果信息的数据对象
        """
        # 去除 URL 首尾的空白字符
        url = url.strip()  # 使用 strip() 去除首尾空格和换行符

        # 步骤1：校验 URL 格式
        is_valid, error_msg = self.validate_url(url)  # 调用校验方法检查 URL
        if not is_valid:  # 如果 URL 格式校验不通过
            return DownloadResult(  # 返回一个失败的结果对象
                success=False,  # 标记为下载失败
                message=f"URL validation failed: {error_msg}",  # 设置失败描述信息（英文）
                error=error_msg  # 设置错误详情
            )

        # 步骤2：确定本次下载使用的输出目录
        save_dir = output_dir if output_dir else self.output_dir  # 优先使用参数指定的目录

        # 确保输出目录存在
        if not os.path.exists(save_dir):  # 检查输出目录是否存在
            os.makedirs(save_dir)  # 如果不存在则创建

        # 步骤3：构建 yt-dlp 的输出文件名模板（包含目录路径）
        output_template = os.path.join(save_dir, "%(title)s.%(ext)s")  # 输出路径：目录/标题.扩展名

        # 步骤4：截断 URL 中 "&" 之后的内容，模拟 Windows CMD 的行为
        clean_url = url.split("&")[0]  # 以 "&" 为分隔符取第一段，模拟 CMD 对 "&" 的截断行为

        # 步骤5：构建 yt-dlp 命令行参数列表
        command = [  # 将所有命令行参数组织为列表形式
            self.ytdlp_path,  # yt-dlp.exe 的完整路径
            "--ffmpeg-location", self.ffmpeg_path,  # 指定 ffmpeg 所在目录
            "--newline",  # 强制 yt-dlp 每行进度输出使用换行符（而非 \r 回车符），便于逐行解析进度
            "-o", output_template,  # 指定输出文件的命名模板
            "--no-warnings",  # 抑制警告信息的输出
            clean_url  # 截断后的视频 URL（与 CMD 命令行行为一致）
        ]

        try:
            # 步骤6：获取系统默认编码（Windows 中文系统通常为 gbk/cp936）
            system_encoding = locale.getpreferredencoding() or "utf-8"  # 获取系统首选编码，兜底使用 utf-8

            # 步骤7：使用 Popen 启动 yt-dlp 进程，以二进制模式读取输出（便于逐行解码）
            proc = subprocess.Popen(  # 启动子进程
                command,  # 命令及参数列表
                stdout=subprocess.PIPE,  # 将标准输出重定向到管道，用于实时读取
                stderr=subprocess.STDOUT  # 将标准错误合并到标准输出，统一读取
            )

            # 步骤8：设置超时定时器（1小时），超时后自动终止进程
            def kill_process():  # 定义超时回调函数
                try:  # 尝试终止进程
                    proc.kill()  # 强制终止 yt-dlp 进程
                except OSError:  # 如果进程已结束（无需终止）
                    pass  # 忽略异常

            timer = threading.Timer(3600, kill_process)  # 创建 3600 秒（1 小时）的超时定时器
            timer.daemon = True  # 设置为守护线程，不阻止程序退出
            timer.start()  # 启动定时器

            # 步骤9：逐行读取 yt-dlp 的输出，实时解析下载进度
            # 使用 readline() 逐行读取（而非逐字节），确保多字节编码字符（如中文 GBK）完整解码
            full_output = ""  # 初始化变量，用于保存完整的命令输出
            while True:  # 循环读取输出，直到进程结束
                line_bytes = proc.stdout.readline()  # 从管道中读取一行（二进制）
                if not line_bytes:  # 如果读取到 EOF（进程已结束）
                    break  # 退出循环
                # 将完整的一行用系统编码解码（整行解码，避免多字节字符被截断导致乱码）
                line = line_bytes.decode(system_encoding, errors="replace")  # 解码为字符串
                full_output += line  # 将该行追加到完整输出中
                # 解析该行中的进度信息
                self._parse_progress(line, progress_callback)  # 调用进度解析方法

            # 等待进程完全结束并获取返回码
            proc.wait()  # 阻塞等待进程结束

            # 取消超时定时器（进程已正常结束）
            timer.cancel()  # 取消定时器

            # 步骤10：根据 yt-dlp 的返回码判断下载是否成功
            if proc.returncode == 0:  # 返回码为 0 表示下载成功
                # 尝试从输出中提取下载的文件路径
                video_path = self._extract_video_path(full_output, save_dir)  # 调用辅助方法提取路径

                return DownloadResult(  # 返回成功的结果对象
                    success=True,  # 标记为下载成功
                    message=f"Video downloaded successfully: {url}",  # 设置成功描述信息（英文）
                    output=full_output,  # 保存完整的命令输出
                    video_path=video_path,  # 保存下载的视频文件路径
                    error=""  # 成功时无错误信息
                )
            else:  # 返回码非 0 表示下载失败
                # 从完整输出中提取错误信息（取最后几行）
                error_lines = [l for l in full_output.strip().split("\n") if l.strip()]  # 过滤空行
                error_text = error_lines[-1].strip() if error_lines else f"yt-dlp returned error code: {proc.returncode}"  # 取最后一行作为错误信息

                return DownloadResult(  # 返回失败的结果对象
                    success=False,  # 标记为下载失败
                    message=f"Video download failed: {url}",  # 设置失败描述信息（英文）
                    output=full_output,  # 保存完整的命令输出（含错误信息）
                    video_path="",  # 失败时无视频路径
                    error=error_text  # 设置错误详情
                )

        except subprocess.TimeoutExpired:  # 捕获子进程超时异常
            return DownloadResult(  # 返回超时的结果对象
                success=False,  # 标记为下载失败
                message=f"Download timed out: {url}",  # 设置超时描述信息（英文）
                error="Download timed out, exceeded maximum wait time (1 hour)"  # 设置错误详情（英文）
            )

        except Exception as e:  # 捕获其他所有未预期的异常
            return DownloadResult(  # 返回异常的结果对象
                success=False,  # 标记为下载失败
                message=f"Error during download: {url}",  # 设置错误描述信息（英文）
                error=str(e)  # 将异常对象转为字符串作为错误详情
            )

    def _parse_progress(self, line, progress_callback):
        """
        解析 yt-dlp 输出行中的进度信息
        ==================================
        功能：从 yt-dlp 的一行输出文本中提取下载进度百分比或处理状态，
              通过 progress_callback 回调函数报告进度。
              回调参数：0.0-100.0 表示下载百分比，-1 表示不确定模式（合并/处理阶段）。

        参数：
            line (str): yt-dlp 的一行输出文本
            progress_callback (callable or None): 进度回调函数，为 None 时不报告进度
        """
        # 如果没有提供回调函数，则直接返回不做解析
        if not progress_callback:  # 检查回调函数是否为 None
            return  # 无回调，跳过进度解析

        # 去除首尾空白字符
        line = line.strip()  # 使用 strip() 去除空格和换行符
        if not line:  # 如果行为空
            return  # 跳过空行

        # 尝试匹配下载进度百分比，如 "[download]  45.2% of  50.27MiB at 10.5MiB/s ETA 00:05"
        percent_match = re.search(r"\[download\]\s+([\d.]+)%", line)  # 正则匹配百分比数字
        if percent_match:  # 如果匹配到百分比
            try:  # 尝试转换为浮点数
                percent = float(percent_match.group(1))  # 提取并转换为浮点数
                progress_callback(percent)  # 通过回调报告进度百分比
            except (ValueError, Exception):  # 转换失败时忽略
                pass  # 忽略异常，不影响下载流程
            return  # 已处理，直接返回

        # 检测合并/处理阶段（如 [Merger]、[ExtractAudio] 等）
        if "[Merger]" in line or "[ExtractAudio]" in line:  # 如果检测到合并或提取音频的关键字
            progress_callback(-1)  # 报告 -1，表示进入不确定模式（GUI 可切换为滚动进度条）
            return  # 已处理，直接返回

    def _extract_video_path(self, stdout, save_dir):
        """
        从 yt-dlp 输出中提取已下载视频的文件路径
        ==========================================
        功能：解析 yt-dlp 的标准输出，尝试找到下载完成的视频文件路径。
              yt-dlp 在下载成功后通常会输出 "Destination:" 或 "has already" 等信息。

        参数：
            stdout (str): yt-dlp 的标准输出文本
            save_dir (str): 视频保存的目录路径

        返回：
            str: 提取到的视频文件完整路径，如果无法提取则返回 save_dir
        """
        # 按 newline 拆分输出为行列表
        lines = stdout.strip().split("\n") if stdout else []  # 如果 stdout 为空则使用空列表

        # 从最后一行开始反向遍历，查找包含文件路径的行
        for line in reversed(lines):  # 反向遍历输出行（文件路径通常出现在末尾）
            # 查找包含 "Destination:" 的行（yt-dlp 下载成功后的输出格式）
            if "Destination:" in line:  # 检查当前行是否包含 "Destination:" 关键字
                # 提取 "Destination:" 之后的文件路径
                parts = line.split("Destination:", 1)  # 以 "Destination:" 为分隔符拆分，最多拆分一次
                if len(parts) > 1:  # 如果拆分成功（即确实存在 "Destination:"）
                    path = parts[1].strip()  # 取第二部分并去除首尾空格
                    # 检查路径是否为绝对路径
                    if os.path.isabs(path):  # 如果提取的路径已经是绝对路径
                        return path  # 直接返回该路径
                    else:  # 如果是相对路径
                        return os.path.join(save_dir, path)  # 拼接为绝对路径后返回
            # 查找包含 "has already been downloaded" 的行（视频已存在的情况）
            elif "has already been downloaded" in line:  # 检查是否提示视频已存在
                # 尝试提取文件名（通常在 "has already" 之前）
                parts = line.split("has already been downloaded", 1)  # 拆分行
                if parts:  # 如果拆分成功
                    filename = parts[0].strip()  # 取第一部分作为文件名
                    if filename:  # 如果文件名非空
                        return filename  # 返回文件名

        # 如果无法从输出中提取路径，则返回保存目录
        return save_dir  # 返回保存目录作为兜底结果
