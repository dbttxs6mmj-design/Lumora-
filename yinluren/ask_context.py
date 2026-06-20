from __future__ import annotations

from typing import Any, Dict, List


SELF_PROFILE_HINTS = [
    "根據我的命盤",
    "根据我的命盘",
    "我的命盤",
    "我的命盘",
    "依我的命盤",
    "依我的命盘",
    "my chart",
    "my natal chart",
    "based on my chart",
]


def wants_self_profile(question: str) -> bool:
    text = (question or "").strip().lower()
    return any(hint.lower() in text for hint in SELF_PROFILE_HINTS)


def choose_effective_profile(
    requested_profile: Dict[str, Any],
    all_profiles: List[Dict[str, Any]],
    question: str,
) -> Dict[str, Any]:
    if requested_profile.get("is_self"):
        return requested_profile
    if not wants_self_profile(question):
        return requested_profile
    return next((profile for profile in all_profiles if profile.get("is_self")), requested_profile)


def _birth_precision(profile: Dict[str, Any]) -> str:
    slot = str(profile.get("birth_time_slot") or "").strip()
    if not slot or slot == "不確定":
        return "unknown"
    if slot == "估算時辰":
        return "shichen"
    if slot.startswith("約 "):
        return "approximate"
    return "exact"


def _subject_focus(analysis: Dict[str, Any]) -> str:
    domain = analysis.get("domain", "general")
    scope = analysis.get("scope", "general")
    if domain == "relationship":
        return "relationship"
    if domain == "health" and scope in {"family", "pair"}:
        return "family_member"
    if any(entity.get("category") == "animal" for entity in analysis.get("entities", [])):
        return "pet"
    if any(entity.get("category") == "object" for entity in analysis.get("entities", [])):
        return "object"
    if scope == "pair":
        return "counterpart"
    if scope == "family":
        return "family"
    if scope in {"organization", "team"}:
        return "collaboration"
    return "self"


def _known_background(answers: Dict[str, Any]) -> Dict[str, Any]:
    return {
        key: str(value).strip()
        for key, value in (answers or {}).items()
        if str(value).strip()
    }


def _needs_research(question: str, analysis: Dict[str, Any]) -> bool:
    lowered = (question or "").lower()
    domain = analysis.get("domain", "general")
    if domain in {"career", "cooperation", "financial", "situation", "decision"}:
        return True
    if analysis.get("features", {}).get("has_location_reference"):
        return True
    return any(
        keyword in lowered
        for keyword in [
            "移民", "城市", "地區", "政策", "市場", "產業", "公司", "offer",
            "immigration", "city", "region", "policy", "market", "industry",
        ]
    )


def build_ask_context(
    *,
    requested_profile: Dict[str, Any],
    effective_profile: Dict[str, Any],
    question: str,
    mode: str,
    clarification_answers: Dict[str, Any],
    analysis: Dict[str, Any],
    routing: Dict[str, Any],
    birthplace_factor: Dict[str, Any],
) -> Dict[str, Any]:
    known_background = _known_background(clarification_answers)
    needs_research = _needs_research(question, analysis)
    return {
        "active_profile": {
            "requested_profile_id": requested_profile.get("id"),
            "effective_profile_id": effective_profile.get("id"),
            "label": effective_profile.get("label"),
            "name": effective_profile.get("name", ""),
            "is_self": bool(effective_profile.get("is_self")),
            "gender": effective_profile.get("gender"),
            "birth_date": effective_profile.get("birth_date"),
            "birth_time_slot": effective_profile.get("birth_time_slot"),
            "branch": effective_profile.get("branch"),
            "zodiac": effective_profile.get("zodiac"),
            "birth_precision": _birth_precision(effective_profile),
            "occupation": effective_profile.get("occupation", ""),
        },
        "birthplace": {
            "country": effective_profile.get("country"),
            "province": effective_profile.get("province"),
            "city": effective_profile.get("city"),
        },
        "birthplace_factor": birthplace_factor,
        "question": {
            "text": question,
            "mode": mode,
            "domain": analysis.get("domain", "general"),
            "scope": analysis.get("scope", "general"),
            "subject_focus": _subject_focus(analysis),
            "entities": analysis.get("entities", []),
            "time_sensitive": bool(analysis.get("features", {}).get("needs_calendar_anchor")),
        },
        "routing": {
            "primary_layers": routing.get("primary_layers", []),
            "support_layers": routing.get("support_layers", []),
            "requirements": routing.get("requirements", {}),
        },
        "known_background": known_background,
        "missing_information": [],
        "needs_clarification": False,
        "research": {
            "pipeline_started": True,
            "required": needs_research,
            "reason": "question_or_domain_requires_external_comparison" if needs_research else "internal_context_is_primary",
        },
    }
