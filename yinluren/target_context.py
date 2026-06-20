from __future__ import annotations

import re
from typing import Any, Dict


FEMALE_HINTS = ("女孩", "女生", "女人", "女方", "她", "girlfriend", "girl", "woman", "she", "her")
MALE_HINTS = ("男孩", "男生", "男人", "男方", "他", "boyfriend", "boy", "man", "he", "him")

RELATIONSHIP_ROLE_HINTS = (
    "朋友",
    "曖昧",
    "同學",
    "同事",
    "伴侶",
    "前任",
    "老婆",
    "老公",
    "妻子",
    "丈夫",
)

STATUS_HINTS = (
    "交往",
    "曖昧",
    "分手",
    "失聯",
    "冷淡",
    "朋友",
    "同學",
    "同事",
)

DURATION_PATTERN = re.compile(
    r"(最近|近期|這陣子|這幾天|幾天|幾週|幾個月|半年|一年|[一二三四五六七八九十兩\\d]+天|[一二三四五六七八九十兩\\d]+週|[一二三四五六七八九十兩\\d]+個?月|[一二三四五六七八九十兩\\d]+年)"
)
AGE_PATTERN = re.compile(r"([1-9]\\d?)\\s*歲")
NAME_PATTERN = re.compile(r"(?:叫|名字是|名叫)([\\u4e00-\\u9fffA-Za-z]{1,20})")


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _contains_any(text: str, hints: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(hint.lower() in lowered for hint in hints)


def infer_target_sex(question: str, existing: str = "") -> str:
    if existing:
        return existing
    if _contains_any(question, FEMALE_HINTS):
        return "女"
    if _contains_any(question, MALE_HINTS):
        return "男"
    return ""


def infer_relationship_to_user(question: str, existing: str = "") -> str:
    if existing:
        return existing
    for hint in RELATIONSHIP_ROLE_HINTS:
        if hint in question:
            return hint
    return ""


def infer_current_status(question: str, existing: str = "") -> str:
    if existing:
        return existing
    for hint in STATUS_HINTS:
        if hint in question:
            return hint
    return ""


def infer_user_goal(question: str, existing: str = "") -> str:
    if existing:
        return existing
    text = _clean(question)
    if "為什麼" in text or "为什么" in text:
        return "原因"
    if "有沒有機會" in text or "有没有机会" in text or "可能" in text:
        return "機會"
    if "怎麼做" in text or "怎么办" in text or "下一步" in text:
        return "下一步"
    if "阻礙" in text or "障礙" in text:
        return "阻礙"
    return ""


def infer_duration(question: str, existing: str = "") -> str:
    if existing:
        return existing
    match = DURATION_PATTERN.search(question or "")
    return match.group(0) if match else ""


def infer_name(question: str, existing: str = "") -> str:
    if existing:
        return existing
    match = NAME_PATTERN.search(question or "")
    return match.group(1) if match else ""


def infer_approximate_age(value: str, existing: str = "") -> str:
    if existing:
        return existing
    match = AGE_PATTERN.search(value or "")
    return match.group(1) if match else ""


def build_target_person(
    *,
    question: str,
    answers: Dict[str, Any],
    existing: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    existing = existing or {}
    normalized_answers = {
        key: _clean(value)
        for key, value in (answers or {}).items()
        if _clean(value)
    }
    birth_answer = normalized_answers.get("target_birth", "")
    region_answer = normalized_answers.get("target_region", "")
    status_answer = normalized_answers.get("current_status", "")
    name_answer = normalized_answers.get("target_name", "")

    inferred_relation = infer_relationship_to_user(question)
    relationship_to_user = normalized_answers.get("relationship_to_user") or existing.get("relationship_to_user") or ""
    if not relationship_to_user and status_answer:
        relationship_to_user = status_answer

    return {
        "name": name_answer or existing.get("name") or infer_name(question),
        "sex": infer_target_sex(question, _clean(existing.get("sex"))),
        "birthday": birth_answer or _clean(existing.get("birthday")),
        "approximate_age": infer_approximate_age(birth_answer, _clean(existing.get("approximate_age"))),
        "birthplace": region_answer or _clean(existing.get("birthplace")),
        "region": region_answer or _clean(existing.get("region")),
        "relationship_to_user": relationship_to_user or inferred_relation,
        "relation_known_from_question": bool(inferred_relation),
        "how_they_met": normalized_answers.get("how_they_met") or _clean(existing.get("how_they_met")),
        "current_status": status_answer or infer_current_status(question, _clean(existing.get("current_status"))),
        "user_goal": normalized_answers.get("user_goal") or infer_user_goal(question, _clean(existing.get("user_goal"))),
    }


def has_target_person(question: str, domain: str, analysis: Dict[str, Any]) -> bool:
    if domain == "relationship":
        return True
    if analysis.get("features", {}).get("has_other_entities"):
        return True
    text = question or ""
    return _contains_any(text, FEMALE_HINTS + MALE_HINTS)
