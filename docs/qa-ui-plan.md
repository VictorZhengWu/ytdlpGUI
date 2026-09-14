# ytdlpGUI 界面（UI）测试方案

- 版本：v1（对应前端资产 app.js?v=46 / style.css?v=44 / APP_VER 37+）
- 分工：QA 设计用例并判读；执行者在浏览器逐条执行并回传断言原值
- 断言约定：
  - 在 DevTools Console（与页面同一 JS 世界）执行；页面脚本的 `state` / `t` / `I18N` / `$` 均可直接引用
  - 标注 **async** 的断言返回 Promise，控制台展开读取解决值后回传
  - 回传格式：`UI-xx: <断言原值>`；「观察项」回传文字描述
- 测试数据：
  - `S` = `https://download.samplelib.com/mp4/sample-5s.mp4`（有效，单格式 mp4）
  - `F` = `https://example.com/notexist`（generic 404，快速失败）
- 执行顺序：按编号顺序。**M4 会把下载目录切到项目 `downloads/`**（供 M6/M7 落盘），全部执行完后按「收尾清理」还原
- 前置：服务运行于 http://127.0.0.1:8765；建议新建隐身/无痕窗口打开（localStorage 干净，默认精简模式）
- 【高危】= 历史故障区（boot 崩溃 / 死按钮 / 语言残留中文 / 假死），优先 P0

---

## M1 启动冒烟（UI-01 ~ UI-08）

| 编号 | 级别 | 步骤 | 预期 | 断言 |
|---|---|---|---|---|
| UI-01 | P0【高危】 | 无痕窗口打开首页，等待加载完成 | boot 全链路成功，精简模式，注册表就绪 | `document.body.classList.contains('simple') && !!state.registry && state.flagMap.size >= 240` |
| UI-02 | P0 | 同上（无需点击） | 16 个分类标签已构建 | `document.querySelectorAll('#optTabs button').length === 16` |
| UI-03 | P0 | 同上 | 队列空态文案 | `document.querySelector('#jobList .empty-hint').textContent.trim() === t('emptyQueue')` |
| UI-04 | P0 | 同上 | 历史空态节点存在 | `document.querySelector('#historyList .empty-hint') !== null` |
| UI-05 | P0 | 同上 | 初始语言 zh（html 与 body 双标记） | `document.body.dataset.lang === 'zh' && document.documentElement.lang === 'zh'` |
| UI-06 | P0 | 同上 | 精简模式：右列/查询按钮/命令条三者隐藏 | `getComputedStyle(document.querySelector('.col-right')).display === 'none' && getComputedStyle(document.querySelector('#btnInfo')).display === 'none' && getComputedStyle(document.querySelector('.cmdbar')).display === 'none'` |
| UI-07 | P0【高危】 | 同上 | 核心控件无一 disabled（死按钮检测） | `!document.querySelector('#btnDownload').disabled && !document.querySelector('#btnAdvance').disabled && !document.querySelector('#langSelect').disabled` |
| UI-08 | P0 | 同上 | js/css 资源全部加载成功（无 404 白屏风险） | `performance.getEntriesByType('resource').filter(e => e.name.includes('.js') || e.name.includes('.css')).every(e => e.transferSize > 0)` |

## M2 精简模式（UI-09 ~ UI-16）

