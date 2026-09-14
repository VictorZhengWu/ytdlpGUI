/* 前端应用：纯渲染 + API 调用，不含业务逻辑（命令构建/校验均在后端）。 */
"use strict";

const $ = sel => document.querySelector(sel);
const state = {
  registry: null, flagMap: new Map(), activeSection: null,
  options: {},           // 用户当前选项 {flag: value}（常用/高级共用）
  jobs: new Map(), lang: "zh",
  panel: "queue",        // 左下面板当前页：queue | history
  groupFlagTo: new Map(),  // flag → 互斥组（元数据来自后端 conflicts.groups）
  mixed: new Map(),        // flag → Set<对端>（元数据来自后端 conflicts.mixed）
  triEls: new Map(),       // 互斥组 → 三态控件
  inputs: new Map(),       // flag → 输入控件（互斥清除时同步界面）
};

// ---------- 互斥元数据：直接消费后端 /api/options 的 conflicts（前后端单一数据源） ----------

function buildConflicts() {
  const conflicts = state.registry.conflicts || { groups: [], mixed: [] };
  conflicts.groups.forEach(g => {
    // 界面未展示的成员（UI_HIDE 项）不参与三态组；任一侧过滤后为空则整组跳过
    const on = g.on.filter(f => state.flagMap.has(f));
    const off = g.off.filter(f => state.flagMap.has(f));
    if (!on.length || !off.length) return;
    const gg = { id: g.id, on, off, flags: [...on, ...off] };
    gg.flags.forEach(f => state.groupFlagTo.set(f, gg));
  });
  conflicts.mixed.forEach(([a, b]) => {
    if (!state.flagMap.has(a) || !state.flagMap.has(b)) return;  // 界面未展示的选项跳过
    if (!state.mixed.has(a)) state.mixed.set(a, new Set());
    if (!state.mixed.has(b)) state.mixed.set(b, new Set());
    state.mixed.get(a).add(b);
    state.mixed.get(b).add(a);
  });
  // tripwire：双侧必须非空（后端结构断言的镜像）
  state.groupFlagTo.forEach(g => { if (!g.on.length || !g.off.length) console.warn("互斥组极性未定:", g.flags); });
}

// ---------- 初始化 ----------

async function boot() {
  await loadI18n();
  const cfg = await api("/api/config");
  state.lang = AVAILABLE_LANGS.includes(cfg.language) ? cfg.language : "en";
  $("#langSelect").value = state.lang;
  LANG = state.lang; applyI18n();

  const reg = await api("/api/options");
  state.registry = reg;
  for (const sec of reg.sections)
    for (const opt of sec.options) {
      state.flagMap.set(opt.flag, opt);
      if (opt.short) state.flagMap.set(opt.short, opt);
    }

  buildConflicts();
  buildQuickPanel(cfg);
  buildOptionTabs();
  loadPresets();
  bindEvents();
  setAdvanceMode(localStorage.getItem("ytdlpgui-advance") === "1");
  $("#infoDlg .nav-up").title = t("prevResult");
  $("#infoDlg .nav-down").title = t("nextResult");
  refreshJobs();
  setInterval(refreshJobs, 5000);
}

async function api(path, opts) {
  const method = (opts && opts.method) || (opts && opts.body !== undefined ? "POST" : "GET");
  const init = { method, headers: { "Content-Type": "application/json" } };
  if (opts && opts.body !== undefined && method !== "GET" && method !== "DELETE") init.body = JSON.stringify(opts.body);
  const res = await fetch(path, init);
  if (!res.ok) {
    let msg = res.statusText;
    try { msg = (await res.json()).detail || msg; } catch {}
    throw new Error(msg);
  }
  return res.json();
}

// ---------- 精简 / 高级模式 ----------

function setAdvanceMode(on) {
  document.body.classList.toggle("simple", !on);
  $("#advanceLabelOn").classList.toggle("hidden", on);
  $("#advanceLabelOff").classList.toggle("hidden", !on);
  localStorage.setItem("ytdlpgui-advance", on ? "1" : "0");
  updateCmdPreview();
}

// ---------- 常用设置面板 ----------

