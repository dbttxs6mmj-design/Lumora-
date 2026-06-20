import logging
import re
from datetime import UTC, datetime
from typing import Optional, Literal, Dict, Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, model_validator

logger = logging.getLogger(__name__)

from yinluren.ask_context import choose_effective_profile
from yinluren.birthplace_context import canonicalize_birthplace
from yinluren.kernel.timezone_calibration import calibrate_birth_time
from yinluren.db import (
    list_profiles as db_list_profiles,
    get_profile as db_get_profile,
    create_profile as db_create_profile,
    update_profile as db_update_profile,
    delete_profile as db_delete_profile,
    get_setting as db_get_setting,
    set_setting as db_set_setting,
)
from yinluren.kernel.final_kernel import orchestrate_final_kernel
from yinluren.kernel.llm_divination import run_llm_divination
from yinluren.ui_i18n import get_bundle as _ui_get_bundle, is_rtl as _ui_is_rtl

router = APIRouter()

UNCERTAIN_TIME = "不確定"
SELF_PROFILE_LABEL = "我的命單"
DEFAULT_LANGUAGE = "zh-Hant-TW"

LanguageCode = Literal["zh-Hans", "zh-Hant-TW", "zh-Hant-HK", "en"]
LegacyLanguageCode = Literal["zh-Hant", "zh-Yue"]
AcceptedLanguageCode = LanguageCode | LegacyLanguageCode
ReadingMode = Literal["liuyao", "bazi", "qimen", "face", "lingqi"]

LEGACY_LANGUAGE_ALIASES = {
    "zh-Hant": "zh-Hant-TW",
    "zh-Yue": "zh-Hant-HK",
}


class ProfileCreate(BaseModel):
    label: str = Field(..., description="命單名稱，例如：我自己、媽媽、同事A")
    name: str = ""
    gender: Literal["男", "女"]
    birth_date: str
    birth_time_slot: str = UNCERTAIN_TIME
    branch: str = "不確定"
    zodiac: str = "不確定"
    country: str = "未設定"
    province: str = "未設定"
    city: str = "未設定"
    occupation: str = "未設定"
    consent: bool = True
    is_self: bool = False

    @model_validator(mode="after")
    def validate_business_rules(self):
        normalized = _normalize_profile_payload(self.model_dump())
        for field, value in normalized.items():
            setattr(self, field, value)
        _validate_profile_payload(normalized)
        return self


class ProfileUpdate(BaseModel):
    label: Optional[str] = Field(default=None, min_length=1, max_length=30)
    name: Optional[str] = Field(default=None, max_length=30)
    gender: Optional[Literal["男", "女"]] = None
    birth_date: Optional[str] = None
    birth_time_slot: Optional[str] = None
    branch: Optional[str] = None
    zodiac: Optional[str] = None
    country: Optional[str] = None
    province: Optional[str] = None
    city: Optional[str] = None
    occupation: Optional[str] = None
    consent: Optional[bool] = None
    is_self: Optional[bool] = None

    @model_validator(mode="after")
    def normalize_optional_strings(self):
        for field in PROFILE_STRING_FIELDS:
            value = getattr(self, field)
            if isinstance(value, str):
                setattr(self, field, value.strip())
        return self


class ProfileOut(ProfileCreate):
    id: str
    updated_at: str
    timezone_calibration: Optional[Any] = None


class DivineByProfileIn(BaseModel):
    profile_id: str
    question: str = Field(..., min_length=1, max_length=500)
    language: Optional[AcceptedLanguageCode] = None
    mode: ReadingMode = "liuyao"
    clarification_answers: Dict[str, Any] = Field(default_factory=dict)
    conversation_state: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_question(self):
        self.question = self.question.strip()
        if not self.question:
            raise ValueError("question must not be blank")
        self.language = normalize_language_code(self.language)
        self.clarification_answers = self.clarification_answers or {}
        self.conversation_state = self.conversation_state or {}
        return self