| 编号 | 级别 | 步骤 | 预期 | 断言 |
|---|---|---|---|---|
| UI-09 | P1 | URL 框输入 `S`（单行），点「下 载」，等任务卡出现 | 纯净下载：argv 为空 | **async** `(async () => (await (await fetch('/api/jobs')).json())[0].argv.length === 0)()` |
| UI-10 | P1 | 清空 URL，点「下 载」 | 原生 alert 弹出，文案=emptyUrl；回传弹窗文案 | `t('emptyUrl')` |
| UI-11 | P1 | URL 框两行输入 `S` 与 `F`，点下载 | 两个 URL 一并提交 | **async** `(async () => (await (await fetch('/api/jobs')).json())[0].urls.length === 2)()` |
| UI-12 | P1 | 观察 main 布局 | 精简单列居中 | `getComputedStyle(document.querySelector('main')).gridTemplateColumns.split(' ').length === 1` |
| UI-13 | P0【高危】 | 点「⚙ 高级」再点「✕ 精简」往返 | 状态还原并持久化 | `document.body.classList.contains('simple') && localStorage.getItem('ytdlpgui-advance') === '0'` |
| UI-14 | P1 | 精简模式下点「下载历史」标签 | 左下面板切换正常 | `!document.querySelector('#historyList').classList.contains('hidden') && document.querySelector('#jobList').classList.contains('hidden')` |
| UI-15 | P2 | 切换任一语言后观察 | 精简/高级状态不被语言切换重置 | `document.body.classList.contains('simple')` |
| UI-16 | P0【高危】 | UI-09 任务提交后观察至终态 | 60 秒内到终态、无假死 | **async** `(async () => (await (await fetch('/api/jobs')).json())[0].status)()`（回传状态字符串） |

## M3 高级模式（UI-17 ~ UI-35）

| 编号 | 级别 | 步骤 | 预期 | 断言 |
|---|---|---|---|---|
| UI-17 | P0【高危】 | 点「⚙ 高级」 | 进入高级：右列显示且状态持久化 | `!document.body.classList.contains('simple') && getComputedStyle(document.querySelector('.col-right')).display !== 'none' && localStorage.getItem('ytdlpgui-advance') === '1'` |
| UI-18 | P0【高危】 | 同上 | 命令条常显且有前缀 | `getComputedStyle(document.querySelector('.cmdbar')).display !== 'none' && document.querySelector('#cmdPreview').textContent.trim().startsWith('yt-dlp')` |
| UI-19 | P1 | 点「全部选项」 | 高级面板切换 | `!document.querySelector('#advancedPanel').classList.contains('hidden') && document.querySelector('#quickPanel').classList.contains('hidden') && document.querySelector('#modeAdvanced').classList.contains('active')` |
| UI-20 | P1 | 切回「常用设置」 | 6 个常用组 | `document.querySelectorAll('#quickPanel .quick-group').length === 6` |
| UI-21 | P1 | 常用面板下执行（为 M8 存快照） | 快照含全部组名与控件标签 | `window.__qaSnap = [...document.querySelectorAll('#quickPanel .quick-group-title, #quickPanel .quick-item > label')].map(e => e.textContent.trim()); window.__qaSnap.length >= 20 && window.__qaSnap.some(x => x.includes('保存位置'))` |
| UI-22 | P1 | 观察「保存位置」组 | 两个目录控件（下载目录/历史日志路径）均带浏览按钮 | `[...document.querySelectorAll('#quickPanel .quick-item')].filter(i => i.querySelector('input[data-cfgkey]') && i.querySelector('.dir-row .btn')).length === 2` |
| UI-23 | P1 | 观察「画质与格式」组 | 容器默认 mp4 | `document.querySelector('#quickPanel select[data-flag="--merge-output-format"]').value === 'mp4'` |
| UI-24 | P1 | 进入「全部选项」 | 第一个分类标签 active | `document.querySelector('#optTabs button').classList.contains('active')` |
| UI-25 | P1 | 点「SponsorBlock 去广告」标签 | 对应面板独显 | `document.querySelector('#optPanels .opt-panel:not(.hidden)').dataset.section === 'SponsorBlock Options'` |
| UI-26 | P1 | 观察「通用」面板 | 三态组约 47（40-55 合理区间） | `(n => n >= 40 && n <= 55)(document.querySelectorAll('#optPanels .tri').length)` |
| UI-27 | P1 | 搜索 `ignore-errors` | 组合并渲染：ignore-errors 组仅一张卡 | `document.querySelectorAll('[data-flag="--ignore-errors"]').length === 1 && document.querySelectorAll('[data-flag="--abort-on-error"]').length === 0` |
| UI-28 | P2 | 找到 `--format` 条目 | 取值型输入 placeholder=中文层 example | `document.querySelector('[data-flag="--format"] input').placeholder === 'bv*+ba/b'` |
| UI-29 | P2 | 点击 `--format` 条目文字区（非输入框）两次 | 展开→收起 | 第一次后：`document.querySelector('[data-flag="--format"]').classList.contains('expanded')`；第二次后同式应 false（回传两次值） |
| UI-30 | P1 | 「全部选项」搜索框输入 `sponsorblock` | 进入过滤态，非命中隐藏 | `document.querySelector('#optPanels').classList.contains('searching') && document.querySelectorAll('.opt-item.hit').length > 0 && [...document.querySelectorAll('#optPanels .opt-item:not(.hit)')].every(e => getComputedStyle(e).display === 'none')` |
| UI-31 | P1 | 同上 | 命中相关性 | `[...document.querySelectorAll('.opt-item.hit')].every(e => e.textContent.toLowerCase().includes('sponsorblock'))` |
| UI-32 | P1 | 清空搜索框 | 恢复单面板激活模式 | `!document.querySelector('#optPanels').classList.contains('searching') && document.querySelectorAll('#optPanels .opt-panel:not(.hidden)').length === 1` |
| UI-33 | P1 | 勾选 `--no-warnings`、`--sub-langs` 填 `zh` → 点「存为预设」，prompt 输入 `qa-preset` → 点「清空」→ 下拉选 `qa-preset` → 观察回填 → 点「删除」确认 | 保存/应用/删除全链路 | 应用后：`state.options['--no-warnings'] === true && state.options['--sub-langs'] === 'zh'`；删除后：`![...document.querySelectorAll('#presetSelect option')].some(o => o.value === 'qa-preset')`（两段回传） |
| UI-34 | P2 | 随意设 2-3 个选项后点「清空」 | 选项与高亮全清 | `Object.keys(state.options).length === 0 && document.querySelectorAll('.opt-flag.set').length === 0` |
| UI-35 | P2 | 展开预设下拉 | 默认项文案=i18n | `document.querySelector('#presetSelect option[value=""]').textContent === t('presetNone')` |

