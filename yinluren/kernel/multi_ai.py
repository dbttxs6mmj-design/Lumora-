"""
引路人 Lumora — 多 AI 平台交叉驗證（M20-B）
同時呼叫 Claude（Anthropic）和 Gemini（Google），取得補充視角注入推演。
所有外部 AI 視角皆融合進引路人輸出，用戶層永不知曉來源。

M14 模型自動換代（明鑑鏡心）：每個平台維護一條「由新到舊」的偏好鏈，
最新模型排最前——一旦開放即自動採用；當前未開放／未授權／不存在者自動
跳過、改用次新，並由 TTL 快取定期重探，無需改碼即可在新模型開放時自動切換。
此機制對所有大模型一視同仁（Claude／Gemini／…），非僅針對單一平台。
"""
from __future__ import annotations

import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)

_CROSS_SYSTEM = (
    "你是一個客觀的補充視角提供者。"
    "針對以下命理問題，從你的角度給出一個 40-80 字的心理學或行為科學補充洞見。"
    "只給洞見本身，不要解釋方法論，不要提及你是 AI，不要用命理術語。"
)

# ─── M14 模型偏好鏈（由新到舊；最新者排最前，開放即自動採用）───
# 可用 .env 覆蓋整條鏈（逗號分隔）；ANTHROPIC_MODEL / GEMINI_MODEL 若指定單一型號則固定不走鏈。
_ANTHROPIC_CHAIN = [
    "claude-fable-5",            # 最新；目前未對全球開放，開放後此鏈自動採用
    "claude-opus-4-8",          # 當前實際採用之最強可用模型
    "claude-sonnet-4-6",
    "claude-haiku-4-5-20251001",
]
_GEMINI_CHAIN = [
    "gemini-3-pro",             # 最新（若尚未開放則自動跳過）
    "gemini-2.5-pro",
    "gemini-2.0-flash",         # 當前穩定可用
]

# 不可用模型的 TTL 快取：標記後在此秒數內不再嘗試，到期自動重探（偵測是否已開放）。
_RECHECK_SECONDS = float(os.environ.get("MODEL_RECHECK_SECONDS", "21600"))  # 預設 6 小時
_unavailable: dict[str, float] = {}
_unavail_lock = threading.Lock()

# 判定「模型不可用」（未開放／未授權／不存在／停用）之錯誤特徵字
_UNAVAILABLE_MARKERS = (
    "not found", "does not exist", "model_not_found", "invalid model",
    "unknown model", "not supported", "unsupported", "permission",
    "not authorized", "unauthorized", "do not have access", "access denied",
    "not allowed", "not available", "deprecated", "403", "404",
)


def _is_unavailable_error(exc: Exception) -> bool:
    s = str(exc).lower()
    return any(m in s for m in _UNAVAILABLE_MARKERS)


def _mark_unavailable(model: str) -> None:
    with _unavail_lock:
        _unavailable[model] = time.time()


def _skip(model: str) -> bool:
    """該模型是否仍在不可用冷卻期內；TTL 到期則清除並重探。"""
    with _unavail_lock:
        ts = _unavailable.get(model)
        if ts is None:
            return False
        if time.time() - ts > _RECHECK_SECONDS:
            del _unavailable[model]  # 冷卻到期：重探，以偵測新開放（M14）
            return False
        return True


def _resolve_chain(env_pin: str, env_chain: str, default_chain: List[str]) -> List[str]:
    """組出本次要嘗試的模型鏈：env 指定單一型號 > env 自訂整鏈 > 內建鏈；並濾掉冷卻中的。"""
    pin = os.environ.get(env_pin, "").strip()
    if pin:
        return [pin]  # 明確指定單一型號：尊重之、不走自動換代
    raw = os.environ.get(env_chain, "").strip()
    chain = [m.strip() for m in raw.split(",") if m.strip()] if raw else list(default_chain)
    active = [m for m in chain if not _skip(m)]
    return active or chain  # 全在冷卻期：仍回完整鏈，至少試一次（避免完全啞火）


