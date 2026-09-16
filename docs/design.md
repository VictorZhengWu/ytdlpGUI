# 设计文档（Design）

## 1. 技术选型

| 层 | 选择 | 理由 |
|---|---|---|
| 后端 | Python 3 + FastAPI + uvicorn | 复用旧版 Python 经验；yt-dlp 本身是 Python；FastAPI 自带 OpenAPI 文档与异步 SSE |
| 下载引擎 | `yt-dlp` 子进程（CLI 模式） | 与旧版一致；CLI 是 yt-dlp 最完整的功能面（Python API 不暴露全部选项），升级 yt-dlp 即获得全部新选项 |
| 前端 | 原生 HTML/CSS/JS（无构建） | 可直接服务、可直接嵌入 WebView（将来 macOS/iOS/Android），无工具链依赖 |
| 通信 | REST + Server-Sent Events | SSE 单向推流足够（进度/日志），比 WebSocket 简单且代理友好 |

## 2. 架构

```
┌─────────────────────────────┐        ┌──────────────────────────────┐
│  frontend (静态资源)          │  HTTP  │  backend (FastAPI)            │
│  index.html / app.js / css  │ ◄────► │  main.py        路由/静态挂载  │
│  - 由 options registry 驱动  │  SSE   │  api/           HTTP 层       │
│  - 无业务逻辑                │        │  services/      业务逻辑      │
└─────────────────────────────┘        │    downloader   任务/进程/进度 │
                                       │    options      校验/建命令    │
                                       │    presets      预设持久化     │
                                       │    metadata     -J 元数据查询  │
                                       │  data/options_registry.json   │
                                       └──────────────────────────────┘
```

依赖方向（严格单向）：`api → services → core(yt-dlp)`。`services/downloader.py` 不 import 任何 FastAPI 类型，可独立使用（移植到移动端后端时整层复用）。

## 3. 关键设计

### 3.1 选项注册表（单一数据源）
- `generate_registry.py` 解析 `yt-dlp --help`：17 节 → 250 项，字段 `{flag, short, metavar, description}`。
- 前端按节渲染分组面板；后端构建白名单 Set 做校验。
- 布尔型/取值型区分：`metavar == null` 视为开关型（渲染 checkbox），否则渲染文本输入；多值选项（`--merge-output-format` 等）由前端以逗号分隔输入、后端按注册表中的 `multi` 标记拆分。

### 3.2 任务模型
```python
@dataclass
class Job:
    id: str; urls: list[str]; argv: list[str]
    status: str  # queued|running|done|error|canceled
    progress: float; speed: str; eta: str; lines: deque[str]
    process: subprocess.Popen | None
```
- `DownloadManager`：内存任务表 + 单工作线程顺序消费队列；每任务 spawn `yt-dlp`，逐行读取 stdout/stderr。
- 进度解析正则（兼容旧版思路）：`\[download\]\s+([\d.]+)%\s+of...\s+at\s+([\d.]+[KMG]iB/s)\s+ETA\s+(\S+)`。
- 取消：`process.terminate()` → 超时 kill；状态置 canceled。

### 3.3 API 契约
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/options` | 返回注册表（含 multi 补充标记） |
| GET | `/api/config` / PUT | 下载目录、语言 |
| GET | `/api/formats?url=` | 调 `yt-dlp -J --skip-download` 返回标题/时长/格式表 |
| POST | `/api/jobs` | `{urls: [...], options: {flag: value}}` → Job |
| GET | `/api/jobs` | 任务列表 |
| GET | `/api/jobs/{id}/events` | SSE：progress/log/status |
| POST | `/api/jobs/{id}/cancel` | 取消 |
| GET/POST/DELETE | `/api/presets[/{name}]` | 预设 CRUD（data/presets.json） |

### 3.4 安全
- 用户选项 key 必须在白名单 Set 中；value 标量化（str/int/bool/list[str]），逐元素不包含空白/控制字符。
- URL 用 `urllib.parse` 校验 scheme ∈ {http, https} 或无 scheme 时交由 yt-dlp 的 extractor 语义但拒绝以 `-` 开头。
- 服务默认绑定 127.0.0.1；局域网部署由用户显式传 `--host 0.0.0.0`。

### 3.5 前端结构
- 顶栏：URL 多行输入 + "查询信息" + "下载"。
- 左区：视频信息卡（查询结果、格式选择）。
- 右区：选项面板（17 个分类 tab + 搜索框 + 预设下拉），全部由 `/api/options` 动态生成。
- 底区：任务队列（进度条 + 实时日志）+ 命令预览条。
- i18n：`frontend/js/i18n.js` 内置 zh/en 字典，界面语言入 config。

## 4. 目录结构

```
ytdlpGUI/
├── docs/                     # SDD 文档
├── backend/
│   ├── app/
│   │   ├── main.py           # 入口：挂路由+静态资源
│   │   ├── api/routes.py     # HTTP 路由层（薄）
│   │   ├── services/{downloader,options,presets,metadata,config}.py
│   │   └── data/{options_registry.json,presets.json,config.json}
│   └── requirements.txt
├── frontend/{index.html,css/style.css,js/{app.js,i18n.js}}
├── scripts/generate_registry.py
├── run.sh / run.bat
└── README.md
```

## 5. v3.6 契约增补（T71~T77，竞品优点吸收轮）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/config` | 增发派生字段：`ffmpeg`（探测结果）、`js_runtime{available,name,path}`、`browsers[chrome,edge,firefox]` |
| POST | `/api/jobs` | body 增可选 `meta: {url: {title, thumbnail}}`（前端查询信息缓存，供历史卡片用，后端不发起网络请求） |
| POST | `/api/jobs/{id}/pause` `resume` | 暂停=终止子进程保留 .part；继续/重试=同 argv 重新入队（yt-dlp 默认断点续传） |
| GET | `/api/proxy/image?url=` | 缩略图代理（同源 Referer 过防盗链；SSRF 硬约束见 services/imageproxy.py 模块注释） |
| GET | `/api/update` | 更新检查（https + api.github.com 白名单 + 公网 IP 校验；返回 {current,latest,has_update,url}） |
| GET | `/api/formats?url=` | v3.7 起增 audio_tracks（>1 语言）与 subtitle_langs（常见语言优先） |
| POST | `/api/history/open` | `{filepath, reveal}` 打开文件/定位文件夹；filepath 必须已登记在历史条目中 |
| DELETE | `/api/history/{id}` | 单条删除（条目新增 id/title/thumbnail 字段） |

前端规约（主题化预留）：文案只经 i18n 键；样式只用 CSS 变量类名（禁内联样式与硬编码色值）；DOM 生成集中在 render*/make* 函数，事件与状态逻辑不直接拼界面。