class DivineResult(BaseModel):
    state: str
    core_conclusion: Optional[str] = None
    traditional_model_judgment: str
    yinluren_guidance: str
    multi_perspectives: list[str] = Field(default_factory=list)
    resonance_points: list[str] = Field(default_factory=list)
    divergence_points: list[str] = Field(default_factory=list)
    research_summary: Optional[str] = None
    risk_focus: list[str]
    timing_window: str


class DivineEngine(BaseModel):
    type: str
    active: bool
    confidence: float
    best_candidate: Optional[Dict[str, Any]]
    top_candidates: list[Dict[str, Any]]
    adapter_status: Optional[str] = None
    steps: list[str] = Field(default_factory=list)
    note: Optional[str] = None
    birthplace_factor_used: bool = False
    birthplace_factor_signature: Optional[str] = None


class DivineByProfileOut(BaseModel):
    ok: bool
    status: str = "ready"
    assistant: str
    language: LanguageCode
    scenario: str
    mode: ReadingMode = "liuyao"
    profile_id: str
    question: str
    used_profile: Dict[str, Any]
    current_timestamp: str
    model_used: Optional[str] = None
    analysis: Dict[str, Any] = Field(default_factory=dict)
    routing: Dict[str, Any] = Field(default_factory=dict)
    intake: Dict[str, Any] = Field(default_factory=dict)
    clarification: Optional[Dict[str, Any]] = None
    conversation_state: Dict[str, Any] = Field(default_factory=dict)
    engine_registry: Dict[str, Any] = Field(default_factory=dict)
    classics_registry: Dict[str, Any] = Field(default_factory=dict)
    internal_engine: Dict[str, Any] = Field(default_factory=dict)
    result: DivineResult
    engine: DivineEngine
    card: str


class LanguagePreferenceIn(BaseModel):
    language: AcceptedLanguageCode

    @model_validator(mode="after")
    def normalize_language(self):
        self.language = normalize_language_code(self.language) or DEFAULT_LANGUAGE
        return self


PROFILE_PRECISION_FIELDS = ("birth_time_slot", "branch", "zodiac")
DIVINE_RESULT_REQUIRED_FIELDS = (
    "state",
    "traditional_model_judgment",
    "yinluren_guidance",
    "risk_focus",
    "timing_window",
)
DIVINE_ENGINE_REQUIRED_FIELDS = (
    "type",
    "active",
    "confidence",
    "best_candidate",
    "top_candidates",
)
PROFILE_STRING_FIELDS = (
    "label",
    "name",
    "birth_date",
    "birth_time_slot",
    "branch",
    "zodiac",
    "country",
    "province",
    "city",
    "occupation",
)
LEGACY_EMPTY_PROFILE_LABEL = "未命名命單"


_EARTHLY_BRANCH_HOURS: Dict[str, int] = {
    "子": 0, "丑": 2, "寅": 4, "卯": 6, "辰": 8, "巳": 10,
    "午": 12, "未": 14, "申": 16, "酉": 18, "戌": 20, "亥": 22,
}


def _parse_time_slot(slot: str) -> tuple:
    """Extract (hour, minute) from a birth_time_slot string, or (None, None) if uncertain."""
    if not slot or slot in {"不確定", "估算時辰", UNCERTAIN_TIME}:
        return None, None
    # Direct HH:MM pattern
    hm = re.search(r"(\d{1,2}):(\d{2})", slot)
    if hm:
        return int(hm.group(1)), int(hm.group(2))
    # Earthly-branch prefix e.g. "子時", "子時 23:00 - 00:59"
    for branch, hour in _EARTHLY_BRANCH_HOURS.items():
        if slot.startswith(branch):
            return hour, 0
    return None, None