## M4 目录选择对话框（UI-36 ~ UI-47）

| 编号 | 级别 | 步骤 | 预期 | 断言 |
|---|---|---|---|---|
| UI-36 | P0【高危】 | 常用面板「下载目录」点「浏览…」 | 对话框打开且显示当前路径 | `document.querySelector('#dirDlg').open === true && document.querySelector('#dirCurrent').textContent.length > 0` |
| UI-37 | P1 | 观察快捷条 | roots ≥ 2（主目录 + 根；有挂载则更多） | `document.querySelectorAll('#dirRoots .dir-root').length >= 2` |
| UI-38 | P1 | 点快捷条「主目录」→ 再点「/」 | 当前路径切换正确 | 点主目录后：`document.querySelector('#dirCurrent').textContent.startsWith('/home/')`；点「/」后：`document.querySelector('#dirCurrent').textContent === '/'`（两段回传） |
| UI-39 | P1 | 在主目录下点子目录 `myCode` | 下钻导航 | `document.querySelector('#dirCurrent').textContent.endsWith('/myCode')` |
| UI-40 | P1 | 连点「↑ 上级」直至根 | 到顶后上级按钮禁用 | `document.querySelector('#dirUp').disabled === true` |
| UI-41 | P0【高危】 | 导航到 `/home/victor/myCode/ytdlpGUI/downloads`，点「选择此目录」 | 对话框关、输入框更新、配置持久化 | `!document.querySelector('#dirDlg').open && document.querySelector('#quickPanel input[data-cfgkey="download_dir"]').value.includes('ytdlpGUI/downloads')`；**async** `(async () => (await (await fetch('/api/config')).json()).download_dir.includes('ytdlpGUI/downloads'))()` |
| UI-42 | P0 | 再开浏览，导航到 `/tmp`，点「取消」 | 取消不改动输入框 | `!document.querySelector('#dirDlg').open && document.querySelector('#quickPanel input[data-cfgkey="download_dir"]').value.includes('ytdlpGUI/downloads')` |
| UI-43 | P2 | 再开浏览，按 Esc | Esc 关闭且不改动 | `!document.querySelector('#dirDlg').open && document.querySelector('#quickPanel input[data-cfgkey="download_dir"]').value.includes('ytdlpGUI/downloads')` |
| UI-44 | P2 | 开浏览导航到项目 `downloads`（无子目录） | 空目录提示 | `document.querySelector('#dirList .empty-hint').textContent.trim() === t('noSubdirs')` |
| UI-45 | P1 | 观察「历史日志路径」控件 | 同款目录控件存在 | `!!document.querySelector('#quickPanel input[data-cfgkey="history_path"]')` |
| UI-46 | P2 | 对话框打开时观察主界面 | 模态遮罩、主界面不可点（观察项） | 观察项：回传描述 |
| UI-47 | P2 | 关闭对话框后手动改「下载目录」输入框为 `/home/victor/myCode/ytdlpGUI/downloads` 并失焦 | onchange 持久化 | **async** `(async () => (await (await fetch('/api/config')).json()).download_dir.includes('ytdlpGUI/downloads'))()` |