function quickText(obj) {  // 多语言软编码取值：中文回退 zh，其它语言缺失时回退 en（不回退中文）
  if (typeof obj === "string") return obj;
  if (state.lang === "zh") return obj.zh || obj.en;
  return obj[state.lang] || obj.en || obj.zh;
}

function buildQuickPanel(cfg) {
  const panel = $("#quickPanel");
  panel.innerHTML = "";
  QUICK_GROUPS.forEach(group => {
    const g = document.createElement("div");
    g.className = "quick-group";
    const title = document.createElement("div");
    title.className = "quick-group-title";
    title.textContent = quickText(group.title);
    const grid = document.createElement("div");
    grid.className = "quick-grid";
    group.items.forEach(item => grid.appendChild(makeQuickControl(item, cfg)));
    g.append(title, grid);
    panel.appendChild(g);
  });
}

function makeQuickControl(item, cfg) {
  const div = document.createElement("div");
  div.className = "quick-item";
  const label = quickText(item.label);

  // 目录类：输入框 + 浏览按钮（服务器端目录选择对话框）
  if (item.widget === "dir") {
    const key = item.configKey || "download_dir";
    const lab = document.createElement("label");
    lab.textContent = label;
    const row = document.createElement("div");
    row.className = "dir-row";
    const input = document.createElement("input");
    input.type = "text"; input.dataset.cfgkey = key;
    input.id = key === "history_path" ? "historyPathInput" : "downloadDirInput";
    input.value = cfg?.[key] ?? "";
    input.onchange = () => api("/api/config", { method: "PUT", body: { [key]: input.value.trim() } }).catch(showErr);
    const browse = document.createElement("button");
    browse.className = "btn ghost sm";
    browse.textContent = t("browse");
    browse.onclick = () => openDirPicker(input.value.trim()).then(p => {
      if (p) { input.value = p; return api("/api/config", { method: "PUT", body: { [key]: p } }); }
    }).catch(showErr);
    row.append(input, browse);
    div.append(lab, row);
    return div;
  }

  if (item.widget === "check") {
    const lab = document.createElement("label");
    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.onchange = () => setOption(item.flag, cb.checked ? true : undefined);
    lab.append(cb, document.createTextNode(label));
    div.appendChild(lab);
    return div;
  }

  const lab = document.createElement("label");
  lab.textContent = label;
  div.appendChild(lab);

  if (item.widget === "select") {
    const sel = document.createElement("select");
    sel.className = "glass-select";
    sel.style.width = "100%";
    item.choices.forEach(c => {
      const o = document.createElement("option");
      o.value = c.v;
      o.textContent = typeof c.l === "string" ? c.l : quickText(c.l);
      sel.appendChild(o);
    });
    sel.value = item.def ?? "";
    const flag = item.flag === "__quality" ? "--format-sort" : item.flag;
    sel.onchange = () => {
      if (flag === "--format-sort") {
        setOption("-f", undefined);
        const fmtSel = document.querySelector("#quickPanel select[data-flag='--merge-output-format']");
        if (sel.value === "best") setOption(flag, undefined);
        else setOption(flag, `res:${sel.value}` + (fmtSel && fmtSel.value === "mp4" ? ",vext:mp4,aext:m4a" : ""));
      } else if (sel.value === "") {
        setOption(flag, undefined);
      } else {
        setOption(flag, sel.value);
      }
    };
    sel.dataset.flag = flag;
    div.appendChild(sel);
  } else {
    const input = document.createElement("input");
    input.type = "text";
    input.placeholder = (item.ph && quickText(item.ph)) || "";
    input.oninput = () => setOption(item.flag, input.value.trim() || undefined);
    div.appendChild(input);
  }
  return div;
}

// ---------- 目录选择对话框 ----------

let dirPickerResolve = null;

function openDirPicker(startPath) {
  const dlg = $("#dirDlg");
  dlg.showModal();
  loadDir(startPath || "");
  return new Promise(resolve => { dirPickerResolve = resolve; });
}

