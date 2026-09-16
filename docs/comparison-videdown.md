# 竞品对比：videdown（cshuangyy/videdown）× ytdlpGUI

- 分析日期：2026-09-16（第十三轮，T70）
- 方法：完整阅读 videdown 源码（electron/main.ts 2756 行 + Vue 前端 5 视图 + electron-builder 配置）
- 结论先行：videdown 是"国内短视频场景特化的轻量下载器"，我们在 yt-dlp 功能面/工程治理上有压倒性优势；它有 6 项体验设计值得吸收，其中 **JS 运行时自动配置** 与 **Cookie 智能应用** 直接命中本机已复现的痛点。

## 一、videdown 概览

- 技术栈：Electron + Vue3 + TS + Tailwind，pnpm；yt-dlp.exe/ffmpeg.exe 作为 extraResources 随安装包分发（NSIS 安装器）
- 定位：抖音/快手/B站/YouTube 无水印下载，中文单语，单一窗口
- 核心：`electron/main.ts` 单文件承载全部逻辑（解析/下载/历史/设置/更新检查）

## 二、它做得好、我们值得吸收的（按价值排序）

| # | 功能 | 它的实现 | 对我们的价值 |
|---|---|---|---|
| V1 | **JS 运行时检测与注入** | checkJsRuntime() 找 Node/Deno → `--js-runtimes node:<path>`；缺失弹窗引导安装 | **本机已复现痛点**：无 JS 运行时时 YouTube 格式列表残缺（我们 9/15 实测 WARNING）。我们应检测+注入+横幅引导 |
| V2 | **Cookie 智能应用** | YouTube/B站自动 `--cookies-from-browser chrome/edge`（探测已装浏览器），或用户选 cookies.txt | B站 412/YouTube 限制是国内用户高频痛点；我们已有该选项但无"自动"档 |
| V3 | **暂停/继续/重试** | 暂停=kill 进程树；继续=重启 yt-dlp（--continue 续传 .part）；失败任务一键重试 | 我们只有取消；断点续传是 yt-dlp 默认能力，我们白白没接 |
| V4 | **历史卡片化** | 缩略图（fetchImage 带 Referer 代理防盗链）+ 打开文件/打开所在文件夹 + 单条删除 + 画质标签 | 我们历史是纯文本行；打开文件/文件夹是高频操作 |
| V5 | **解析结果的音轨/字幕选择** | -J 解析出多音轨（m3u8 language）与字幕语言列表，点选后构造 `fmt+bestaudio[language^=xx]` 选择器；"仅下载字幕"模式 | 我们的查询浮窗已有格式表点击；扩展音轨/字幕行即可复用同一交互 |
| V6 | **文件名模板** | 设置页配置 `%(title)s` 等模板 + 每次下载可改名 + 非法字符清理 | 我们硬编码 `%(title)s [%(id)s].%(ext)s` |
| V7 | 剪贴板一键粘贴 | 读写剪贴板 IPC + 粘贴按钮 | 小 UX 甜点 |
| V8 | 应用内更新检查 | GitHub Releases API 版本比对 + 跳转下载 | 我们 exe 已入库，配套 Release + 检查更新顺理成章 |
| V9 | 临时文件清理 | 成功后清 `.part/.ytdl/.fNNN` 残留 | 我们合并后残留 .fNNN 中间流文件（用户已见过） |

## 三、我们的既有优势（videdown 没有）

1. **全量 yt-dlp 选项面**：322 选项注册表数据驱动、三态互斥治理、预设、搜索、四语界面——videdown 硬编码约 15 个参数，无高级选项
2. **播放列表支持**：videdown 恒定 `--no-playlist`，完全不能下合集
3. **架构**：services 层可独立移植（未来 macOS/iOS/Android）；Web/LAN 模式；videdown 是纯桌面单机
4. **工程质量**：注册表漂移检测、结构断言、96 条示例回归、CI、两轮 QA（27 缺陷+123 UI 用例）；videdown 无测试无 CI
5. **安全**：选项白名单+值校验+URL scheme 校验；videdown 对 URL 无校验直接进 spawn 参数
6. ffmpeg：我们有注册表实时检测+一键自动安装；videdown 靠安装包捆绑（体积大但省心——可借鉴进我们的 NSIS/打包计划）

## 四、改进计划（映射到我们的架构）

### P0（下轮优先，均为小-中工作量）

- **T71 JS 运行时自动配置**：`services/` 新增 runtime 探测（node/deno：which + 常见安装位 + PATH 注册表，复用 ffmpeg.py 模式）；`/api/config` 下发；downloader 注入 `--js-runtimes`（做成常用面板三态：自动/手动路径/关）；缺失时 YouTube 相关任务前置横幅提示
- **T72 Cookie 智能档**：常用面板"浏览器登录态"改为三态：自动（探测 Chrome/Edge→`--cookies-from-browser`）/cookies.txt（文件选择）/关；B站/YouTube 默认建议开启
- **T73 暂停/继续/重试**：Job 增 paused 状态与 resume（重启同 argv，yt-dlp 默认续传）；前端任务卡 pause/resume/retry 按钮；SSE 状态联动
- **T74 历史增强**：记录时存 title/thumbnail（查询信息的结果缓存命中则带缩略图）；新增"打开文件/打开文件夹"（`os.startfile` / `explorer /select`）API；单条删除；缩略图经后端代理（**Mimosa 约束：仅 http/https、校验 host、拒 localhost/环回/私有/保留地址**，仅放行 http(s) 且加 Referer 白名单站点）

### P1（体验打磨）

- **T75 文件名模板**：config 增 `filename_template`（默认 `%(title)s [%(id)s].%(ext)s`），常用面板可编辑+非法字符提示
- **T76 查询浮窗扩展音轨/字幕行**：/api/formats 补充 audio_tracks（language 去重）与 subtitles 列表，行点击构造选择器或勾选语言
- **T77 临时文件清理**：任务成功后清理 `.fNNN` 中间流与 `.ytdl`；取消时保留 `.part`（续传依赖）
- **T78 剪贴板粘贴按钮 + 更新检查**（GitHub API，固定 host 白名单）
- **T79 应用图标 .ico**（任务栏/窗口/Release 三处）

### P2（择机）

- **T80 仅下载字幕模式**（skip-download + write-subs 组合快捷档）
- **T81 安装包分发**：NSIS/electron-builder 风格 Setup.exe + GitHub Release 流（含 exe 自动捆绑 yt-dlp/ffmpeg，离线可用）

### 明确不抄

- **抖音/快手私有 API + 无头浏览器解析**：维护成本高、随网站改版即碎；yt-dlp 原生支持这两站（配 Cookie 即可用），我们靠 V2 的 Cookie 智能档解决同等需求
- **恒定 --no-playlist**：功能倒退
- **仅音频强制 mp3**：我们已有完整音频选项面

## 五、安全红线（实现 T74/T78 时强制）

后端任何新增的服务端 URL 请求（缩略图代理、更新检查）：仅 http/https；发请求前校验 host；拒绝 localhost、环回、私有与保留地址。缩略图代理仅放行解析结果中的缩略图 URL，且限制协议与端口。