## M5 查询信息浮动窗口（UI-48 ~ UI-59）【前置：高级模式】

| 编号 | 级别 | 步骤 | 预期 | 断言 |
|---|---|---|---|---|
| UI-48 | P0【高危】 | URL=`S` 单行，点「查询信息」 | 浮窗打开且渲染格式表 | `document.querySelector('#infoDlg').open === true && document.querySelector('#infoBody tr[data-fid]') !== null` |
| UI-49 | P1 | 同上 | 表头列名随语言 | `[...document.querySelectorAll('#infoBody th')].slice(1, 3).map(e => e.textContent).join() === t('colExt') + ',' + t('colRes')` |
| UI-50 | P1 | 单链接查询完成后观察导航区 | 单条边界：↑↓ 均禁用，位置指示 1/1 | `document.querySelector('#infoDlg .nav-up').disabled === true && document.querySelector('#infoDlg .nav-down').disabled === true && document.querySelector('#infoDlg .pos').textContent.trim() === '1 / 1'` |
| UI-51 | P0 | URL 两行 `S` 与 `F`，点查询 | 两个结果块逐条渲染 | `document.querySelectorAll('#infoBody .info-result').length === 2` |
| UI-52 | P1 | 点 ↓ | 位置 2/2，下禁上启 | `document.querySelector('#infoDlg .pos').textContent.trim() === '2 / 2' && document.querySelector('#infoDlg .nav-down').disabled === true && document.querySelector('#infoDlg .nav-up').disabled === false` |
| UI-53 | P1 | 观察第二块 | 失败链接独立报错（不阻塞第一块） | `document.querySelectorAll('#infoBody .info-result')[1].textContent.includes(t('fetchFail'))` |
| UI-54 | P1 | 点「清空」→ 点第一块第一格式行 | 行选中且 `-f` 写入高级面板输入框 | `document.querySelector('#infoBody tr.selected') !== null && state.options['-f'] !== undefined && document.querySelector('[data-flag="-f"] input').value === document.querySelector('#infoBody tr.selected td b').textContent` |
| UI-55 | P1 | 点「✕ 关闭」 | 浮窗关闭 | `document.querySelector('#infoDlg').open === false` |
| UI-56 | P2 | 再次点「查询信息」 | 重新拉取重建两块 | `document.querySelectorAll('#infoBody .info-result').length === 2` |
| UI-57 | P2 | 点查询后立即观察 ↑↓ | 查询期间禁用态（观察项） | 观察项：回传描述 |
| UI-58 | P2 | 长内容下观察浮窗体 | 内部滚动（观察项，可选） | 观察项：回传描述 |
| UI-59 | P1 | UI-54 之后看命令条 | 预览联动 `--format` | `document.querySelector('#cmdPreview').textContent.includes('--format')` |

## M6 下载队列（UI-60 ~ UI-71）【前置：M4 已切换下载目录到项目 downloads/】