async function loadDir(path) {
  try {
    const info = await api("/api/fs/list" + (path ? `?path=${encodeURIComponent(path)}` : ""), { method: "GET" });
    $("#dirCurrent").textContent = info.path;
    const list = $("#dirList");
    list.innerHTML = "";
    info.dirs.forEach(entry => {
      const b = document.createElement("button");
      b.className = "dir-entry";
      b.textContent = "📁 " + entry.name;
      b.onclick = () => loadDir(entry.path);   // 完整路径由后端按平台拼接
      list.appendChild(b);
    });
    if (!info.dirs.length) list.innerHTML = `<div class="empty-hint">${t("noSubdirs")}</div>`;
    list.dataset.path = info.path;
    $("#dirUp").onclick = () => loadDir(info.parent ?? "");
    $("#dirUp").disabled = !info.parent;
    // 快捷位置：主目录 / 根 / 局域网共享与网盘挂载点（标签前端按语言本地化）
    const roots = $("#dirRoots");
    roots.innerHTML = "";
    (info.roots || []).forEach(r => {
      const b = document.createElement("button");
      b.className = "dir-root";
      b.textContent = r.kind === "home" ? t("rootHome")
        : r.kind === "net" ? `${t("netShare")} ${r.name}`
        : r.name;
      b.title = r.path;
      b.onclick = () => loadDir(r.path);
      roots.appendChild(b);
    });
  } catch (e) { showErr(e); }
}

function showErr(e) { console.error(e); alert(e.message || String(e)); }

// ---------- 高级选项面板 ----------

function sectionLabel(name) {
  const secs = t("sections");
  return (typeof secs === "object" && secs[name]) || name.replace(/ Options$/, "");
}

function buildOptionTabs() {
  const tabs = $("#optTabs"), panels = $("#optPanels");
  tabs.innerHTML = ""; panels.innerHTML = "";
  state.registry.sections.forEach((sec, i) => {
    if (!sec.options.length) return;
    const btn = document.createElement("button");
    btn.textContent = sectionLabel(sec.name);
    btn.dataset.section = sec.name;
    btn.onclick = () => activateSection(sec.name);
    tabs.appendChild(btn);

    const panel = document.createElement("div");
    panel.className = "opt-panel" + (i === 0 ? "" : " hidden");
    panel.dataset.section = sec.name;
    const grid = document.createElement("div");
    grid.className = "opt-grid";
    const renderedGroups = new Set();  // 每次构建独立记录，避免重复构建（如语言切换）时误跳过
    sec.options.forEach(opt => {
      const g = state.groupFlagTo.get(opt.flag);
      if (g && renderedGroups.has(g.id)) return;   // 互斥组只渲染一次
      grid.appendChild(makeOptionControl(opt, g));
      if (g) renderedGroups.add(g.id);
    });
    panel.appendChild(grid);
    panels.appendChild(panel);
    if (i === 0) state.activeSection = sec.name;
  });
  tabs.querySelector("button")?.classList.add("active");
}

function makeOptionControl(opt, group) {
  const item = document.createElement("div");
  item.className = "opt-item";
  const primary = group ? (group.on[0] || group.off[0]) : opt.flag;
  item.dataset.flag = primary;
  const id = "opt-" + primary.replace(/[^a-z0-9]+/gi, "-");

  const tooltip = state.lang === "zh"
    ? `${opt.zh || opt.description}\n${opt.description}` + (opt.example ? `\n示例: ${opt.flag} ${opt.example}` : "")
    : opt.description + (opt.example ? `\nExample: ${opt.flag} ${opt.example}` : "");

  const label = document.createElement("label");
  label.htmlFor = id;
  const flagEl = document.createElement("span");
  flagEl.className = "opt-flag";
  // 互斥组：合并显示 开/关 两侧的全部 flag 名
  const names = group
    ? [...group.on, ...group.off].map(f => { const m = state.flagMap.get(f); return (m && m.short ? m.short + ", " : "") + f; }).join(" / ")
    : (opt.short ? opt.short + ", " : "") + opt.flag;
  flagEl.textContent = names;
  const zh = document.createElement("span");
  zh.className = "opt-zh";
  zh.textContent = opt.zh || "";
  const desc = document.createElement("span");
  desc.className = "opt-desc";
  desc.textContent = opt.description;
  label.append(flagEl, zh, desc);
  label.title = tooltip;

  if (group) {
    // 三态：默认 / 开 / 关（互斥组）
    const tri = document.createElement("div");
    tri.className = "tri";
    [["", "optDefault"], ["on", "optOn"], ["off", "optOff"]].forEach(([v, key]) => {
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = t(key);
      b.dataset.v = v;
      b.onclick = e => { e.preventDefault(); setGroupSide(group, v || null); };
      tri.appendChild(b);
    });
    tri.querySelector("button").classList.add("active");
    state.triEls.set(group.id, tri);
    label.appendChild(tri);
    item.append(label);
  } else if (!opt.metavar) {
    const cb = document.createElement("input");
    cb.type = "checkbox"; cb.id = id; cb.title = tooltip;
    cb.onchange = () => setOption(opt.flag, cb.checked ? true : undefined);
    state.inputs.set(opt.flag, cb);
    item.append(cb, label);
  } else {
    const input = document.createElement("input");
    input.type = "text"; input.id = id;
    input.placeholder = opt.nargs
      ? (state.lang === "zh" ? `需 ${opt.nargs} 个取值（空格分隔）` : `${opt.nargs} values (space-separated)`)
      : (opt.example || opt.metavar);
    input.title = tooltip;
    input.oninput = () => setOption(opt.flag, input.value.trim() || undefined);
    state.inputs.set(opt.flag, input);
    label.appendChild(input);
    item.append(label);
  }
  // 点击条目（非输入控件）展开/收起完整描述
  item.addEventListener("click", e => {
    if (e.target.tagName !== "INPUT" && e.target.tagName !== "BUTTON") item.classList.toggle("expanded");
  });
  return item;
}