def _attach_calibration(profile_data: Dict[str, Any]) -> Dict[str, Any]:
    """Compute timezone calibration and attach it to profile_data in-place."""
    import json as _json
    hour, minute = _parse_time_slot(profile_data.get("birth_time_slot", ""))
    try:
        calibration = calibrate_birth_time(
            birth_date=profile_data.get("birth_date", ""),
            birth_hour=hour,
            birth_minute=minute,
            country=profile_data.get("country", ""),
            province=profile_data.get("province", ""),
            city=profile_data.get("city", ""),
        )
        profile_data["timezone_calibration"] = _json.dumps(calibration, ensure_ascii=False)
    except Exception as exc:
        logger.warning(
            "timezone calibration failed for profile id=%s birth_date=%r country=%r province=%r city=%r: %s",
            profile_data.get("id"),
            profile_data.get("birth_date"),
            profile_data.get("country"),
            profile_data.get("province"),
            profile_data.get("city"),
            exc,
        )
        profile_data["timezone_calibration"] = _json.dumps(
            {"calibrated": False, "error": str(exc)}, ensure_ascii=False
        )
    return profile_data


def _normalize_profile_strings(profile: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(profile)
    for field in PROFILE_STRING_FIELDS:
        value = normalized.get(field)
        if isinstance(value, str):
            normalized[field] = value.strip()
    return normalized


def _validate_profile_payload(profile: Dict[str, Any]) -> None:
    profile = _normalize_profile_strings(profile)
    is_self = bool(profile.get("is_self"))
    consent = profile.get("consent")
    label = profile.get("label", "")
    birth_date = profile.get("birth_date", "")
    uncertain_fields = [
        field
        for field in PROFILE_PRECISION_FIELDS
        if profile.get(field) == UNCERTAIN_TIME
    ]

    if not label:
        raise ValueError("profile label must not be blank")
    if len(label) > 30:
        raise ValueError("profile label must be 30 characters or fewer")
    if not birth_date:
        raise ValueError("birth_date must not be blank")

    if consent is False:
        raise ValueError("profiles require consent=true")

    if is_self and uncertain_fields:
        raise ValueError(
            "self profiles require exact birth_time_slot, branch, and zodiac"
        )

    if (
        not is_self
        and profile.get("birth_time_slot") == "估算時辰"
        and profile.get("branch") == UNCERTAIN_TIME
        and profile.get("zodiac") == UNCERTAIN_TIME
    ):
        return

    if not is_self and uncertain_fields and len(uncertain_fields) != len(PROFILE_PRECISION_FIELDS):
        raise ValueError(
            "non-self profiles must mark birth_time_slot, branch, and zodiac as all exact or all uncertain"
        )


def _normalize_profile_payload(profile: Dict[str, Any]) -> Dict[str, Any]:
    normalized = _normalize_profile_strings(profile)
    birthplace = canonicalize_birthplace(
        normalized.get("country", ""),
        normalized.get("province", ""),
        normalized.get("city", ""),
    )
    normalized["country"] = birthplace["country"]
    normalized["province"] = birthplace["province"]
    normalized["city"] = birthplace["city"]
    if normalized.get("is_self"):
        normalized["label"] = SELF_PROFILE_LABEL
        normalized["consent"] = True
    return normalized


def _normalize_profile_record(profile: Dict[str, Any]) -> Dict[str, Any]:
    normalized = _normalize_profile_payload(profile)
    if not normalized.get("label"):
        normalized["label"] = LEGACY_EMPTY_PROFILE_LABEL
    raw_cal = profile.get("timezone_calibration")
    if isinstance(raw_cal, str):
        try:
            import json as _j
            normalized["timezone_calibration"] = _j.loads(raw_cal)
        except Exception:
            normalized["timezone_calibration"] = None
    elif isinstance(raw_cal, dict):
        normalized["timezone_calibration"] = raw_cal
    else:
        normalized["timezone_calibration"] = None
    return normalized


def normalize_language_code(language: Optional[str]) -> Optional[LanguageCode]:
    if language is None:
        return None
    return LEGACY_LANGUAGE_ALIASES.get(language, language)


TEXTS = {
    "zh-Hans": {"assistant": "引路人"},
    "zh-Hant-TW": {"assistant": "引路人"},
    "zh-Hant-HK": {"assistant": "引路人"},
    "en": {"assistant": "Lumora"},
}


def get_language_used(requested_language: Optional[str]) -> str:
    if requested_language:
        return normalize_language_code(requested_language) or DEFAULT_LANGUAGE
    saved = db_get_setting("language_preference", DEFAULT_LANGUAGE)
    return normalize_language_code(saved) or DEFAULT_LANGUAGE


def get_text_pack(language: str) -> Dict[str, Any]:
    return TEXTS.get(language, TEXTS[DEFAULT_LANGUAGE])


def assert_divine_contract(response: Dict[str, Any]) -> Dict[str, Any]:
    missing_top_level = [
        field for field in ("result", "engine", "card") if field not in response
    ]
    if missing_top_level:
        raise RuntimeError(
            "divine_by_profile contract missing top-level fields: "
            + ", ".join(missing_top_level)
        )

    result = response["result"]
    engine = response["engine"]
    if not isinstance(result, dict):
        raise RuntimeError("divine_by_profile contract field result must be an object")
    if not isinstance(engine, dict):
        raise RuntimeError("divine_by_profile contract field engine must be an object")
    if not isinstance(response["card"], str) or not response["card"].strip():
        raise RuntimeError("divine_by_profile contract field card must be a non-empty string")

    missing_result = [
        field for field in DIVINE_RESULT_REQUIRED_FIELDS if field not in result
    ]
    missing_engine = [
        field for field in DIVINE_ENGINE_REQUIRED_FIELDS if field not in engine
    ]
    if missing_result:
        raise RuntimeError(
            "divine_by_profile contract missing result fields: "
            + ", ".join(missing_result)
        )
    if missing_engine:
        raise RuntimeError(
            "divine_by_profile contract missing engine fields: "
            + ", ".join(missing_engine)
        )

    return response


@router.get("/api/v1/ping")
def ping():
    return {"ok": True, "msg": "pong"}


@router.get("/api/v1/divine")
def divine_placeholder():
    return {"ok": True, "msg": "divine endpoint is alive"}


@router.get("/api/v1/settings/language", tags=["settings"])
def get_language_preference():
    language = normalize_language_code(
        db_get_setting("language_preference", DEFAULT_LANGUAGE)
    ) or DEFAULT_LANGUAGE
    return {
        "ok": True,
        "language": language,
        "supported_languages": ["zh-Hans", "zh-Hant-TW", "zh-Hant-HK", "en"],
    }


@router.put("/api/v1/settings/language", tags=["settings"])
def set_language_preference(payload: LanguagePreferenceIn):
    db_set_setting("language_preference", payload.language)
    return {
        "ok": True,
        "language": payload.language,
        "message": "language preference updated",
    }


@router.get("/api/v1/profiles", response_model=list[ProfileOut], tags=["profiles"])
def list_profiles():
    return [_normalize_profile_record(profile) for profile in db_list_profiles()]


@router.get("/api/v1/profiles/{profile_id}", response_model=ProfileOut, tags=["profiles"])
def get_profile(profile_id: str):
    profile = db_get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="profile not found")
    return _normalize_profile_record(profile)