def _call_with_chain(chain: List[str], call: Callable[[str], str], platform: str) -> str:
    """依鏈逐一嘗試 call(model)；遇「不可用」錯誤標記並降級，其他錯誤即放棄（best-effort）。"""
    for model in chain:
        try:
            return (call(model) or "").strip()
        except Exception as exc:
            if _is_unavailable_error(exc):
                _mark_unavailable(model)
                logger.info("%s 模型 %s 暫不可用，自動降級：%s", platform, model, exc)
                continue
            logger.warning("%s cross-val failed (%s): %s", platform, model, exc)
            return ""
    logger.warning("%s 偏好鏈全部不可用：%s", platform, chain)
    return ""


def _ask_claude(question: str, profile_summary: str, api_key: str) -> str:
    """透過 Anthropic SDK 呼叫 Claude（M14 自動換代鏈），取得補充視角。"""
    try:
        import anthropic
    except Exception as exc:
        logger.warning("anthropic SDK 不可用：%s", exc)
        return ""
    client = anthropic.Anthropic(api_key=api_key)

    def _call(model: str) -> str:
        msg = client.messages.create(
            model=model,
            max_tokens=200,
            messages=[{
                "role": "user",
                "content": (
                    f"{_CROSS_SYSTEM}\n\n"
                    f"問題：{question}\n用戶背景：{profile_summary}"
                ),
            }],
        )
        return msg.content[0].text or ""

    chain = _resolve_chain("ANTHROPIC_MODEL", "ANTHROPIC_MODEL_CHAIN", _ANTHROPIC_CHAIN)
    return _call_with_chain(chain, _call, "Claude")


def _ask_gemini(question: str, profile_summary: str, api_key: str) -> str:
    """透過 Google OpenAI-相容端點呼叫 Gemini（M14 自動換代鏈），取得補充視角。"""
    try:
        from openai import OpenAI
    except Exception as exc:
        logger.warning("openai SDK 不可用：%s", exc)
        return ""
    # Google 提供 OpenAI 相容 API，無需額外套件
    client = OpenAI(
        api_key=api_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    )

    def _call(model: str) -> str:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _CROSS_SYSTEM},
                {"role": "user", "content": f"問題：{question}\n用戶背景：{profile_summary}"},
            ],
            max_tokens=200,
            timeout=10.0,
        )
        return resp.choices[0].message.content or ""

    chain = _resolve_chain("GEMINI_MODEL", "GEMINI_MODEL_CHAIN", _GEMINI_CHAIN)
    return _call_with_chain(chain, _call, "Gemini")


def fetch_multi_ai_context(
    question: str,
    profile_summary: str,
    anthropic_key: Optional[str] = None,
    gemini_key: Optional[str] = None,
) -> str:
    """
    並行呼叫 Claude + Gemini，合併補充視角為可注入的上下文字串。
    任一 key 缺失則跳過對應服務，全缺則回空字串。
    """
    ant_key = (anthropic_key or os.environ.get("ANTHROPIC_API_KEY", "")).strip()
    gem_key = (gemini_key or os.environ.get("GEMINI_API_KEY", "")).strip()

    tasks: dict[str, Callable[[], str]] = {}
    if ant_key:
        tasks["claude"] = lambda: _ask_claude(question, profile_summary, ant_key)
    if gem_key:
        tasks["gemini"] = lambda: _ask_gemini(question, profile_summary, gem_key)

    if not tasks:
        return ""

    results: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=len(tasks)) as ex:
        futs = {ex.submit(fn): name for name, fn in tasks.items()}
        for fut in as_completed(futs, timeout=13):
            name = futs[fut]
            try:
                results[name] = fut.result() or ""
            except Exception as exc:
                logger.warning("%s future failed: %s", name, exc)

    parts = [v for v in [results.get("claude"), results.get("gemini")] if v]
    if not parts:
        return ""

    labels = {"claude": "心理學視角", "gemini": "跨文化洞見"}
    lines = []
    for name in ("claude", "gemini"):
        if results.get(name):
            lines.append(f"{labels[name]}：{results[name]}")
    return "【多維交叉洞見】\n" + "\n".join(lines)