// 三态互斥组写入：side = on | off | null(默认)
function setGroupSide(g, side) {
  if (side && !g[side].length) { console.warn("组", g.flags, "的", side, "侧为空，忽略"); return; }
  g.flags.forEach(f => delete state.options[f]);
  if (side === "on") state.options[g.on[0]] = true;
  if (side === "off") state.options[g.off[0]] = true;
  syncGroupUI(g, side);
  updateCmdPreview();
}

function syncGroupUI(g, side) {
  const tri = state.triEls.get(g.id);
  if (tri) [...tri.children].forEach(b => b.classList.toggle("active", b.dataset.v === (side || "")));
  const item = document.querySelector(`.opt-item[data-flag="${CSS.escape(g.on[0] || g.off[0])}"] .opt-flag`);
  if (item) item.classList.toggle("set", !!side);
}

function setOption(flag, value) {
  if (value === undefined) delete state.options[flag];
  else state.options[flag] = value;
  // 值型 --X 与 布尔 --no-X / 手工冲突对：设一端遍历清除全部对端
  const others = state.mixed.get(flag);
  if (value !== undefined && others) {
    others.forEach(other => {
      if (state.options[other] !== undefined) {
        delete state.options[other];
        const otherInput = state.inputs.get(other);
        if (otherInput) { otherInput.value = ""; otherInput.checked = false; }
      }
    });
  }
  // 高亮：互斥组任一成员置位即整组高亮
  const flags = state.groupFlagTo.get(flag)?.flags || [flag];
  flags.forEach(f => document.querySelectorAll(`.opt-item[data-flag="${CSS.escape(f)}"] .opt-flag`)
    .forEach(el => el.classList.toggle("set", state.options[f] !== undefined || state.options[flag] !== undefined)));
  updateCmdPreview();
}

function activateSection(name) {
  state.activeSection = name;
  document.querySelectorAll("#optTabs button").forEach(b =>
    b.classList.toggle("active", b.dataset.section === name));
  document.querySelectorAll("#optPanels .opt-panel").forEach(p =>
    p.classList.toggle("hidden", p.dataset.section !== name));
}

function filterOptions(q) {
  const panels = $("#optPanels");
  if (!q) {
    panels.classList.remove("searching");
    document.querySelectorAll("#optPanels .opt-panel").forEach(p => p.classList.remove("hidden"));
    activateSection(state.activeSection);
    return;
  }
  panels.classList.add("searching");
  const ql = q.toLowerCase();
  document.querySelectorAll(".opt-item").forEach(item => {
    const opt = state.flagMap.get(item.dataset.flag);
    if (!opt) return;
    const g = state.groupFlagTo.get(item.dataset.flag);
    const nameHit = [item.dataset.flag, ...(g ? g.flags : [])]
      .some(f => f.toLowerCase().includes(ql) || (state.flagMap.get(f)?.short || "").includes(ql));
    const hit = nameHit || opt.description.toLowerCase().includes(ql) || (opt.zh || "").includes(q);
    item.classList.toggle("hit", hit);
  });
  document.querySelectorAll("#optPanels .opt-panel").forEach(p => p.classList.remove("hidden"));
}