| 编号 | 级别 | 步骤 | 预期 | 断言 |
|---|---|---|---|---|
| UI-60 | P0 | URL=`S` 点下载 | 任务卡出现且 URL 显示 | `document.querySelector('#jobList .job') !== null && document.querySelector('#jobList .job .job-url').textContent.includes('samplelib')` |
| UI-61 | P1 | 等待下载过程 | 进度数字与进度条增长 | `parseFloat(document.querySelector('#jobList .job .pct').textContent) >= 0`；并回传 `document.querySelector('#jobList .job .progressbar > div').style.width` 原值 |
| UI-62 | P1 | 等待终态 | badge=done | `document.querySelector('#jobList .job .badge').className.includes('done')` |
| UI-63 | P1 | 终态后观察 | 文件路径上报 | `document.querySelector('#jobList .job .fp').textContent.includes('.mp4')` |
| UI-64 | P1 | 点「显示/隐藏日志」两次 | pre 显隐切换 | 第一次后 `!document.querySelector('#jobList .job pre').classList.contains('hidden')`；第二次后同式（两段回传） |
| UI-65 | P0【高危】 | 常用面板「限速」填 `2K`，URL=`S` 点下载，running 后点「取消任务」 | 运行中任务可取消，badge=canceled | `document.querySelector('#jobList .job .badge').className.includes('canceled')` |
| UI-66 | P1 | 立即再提交一个任务（排队中），点其「取消任务」 | 排队任务可取消 | `document.querySelectorAll('#jobList .job')[0].querySelector('.badge').className.includes('canceled')` |
| UI-67 | P1 | UI-65 后观察首个限速任务 | 取消不毒化队列，后续任务照常执行 | **async** `(async () => (await (await fetch('/api/jobs')).json()).some(j => j.status === 'done' || j.status === 'canceled'))()` |
| UI-68 | P0 | 保留一张终态卡，切语言 en，等 ≥5s（自动刷新） | badge 文案随语言（若不变=语言残留缺陷，如实回传） | `document.querySelector('#jobList .job .badge').textContent.trim() === I18N.en.statusMap.done` |
| UI-69 | P1 | running 时观察速度/ETA（观察项） | .spd/.eta 有值 | 回传 `document.querySelector('#jobList .job .spd').textContent` 原值 |
| UI-70 | P2 | 连续提交 5 个 `F` 任务 | 队列区内部滚动 | `document.querySelector('#jobList').scrollHeight > document.querySelector('#jobList').clientHeight` |
| UI-71 | P2 | 长 URL 任务卡 | 卡内无横向溢出 | `(j => j.scrollWidth <= j.clientWidth + 1)(document.querySelector('#jobList .job'))` |

## M7 下载历史（UI-72 ~ UI-79）

| 编号 | 级别 | 步骤 | 预期 | 断言 |
|---|---|---|---|---|
| UI-72 | P1 | 点「下载历史」标签 | 历史面板显示，清空按钮出现 | `!document.querySelector('#historyList').classList.contains('hidden') && !document.querySelector('#btnClearHistory').classList.contains('hidden')` |
| UI-73 | P1 | 有历史记录时观察 | 字段完整（时间/标题/URL） | `(r => !!r && ['h-time', 'h-title', 'h-url'].every(c => r.querySelector('.' + c) !== null))(document.querySelector('.history-table tr'))` |
| UI-74 | P1 | 成功记录 | 路径字段含产物 | `document.querySelector('.history-table .h-path').textContent.includes('.mp4')` |
| UI-75 | P0 | 点「清空历史」，确认框选确定 | 清空后空态 | `document.querySelector('#historyList .empty-hint').textContent.trim() === t('emptyHistory')` |
| UI-76 | P2 | 再造一条历史（下载 `S`），点清空但确认框选取消 | 取消则记录保留 | `document.querySelectorAll('.history-table tr').length >= 1` |
| UI-77 | P1 | 队列↔历史来回切换 | 面板互斥 | `document.querySelector('#jobList').classList.contains('hidden') === !document.querySelector('#historyList').classList.contains('hidden')` |
| UI-78 | P2 | 提交 `F`（404 失败）后查历史 | 失败记录带 error 徽标与错误行 | `document.querySelector('.history-table .badge.error') !== null` |
| UI-79 | P1 | 切回「下载队列」 | 清空按钮仅历史页显示 | `document.querySelector('#btnClearHistory').classList.contains('hidden')` |

