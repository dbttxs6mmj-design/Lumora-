from __future__ import annotations

from typing import Any, Dict, List

from .target_context import build_target_person, has_target_person


def _clean_dict(values: Dict[str, Any] | None) -> Dict[str, str]:
    return {
        key: str(value).strip()
        for key, value in (values or {}).items()
        if str(value).strip()
    }


def _active_profile_snapshot(profile: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": profile.get("id"),
        "label": profile.get("label"),
        "name": profile.get("name", ""),
        "is_self": bool(profile.get("is_self")),
        "gender": profile.get("gender"),
        "birth_date": profile.get("birth_date"),
        "birth_time_slot": profile.get("birth_time_slot"),
        "country": profile.get("country"),
        "province": profile.get("province"),
        "city": profile.get("city"),
    }


def _counterpart_label(target_person: Dict[str, Any]) -> str:
    if target_person.get("name"):
        return str(target_person["name"])
    sex = str(target_person.get("sex") or "").strip()
    if sex == "女":
        return "她"
    if sex == "男":
        return "他"
    return "對方"


def _goal_inferable_from_question(question: str) -> bool:
    q = (question or "").lower()
    why_signals = ["為什麼", "為何", "什麼原因", "怎麼了", "why", "reason"]
    future_signals = ["有沒有機會", "還有希望", "未來", "之後會", "結果會", "能不能", "有可能", "will", "future"]
    how_signals = ["該怎麼", "怎麼辦", "我應該", "how should", "what should", "怎樣做"]
    question_signals = ["嗎", "呢", "嗯", "吧", "？", "?"]
    return (
        any(s in q for s in why_signals)
        or any(s in q for s in future_signals)
        or any(s in q for s in how_signals)
        or (any(s in q for s in question_signals) and len(q) > 15)
    )


def _relationship_context_in_question(question: str) -> bool:
    q = (question or "").lower()
    context_signals = [
        "喜歡", "暗戀", "追求", "曖昧", "在一起", "分手", "失戀", "前任", "前男友", "前女友",
        "老公", "老婆", "丈夫", "妻子", "伴侶", "感情", "戀愛", "交往",
        "沒感覺", "沒喜歡", "不喜歡", "拒絕", "不理",
        "like", "love", "crush", "dating", "broke up", "ex",
    ]
    return any(s in q for s in context_signals)


def _profile_has_birth_data(profile: Dict[str, Any]) -> bool:
    return bool(profile.get("birth_date"))


def _question_bank(label: str) -> Dict[str, str]:
    return {
        "date_anchor": "我先對準起算時間：請直接告訴我今天的日期。",
        "user_goal": f"你這次最想知道的是什麼——{label}為什麼會這樣、你們之後還有沒有機會，還是你現在該怎麼做？",
        "current_status": f"你們目前比較像朋友、曖昧、同學、同事，還是其實幾乎沒互動？",
        "how_they_met": "你們是怎麼認識的？",
        "duration": "這件事大概持續多久了？",
        "target_name": f"如果你知道{label}的名字，可以直接告訴我，這樣我比對起來更準。",
        "target_birth": f"如果你知道{label}的生日，或大概幾年出生、幾歲，也一起說。",
        "target_region": f"如果你知道{label}是哪裡人，或在哪個城市長大，也可以告訴我。",
        "event_background": "你先說一下目前最關鍵的變化或背景，我再往下推。",
        "time_context": "你希望我看的是現在這段，還是某個明確的時間點？",
        "subject_context": "這題你主要想看你自己的狀況，還是另一個人？",
        "location_context": "這件事主要發生在哪個城市或地區？",
        "decision_focus": "你現在最在意的是能不能成、風險在哪裡，還是下一步怎麼選？",
        "work_topic": "你這次主要想看現職、轉職，還是某個合作機會？",
        "health_subject": "這題是你自己的身體狀況，還是家人的？",
        "health_state": "目前是已經出現明確症狀，還是整體狀態感覺不太對？",
        "health_duration": "這種狀況大概多久了？",
    }


