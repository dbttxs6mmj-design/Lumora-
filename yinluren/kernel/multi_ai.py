"""
引路人 Lumora — 多 AI 平台交叉驗證（M20-B）
同時呼叫 Claude（Anthropic）和 Gemini（Google），取得補充視角注入推演。
所有外部 AI 視角皆融合進引路人輸出，用戶層永不知曉來源。
"""
from __future__ import annotations

import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

logger = logging.getLogger(__name__)

_CROSS_SYSTEM = (
    "你是一個客觀的補充視角提供者。"
    "針對以下命理問題，從你的角度給出一個 40-80 字的心理學或行為科學補充洞見。"
    "只給洞見本身，不要解釋方法論，不要提及你是 AI，不要用命理術語。"
)


def _ask_claude(question: str, profile_summary: str, api_key: str) -> str:
    """透過 Anthropic SDK 呼叫 Claude，取得補充視角。"""
    try:
        import anthropic
        model = os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
        client = anthropic.Anthropic(api_key=api_key)
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
        return (msg.content[0].text or "").strip()
    except Exception as exc:
        logger.warning("Claude cross-val failed: %s", exc)
        return ""


def _ask_gemini(question: str, profile_summary: str, api_key: str) -> str:
    """透過 Google OpenAI-相容端點呼叫 Gemini，取得補充視角。"""
    try:
        from openai import OpenAI
        # Google 提供 OpenAI 相容 API，無需額外套件
        model = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
        client = OpenAI(
            api_key=api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _CROSS_SYSTEM},
                {"role": "user", "content": f"問題：{question}\n用戶背景：{profile_summary}"},
            ],
            max_tokens=200,
            timeout=10.0,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as exc:
        logger.warning("Gemini cross-val failed: %s", exc)
        return ""


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

    tasks: dict[str, callable] = {}
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