## M8 四语言切换（UI-80 ~ UI-97）

通用残留检测式（说明）：`[...document.querySelectorAll('[data-i18n]')].filter(e => { const k = e.dataset.i18n, z = I18N.zh[k], c = I18N[L][k]; return c && z && c !== z && e.textContent.trim() === z; }).length === 0`（L 替换为目标语言）。快照比对依赖 UI-21 的 `window.__qaSnap`。

| 编号 | 级别 | 步骤 | 预期 | 断言 |
|---|---|---|---|---|
| UI-80 | P0【高危】 | 切换 en | 基础文案切换 | `document.body.dataset.lang === 'en' && document.querySelector('[data-i18n="urlLabel"]').textContent === I18N.en.urlLabel` |
| UI-81 | P0【高危】 | en 下全页面 | 可见文本无任何中文字符（前置：URL/取值无中文） | `[...document.body.innerText.matchAll(/[\u4e00-\u9fff]/g)].length === 0` |
| UI-82 | P0【高危】 | en 下 | data-i18n 无 zh 回落残留 | `[...document.querySelectorAll('[data-i18n]')].filter(e => { const k = e.dataset.i18n, z = I18N.zh[k], c = I18N.en[k]; return c && z && c !== z && e.textContent.trim() === z; }).length === 0` |
| UI-83 | P0【高危】 | en 下看常用面板 | 常用面板标签全部脱离 zh 快照 | `window.__qaSnap.filter(x => [...document.querySelectorAll('#quickPanel .quick-group-title, #quickPanel .quick-item > label')].map(e => e.textContent.trim()).includes(x)).length === 0` |
| UI-84 | P1 | en 下进「全部选项」 | 搜索占位符/预设默认项 | `document.querySelector('#optSearch').placeholder === I18N.en.searchOptions && document.querySelector('#presetSelect option[value=""]').textContent === I18N.en.presetNone` |
| UI-85 | P1 | en 下看队列/历史标签 | 标签翻译 | `document.querySelector('#tabQueue').textContent === I18N.en.queue && document.querySelector('#tabHistory').textContent === I18N.en.history` |
| UI-86 | P0【高危】 | 切换 ja | 基础文案切换 | `document.body.dataset.lang === 'ja' && document.querySelector('[data-i18n="download"]').textContent === I18N.ja.download` |
| UI-87 | P0【高危】 | ja 下 | data-i18n 无 zh 回落残留 | UI-82 式，`I18N.en` 换 `I18N.ja` |
| UI-88 | P0【高危】 | ja 下常用面板 | 脱离 zh 快照 | UI-83 式（语言无关，直接执行） |
| UI-89 | P1 | ja 下看分类标签 | 首标签=ja 分节翻译 | `document.querySelector('#optTabs button').textContent === I18N.ja.sections['General Options']` |
| UI-90 | P0【高危】 | 切换 ko | 基础文案切换 | `document.body.dataset.lang === 'ko' && document.querySelector('[data-i18n="fetchInfo"]').textContent === I18N.ko.fetchInfo` |
| UI-91 | P0【高危】 | ko 下 | data-i18n 无 zh 回落残留 | UI-82 式，换 `I18N.ko` |
| UI-92 | P0【高危】 | ko 下常用面板 | 脱离 zh 快照 | UI-83 式 |
| UI-93 | P1 | ko 下分类标签 | 首标签=ko 翻译 | UI-89 式，换 `I18N.ko` |
| UI-94 | P1 | 切回 zh，刷新页面 | 语言经服务端配置持久化 | 刷新后：`document.body.dataset.lang === 'zh'` |
| UI-95 | P2 | en 下进「全部选项」 | 非中文界面隐藏中文说明行 | `[...document.querySelectorAll('.opt-item .opt-zh')].every(e => getComputedStyle(e).display === 'none')` |
| UI-96 | P1 | en 下打开目录对话框 | 对话框文案随语言 | `document.querySelector('#dirDlg h3').textContent === I18N.en.chooseDir && document.querySelector('#dirChoose').textContent === I18N.en.choose`（断言后关闭） |
| UI-97 | P1 | en 下查询 `S` | 浮窗标题/表头随语言 | `document.querySelector('#infoDlg h3').textContent === I18N.en.infoTitle && [...document.querySelectorAll('#infoBody th')].map(e => e.textContent).includes(I18N.en.colSize)` |