def _pick_single_relationship_question(
    question: str,
    target_person: Dict[str, Any],
    answers: Dict[str, str],
    analysis: Dict[str, Any],
    profile: Dict[str, Any],
    label: str,
) -> str | None:
    if answers:
        return None

    features = analysis.get("features", {})
    if features.get("needs_calendar_anchor") and "date_anchor" not in answers:
        if not _profile_has_birth_data(profile):
            return "date_anchor"

    has_goal = _goal_inferable_from_question(question)
    has_context = _relationship_context_in_question(question)

    if not has_goal and "user_goal" not in answers:
        return "user_goal"

    if has_goal and has_context and "current_status" not in answers and not target_person.get("current_status"):
        return "current_status"

    return None


def _pick_single_generic_question(
    analysis: Dict[str, Any],
    answers: Dict[str, str],
    profile: Dict[str, Any],
) -> str | None:
    if answers:
        return None

    features = analysis.get("features", {})
    domain = analysis.get("domain", "general")

    if features.get("needs_calendar_anchor"):
        if not _profile_has_birth_data(profile):
            return "date_anchor"

    if domain == "health":
        scope = analysis.get("scope", "general")
        if scope not in {"personal"} and "health_subject" not in answers:
            return "health_subject"
        if "health_state" not in answers:
            return "health_state"

    if domain in {"career", "cooperation", "financial", "decision"}:
        if "decision_focus" not in answers:
            return "decision_focus"

    return None


def build_followup_turn(
    *,
    question: str,
    analysis: Dict[str, Any],
    routing: Dict[str, Any],
    profile: Dict[str, Any],
    clarification_answers: Dict[str, Any] | None = None,
    conversation_state: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    answers = _clean_dict(clarification_answers)
    existing_state = conversation_state or {}
    target_person = build_target_person(
        question=question,
        answers=answers,
        existing=existing_state.get("target_person"),
    )
    domain = analysis.get("domain", "general")
    involved_target = has_target_person(question, domain, analysis)
    label = _counterpart_label(target_person)
    prompt_bank = _question_bank(label)

    if domain == "relationship" and involved_target:
        asked_key = _pick_single_relationship_question(question, target_person, answers, analysis, profile, label)
    else:
        asked_key = _pick_single_generic_question(analysis, answers, profile)

    questions: List[Dict[str, Any]] = []
    if asked_key:
        questions.append({
            "key": asked_key,
            "question": prompt_bank[asked_key],
            "required": True,
        })

    recommended_missing: List[str] = []
    if domain == "relationship" and involved_target and not answers:
        should_collect = not target_person.get("relation_known_from_question")
        if should_collect and not target_person.get("name") and "target_name" not in answers:
            recommended_missing.append("target_name")
        if should_collect and not (target_person.get("birthday") or target_person.get("approximate_age")) and "target_birth" not in answers:
            recommended_missing.append("target_birth")
        if should_collect and not (target_person.get("region") or target_person.get("birthplace")) and "target_region" not in answers:
            recommended_missing.append("target_region")

    required_missing = [asked_key] if asked_key else []
    current = questions[0] if questions else None

    conversation_snapshot = {
        "answers": answers,
        "asked_keys": list(answers.keys()),
        "active_profile": _active_profile_snapshot(profile),
        "target_person": target_person,
        "missing_fields": {
            "required": required_missing,
            "recommended": recommended_missing,
        },
        "question_domain": domain,
    }

    return {
        "needs_clarification": asked_key is not None,
        "prompt": current["question"] if current else "",
        "asked_key": asked_key,
        "questions": questions,
        "current_question": current,
        "missing_required_fields": required_missing,
        "recommended_missing_fields": recommended_missing,
        "collected_answers": answers,
        "conversation_state": conversation_snapshot,
        "target_person": target_person,
        "next_step": "ask" if asked_key else "ready",
    }
