// ======================================================================
// 引路人 Lumora · 前端 SPA · v3.0
// 模組：場景動畫 / 5步onboarding / 聊天 / 抽屜 / +號菜單 / API 呼叫
// 雙層記憶：localStorage（持久）+ 記憶體（會話）
// ======================================================================

(function () {
  "use strict";

  // 後端 API：本地兩服務模式(前端 :5173)→ 打 :8000；同源模式(FastAPI 直供／部署)→ 同源 /api/v1
  const API_BASE = (location.port === "5173")
    ? `${location.protocol}//${location.hostname}:8000/api/v1`
    : `${location.origin}/api/v1`;

  // i18n 捷徑：t("key") / t("key", {name:"…"})；i18n.js 未載入時回 key 本身
  const t = (k, vars) => (window.LUMORA_I18N ? window.LUMORA_I18N.t(k, vars) : k);

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
        chats: state.chats,
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

    // 國家
    const countrySel = $("#ob-country");
    LUMORA_DATA.countries.forEach(c => {
      const opt = document.createElement("option");
      opt.value = c.code;
      opt.textContent = c.name;
      countrySel.appendChild(opt);
    });
    countrySel.addEventListener("change", () => {
      const provSel = $("#ob-province");
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

    // 職業
    const occSel = $("#ob-occupation");
    LUMORA_DATA.occupations.forEach(o => {
      const opt = document.createElement("option");
      opt.value = o;
      opt.textContent = o;
      occSel.appendChild(opt);
    });

    // 性別 seg
    $$(".seg-radio .seg").forEach(btn => {
      btn.addEventListener("click", () => {
        $$(".seg-radio .seg").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
      });
    });

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
    const sexBtn = $$(".seg-radio .seg.active")[0];
    const provRaw = $("#ob-province").value;
    let prov = null, lng = null;
    if (provRaw) {
      try { prov = JSON.parse(provRaw); lng = prov.lng; } catch (e) {}
    }
    const country = LUMORA_DATA.countries.find(c => c.code === $("#ob-country").value);

    state.profile = {
      name: $("#ob-name").value.trim(),
      nickname: $("#ob-nickname").value.trim() || null,
      sex: sexBtn ? sexBtn.dataset.sex : "M",
      birth_date: $("#ob-birth-date").value || null,
      birth_hour: $("#ob-birth-hour").value ? parseInt($("#ob-birth-hour").value, 10) : null,
      birth_minute: $("#ob-birth-minute").value ? parseInt($("#ob-birth-minute").value, 10) : null,
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
        el.textContent = msg.content;
      } else if (msg.role === "assistant") {
        el.innerHTML = renderAssistantContent(msg);
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
        html += `<div class="reading-block"><div class="reading-block-title">${t("rb_perspectives")}</div><ul>${r.multi_perspectives.map(p => `<li><b>${escapeHtml(p.engine || "")}</b>：${escapeHtml(p.view || p)}</li>`).join("")}</ul></div>`;
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

    chat.messages.push({ role: "user", content: question });
    if (!chat.title || chat.title === "新對話") {
      chat.title = question.slice(0, 24);
    }
    saveState();
    show("screen-chat");
    renderChatList();

    // 近 6 輪歷史
    const history = chat.messages.slice(-12, -1).map(m => ({ role: m.role, content: m.content }));

    showLoading();
    try {
      const res = await fetch(`${API_BASE}/divine`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question,
          profile: state.profile,
          chat_history: history,
          language: state.lang,
          use_thinking: false,
        }),
      });
      const data = await res.json();
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
    } catch (err) {
      chat.messages.push({ role: "assistant", content: t("err_connection") });
    } finally {
      hideLoading();
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
      const res = await fetch(`${API_BASE}/engines`);
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

    $("#file-input-image").addEventListener("change", async (e) => {
      const f = e.target.files[0]; if (!f) return;
      toast(t("toast_image_selected", { name: f.name }));
      // TODO: POST /api/v1/vision/analyze
      e.target.value = "";
    });
    $("#file-input-doc").addEventListener("change", async (e) => {
      const f = e.target.files[0]; if (!f) return;
      toast(t("toast_file_selected", { name: f.name }));
      // TODO: POST /api/v1/file/analyze
      e.target.value = "";
    });
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
    ta.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {
        e.preventDefault();
        doSend();
      }
    });
    btn.addEventListener("click", doSend);

    function doSend() {
      const text = ta.value.trim();
      if (!text) return;
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