function clearOptions() {
  state.options = {};
  document.querySelectorAll("#advancedPanel .opt-item input").forEach(el => { el.checked = false; el.value = ""; });
  state.triEls.forEach(tri => [...tri.children].forEach((b, i) => b.classList.toggle("active", i === 0)));
  document.querySelectorAll(".opt-flag.set").forEach(el => el.classList.remove("set"));
  api("/api/config", { method: "GET" }).then(cfg => buildQuickPanel(cfg));
  updateCmdPreview();
}

// ---------- 命令预览（反映当前模式的真实命令） ----------

function updateCmdPreview() {
  // 精简模式：yt-dlp <链接>（不带选项）
  if (document.body.classList.contains("simple")) {
    const urls = $("#urlInput").value.split("\n").map(s => s.trim()).filter(Boolean);
    $("#cmdPreview").textContent = "yt-dlp " + (urls.join(" ") || "<video link>");
    return;
  }
  const parts = ["yt-dlp"];
  for (const [flag, value] of Object.entries(state.options)) {
    const opt = state.flagMap.get(flag);
    if (!opt) continue;
    if (value === true) { parts.push(opt.flag); continue; }
    // 多值/多参数选项按后端真实拼装方式预览（重复 flag）
    if (opt.multi || opt.nargs) {
      String(value).split(",").map(s => s.trim()).filter(Boolean)
        .forEach(v => parts.push(opt.flag, v));
    } else {
      parts.push(opt.flag, String(value));
    }
  }
  $("#cmdPreview").textContent = parts.join(" ");
}

// ---------- 信息查询（浮动窗口展示，逐条查询多行 URL，右上角 ↑↓ 导航 + 关闭） ----------

async function fetchInfo() {
  const urls = $("#urlInput").value.split("\n").map(s => s.trim()).filter(Boolean);
  if (!urls.length) return alert(t("emptyUrl"));
  const dlg = $("#infoDlg"), box = $("#infoBody");
  if (!dlg.open) dlg.show();          // 非模态浮动窗口：不打断主界面操作
  box.innerHTML = "";

  const up = dlg.querySelector(".nav-up"), down = dlg.querySelector(".nav-down");
  const pos = dlg.querySelector(".info-nav .pos");
  up.disabled = down.disabled = true;
  pos.textContent = "";

  const blocks = [];
  for (const url of urls.slice(0, 10)) {
    const block = document.createElement("div");
    block.className = "info-result";
    if (urls.length > 1) {
      const head = document.createElement("div");
      head.className = "vtitle";
      head.style.cssText = "color:var(--accent);font-size:12px;word-break:break-all";
      head.textContent = url;
      block.appendChild(head);
    }
    const holder = document.createElement("div");
    holder.textContent = "…";
    block.appendChild(holder);
    box.appendChild(block);
    blocks.push(block);
    try {
      const info = await api("/api/formats?url=" + encodeURIComponent(url), { method: "GET" });
      holder.innerHTML = "";
      renderInfo(info, holder);
    } catch (e) { holder.textContent = t("fetchFail") + ": " + e.message; }
  }

  let idx = 0;
  const show = i => {
    idx = Math.max(0, Math.min(blocks.length - 1, i));
    box.scrollTo({ top: blocks[idx].offsetTop - 4, behavior: "smooth" });
    up.disabled = idx === 0;
    down.disabled = idx === blocks.length - 1;
    pos.textContent = `${idx + 1} / ${blocks.length}`;
  };
  up.onclick = () => show(idx - 1);
  down.onclick = () => show(idx + 1);
  show(0);
}