@router.post("/api/v1/profiles", response_model=ProfileOut, tags=["profiles"])
def create_profile(payload: ProfileCreate):
    if payload.is_self and any(profile.get("is_self") for profile in db_list_profiles()):
        raise HTTPException(status_code=400, detail="a self profile already exists")

    profile_id = str(uuid4())
    item = _normalize_profile_payload({
        "id": profile_id,
        **payload.model_dump(),
        "updated_at": datetime.now(UTC).isoformat()
    })
    _attach_calibration(item)
    return _normalize_profile_record(db_create_profile(item))


@router.put("/api/v1/profiles/{profile_id}", response_model=ProfileOut, tags=["profiles"])
def update_profile(profile_id: str, payload: ProfileUpdate):
    existing = db_get_profile(profile_id)
    if not existing:
        raise HTTPException(status_code=404, detail="profile not found")

    updates = payload.model_dump(exclude_unset=True)
    if "is_self" in updates and updates["is_self"] != existing.get("is_self"):
        raise HTTPException(status_code=400, detail="is_self cannot be changed")

    merged = _normalize_profile_payload({**existing, **updates})
    try:
        _validate_profile_payload(merged)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    _attach_calibration(merged)
    updates = {
        key: value
        for key, value in merged.items()
        if key not in {"id"} and existing.get(key) != value
    }
    updates["updated_at"] = datetime.now(UTC).isoformat()

    updated = db_update_profile(profile_id, updates)
    return _normalize_profile_record(updated)