## M9 命令预览（UI-98 ~ UI-105）

模块辅助（先在控制台粘贴一次）：

```js
window.qaCmdCmp = async () => {
  const j = (await (await fetch('/api/jobs')).json())[0];
  const argv = j.command.split(/\s+/).filter(tk => tk !== 'yt-dlp' && tk !== '-o'
    && !tk.includes('%(title)s') && !tk.includes('%(id)s') && !j.urls.includes(tk));
  const prev = document.querySelector('#cmdPreview').textContent.trim().split(/\s+/).filter(tk => tk !== 'yt-dlp');
  return { argv: argv.join(' '), preview: prev.join(' '), equal: argv.join(' ') === prev.join(' ') };
};
```

| 编号 | 级别 | 步骤 | 预期 | 断言 |
|---|---|---|---|---|
| UI-98 | P0 | 「全部选项」找到 `--ignore-errors` 组，依次点 开 / 关 / 默认 | 三态命令正确 | 开后 `document.querySelector('#cmdPreview').textContent.trim() === 'yt-dlp --ignore-errors'`；关后 `=== 'yt-dlp --abort-on-error'`；默认后 `=== 'yt-dlp'`（三段回传） |
| UI-99 | P0 | 找到 `--add-headers` 输入 `A:b,C:d` | multi 重复拼装预览 | `document.querySelector('#cmdPreview').textContent.trim() === 'yt-dlp --add-headers A:b --add-headers C:d'` |
| UI-100 | P1 | 找到 `--replace-in-metadata` 输入 `title Intro 前言` | nargs 预览 | `document.querySelector('#cmdPreview').textContent.trim() === 'yt-dlp --replace-in-metadata title Intro 前言'` |
| UI-101 | P0 | 清空→重设 UI-99 组合→URL=`F` 点下载 | 预览与后端 command 一致（例 1/3） | **async** `(async () => (await window.qaCmdCmp()).equal)()`（回传 equal 与 argv/preview 原值） |
| UI-102 | P0 | 清空→`--ignore-errors` 组点开→下载 `F` | 一致（例 2/3） | **async** 同 UI-101 |
| UI-103 | P1 | 清空→UI-100 组合→下载 `F` | 一致（例 3/3） | **async** 同 UI-101 |
| UI-104 | P1 | 任设一个取值型选项 | 对应 flag 高亮 | `document.querySelectorAll('.opt-flag.set').length > 0` |
| UI-105 | P2 | 切回精简模式 | 预览重置为 URL 形式（命令条隐藏） | `getComputedStyle(document.querySelector('.cmdbar')).display === 'none' && document.querySelector('#cmdPreview').textContent.startsWith('yt-dlp')` |

## M10 响应式（UI-106 ~ UI-113）

视口设置：用 DevTools 设备工具栏分别调至 1366×500、1920×1080、420×800（每次调整后执行对应断言；高级模式、常用面板视图）。

| 编号 | 级别 | 视口 | 预期 | 断言 |
|---|---|---|---|---|
| UI-106 | P1 | 1366×500 | 无横向溢出 | `document.documentElement.scrollWidth <= window.innerWidth + 1` |
| UI-107 | P1 | 1366×500 | 队列卡保底 340px | `parseFloat(getComputedStyle(document.querySelector('.col-left .card.grow')).minHeight) >= 340` |
| UI-108 | P1 | 1366×500 | 左列内部滚动 | `getComputedStyle(document.querySelector('.col-left')).overflowY === 'auto'` |
| UI-109 | P1 | 1920×1080 | 无溢出 | 同 UI-106 式 |
| UI-110 | P2 | 1920×1080 | 双列布局保持 | `getComputedStyle(document.querySelector('main')).gridTemplateColumns.split(' ').length === 2` |
| UI-111 | P1 | 420×800 | 单列堆叠 | `getComputedStyle(document.querySelector('main')).display === 'block'` |
| UI-112 | P1 | 420×800 | 无横向溢出 | 同 UI-106 式 |
| UI-113 | P2 | 420×800 | 常用网格单列 | `getComputedStyle(document.querySelector('.quick-grid')).gridTemplateColumns.split(' ').length === 1` |