function renderInfo(info, box) {
  if (info.type === "playlist") {
    box.innerHTML = `<div class="vtitle">${esc(info.title)} — ${t("playlist")} (${info.count} ${t("videos")})</div>`
      + info.entries.map(e => `<div>• ${esc(e.title || e.id)}</div>`).join("");
    return;
  }
  const head = document.createElement("div");
  head.className = "vtitle";
  head.textContent = info.title;
  const meta = document.createElement("div");
  meta.style.cssText = "font-size:12.5px;color:var(--muted);margin-bottom:6px";
  meta.textContent = `${t("duration")}: ${fmtDur(info.duration)}  ${t("uploader")}: ${info.uploader}`;
  const hint = document.createElement("div");
  hint.style.cssText = "font-size:11.5px;color:var(--muted)";
  hint.textContent = t("clickToUse");
  const table = document.createElement("table");
  table.innerHTML = `<tr><th>ID</th><th>${t("colExt")}</th><th>${t("colRes")}</th><th>fps</th><th>${t("colVideo")}</th><th>${t("colAudio")}</th><th>${t("colSize")}</th></tr>`
    + info.formats.map(f =>
      `<tr data-fid="${esc(f.format_id)}" title="${esc(f.note)}">
        <td><b>${esc(f.format_id)}</b></td><td>${esc(f.ext)}</td><td>${esc(f.resolution)}</td>
        <td>${f.fps || ""}</td><td>${esc(f.vcodec)}</td><td>${esc(f.acodec)}</td>
        <td>${fmtSize(f.filesize)}</td></tr>`).join("");
  table.querySelectorAll("tr[data-fid]").forEach(tr => tr.onclick = () => {
    table.querySelectorAll("tr").forEach(r => r.classList.remove("selected"));
    tr.classList.add("selected");
    setOption("-f", tr.dataset.fid);
    // 同步回显到高级面板的 --format 输入框（-f 是其短名）
    const fmtInput = state.inputs.get("--format");
    if (fmtInput) fmtInput.value = tr.dataset.fid;
  });
  box.append(head, meta, hint, table);
}

// ---------- 下载任务 ----------

async function startDownload() {
  const urls = $("#urlInput").value.split("\n").map(s => s.trim()).filter(Boolean);
  if (!urls.length) return alert(t("emptyUrl"));
  // 精简模式：纯净下载，只使用 yt-dlp <url>，不附加任何选项
  const opts = document.body.classList.contains("simple") ? {} : state.options;
  try {
    const job = await api("/api/jobs", { body: { urls, options: opts } });
    addJobCard(job);
    followJob(job.id);
    setPanel("queue");
  } catch (e) { alert(t("dlFail") + ": " + e.message); }
}

async function refreshJobs() {
  try {
    const jobs = await api("/api/jobs", { method: "GET" });
    jobs.forEach(j => {
      if (!state.jobs.has(j.id)) { addJobCard(j); if (["queued", "running"].includes(j.status)) followJob(j.id); }
    });
    if (state.panel === "history") loadHistory();
  } catch {}
}

function addJobCard(job) {
  $(".job-list .empty-hint")?.remove();
  const el = document.createElement("div");
  el.className = "job"; el.dataset.id = job.id;
  el.innerHTML = `
    <div class="job-head">
      <span class="job-url">${esc(job.urls.join(" "))}</span>
      <span class="badge ${job.status}">${t("statusMap")[job.status] || job.status}</span>
    </div>
    <div class="progressbar"><div></div></div>
    <div class="job-stats"><span class="pct">0%</span><span class="spd"></span><span class="eta"></span><span class="fp"></span></div>
    <pre class="hidden"></pre>
    <div class="btnrow">
      <button class="btn ghost sm log-btn">${t("toggleLog")}</button>
      <button class="btn ghost sm danger cancel-btn">${t("cancelJob")}</button>
    </div>`;
  el.querySelector(".log-btn").onclick = () => el.querySelector("pre").classList.toggle("hidden");
  el.querySelector(".cancel-btn").onclick = () => api(`/api/jobs/${job.id}/cancel`, { body: {} }).catch(() => {});
  $("#jobList").prepend(el);
  state.jobs.set(job.id, {
    el,
    badge: el.querySelector(".badge"), bar: el.querySelector(".progressbar > div"),
    pct: el.querySelector(".pct"), spd: el.querySelector(".spd"), eta: el.querySelector(".eta"),
    fp: el.querySelector(".fp"), pre: el.querySelector("pre"), done: false,
  });
  updateJobCard(job.id, job);
}