@router.delete("/api/v1/profiles/{profile_id}", tags=["profiles"])
def delete_profile(profile_id: str):
    existing = db_get_profile(profile_id)
    if not existing:
        raise HTTPException(status_code=404, detail="profile not found")
    if existing.get("is_self"):
        raise HTTPException(status_code=400, detail="self profiles cannot be deleted")

    deleted = db_delete_profile(profile_id)

    return {
        "ok": True,
        "deleted_profile_id": profile_id,
        "deleted_label": deleted.get("label", "")
    }


@router.post("/api/v1/divine_by_profile", response_model=DivineByProfileOut, tags=["divine"])
def divine_by_profile(payload: DivineByProfileIn):
    requested_profile = db_get_profile(payload.profile_id)
    if not requested_profile:
        raise HTTPException(status_code=404, detail="profile not found")
    effective_profile = choose_effective_profile(
        requested_profile=requested_profile,
        all_profiles=db_list_profiles(),
        question=payload.question,
    )

    language_used = get_language_used(payload.language)
    pack = get_text_pack(language_used)
    kernel = orchestrate_final_kernel(
        profile=effective_profile,
        requested_profile=requested_profile,
        question=payload.question,
        mode=payload.mode,
        language=language_used,
        clarification_answers=payload.clarification_answers,
        conversation_state=payload.conversation_state,
    )
    scenario = kernel["analysis"].get("domain", "general")

    response = {
        "ok": True,
        "status": kernel["status"],
        "assistant": pack["assistant"],
        "language": language_used,
        "scenario": scenario,
        "mode": payload.mode,
        "profile_id": payload.profile_id,
        "question": payload.question,
        "used_profile": effective_profile,
        "current_timestamp": kernel["analysis"]["current_timestamp"],
        "model_used": kernel.get("model_used"),
        "analysis": kernel["analysis"],
        "routing": kernel["routing"],
        "intake": kernel["intake"],
        "clarification": kernel["clarification"],
        "conversation_state": kernel.get("conversation_state", {}),
        "engine_registry": kernel["engine_registry"],
        "classics_registry": kernel["classics_registry"],
        "internal_engine": kernel.get("internal_engine", {}),
        "result": kernel["result"],
        "engine": kernel["engine"],
        "card": kernel["card"],
    }
    return assert_divine_contract(response)


# ════════════════════════════════════════════════════════════════════
# 新前端 UI 相容層（inline profile，不經 DB；與 /divine_by_profile 並存）
#   POST /api/v1/divine  ：聊天式單次推演 → 走 V7.6 Final Kernel(run_llm_divination)
#   GET  /api/v1/engines ：子引擎總覽（新 UI About 頁讀 summary）
# 新 UI 以 localStorage 單一 profile + 每次帶 chat_history 呼叫。
# ════════════════════════════════════════════════════════════════════

ENGINE_SUMMARY = {"total": 18, "primary": 14, "secondary": 3, "meta": 1}

_INLINE_EMPTY_RESULT = {
    "state": "",
    "core_conclusion": "",
    "traditional_model_judgment": "",
    "yinluren_guidance": "",
    "multi_perspectives": [],
    "resonance_points": [],
    "divergence_points": [],
    "research_summary": "",
    "risk_focus": [],
    "timing_window": "",
}


