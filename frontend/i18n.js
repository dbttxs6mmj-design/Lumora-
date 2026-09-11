// 引路人 Lumora · 前端 i18n（選語言 → 整個介面換語言）
// 原文 = 繁中（離線預設＋缺鍵 fallback）；其他語言向 /api/v1/ui_strings?lang= 取
// （後端用 LLM 翻譯整包、有快取）。RTL（阿拉伯/波斯/烏爾都）自動切 dir=rtl。
(function () {
  "use strict";

  // 與後端 yinluren/ui_i18n.py 的 UI_STRINGS keys 必須一致
  const SOURCE = {
    slogan: "指路與守心的那盞燈",
    start_journey: "開始旅程",
    ob1_title: "先彼此認識",
    name: "姓名",
    name_hint: "※ 將用於《姓名學》子引擎為您算命之用，不會被分享給任何第三方。",
    nickname: "稱呼（可略）",
    name_ph: "請輸入您的姓名",
    nickname_ph: "您希望引路人怎麼稱呼您",
    gender: "性別",
    male: "男",
    female: "女",
    next: "下一步",
    prev: "上一步",
    ob2_title: "您的生辰",
    birth_date: "出生日期",
    birth_date_hint: "不確定可先跳過，未來可在設定補上。",
    ob3_title: "出生時辰",
    birth_time_mode_label: "時辰知悉程度",
    time_exact: "精確時間",
    time_shichen: "約時辰",
    time_unknown: "不清楚",
    birth_time_label: "時間（民用時，後端會自動校正真太陽時）",
    hour: "小時",
    minute: "分",
    birth_shichen_label: "選擇時辰",
    shichen_approx_hint: "引路人將取時辰中點作為命盤基礎。",
    time_unknown_hint: "引路人將在推演中啟動《明鍵鏡心》出生時辰反推機制，結合您的問題、性格與人生軌跡，推算最可能的時辰，無需擔心。",
    birth_time_hint: "時辰未知亦可，但有時辰才能完整啟動八字、紫微。",
    ob4_title: "出生地點",
    country: "國家",
    please_select: "請選擇",
    region: "地區 / 省 / 城市",
    select_country_first: "請先選國家",
    birthplace_hint: "用於真太陽時的經度校正，出生地的地氣對命理推演影響深遠。",
    country_search_ph: "輸入搜尋國家…",
    province_search_ph: "輸入搜尋地區…",
    ob5_title: "您目前的角色",
    occupation: "職業大類",
    occupation_detail: "細項（可略）",
    occupation_ph: "例如：軟體後端工程師",
    occupation_hint: "引路人會用此資訊客製化推演視角。",
    enter: "進入引路人",
    login_slogan: "輸入密碼，開啟你的引路人",
    login_ph: "請輸入密碼",
    login_btn: "進入",
    login_err: "密碼錯誤，請再試一次",
    login_err_net: "連線出現問題，請稍後再試",
    target_add: "合盤：計算與他者的關係",
    target_title: "他者命盤（合盤）",
    target_intro: "填入你想合盤的對象資料，引路人將推演「你與對方」的關係。時辰不確定沒關係——按「不確定」即自動啟動出生時辰反推。",
    target_relation: "與你的關係",
    target_name: "對方稱呼（可略）",
    target_name_ph: "例如：太太、阿明、對方",
    target_unknown_hint: "✔ 已選「不確定」——引路人將啟動出生時辰反推專業流程，依你與對方的互動、性格與已知事件，推算對方最可能的時辰（附候選與置信度），無需擔心。",
    target_birthplace: "出生地（可略）",
    target_birthplace_ph: "例如：新疆若羌、台北",
    target_save: "確定合盤",
    target_clear: "清除合盤",
    target_saved: "已設定合盤對象，接下來的提問將計算你與對方的關係",
    target_cleared: "已清除合盤對象",
    target_need_relation: "請先選擇與對方的關係",
    target_chip_prefix: "正在合盤：",
    rel_spouse: "配偶", rel_partner: "伴侶", rel_crush: "曖昧對象／喜歡的人",
    rel_father: "父親", rel_mother: "母親", rel_child: "子女", rel_sibling: "兄弟姊妹",
    rel_friend: "朋友", rel_colleague: "同事", rel_boss: "上司／長官", rel_other: "其他",
    home_hint: "把任何事都問引路人",
    composer_ph: "請問引路人……",
    guide: "引路人",
    history: "對話歷史",
    no_history: "尚無對話紀錄",
    other: "其他",
    settings: "設定",
    about: "關於引路人",
    photo: "拍照",
    gallery: "從圖庫選擇照片／圖片／影片",
    upload: "上傳檔案",
    cancel: "取消",
    about_text: "由 Final Kernel 真 AI 引擎驅動，整合 18 部子引擎與 92 部古籍知識，從個人運勢到國運大勢，萬事皆可問、皆可聊、皆可答。",
    loading: "引路人正在推演……",
    translating: "正在切換語言…",
    new_chat: "新對話",
    save: "儲存",
    redo_all: "重新填寫所有資料",
    birthplace: "出生地",
    not_filled: "未填",
    nickname_short: "稱呼",
    confirm_redo: "確定要重新填寫嗎？對話歷史會保留。",
    toast_name_required: "請填寫姓名",
    toast_gender_required: "請選擇性別",
    toast_name_required2: "姓名為必填",
    toast_saved: "已儲存",
    toast_image_selected: "已選擇：{name}（視覺分析模組整合中）",
    toast_file_selected: "已選擇：{name}（檔案分析模組整合中）",
    err_incomplete_prefix: "推演暫時無法完成：",
    err_incomplete: "推演暫時無法完成，請稍後再試。",
    err_connection: "連線出現問題，請確認後端是否啟動。",
    engines_summary: "共 {total} 部子引擎（{primary} Primary + {secondary} Secondary + {meta} Meta）已全數啟動。",
    rb_state: "現況",
    rb_perspectives: "多術觀點",
    rb_resonance: "共振點",
    rb_divergence: "分歧點",
    rb_risk: "風險焦點",
    rb_timing: "時機窗口",
    rb_guidance: "引路人提點",
    aria_menu: "選單",
    aria_new: "新對話",
    aria_attach: "附加",
    aria_send: "送出",
    aria_back: "返回",
  };

  const RTL = new Set(["ar", "fa", "ur"]);
  const cache = { "zh-Hant": SOURCE };
  let current = SOURCE;
  let currentLang = "zh-Hant";

  function isDefault(lang) {
    return !lang || ["zh", "zh-tw", "zh-hant", "zh-hant-tw"].includes(String(lang).toLowerCase());
  }

  function t(key, vars) {
    let s = current && current[key] != null ? current[key] : (SOURCE[key] != null ? SOURCE[key] : key);
    if (vars) for (const k in vars) s = s.split("{" + k + "}").join(vars[k]);
    return s;
  }

  function applyI18n(root) {
    root = root || document;
    root.querySelectorAll("[data-i18n]").forEach(function (el) { el.textContent = t(el.getAttribute("data-i18n")); });
    root.querySelectorAll("[data-i18n-ph]").forEach(function (el) { el.setAttribute("placeholder", t(el.getAttribute("data-i18n-ph"))); });
    root.querySelectorAll("[data-i18n-aria]").forEach(function (el) { el.setAttribute("aria-label", t(el.getAttribute("data-i18n-aria"))); });
  }

  function apiBase() {
    return location.port === "5173"
      ? location.protocol + "//" + location.hostname + ":8000/api/v1"
      : location.origin + "/api/v1";
  }

  async function setLanguage(lang) {
    lang = lang || "zh-Hant";
    currentLang = lang;
    document.documentElement.setAttribute("lang", lang);
    document.documentElement.setAttribute("dir", RTL.has(String(lang).split("-")[0].toLowerCase()) ? "rtl" : "ltr");
    if (isDefault(lang)) { current = SOURCE; applyI18n(document); return; }
    if (cache[lang]) { current = cache[lang]; applyI18n(document); return; }
    try {
      const res = await fetch(apiBase() + "/ui_strings?lang=" + encodeURIComponent(lang));
      const data = await res.json();
      const strings = data && data.strings ? data.strings : null;
      current = strings ? Object.assign({}, SOURCE, strings) : SOURCE;
      cache[lang] = current;
    } catch (e) {
      current = SOURCE; // 取不到就退回繁中，不卡死
    }
    applyI18n(document);
  }

  window.LUMORA_I18N = {
    t: t,
    applyI18n: applyI18n,
    setLanguage: setLanguage,
    isDefault: isDefault,
    get lang() { return currentLang; },
  };
})();
