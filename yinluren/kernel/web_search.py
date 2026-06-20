"""
引路人 Lumora — 即時外網資訊增強（M20-A）
透過 Perplexity Sonar API 取得最新時事/財經/醫療等資訊注入推演上下文。
所有操作後台靜默，用戶層永不知曉。
"""
from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# Perplexity 使用 OpenAI 相容介面
_PERPLEXITY_BASE = "https://api.perplexity.ai"
_DEFAULT_MODEL = "sonar"  # sonar = online 即時搜尋版；sonar-pro = 深度版（費用較高）

# 觸發外網搜尋的關鍵詞（命中任一即搜）
_SEARCH_TRIGGERS = (
    "最新", "現在", "目前", "今年", "今天", "今日", "近期", "近況", "最近",
    "股票", "股市", "匯率", "金融", "房價", "地產", "幣", "比特幣", "加密",
    "疫情", "病毒", "醫療", "藥物", "治療", "癌症", "新藥",
    "新聞", "事件", "事故", "災難", "選舉", "戰爭", "衝突", "政變",
    "AI", "人工智慧", "科技", "新技術", "ChatGPT", "Gemini", "Claude",
    "政策", "法規", "政府", "國際", "外交", "制裁",
    "2025", "2026", "2027",
)


def _should_search(question: str) -> bool:
    return any(kw in question for kw in _SEARCH_TRIGGERS)


def fetch_web_context(question: str, api_key: Optional[str] = None, force: bool = False) -> str:
    """
    呼叫 Perplexity Sonar 取得外網最新資訊；回傳供注入提示詞的摘要字串。
    - force=True 跳過關鍵詞過濾，強制搜尋。
    - 若無 PERPLEXITY_API_KEY 或不應搜尋，靜默回空字串。
    """
    key = api_key or os.environ.get("PERPLEXITY_API_KEY", "").strip()
    if not key:
        return ""
    if not force and not _should_search(question):
        return ""

    try:
        from openai import OpenAI
        client = OpenAI(api_key=key, base_url=_PERPLEXITY_BASE)
        model = os.environ.get("PERPLEXITY_MODEL", _DEFAULT_MODEL)
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是精準資訊提取器。只提供與用戶問題最相關的最新客觀事實與數據，"
                        "100 字以內，不評論，不建議，僅陳述事實。"
                    ),
                },
                {"role": "user", "content": question},
            ],
            max_tokens=300,
            timeout=9.0,
        )
        text = (resp.choices[0].message.content or "").strip()
        return f"【即時外網資訊】\n{text}" if text else ""
    except Exception as exc:
        logger.warning("Perplexity search failed: %s", exc)
        return ""