function updateJobCard(id, data) {
  const j = state.jobs.get(id);
  if (!j) return;
  if (data.status) { j.badge.className = "badge " + data.status; j.badge.textContent = t("statusMap")[data.status] || data.status; }
  if (typeof data.progress === "number") { j.bar.style.width = data.progress + "%"; j.pct.textContent = data.progress.toFixed(1) + "%"; }
  if (data.speed) j.spd.textContent = data.speed;
  if (data.eta) j.eta.textContent = "ETA " + data.eta;
  if (data.filepath) j.fp.textContent = data.filepath;
}

function followJob(id) {
  const j = state.jobs.get(id);
  if (!j || j.done) return;
  const es = new EventSource(`/api/jobs/${id}/events`);
  es.onmessage = ev => {
    const [kind, payload] = JSON.parse(ev.data);
    if (kind === "log") { j.pre.textContent += payload + "\n"; j.pre.scrollTop = j.pre.scrollHeight; }
    else if (kind === "file") updateJobCard(id, { filepath: payload });
    else if (kind === "progress") updateJobCard(id, payload);
    else if (kind === "status") {
      updateJobCard(id, { status: payload });
      if (["done", "error", "canceled"].includes(payload)) {
        j.done = true; es.close();
        if (state.panel === "history") loadHistory();
      }
    }
  };
  es.onerror = () => { if (j.done) es.close(); };
}

// ---------- 下载历史 ----------

function setPanel(name) {
  state.panel = name;
  $("#tabQueue").classList.toggle("active", name === "queue");
  $("#tabHistory").classList.toggle("active", name === "history");
  $("#jobList").classList.toggle("hidden", name !== "queue");
  $("#historyList").classList.toggle("hidden", name !== "history");
  $("#btnClearHistory").classList.toggle("hidden", name !== "history");
  if (name === "history") loadHistory();
}

async function loadHistory() {
  const box = $("#historyList");
  try {
    const entries = await api("/api/history", { method: "GET" });
    box.innerHTML = "";
    if (!entries.length) { box.innerHTML = `<div class="empty-hint">${t("emptyHistory")}</div>`; return; }
    const table = document.createElement("table");
    table.className = "history-table";
    entries.forEach(e => {
      const tr = document.createElement("tr");
      const badge = `<span class="badge ${e.status}">${t("statusMap")[e.status] || e.status}</span>`;
      const titles = e.titles.length ? esc(e.titles.join(" / ")) : esc(e.urls.join(" "));
      const err = e.error ? `<div class="h-err">${esc(e.error.slice(0, 120))}</div>` : "";
      tr.innerHTML = `
        <td class="h-time">${esc(e.time)}</td>
        <td>
          <div class="h-title">${titles}</div>
          <div class="h-url">${esc(e.urls[0] || "")}${e.urls.length > 1 ? ` (+${e.urls.length - 1})` : ""}</div>
          ${e.filepath ? `<div class="h-path">${esc(e.filepath)}</div>` : ""}
          ${err}
        </td>
        <td>${badge}</td>`;
      table.appendChild(tr);
    });
    box.appendChild(table);
  } catch (e) { box.innerHTML = `<div class="empty-hint">${esc(e.message)}</div>`; }
}

// ---------- 预设 ----------

async function loadPresets() {
  const presets = await api("/api/presets", { method: "GET" });
  const sel = $("#presetSelect");
  sel.innerHTML = `<option value="" data-i18n="presetNone">${t("presetNone")}</option>`;
  Object.keys(presets).forEach(name => {
    const o = document.createElement("option");
    o.value = name; o.textContent = name;
    sel.appendChild(o);
  });
}

function applyPresetOptions(opts) {
  clearOptions();
  for (const [flag, value] of Object.entries(opts)) {
    const opt = state.flagMap.get(flag);
    if (!opt) continue;
    const g = state.groupFlagTo.get(flag);
    if (g) { setGroupSide(g, g.on.includes(flag) ? "on" : "off"); continue; }
    state.options[flag] = value;
    const input = state.inputs.get(flag);
    if (input) { if (input.type === "checkbox") input.checked = true; else input.value = value; }
  }
  updateCmdPreview();
}

// ---------- 事件绑定 ----------

