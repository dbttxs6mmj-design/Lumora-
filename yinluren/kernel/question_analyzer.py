from __future__ import annotations

import re
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List

try:
    from zoneinfo import ZoneInfo

    TAIPEI_TZ = ZoneInfo("Asia/Taipei")
except Exception:
    TAIPEI_TZ = timezone(timedelta(hours=8))

SCOPE_KEYWORDS = {
    "personal": ["我", "自己", "本人", "myself", "me"],
    "pair": ["雙方", "兩人", "對方", "伴侶", "老婆", "老公", "妻子", "丈夫", "她", "他", "女生", "男生", "partner", "counterpart", "wife", "husband"],
    "family": ["家庭", "家人", "父母", "孩子", "family", "parents", "children"],
    "team": ["團隊", "小組", "team", "crew", "department"],
    "organization": ["公司", "組織", "企業", "品牌", "school", "company", "organization", "enterprise"],
    "regional": ["地區", "市場", "社群", "民眾", "城市", "region", "market", "community", "public"],
    "national": ["國家", "政府", "政局", "戰局", "局勢", "時勢", "nation", "state", "government", "geopolitics"],
}

DOMAIN_KEYWORDS = {
    "relationship": ["感情", "婚姻", "關係", "互動", "老婆", "老公", "伴侶", "吵架", "分手", "喜歡", "暗戀", "追求", "曖昧", "沒感覺", "relationship", "love", "marriage", "wife", "husband", "partner"],
    "career": ["事業", "工作", "職涯", "career", "job", "work", "轉職", "升職", "離職", "offer"],
    "financial": ["財務", "金錢", "投資", "finance", "money", "investment"],
    "health": ["健康", "身體", "疾病", "health", "body", "disease", "累", "疲憊", "疲勞", "無力", "失眠", "焦慮", "頭痛", "胃痛", "沒精神", "躺平"],
    "family": ["家庭", "親子", "家運", "family", "parenting"],
    "cooperation": ["合作", "合夥", "談判", "cooperation", "partnership", "deal"],
    "decision": ["選擇", "方向", "時機", "要不要", "should", "decision", "timing"],
    "fortune": ["運勢", "運程", "流年", "fortune", "trend"],
    "situation": ["局勢", "時勢", "國運", "市場", "situation", "momentum", "macro"],
}

ENTITY_PATTERNS = {
    "person": ["我", "自己", "本人", "對方", "當事人", "她", "他", "女孩", "男孩", "女生", "男生", "someone", "person", "people"],
    "group": ["團隊", "群體", "市場", "民眾", "team", "group", "community", "public"],
    "organization": ["公司", "組織", "政府", "學校", "品牌", "company", "organization", "government", "school"],
    "location": ["台北", "台灣", "香港", "中國", "美國", "日本", "Taipei", "Taiwan", "Tokyo", "USA", "China"],
    "animal": ["寵物", "動物", "狗", "貓", "馬", "bird", "dog", "cat", "pet", "animal"],
    "object": ["房子", "股票", "專案", "產品", "合約", "資產", "house", "stock", "project", "product", "contract", "asset"],
}

TIME_PATTERN = re.compile(
    r"(\d{4}[-/年]\d{1,2}([-/月]\d{1,2})?|\d{1,2}月\d{1,2}日|今天|明天|昨天|最近|近期|今年|明年|today|tomorrow|yesterday|recently|this year|next year)",
    re.IGNORECASE,
)

EVENT_PATTERN = re.compile(
    r"(發生|開始|結束|簽約|分手|結婚|離職|上任|發布|上市|衝突|變動|occur|start|end|launch|sign|break|conflict)",
    re.IGNORECASE,
)

# ── 修正：大幅收窄 needs_calendar_anchor 觸發條件 ──────────────────────────
# 原本：含「今天/最近/目前/現在/何時...」就觸發 → 幾乎所有問題都中招
# 修正後：只有明確詢問「具體是哪一天/哪個時間點」才觸發
# 「今年事業怎麼樣」「現在創業好嗎」→ 不觸發（伺服器已知當前日期）
# 「我今天該不該主動聯絡？」→ 不觸發（問的是決策，不是要我定位某天）
# 「這件事發生在什麼時候？」→ 觸發（用戶自己要錨定某個過去事件時間點）
CALENDAR_ANCHOR_KEYWORDS = [
    "什麼時候發生",
    "哪一天",
    "哪天開始",
    "幾月幾號",
    "起算哪天",
    "哪個時間點",
    "when did it happen",
    "which date",
    "what date",
]