## M11 互斥 UI（UI-114 ~ UI-123）【前置：高级模式·全部选项】

| 编号 | 级别 | 步骤 | 预期 | 断言 |
|---|---|---|---|---|
| UI-114 | P0【高危】 | `--ignore-errors` 组点「开」 | on 侧 flag 写入且按钮高亮 | `state.options['--ignore-errors'] === true && document.querySelector('[data-flag="--ignore-errors"] .tri button[data-v="on"]').classList.contains('active')` |
| UI-115 | P0【高危】 | 同组点「关」 | 切换到 off 侧 flag，on 侧清除 | `state.options['--abort-on-error'] === true && state.options['--ignore-errors'] === undefined` |
| UI-116 | P1 | 同组点「默认」 | 复位为空 | `Object.keys(state.options).length === 0` |
| UI-117 | P0【高危】 | `--skip-unavailable-fragments` 组点「开」 | 写入 skip（历史极性 bug 区） | `state.options['--skip-unavailable-fragments'] === true` |
| UI-118 | P0【高危】 | `--allow-dynamic-mpd` 组点「开」 | 写入 allow（历史极性 bug 区） | `state.options['--allow-dynamic-mpd'] === true` |
| UI-119 | P0【高危】 | `--plugin-dirs` 输入 `a,b`，再勾选 `--no-plugin-dirs` | 值型被自动清除（mixed 单向） | `document.querySelector('[data-flag="--plugin-dirs"] input').value === '' && state.options['--plugin-dirs'] === undefined && state.options['--no-plugin-dirs'] === true` |
| UI-120 | P1 | 再向 `--plugin-dirs` 输入 `c` | 反向：复选框自动取消 | `!document.querySelector('[data-flag="--no-plugin-dirs"] input').checked && state.options['--no-plugin-dirs'] === undefined && state.options['--plugin-dirs'] === 'c'` |
| UI-121 | P0【高危】 | SponsorBlock 标签：`--sponsorblock-mark` 填 `all`、`--sponsorblock-remove` 填 `sponsor`，再勾选 `--no-sponsorblock` | 一对多清除：两个值型同时被清 | `document.querySelector('[data-flag="--sponsorblock-mark"] input').value === '' && document.querySelector('[data-flag="--sponsorblock-remove"] input').value === '' && state.options['--no-sponsorblock'] === true` |
| UI-122 | P1 | `--no-playlist` 组点「开」再点「关」 | dest 极性：开=no-playlist，关=yes-playlist | 开后 `state.options['--no-playlist'] === true`；关后 `state.options['--yes-playlist'] === true && state.options['--no-playlist'] === undefined`（两段回传） |
| UI-123 | P2 | 组置位后观察组卡 | flag 名高亮 set 类 | `document.querySelector('[data-flag="--ignore-errors"] .opt-flag').classList.contains('set')`（先按 UI-114 置位） |

---

## 收尾清理（执行完全部用例后）

1. 删除项目 `downloads/` 下测试产物（`sample-5s*.mp4` 等）
2. 还原配置：`PUT /api/config` → `{"download_dir":"/home/victor/share","language":"zh"}`
3. 清空历史：`DELETE /api/history`
4. 删除测试预设 `qa-preset`（若 UI-33 删除步骤未执行：`DELETE /api/presets/qa-preset`）
5. （可选）清 localStorage 的 `ytdlpgui-advance`，恢复默认精简模式

## 统计

- 总用例：123（M1:8 / M2:8 / M3:19 / M4:12 / M5:12 / M6:12 / M7:8 / M8:18 / M9:8 / M10:8 / M11:10）
- 优先级：P0 × 41（其中【高危】标注 26）/ P1 × 60 / P2 × 22
- async 断言 9 条（UI-09/11/16/41/47/67/101/102/103）；纯观察项 5 处（UI-46/57/58/61 部分/69 部分）
