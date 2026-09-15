/* 界面文案：软编码，语言字典存放于 js/i18n/<lang>.json，启动时加载。
   新增语言 = 添加一个 JSON 文件 + index.html 下拉框加一项，无需改逻辑。 */
"use strict";

const AVAILABLE_LANGS = ["zh", "en", "ja", "ko"];
const I18N = {};
let LANG = "zh";

async function loadI18n() {
  const ver = window.APP_VER || "";
  await Promise.all(AVAILABLE_LANGS.map(async l => {
    try {
      const res = await fetch(`js/i18n/${l}.json?v=${ver}`);
      I18N[l] = await res.json();
    } catch { I18N[l] = {}; }
  }));
}

function t(key) {
  const d = I18N[LANG] || {};
  return d[key] ?? (I18N.zh && I18N.zh[key]) ?? key;
}

function applyI18n() {
  document.documentElement.lang = LANG;
  document.body.dataset.lang = LANG;
  document.title = t("appTitle");
  document.querySelectorAll("[data-i18n]").forEach(el => { el.textContent = t(el.dataset.i18n); });
  document.querySelectorAll("[data-i18n-ph]").forEach(el => { el.placeholder = t(el.dataset.i18nPh); });
}