ABSOLUTE_DATE_PATTERN = re.compile(
    r"(\d{4}[-/年]\d{1,2}([-/月]\d{1,2})?|\d{1,2}月\d{1,2}日|\d{1,2}/\d{1,2})",
    re.IGNORECASE,
)


def current_timestamp() -> str:
    return datetime.now(TAIPEI_TZ).isoformat(timespec="seconds")


def _score_from_keywords(question: str, keyword_map: Dict[str, List[str]], fallback: str) -> Dict[str, Any]:
    q = (question or "").lower()
    scores = {}
    for key, keywords in keyword_map.items():
        scores[key] = sum(1 for keyword in keywords if keyword.lower() in q)

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    label, score = ranked[0]
    if score == 0:
        return {"label": fallback, "scores": scores}
    return {"label": label, "scores": scores}


def _dedupe_entities(entities: List[Dict[str, str]]) -> List[Dict[str, str]]:
    seen = set()
    output = []
    for entity in entities:
        key = (entity["category"], entity["label"])
        if key in seen:
            continue
        seen.add(key)
        output.append(entity)
    return output


def extract_entities(question: str) -> List[Dict[str, str]]:
    text = question or ""
    lowered = text.lower()
    entities: List[Dict[str, str]] = []

    for category, keywords in ENTITY_PATTERNS.items():
        for keyword in keywords:
            if keyword.lower() in lowered:
                entities.append({"category": category, "label": keyword, "source": "keyword"})

    for match in TIME_PATTERN.finditer(text):
        entities.append({"category": "time", "label": match.group(0), "source": "pattern"})

    if EVENT_PATTERN.search(text):
        entities.append({"category": "event", "label": EVENT_PATTERN.search(text).group(0), "source": "pattern"})

    return _dedupe_entities(entities)


def build_question_analysis(question: str, profile: Dict[str, Any]) -> Dict[str, Any]:
    entities = extract_entities(question)
    scope = _score_from_keywords(question, SCOPE_KEYWORDS, "general")
    domain = _score_from_keywords(question, DOMAIN_KEYWORDS, "general")
    lowered = (question or "").lower()
    if any(keyword in lowered for keyword in ["老婆", "老公", "妻子", "丈夫", "wife", "husband", "partner", "伴侶"]):
        scope["label"] = "pair"
    has_time = any(entity["category"] == "time" for entity in entities)
    has_absolute_date = bool(ABSOLUTE_DATE_PATTERN.search(question or ""))
    has_location = any(entity["category"] == "location" for entity in entities)
    has_other_entities = any(
        entity["category"] in {"person", "group", "organization", "animal", "object"}
        and entity["label"] not in {"我", "自己", "本人", "myself", "me"}
        for entity in entities
    )

    # ── 修正核心：needs_calendar_anchor 只在用戶明確詢問「某個事件的具體日期」時才為 True
    # 伺服器已能自動提供 current_timestamp，「今年/現在/目前」等詞不代表需要用戶補充日期
    needs_calendar_anchor = (
        not has_absolute_date
        and any(kw in lowered for kw in CALENDAR_ANCHOR_KEYWORDS)
    )

    return {
        "question": question,
        "current_timestamp": current_timestamp(),
        "scope": scope["label"],
        "scope_scores": scope["scores"],
        "domain": domain["label"],
        "domain_scores": domain["scores"],
        "entities": entities,
        "features": {
            "has_time_reference": has_time,
            "has_relative_time_reference": any(kw in lowered for kw in ["今天", "最近", "目前", "現在", "今年"]),
            "has_absolute_date_reference": has_absolute_date,
            "needs_calendar_anchor": needs_calendar_anchor,
            "has_location_reference": has_location,
            "has_event_reference": any(entity["category"] == "event" for entity in entities),
            "has_other_entities": has_other_entities,
            "profile_reusable": bool(profile.get("id")),
            "profile_has_precise_birth": bool(
                profile.get("birth_date")
                and profile.get("birth_time_slot")
                and profile.get("birth_time_slot") != "不確定"
                and profile.get("branch") != "不確定"
                and profile.get("zodiac") != "不確定"
            ),
        },
    }
