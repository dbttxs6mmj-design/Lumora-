// ======================================================================
// 引路人 Lumora · 前端 SPA · v3.0
// 模組：場景動畫 / 5步onboarding / 聊天 / 抽屜 / +號菜單 / API 呼叫
// 雙層記憶：localStorage（持久）+ 記憶體（會話）
// ======================================================================

(function () {
  "use strict";

  // 後端 API 位址：
  //   LUMORA_API_BASE  → 由部署平台注入（Vercel 環境變數 → window.__LUMORA_API__）
  //   本地開發 :5173   → 打同機 :8000
  //   同源（Render/VPS 單服務模式）→ 同源 /api/v1
  const API_BASE = (
    (window.__LUMORA_API__ || "").trim()         // Vercel/CDN 注入
    || (location.port === "5173" ? `${location.protocol}//${location.hostname}:8000/api/v1` : "")
    || `${location.origin}/api/v1`
  );

  // i18n 捷徑：t("key") / t("key", {name:"…"})；i18n.js 未載入時回 key 本身
  const t = (k, vars) => (window.LUMORA_I18N ? window.LUMORA_I18N.t(k, vars) : k);

  // Basic Auth 過期攔截：nginx 回 401 時跳回根目錄觸發瀏覽器重新跳登入框
  function _authGuard(res) {
    if (res && res.status === 401) {
      location.replace(location.origin + "/");
      throw new Error("auth_expired");
    }
    return res;
  }

  // ==================================================================
  // State
  // ==================================================================
  const STORAGE_KEY = "lumora_v3_state";

  const state = {
    lang: "zh-Hant",
    profile: null,        // { name, sex, birth_date, birth_hour, birth_minute, country, province, occupation_category, ... }
    profileComplete: false,
    chats: [],            // [{ id, title, messages: [...] }]
    activeChatId: null,
    onboardingStep: 1,
    enginesMeta: null,    // 從 /api/v1/engines 取
  };

  // ==================================================================
  // 持久化（雙層記憶之長期層）
  // ==================================================================
  function saveState() {
    try {
      const snapshot = {
        lang: state.lang,
        profile: state.profile,
        profileComplete: state.profileComplete,
        chats: state.chats.map(c => ({
          ...c,
          messages: c.messages.map(({ image, ...rest }) => rest),
        })),
        activeChatId: state.activeChatId,
      };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(snapshot));
    } catch (e) { console.warn("save failed", e); }
  }

  function loadState() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      const s = JSON.parse(raw);
      Object.assign(state, s);
    } catch (e) { console.warn("load failed", e); }
  }

  // ==================================================================
  // DOM helpers
  // ==================================================================
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  function show(screenId) {
    $$(".screen").forEach(s => s.classList.remove("active"));
    $("#" + screenId).classList.add("active");
    window.scrollTo(0, 0);
  }

  function toast(text, ms = 2200) {
    const t = $("#toast");
    t.textContent = text;
    t.classList.add("show");
    clearTimeout(t._timer);
    t._timer = setTimeout(() => t.classList.remove("show"), ms);
  }

  function showLoading(text) {
    $(".loading-text").textContent = text || t("loading");
    $("#loading").classList.add("show");
  }

  function hideLoading() {
    $("#loading").classList.remove("show");
  }

  // ==================================================================
  // 打字泡泡（取代全螢幕 loading，僅在聊天流中顯示三點跳動）
  // ==================================================================
  function showTypingBubble() {
    const list = $("#chat-list");
    if ($("#typing-bubble")) return;
    const el = document.createElement("div");
    el.className = "msg assistant typing";
    el.id = "typing-bubble";
    el.innerHTML = '<span class="dot"></span><span class="dot"></span><span class="dot"></span>';
    list.appendChild(el);
    list.scrollTop = list.scrollHeight;
  }

  function removeTypingBubble() {
    const el = $("#typing-bubble");
    if (el) el.remove();
  }

  // ==================================================================
  // 路由邏輯：預設走推演，只有明確是閒聊才走 /chat
  // （引路人的用戶幾乎所有訊息都是命理相關）
  // ==================================================================

  // 明確閒聊關鍵詞 → 走 /chat
  const CHAT_ONLY_PATTERNS = [
    /^(你好|嗨|hi|hello|哈囉|早安|午安|晚安)[！!。,，\s]*$/i,
    /^(謝謝|感謝|多謝|thx|thanks)[！!。,，\s]*$/i,
    /^(好的|好|ok|okay|嗯|哦|哈|呵|哇)[！!。,，\s]*$/i,
    /^(再見|掰掰|bye|晚點見)[！!。,，\s]*$/i,
  ];

  // 明確要推演的關鍵詞（擴充版）
  const DIVINATION_KEYWORDS = [
    // 直接占卜術語
    "占卜","起卦","卜卦","卦象","算命","命盤","命理","批命","看命",
    "塔羅","抽牌","抽卦","抽簽","求籤","抽一","抽個","靈棋",
    "八字","紫微","六爻","奇門","梅花","六壬","擇日","風水","堪輿","陰宅","祖墳",
    "解夢","面相","掌相","看相","骨相",
    // 請幫我…
    "幫我算","幫我看","幫我占","請算","算算","算一算","算出","算看","幫算",
    // 運勢
    "運勢","流年","大運","小運","年運","月運","週運","今日運","今天運",
    // 吉凶/方位
    "吉凶","宜忌","化解","開運","旺","煞","桃花","財運","貴人","官司","劫數",
    // 時間
    "何時","幾時","何年","幾歲","幾月","幾號","哪年","哪月","哪天",
    // 結果/未來導向
    "會怎樣","會怎麼樣","結果怎樣","結果如何","成果如何","成果會","前景如何",
    "未來如何","未來怎樣","以後怎樣","之後如何","將來如何",
    "有沒有希望","有沒有機會","有沒有","能成功","有希望","有前途",
    "適合嗎","能不能","行不行","好不好","該不該","可不可以","能否","是否能","可否",
    "會不會","到底能","究竟能","有無",
    // 情感/事業/財務
    "這段感情","這份工作","這個投資","這次機會","這件事","這個項目","這個案子",
    "創業","離婚","結婚","婚姻","換工作","轉職","買房","置產","投資",
    // 命格/流年
    "前途","命格","格局","大限","小限","流月","流日","事業運","感情運",
    // 通用未來詢問
    "怎麼看","你看","算一下","看一下","看看","能看出","推演","推算",
  ];

  function isDivinationIntent(text) {
    // 短訊息且符合純閒聊 pattern → 走 chat
    if (text.length <= 15 && CHAT_ONLY_PATTERNS.some(r => r.test(text.trim()))) {
      return false;
    }
    // 命中任一推演關鍵詞 → 走 divine
    if (DIVINATION_KEYWORDS.some(k => text.includes(k))) {
      return true;
    }
    // 預設：長度 > 10 字的問題一律走推演（引路人的用戶幾乎不是來閒聊的）
    return text.length > 10;
  }

  // ==================================================================
  // 場景 SVG（夜色山路 + 雙人剪影 + 古燈）
  // ==================================================================
  function renderScene() {
    const svg = `<svg viewBox="0 0 400 700" preserveAspectRatio="xMidYMax slice" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <radialGradient id="lampGlow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stop-color="#E8923F" stop-opacity="0.9"/>
          <stop offset="40%" stop-color="#C06A2B" stop-opacity="0.5"/>
          <stop offset="100%" stop-color="#C06A2B" stop-opacity="0"/>
        </radialGradient>
        <linearGradient id="mistGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#1a2440" stop-opacity="0"/>
          <stop offset="100%" stop-color="#1a2440" stop-opacity="0.45"/>
        </linearGradient>
        <filter id="softBlur">
          <feGaussianBlur stdDeviation="1.2"/>
        </filter>
      </defs>

      <!-- 遠山 -->
      <path d="M0 480 L0 380 L60 340 L120 360 L180 310 L240 345 L300 320 L360 350 L400 330 L400 480 Z"
            fill="#1a2440" opacity="0.7"/>
      <!-- 中山 -->
      <path d="M0 510 L0 410 L40 390 L90 420 L150 380 L210 410 L280 385 L340 410 L400 395 L400 510 Z"
            fill="#142543" opacity="0.85"/>
      <!-- 近山＋山路 -->
      <path d="M0 700 L0 480 L70 440 L140 470 L220 430 L290 460 L360 440 L400 460 L400 700 Z"
            fill="#0b1530"/>
      <!-- 山路（從遠處向近處延伸）-->
      <path d="M200 470 Q205 540 195 610 Q188 660 200 700"
            stroke="#2a3556" stroke-width="22" fill="none" opacity="0.55"/>
      <path d="M200 470 Q205 540 195 610 Q188 660 200 700"
            stroke="#3a4670" stroke-width="3" fill="none" opacity="0.4" stroke-dasharray="4 8"/>

      <!-- 霧氣 -->
      <rect x="0" y="380" width="400" height="320" fill="url(#mistGrad)" opacity="0.6"/>

      <!-- 燈光暈 -->
      <circle cx="180" cy="555" r="60" fill="url(#lampGlow)">
        <animate attributeName="r" values="58;64;58" dur="3.5s" repeatCount="indefinite"/>
        <animate attributeName="opacity" values="0.85;1;0.85" dur="3.5s" repeatCount="indefinite"/>
      </circle>

      <!-- 雙人剪影（左：引路人持燈；右：旅人）-->
      <g filter="url(#softBlur)">
        <!-- 引路人 -->
        <path d="M170 510
                 Q172 502 175 498
                 Q178 494 175 488
                 Q172 482 175 478
                 Q180 474 182 480
                 Q184 488 182 494
                 L184 504
                 L188 540
                 L184 580
                 L186 620
                 L180 622
                 L177 580
                 L172 540
                 L168 525 Z" fill="#050b18"/>
        <!-- 引路人持燈的手＋燈 -->
        <line x1="184" y1="525" x2="178" y2="555" stroke="#050b18" stroke-width="3"/>
        <rect x="174" y="552" width="8" height="10" fill="#050b18"/>
        <circle cx="178" cy="558" r="5" fill="#E8923F" opacity="0.95"/>

        <!-- 旅人 -->
        <path d="M212 514
                 Q214 506 217 502
                 Q220 498 217 492
                 Q214 486 217 482
                 Q222 478 224 484
                 Q226 492 224 498
                 L226 508
                 L230 544
                 L226 584
                 L228 622
                 L222 624
                 L219 584
                 L214 544
                 L210 528 Z" fill="#0a1428"/>
      </g>

      <!-- 星星閃爍 -->
      <g fill="#F5EFE6" opacity="0.65">
        <circle cx="50" cy="60" r="1.2"><animate attributeName="opacity" values="0.3;0.9;0.3" dur="2.8s" repeatCount="indefinite"/></circle>
        <circle cx="120" cy="40" r="0.8"><animate attributeName="opacity" values="0.4;1;0.4" dur="3.4s" repeatCount="indefinite"/></circle>
        <circle cx="260" cy="80" r="1"><animate attributeName="opacity" values="0.5;0.9;0.5" dur="2.2s" repeatCount="indefinite"/></circle>
        <circle cx="340" cy="50" r="1.3"><animate attributeName="opacity" values="0.3;1;0.3" dur="3.8s" repeatCount="indefinite"/></circle>
        <circle cx="180" cy="100" r="0.9"><animate attributeName="opacity" values="0.4;0.8;0.4" dur="2.6s" repeatCount="indefinite"/></circle>
        <circle cx="80" cy="140" r="0.7"><animate attributeName="opacity" values="0.3;0.7;0.3" dur="3s" repeatCount="indefinite"/></circle>
        <circle cx="300" cy="160" r="1.1"><animate attributeName="opacity" values="0.4;0.9;0.4" dur="2.5s" repeatCount="indefinite"/></circle>
        <circle cx="370" cy="120" r="0.8"><animate attributeName="opacity" values="0.3;0.8;0.3" dur="3.2s" repeatCount="indefinite"/></circle>
      </g>
    </svg>`;
    $("#scene-container").innerHTML = svg;
  }

  // ==================================================================
  // Onboarding
  // ==================================================================
  function setupOnboarding() {
    // 動態填入小時、分鐘
    const hourSel = $("#ob-birth-hour");
    LUMORA_DATA.hours.forEach(h => {
      const opt = document.createElement("option");
      opt.value = h;
      opt.textContent = h.toString().padStart(2, "0") + " 時";
      hourSel.appendChild(opt);
    });
    const minSel = $("#ob-birth-minute");
    LUMORA_DATA.minutes.forEach(m => {
      const opt = document.createElement("option");
      opt.value = m;
      opt.textContent = m.toString().padStart(2, "0") + " 分";
      minSel.appendChild(opt);
    });

    // 國家 + 搜尋
    const countrySel = $("#ob-country");
    const countrySearch = $("#ob-country-search");
    const provSel = $("#ob-province");
    const provSearch = $("#ob-province-search");

    function _populateCountry() {
      countrySel.innerHTML = '<option value="">' + t("please_select") + '</option>';
      const q = countrySearch.value.toLowerCase();
      LUMORA_DATA.countries.forEach(c => {
        if (!q || c.name.includes(q) || c.code.toLowerCase().includes(q)) {
          const opt = document.createElement("option");
          opt.value = c.code;
          opt.textContent = c.name;
          countrySel.appendChild(opt);
        }
      });
    }
    _populateCountry();
    countrySearch.addEventListener("input", _populateCountry);

    function _populateProvince() {
      const q = provSearch.value.toLowerCase();
      const c = LUMORA_DATA.countries.find(x => x.code === countrySel.value);
      if (!c) return;
      const prev = provSel.value;
      provSel.innerHTML = '<option value="">' + t("please_select") + '</option>';
      c.provinces.forEach(p => {
        if (!q || p.name.toLowerCase().includes(q)) {
          const opt = document.createElement("option");
          opt.value = JSON.stringify(p);
          opt.textContent = p.name;
          provSel.appendChild(opt);
        }
      });
      if (prev) {
        const match = Array.from(provSel.options).find(o => o.value === prev);
        if (match) provSel.value = prev;
      }
    }

    countrySel.addEventListener("change", () => {
      provSearch.value = "";
      provSearch.disabled = !countrySel.value;
      provSel.innerHTML = '<option value="">' + t("please_select") + '</option>';
      const c = LUMORA_DATA.countries.find(x => x.code === countrySel.value);
      if (c) {
        c.provinces.forEach(p => {
          const opt = document.createElement("option");
          opt.value = JSON.stringify(p);
          opt.textContent = p.name;
          provSel.appendChild(opt);
        });
      }
    });
    provSearch.addEventListener("input", _populateProvince);

    // 職業
    const occSel = $("#ob-occupation");
    LUMORA_DATA.occupations.forEach(o => {
      const opt = document.createElement("option");
      opt.value = o;
      opt.textContent = o;
      occSel.appendChild(opt);
    });

    // seg-radio（支援多組：性別、時辰模式）
    $$(".seg-radio .seg").forEach(btn => {
      btn.addEventListener("click", () => {
        btn.closest(".seg-radio").querySelectorAll(".seg").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        // 時辰模式切換
        if (btn.dataset.timeMode) _onTimeModeChange(btn.dataset.timeMode);
      });
    });

    // 時辰模式顯示控制
    function _onTimeModeChange(mode) {
      const exactWrap = $("#ob-exact-time-wrap");
      const shichenWrap = $("#ob-shichen-wrap");
      const unknownHint = $("#ob-unknown-time-hint");
      exactWrap.style.display = mode === "exact" ? "" : "none";
      shichenWrap.style.display = mode === "shichen" ? "" : "none";
      unknownHint.style.display = mode === "unknown" ? "" : "none";
    }
    // 預設精確模式：隱藏其他
    _onTimeModeChange("exact");

    // 下一步
    $$(".next-btn").forEach(btn => {
      btn.addEventListener("click", () => goStep(parseInt(btn.dataset.next, 10)));
    });
    $$(".back-btn").forEach(btn => {
      btn.addEventListener("click", () => goStep(parseInt(btn.dataset.back, 10)));
    });

    $("#btn-finish-onboarding").addEventListener("click", finishOnboarding);
  }

  function goStep(n) {
    // 校驗當前步
    const cur = state.onboardingStep;
    if (n > cur) {
      if (!validateStep(cur)) return;
    }
    state.onboardingStep = n;
    $$(".ob-step").forEach(s => s.classList.remove("active"));
    $$(`.ob-step[data-step="${n}"]`).forEach(s => s.classList.add("active"));
    // 進度點
    $$(".ob-progress .dot").forEach((d, i) => {
      d.classList.remove("active", "done");
      if (i + 1 < n) d.classList.add("done");
      else if (i + 1 === n) d.classList.add("active");
    });
  }

  function validateStep(n) {
    if (n === 1) {
      const name = $("#ob-name").value.trim();
      if (!name) { toast(t("toast_name_required")); return false; }
      const sex = $$(".seg-radio .seg.active")[0];
      if (!sex) { toast(t("toast_gender_required")); return false; }
    }
    return true;
  }

  function finishOnboarding() {
    if (!validateStep(1)) { goStep(1); return; }
    const sexBtn = $(".seg-radio .seg.active[data-sex]");
    const provRaw = $("#ob-province").value;
    let prov = null, lng = null;
    if (provRaw) {
      try { prov = JSON.parse(provRaw); lng = prov.lng; } catch (e) {}
    }
    const country = LUMORA_DATA.countries.find(c => c.code === $("#ob-country").value);

    // 出生時辰解析
    const timeMode = ($("#ob-time-mode-group .seg.active") || {}).dataset?.timeMode || "exact";
    let birth_hour = null, birth_minute = null, birth_shichen = null, birth_time_unknown = false;
    if (timeMode === "exact") {
      birth_hour = $("#ob-birth-hour").value !== "" ? parseInt($("#ob-birth-hour").value, 10) : null;
      birth_minute = $("#ob-birth-minute").value !== "" ? parseInt($("#ob-birth-minute").value, 10) : null;
    } else if (timeMode === "shichen") {
      const shichenEl = $("#ob-birth-shichen");
      birth_shichen = shichenEl.value || null;
      const sel = shichenEl.selectedOptions[0];
      if (sel && sel.dataset.hour !== undefined) {
        birth_hour = parseInt(sel.dataset.hour, 10);
        birth_minute = 0;
      }
    } else {
      birth_time_unknown = true;
    }

    state.profile = {
      name: $("#ob-name").value.trim(),
      nickname: $("#ob-nickname").value.trim() || null,
      sex: sexBtn ? sexBtn.dataset.sex : "M",
      birth_date: $("#ob-birth-date").value || null,
      birth_hour,
      birth_minute,
      birth_shichen: birth_shichen || null,
      birth_time_unknown,
      birth_time_mode: timeMode,
      country: country ? country.name : null,
      province: prov ? prov.name : null,
      birth_longitude: lng,
      birth_location: prov && country ? `${country.name} · ${prov.name}` : null,
      occupation_category: $("#ob-occupation").value || null,
      occupation_keyword: $("#ob-occupation-detail").value.trim() || null,
      timezone: "Asia/Taipei",
    };
    state.profileComplete = true;
    saveState();
    show("screen-home");
  }

  // ==================================================================
  // 聊天
  // ==================================================================
  function newChat(firstMessage) {
    const id = "c_" + Date.now();
    const chat = {
      id,
      title: firstMessage ? firstMessage.slice(0, 24) : t("new_chat"),
      messages: [],
      created_at: new Date().toISOString(),
    };
    state.chats.unshift(chat);
    state.activeChatId = id;
    saveState();
    return chat;
  }

  function getActiveChat() {
    return state.chats.find(c => c.id === state.activeChatId);
  }

  function renderChatList() {
    const chat = getActiveChat();
    const list = $("#chat-list");
    list.innerHTML = "";
    if (!chat) return;

    $("#chat-title").textContent = chat.title || t("guide");

    chat.messages.forEach((msg, idx) => {
      const el = document.createElement("div");
      el.className = "msg " + msg.role;
      if (msg.role === "user") {
        if (msg.image) {
          const img = document.createElement("img");
          img.src = msg.image;
          img.className = "msg-image";
          img.alt = "圖片";
          el.appendChild(img);
        }
        if (msg.content) {
          const textEl = document.createElement("div");
          textEl.textContent = msg.content;
          el.appendChild(textEl);
        }
        attachLongPress(el, idx);
      } else if (msg.role === "assistant") {
        el.innerHTML = renderAssistantContent(msg);
        attachLongPress(el, idx);
      }
      list.appendChild(el);
    });
    list.scrollTop = list.scrollHeight;
  }

  function renderAssistantContent(msg) {
    // 若有結構化結果就用結構化顯示
    if (msg.result) {
      const r = msg.result;
      let html = "";
        if (r.core_conclusion) {
        html += `<div>${escapeHtml(r.core_conclusion)}</div>`;
      }
      if (r.state) {
        html += `<div class="reading-block"><div class="reading-block-title">${t("rb_state")}</div><div>${escapeHtml(r.state)}</div></div>`;
      }
      if (r.multi_perspectives && r.multi_perspectives.length) {
        html += `<div class="reading-block"><div class="reading-block-title">${t("rb_perspectives")}</div><ul>${r.multi_perspectives.map(p => `<li>${escapeHtml(p.view || p)}</li>`).join("")}</ul></div>`;
      }
      if (r.resonance_points && r.resonance_points.length) {
        html += `<div class="reading-block"><div class="reading-block-title">${t("rb_resonance")}</div><ul>${r.resonance_points.map(p => `<li>${escapeHtml(p)}</li>`).join("")}</ul></div>`;
      }
      if (r.divergence_points && r.divergence_points.length) {
        html += `<div class="reading-block"><div class="reading-block-title">${t("rb_divergence")}</div><ul>${r.divergence_points.map(p => `<li>${escapeHtml(p)}</li>`).join("")}</ul></div>`;
      }
      if (r.risk_focus && r.risk_focus.length) {
        html += `<div class="reading-block"><div class="reading-block-title">${t("rb_risk")}</div><ul>${r.risk_focus.map(p => `<li>${escapeHtml(p)}</li>`).join("")}</ul></div>`;
      }
      if (r.timing_window) {
        html += `<div class="reading-block"><div class="reading-block-title">${t("rb_timing")}</div><div>${escapeHtml(r.timing_window)}</div></div>`;
      }
      if (r.yinluren_guidance) {
        html += `<div class="reading-block"><div class="reading-block-title">${t("rb_guidance")}</div><div>${escapeHtml(r.yinluren_guidance)}</div></div>`;
      }
      return html;
    }
    return escapeHtml(msg.content || "");
  }

  function escapeHtml(s) {
    if (typeof s !== "string") s = JSON.stringify(s);
    return s.replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));
  }

  async function sendQuestion(question) {
    let chat = getActiveChat();
    if (!chat) chat = newChat(question);

    // 加入用戶訊息（含圖片）
    const userMsg = { role: "user", content: question };
    let _imageB64 = null;
    if (_pendingImage) {
      userMsg.image = _pendingImage.dataUrl;
      // 擷取純 base64（去掉 data:image/...;base64, 前綴）
      _imageB64 = _pendingImage.dataUrl.split(",")[1] || null;
      _pendingImage = null;
      const preview = $("#pending-image-preview");
      if (preview) preview.remove();
    }
    chat.messages.push(userMsg);
    if (!chat.title || chat.title === "新對話") {
      chat.title = question.slice(0, 24);
    }
    saveState();
    show("screen-chat");
    renderChatList();
    showTypingBubble();

    // 近 6 輪歷史（只傳文字，不傳圖片 dataUrl）
    const history = chat.messages.slice(-12, -1).map(m => ({ role: m.role, content: m.content || "" }));

    const useDivination = isDivinationIntent(question);

    try {
      let data;
      if (useDivination) {
        // 有圖片時先跑 vision 分析並顯示描述
        let visionDesc = "";
        if (_imageB64) {
          try {
            const vRes = _authGuard(await fetch(`${API_BASE}/vision/analyze`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              credentials: "include",
              body: JSON.stringify({ image_b64: _imageB64, question, language: state.lang }),
            }));
            const vData = await vRes.json();
            if (vData.status === "ok" && vData.description) {
              visionDesc = vData.description;
            }
          } catch (_) {}
        }
        const res = _authGuard(await fetch(`${API_BASE}/divine`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({
            question,
            profile: state.profile,
            chat_history: history,
            language: state.lang,
            use_thinking: false,
            image_b64: _imageB64 || undefined,
          }),
        }));
        data = await res.json();
        if (data.status === "ok" && data.result) {
          chat.messages.push({
            role: "assistant",
            content: data.result.core_conclusion || "",
            result: data.result,
            meta: data._meta,
          });
        } else if (data.detail) {
          chat.messages.push({ role: "assistant", content: t("err_incomplete_prefix") + data.detail });
        } else {
          chat.messages.push({ role: "assistant", content: data.error || t("err_incomplete") });
        }
      } else {
        const res = _authGuard(await fetch(`${API_BASE}/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({
            message: question,
            profile: state.profile,
            chat_history: history,
            language: state.lang,
          }),
        }));
        data = await res.json();
        if (data.status === "ok" && data.reply) {
          chat.messages.push({ role: "assistant", content: data.reply });
        } else if (data.detail) {
          chat.messages.push({ role: "assistant", content: data.detail });
        } else {
          chat.messages.push({ role: "assistant", content: data.error || t("err_incomplete") });
        }
      }
    } catch (err) {
      if (err.message !== "auth_expired") {
        chat.messages.push({ role: "assistant", content: t("err_connection") });
      }
    } finally {
      removeTypingBubble();
      saveState();
      renderChatList();
    }
  }

  function renderChatHistory() {
    const wrap = $("#chat-history");
    wrap.innerHTML = "";
    if (!state.chats.length) {
      wrap.innerHTML = '<div class="drawer-list-empty">' + t("no_history") + '</div>';
      return;
    }
    state.chats.forEach(c => {
      const item = document.createElement("div");
      item.className = "drawer-list-item" + (c.id === state.activeChatId ? " active" : "");
      item.textContent = c.title || t("new_chat");
      item.addEventListener("click", () => {
        state.activeChatId = c.id;
        saveState();
        closeDrawer();
        show("screen-chat");
        renderChatList();
      });
      wrap.appendChild(item);
    });
  }

  // ==================================================================
  // Drawer / Modal / Attach Menu
  // ==================================================================
  function openDrawer() {
    renderChatHistory();
    $("#drawer").classList.add("open");
  }
  function closeDrawer() { $("#drawer").classList.remove("open"); }

  function openModal(id) { $("#" + id).classList.add("open"); }
  function closeModal(id) { $("#" + id).classList.remove("open"); }

  function openAttach() { $("#attach-menu").classList.add("open"); }
  function closeAttach() { $("#attach-menu").classList.remove("open"); }

  // ==================================================================
  // 設定 Modal
  // ==================================================================
  function renderSettings() {
    const p = state.profile || {};
    const html = `
      <div class="field">
        <label>${t("name")}</label>
        <input type="text" id="set-name" value="${escapeHtml(p.name || "")}">
      </div>
      <div class="field">
        <label>${t("nickname_short")}</label>
        <input type="text" id="set-nickname" value="${escapeHtml(p.nickname || "")}">
      </div>
      <div class="field">
        <label>${t("gender")}</label>
        <div class="seg-radio">
          <button class="seg ${p.sex === 'M' ? 'active' : ''}" data-set-sex="M">${t("male")}</button>
          <button class="seg ${p.sex === 'F' ? 'active' : ''}" data-set-sex="F">${t("female")}</button>
        </div>
      </div>
      <div class="field">
        <label>${t("birthplace")}</label>
        <div style="color:var(--c-paper-dim); font-size:14px">${escapeHtml(p.birth_location || t("not_filled"))}</div>
      </div>
      <div class="field">
        <label>${t("occupation")}</label>
        <div style="color:var(--c-paper-dim); font-size:14px">${escapeHtml(p.occupation_category || t("not_filled"))}${p.occupation_keyword ? " · " + escapeHtml(p.occupation_keyword) : ""}</div>
      </div>
      <button class="primary-btn" style="width:100%; margin-top:8px" id="set-save">${t("save")}</button>
      <button class="ghost-btn" style="width:100%; margin-top:10px" id="set-redo">${t("redo_all")}</button>
    `;
    $("#settings-body").innerHTML = html;
    $$('[data-set-sex]').forEach(b => b.addEventListener("click", () => {
      $$('[data-set-sex]').forEach(x => x.classList.remove("active"));
      b.classList.add("active");
    }));
    $("#set-save").addEventListener("click", () => {
      const name = $("#set-name").value.trim();
      if (!name) { toast(t("toast_name_required2")); return; }
      state.profile.name = name;
      state.profile.nickname = $("#set-nickname").value.trim() || null;
      const sex = $$('[data-set-sex].active')[0];
      if (sex) state.profile.sex = sex.dataset.setSex;
      saveState();
      toast(t("toast_saved"));
      closeModal("modal-settings");
    });
    $("#set-redo").addEventListener("click", () => {
      if (!confirm(t("confirm_redo"))) return;
      state.onboardingStep = 1;
      $$(".ob-step").forEach(s => s.classList.remove("active"));
      $$('.ob-step[data-step="1"]').forEach(s => s.classList.add("active"));
      $$(".ob-progress .dot").forEach((d, i) => {
        d.classList.remove("active", "done");
        if (i === 0) d.classList.add("active");
      });
      closeModal("modal-settings");
      show("screen-onboarding");
    });
  }

  // ==================================================================
  // 載入引擎資訊
  // ==================================================================
  async function loadEnginesInfo() {
    try {
      const res = _authGuard(await fetch(`${API_BASE}/engines`, { credentials: "include" }));
      const data = await res.json();
      state.enginesMeta = data;
      // 寫進關於頁
      const s = data.summary;
      $("#about-engines").textContent = t("engines_summary", { total: s.total, primary: s.primary, secondary: s.secondary, meta: s.meta });
    } catch (e) {
      console.warn("engines info load failed", e);
    }
  }

  // ==================================================================
  // 附加（拍照 / 圖庫 / 檔案）
  // ==================================================================
  function setupAttach() {
    $("#btn-plus-home").addEventListener("click", openAttach);
    $("#btn-plus-chat").addEventListener("click", openAttach);
    $("#attach-cancel").addEventListener("click", closeAttach);
    $(".attach-mask").addEventListener("click", closeAttach);

    $$(".attach-opt").forEach(btn => {
      btn.addEventListener("click", () => {
        const type = btn.dataset.attach;
        closeAttach();
        if (type === "camera") {
          // Web 環境用 capture="environment"
          const inp = $("#file-input-image");
          inp.setAttribute("capture", "environment");
          inp.click();
        } else if (type === "gallery") {
          const inp = $("#file-input-image");
          inp.removeAttribute("capture");
          inp.click();
        } else if (type === "file") {
          $("#file-input-doc").click();
        }
      });
    });

    $("#file-input-image").addEventListener("change", (e) => {
      const f = e.target.files[0]; if (!f) return;
      const reader = new FileReader();
      reader.onload = (ev) => {
        _pendingImage = { dataUrl: ev.target.result, name: f.name };
        _showPendingImage();
      };
      reader.readAsDataURL(f);
      e.target.value = "";
    });
    $("#file-input-doc").addEventListener("change", async (e) => {
      const f = e.target.files[0]; if (!f) return;
      toast(t("toast_file_selected", { name: f.name }));
      e.target.value = "";
    });
  }

  // ==================================================================
  // 待傳圖片預覽
  // ==================================================================
  let _pendingImage = null;

  function _showPendingImage() {
    // Always remove any stale preview first
    const existing = $("#pending-image-preview");
    if (existing) existing.remove();

    const preview = document.createElement("div");
    preview.id = "pending-image-preview";
    preview.className = "pending-image-preview";
    const img = document.createElement("img");
    img.alt = "預覽";
    const rmBtn = document.createElement("button");
    rmBtn.className = "pending-image-remove";
    rmBtn.textContent = "×";
    rmBtn.addEventListener("click", () => {
      _pendingImage = null;
      preview.remove();
    });
    preview.appendChild(img);
    preview.appendChild(rmBtn);
    // Append to body — CSS position:fixed pins it above the composer on any screen
    document.body.appendChild(preview);
    preview.querySelector("img").src = _pendingImage.dataUrl;
  }

  // ==================================================================
  // 長按 / 右鍵選單
  // ==================================================================
  let _lpTimer = null;

  function attachLongPress(el, msgIdx) {
    // Touch 長按
    el.addEventListener("touchstart", (e) => {
      _lpTimer = setTimeout(() => { _lpTimer = null; showContextMenu(el, e.touches[0], msgIdx); }, 520);
    }, { passive: true });
    el.addEventListener("touchend", () => { clearTimeout(_lpTimer); _lpTimer = null; });
    el.addEventListener("touchmove", () => { clearTimeout(_lpTimer); _lpTimer = null; });
    // 桌面右鍵
    el.addEventListener("contextmenu", (e) => {
      e.preventDefault();
      showContextMenu(el, e, msgIdx);
    });
    // 雙擊 emoji 反應（桌面）
    el.addEventListener("dblclick", () => showReactionPicker(el));
  }

  function showContextMenu(msgEl, pos, msgIdx) {
    hideContextMenu();
    const isUser = msgEl.classList.contains("user");

    const items = isUser ? [
      { icon: "↩", label: "回覆", fn: () => _replyTo(msgEl) },
      { icon: "📋", label: "複製", fn: () => _copyMsg(msgEl) },
      { icon: "✏️", label: "編輯", fn: () => _editMsg(msgIdx) },
      { icon: "↩️", label: "收回", fn: () => _retractMsg(msgIdx) },
      { icon: "⚠️", label: "回報問題", fn: () => toast("感謝回報！") },
      { icon: "↗️", label: "分享", fn: () => _shareMsg(msgEl) },
    ] : [
      { icon: "↩", label: "回覆", fn: () => _replyTo(msgEl) },
      { icon: "📋", label: "複製", fn: () => _copyMsg(msgEl) },
      { icon: "⚠️", label: "回報問題", fn: () => toast("感謝回報！") },
    ];

    const menu = document.createElement("div");
    menu.id = "context-menu";
    menu.className = "context-menu";
    items.forEach(item => {
      const btn = document.createElement("button");
      btn.className = "context-menu-item";
      btn.innerHTML = `<span class="context-menu-icon">${item.icon}</span><span>${item.label}</span>`;
      btn.addEventListener("click", () => { hideContextMenu(); item.fn(); });
      menu.appendChild(btn);
    });
    document.body.appendChild(menu);

    const rect = msgEl.getBoundingClientRect();
    const mH = items.length * 46 + 8;
    const top = rect.top > mH + 16 ? rect.top - mH - 8 : rect.bottom + 8;
    const left = Math.max(8, Math.min(window.innerWidth - 196, isUser ? rect.right - 188 : rect.left));
    menu.style.cssText = `top:${Math.min(top, window.innerHeight - mH - 8)}px;left:${left}px`;

    setTimeout(() => {
      document.addEventListener("click", hideContextMenu, { once: true });
      document.addEventListener("touchstart", hideContextMenu, { once: true });
    }, 30);
  }

  function hideContextMenu() {
    const m = $("#context-menu");
    if (m) m.remove();
  }

  function _copyMsg(el) {
    navigator.clipboard.writeText(el.innerText || el.textContent || "").catch(() => {});
    toast("已複製");
  }

  function _replyTo(el) {
    const snippet = (el.innerText || el.textContent || "").slice(0, 40).replace(/\n/g, " ");
    const ta = $(".screen.active #chat-input") || $("#chat-input");
    if (ta) { ta.value = `回覆「${snippet}…」\n`; ta.focus(); autosizeTextarea(ta); }
  }

  function _editMsg(idx) {
    const chat = getActiveChat(); if (!chat) return;
    const msg = chat.messages[idx]; if (!msg || msg.role !== "user") return;
    const ta = $("#chat-input");
    if (ta) { ta.value = msg.content; ta.focus(); autosizeTextarea(ta); }
    chat.messages.splice(idx);
    saveState(); renderChatList();
  }

  function _retractMsg(idx) {
    const chat = getActiveChat(); if (!chat) return;
    chat.messages.splice(idx, 1);
    saveState(); renderChatList();
    toast("已收回");
  }

  function _shareMsg(el) {
    const text = el.innerText || el.textContent || "";
    if (navigator.share) {
      navigator.share({ text }).catch(() => {});
    } else {
      navigator.clipboard.writeText(text).catch(() => {});
      toast("已複製分享內容");
    }
  }

  // ==================================================================
  // Emoji 反應（雙擊 / 觸控點兩下）
  // ==================================================================
  const _EMOJIS = ["❤️", "👍", "😂", "😮", "😢", "🙏", "✨", "🔥"];
  let _tapEl = null, _tapTimer = null;

  function setupTapReactions() {
    $("#chat-list").addEventListener("touchend", (e) => {
      const msgEl = e.target.closest(".msg:not(.typing)");
      if (!msgEl) return;
      if (_tapEl === msgEl) {
        clearTimeout(_tapTimer); _tapTimer = null; _tapEl = null;
        showReactionPicker(msgEl);
      } else {
        _tapEl = msgEl;
        _tapTimer = setTimeout(() => { _tapEl = null; _tapTimer = null; }, 320);
      }
    });
  }

  function showReactionPicker(msgEl) {
    hideReactionPicker();
    const picker = document.createElement("div");
    picker.id = "reaction-picker";
    picker.className = "reaction-picker";
    _EMOJIS.forEach(em => {
      const btn = document.createElement("button");
      btn.className = "reaction-emoji-btn";
      btn.textContent = em;
      btn.addEventListener("click", () => { addReaction(msgEl, em); hideReactionPicker(); });
      picker.appendChild(btn);
    });
    document.body.appendChild(picker);

    const rect = msgEl.getBoundingClientRect();
    const isUser = msgEl.classList.contains("user");
    const left = Math.max(8, Math.min(window.innerWidth - 290, isUser ? rect.right - 290 : rect.left));
    picker.style.cssText = `top:${Math.max(8, rect.top - 58)}px;left:${left}px`;

    setTimeout(() => {
      document.addEventListener("click", hideReactionPicker, { once: true });
      document.addEventListener("touchstart", hideReactionPicker, { once: true });
    }, 30);
  }

  function hideReactionPicker() {
    const p = $("#reaction-picker");
    if (p) p.remove();
  }

  function addReaction(msgEl, emoji) {
    let bar = msgEl.querySelector(".reaction-bar");
    if (!bar) {
      bar = document.createElement("div");
      bar.className = "reaction-bar";
      msgEl.appendChild(bar);
    }
    const existing = [...bar.querySelectorAll(".reaction-chip")].find(c => c.dataset.emoji === emoji);
    if (existing) {
      const n = parseInt(existing.querySelector(".reaction-count").textContent) + 1;
      existing.querySelector(".reaction-count").textContent = n;
    } else {
      const chip = document.createElement("button");
      chip.className = "reaction-chip reacted";
      chip.dataset.emoji = emoji;
      chip.innerHTML = `${emoji}<span class="reaction-count">1</span>`;
      chip.addEventListener("click", () => {
        const n = parseInt(chip.querySelector(".reaction-count").textContent) + 1;
        chip.querySelector(".reaction-count").textContent = n;
      });
      bar.appendChild(chip);
    }
  }

  // ==================================================================
  // 輸入框自動調高
  // ==================================================================
  function autosizeTextarea(ta) {
    ta.style.height = "auto";
    ta.style.height = Math.min(ta.scrollHeight, 140) + "px";
  }

  function setupComposer(textareaId, sendBtnId) {
    const ta = $("#" + textareaId);
    const btn = $("#" + sendBtnId);
    ta.addEventListener("input", () => autosizeTextarea(ta));
    // Shift+Enter 送出；單獨 Enter 換行（移動端友善）
    ta.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && e.shiftKey && !e.isComposing) {
        e.preventDefault();
        doSend();
      }
    });
    btn.addEventListener("click", doSend);

    function doSend() {
      const text = ta.value.trim();
      if (!text && !_pendingImage) return;
      ta.value = ""; autosizeTextarea(ta);
      sendQuestion(text);
    }
  }

  // ==================================================================
  // 啟動
  // ==================================================================
  function init() {
    loadState();
    if (window.LUMORA_I18N) { window.LUMORA_I18N.setLanguage(state.lang); }
    renderScene();
    setupOnboarding();
    setupAttach();
    setupComposer("home-input", "btn-send-home");
    setupComposer("chat-input", "btn-send-chat");
    setupTapReactions();

    // 語言
    $$(".lang-btn").forEach(b => {
      b.addEventListener("click", async () => {
        if (b.disabled) return;
        state.lang = b.dataset.lang;
        saveState();
        showLoading(t("translating"));
        try { if (window.LUMORA_I18N) await window.LUMORA_I18N.setLanguage(state.lang); } catch (e) {}
        hideLoading();
        show("screen-intro");
      });
    });

    // 開始旅程
    $("#btn-start-journey").addEventListener("click", () => {
      if (state.profileComplete) {
        show("screen-home");
      } else {
        state.onboardingStep = 1;
        show("screen-onboarding");
      }
    });

    // Header buttons
    $("#btn-menu").addEventListener("click", openDrawer);
    $("#btn-menu-chat").addEventListener("click", openDrawer);
    $("#btn-close-drawer").addEventListener("click", closeDrawer);
    $(".drawer-mask").addEventListener("click", closeDrawer);
    $("#btn-back-chat").addEventListener("click", () => show("screen-home"));

    // 新對話
    $("#btn-new-chat").addEventListener("click", () => {
      state.activeChatId = null;
      saveState();
      show("screen-home");
    });

    // 設定 / 關於
    $("#btn-open-settings").addEventListener("click", () => {
      closeDrawer();
      renderSettings();
      openModal("modal-settings");
    });
    $("#btn-open-about").addEventListener("click", () => {
      closeDrawer();
      openModal("modal-about");
    });
    $$(".close-modal").forEach(b => b.addEventListener("click", () => closeModal(b.dataset.modal)));
    $$(".modal-mask").forEach(m => m.addEventListener("click", () => {
      m.parentElement.classList.remove("open");
    }));

    // 進入點
    if (state.profileComplete) {
      // 已 onboard 過 - 直接進首頁
      show("screen-home");
    } else {
      // 首訪 - 從語言頁開始
      show("screen-lang");
    }

    loadEnginesInfo();
  }

  document.addEventListener("DOMContentLoaded", init);
})();