class DivineInlineIn(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    profile: Optional[Dict[str, Any]] = None
    chat_history: Optional[list[Dict[str, Any]]] = None
    language: Optional[str] = None
    use_thinking: bool = False

    @model_validator(mode="after")
    def _strip_question(self):
        self.question = (self.question or "").strip()
        if not self.question:
            raise ValueError("question must not be blank")
        return self


def _ui_profile_to_backend(p: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """新前端 inline profile（sex M/F、birth_hour/minute…）→ 後端 kernel profile dict，並補時區校正。"""
    p = p or {}
    sex = str(p.get("sex") or "").strip().upper()
    gender = "女" if sex in {"F", "FEMALE", "女"} else "男"

    birth_hour = p.get("birth_hour")
    birth_minute = p.get("birth_minute")
    if birth_hour in (None, ""):
        birth_time_slot = UNCERTAIN_TIME
    else:
        try:
            birth_time_slot = f"{int(birth_hour):02d}:{int(birth_minute or 0):02d}"
        except (TypeError, ValueError):
            birth_time_slot = UNCERTAIN_TIME

    label = (p.get("nickname") or p.get("name") or SELF_PROFILE_LABEL).strip() or SELF_PROFILE_LABEL
    occupation = str(p.get("occupation_category") or "").strip() or "未設定"
    keyword = str(p.get("occupation_keyword") or "").strip()
    if keyword:
        occupation = f"{occupation} · {keyword}"

    profile = {
        "id": "ui-inline",
        "label": label,
        "name": str(p.get("name") or "").strip(),
        "gender": gender,
        "birth_date": str(p.get("birth_date") or "").strip(),
        "birth_time_slot": birth_time_slot,
        "branch": "不確定",
        "zodiac": "不確定",
        "country": str(p.get("country") or "").strip() or "未設定",
        "province": str(p.get("province") or "").strip() or "未設定",
        "city": str(p.get("province") or "").strip() or "未設定",  # 新 UI 的 province 為市級
        "occupation": occupation,
        "consent": True,
        "is_self": False,
    }
    _attach_calibration(profile)
    return profile


def _sanitize_inline_history(history: Optional[list]) -> list[Dict[str, str]]:
    cleaned: list[Dict[str, str]] = []
    for item in history or []:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = item.get("content")
        if role in {"user", "assistant"} and isinstance(content, str) and content.strip():
            cleaned.append({"role": role, "content": content})
    return cleaned[-12:]


@router.get("/api/v1/engines", tags=["divine"])
def list_engine_summary():
    """子引擎總覽（新前端 About 頁讀 summary.{total,primary,secondary,meta}）。"""
    return {
        "summary": dict(ENGINE_SUMMARY),
        "note": "14 Primary ＋ 3 Secondary 推演子引擎（共 17），外加 ⑰明鑑鏡心 Meta 治理層；共 18 編號。",
    }


@router.post("/api/v1/divine", tags=["divine"])
def divine_inline(payload: DivineInlineIn):
    """聊天式單次推演：接受 inline profile + chat_history，內部走 V7.6 Final Kernel。"""
    backend_profile = _ui_profile_to_backend(payload.profile)
    history = _sanitize_inline_history(payload.chat_history)
    try:
        out = run_llm_divination(
            profile=backend_profile,
            question=payload.question,
            language=payload.language or DEFAULT_LANGUAGE,
            clarification_answers={},
            conversation_history=history,
            deep_reasoning=bool(payload.use_thinking),
        )
    except Exception as exc:  # 一律回 500 + 訊息，前端會顯示「推演暫時無法完成」
        logger.exception("inline divine failed")
        raise HTTPException(status_code=500, detail=f"推演失敗：{exc}") from exc

    out = out if isinstance(out, dict) else {}
    result = out.get("result")
    if out.get("status") == "needs_one_question" or not isinstance(result, dict):
        one_q = str(out.get("one_question") or "").strip()
        result = dict(_INLINE_EMPTY_RESULT)
        if one_q:
            result["core_conclusion"] = one_q
    return {
        "status": "ok",
        "result": result,
        "_meta": {"model_used": out.get("_model_used"), "tier": out.get("_tier")},
    }


@router.get("/api/v1/ui_strings", tags=["i18n"])
def ui_strings(lang: str = DEFAULT_LANGUAGE):
    """整包 UI 文字 i18n：選什麼語言就回該語言的全部介面字串（繁中原文直回；其他語言 LLM 翻譯＋快取）。"""
    return {
        "lang": lang,
        "dir": "rtl" if _ui_is_rtl(lang) else "ltr",
        "strings": _ui_get_bundle(lang),
    }