function bindEvents() {
  $("#btnInfo").onclick = fetchInfo;
  $("#btnDownload").onclick = startDownload;
  $("#urlInput").oninput = () => { if (document.body.classList.contains("simple")) updateCmdPreview(); };
  $("#infoDlg .nav-close").onclick = () => $("#infoDlg").close();
  $("#optSearch").oninput = e => filterOptions(e.target.value.trim());
  $("#btnClearOpts").onclick = clearOptions;

  $("#btnAdvance").onclick = () => setAdvanceMode(document.body.classList.contains("simple"));

  $("#tabQueue").onclick = () => setPanel("queue");
  $("#tabHistory").onclick = () => setPanel("history");
  $("#btnClearHistory").onclick = async () => {
    if (!confirm(t("clearHistoryConfirm"))) return;
    await api("/api/history", { method: "DELETE" });
    loadHistory();
  };

  const setTab = quick => {
    $("#modeQuick").classList.toggle("active", quick);
    $("#modeAdvanced").classList.toggle("active", !quick);
    $("#quickPanel").classList.toggle("hidden", !quick);
    $("#advancedPanel").classList.toggle("hidden", quick);
  };
  $("#modeQuick").onclick = () => setTab(true);
  $("#modeAdvanced").onclick = () => setTab(false);

  $("#dirChoose").onclick = () => {
    $("#dirDlg").close();
    dirPickerResolve?.($("#dirList").dataset.path || "");
    dirPickerResolve = null;
  };
  const dirCancel = $("#dirDlg button[value='cancel']");
  dirCancel.type = "button";
  dirCancel.onclick = () => $("#dirDlg").close();  // close 事件统一 resolve(null)
  $("#dirDlg").addEventListener("close", () => {
    if (dirPickerResolve) { dirPickerResolve(null); dirPickerResolve = null; }
  });

  $("#presetSelect").onchange = async e => {
    if (!e.target.value) return;
    applyPresetOptions(await api("/api/presets", { method: "GET" }).then(p => p[e.target.value] || {}));
  };
  $("#btnPresetSave").onclick = async () => {
    const name = prompt(t("presetName"));
    if (!name) return;
    await api("/api/presets", { body: { name, options: state.options } });
    loadPresets();
  };
  $("#btnPresetDelete").onclick = async () => {
    const name = $("#presetSelect").value;
    if (!name || !confirm(t("deleteConfirm"))) return;
    await api(`/api/presets/${encodeURIComponent(name)}`, { method: "DELETE" });
    loadPresets();
  };

  $("#langSelect").onchange = async e => {
    LANG = state.lang = e.target.value;
    applyI18n();
    const up = $("#infoDlg .nav-up"), down = $("#infoDlg .nav-down");
    up.title = t("prevResult"); down.title = t("nextResult");
    api("/api/config", { method: "PUT", body: { language: LANG } });
    buildQuickPanel(await api("/api/config", { method: "GET" }));
    buildOptionTabs();
    refreshJobs();
  };
}

// ---------- 工具 ----------

function esc(s) { const d = document.createElement("div"); d.textContent = s ?? ""; return d.innerHTML; }
function fmtDur(s) {
  if (!s) return "";
  const h = Math.floor(s / 3600), m = Math.floor(s % 3600 / 60), sec = Math.floor(s % 60);
  return (h ? h + ":" : "") + String(m).padStart(2, "0") + ":" + String(sec).padStart(2, "0");
}
function fmtSize(b) {
  if (!b) return "";
  const u = ["B", "KiB", "MiB", "GiB"];
  let i = 0; while (b >= 1024 && i < 3) { b /= 1024; i++; }
  return b.toFixed(b >= 100 || i === 0 ? 0 : 1) + u[i];
}

boot().catch(e => {
  console.error(e);
  const banner = document.createElement("div");
  banner.style.cssText = "position:fixed;inset:auto 12px 12px;z-index:9999;padding:12px 16px;border-radius:10px;" +
    "background:#7f1d1d;color:#fecaca;font-size:13px;box-shadow:0 8px 30px rgba(0,0,0,.5)";
  banner.textContent = "程序初始化失败: " + (e && e.message ? e.message : e) + "（请 Ctrl+F5 强制刷新；若持续出现请查看控制台日志）";
  document.body.appendChild(banner);
});
