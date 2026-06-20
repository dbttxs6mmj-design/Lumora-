from __future__ import annotations

from typing import Any, Dict

from ..classics_registry import build_classics_registry
from .engine_registry import build_engine_registry
from .layer_router import route_layers
from .question_analyzer import build_question_analysis


# Final Kernel 核心來源口徑（單一來源，避免重覆敘述）
KERNEL_SOURCE_NOTE = (
    "Final Kernel 採 92+ 部古籍整合口徑：14 Primary ＋ 3 Secondary 推演子引擎（共 17）"
    "，由 ⑰明鑑鏡心 Meta 治理層全程校正。92 為當前底數非上限，可依 M19 ＋ "
    "AUTO-LEARN-001~005 持續新增知識源；治理規範統一依 R1~R60 ＋ AGI 死命令 "
    "＋ RG-MAIN-001~005+007。完整書單見 FINAL_KERNEL_92_CLASSICS.md。"
)


def _build_card(result: Dict[str, Any], language: str) -> str:
    headers = {
        "zh-Hant-TW": ("核心結論", "古籍共讀", "引路人判斷", "風險焦點", "時間窗口", "多視角", "共振點", "分歧點", "外部比對"),
        "zh-Hant-HK": ("核心結論", "古籍共讀", "引路人判斷", "風險焦點", "時間窗口", "多視角", "共振點", "分歧點", "外部比對"),
        "zh-Hans": ("核心结论", "古籍共读", "引路人判断", "风险焦点", "时间窗口", "多视角", "共振点", "分歧点", "外部比对"),
        "en": ("Core Conclusion", "Classical Consensus", "Lumora Guidance", "Risk Focus", "Timing Window", "Perspectives", "Resonance", "Divergence", "External Research"),
    }.get(language, ("核心結論", "古籍共讀", "引路人判斷", "風險焦點", "時間窗口", "多視角", "共振點", "分歧點", "外部比對"))
    risk_lines = "\n".join(f"- {item}" for item in result.get("risk_focus", []))
    perspectives = "\n".join(f"- {item}" for item in result.get("multi_perspectives", []))
    resonance = "\n".join(f"- {item}" for item in result.get("resonance_points", []))
    divergence = "\n".join(f"- {item}" for item in result.get("divergence_points", []))
    return (
        f"{headers[0]}\n{result.get('core_conclusion', result.get('state', ''))}\n\n"
        f"{headers[1]}\n{result.get('traditional_model_judgment', '')}\n\n"
        f"{headers[2]}\n{result.get('yinluren_guidance', '')}\n\n"
        f"{headers[5]}\n{perspectives}\n\n"
        f"{headers[6]}\n{resonance}\n\n"
        f"{headers[7]}\n{divergence}\n\n"
        f"{headers[8]}\n{result.get('research_summary', '')}\n\n"
        f"{headers[3]}\n{risk_lines}\n\n"
        f"{headers[4]}\n{result.get('timing_window', '')}"
    )


def orchestrate_final_kernel(
    profile: Dict[str, Any],
    question: str,
    mode: str,
    language: str,
    clarification_answers: Dict[str, Any] | None = None,
    requested_profile: Dict[str, Any] | None = None,
    conversation_state: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    from .llm_divination import run_llm_divination

    requested_profile = requested_profile or profile
    analysis = build_question_analysis(question, profile)
    routing = route_layers(analysis, mode)
    engine_registry = build_engine_registry()

    llm_result = run_llm_divination(
        profile=profile,
        question=question,
        language=language,
        clarification_answers=clarification_answers,
    )

    if llm_result.get("status") == "needs_one_question":
        one_q = llm_result.get("one_question", "")
        result = {
            "state": one_q,
            "core_conclusion": one_q,
            "traditional_model_judgment": "",
            "yinluren_guidance": one_q,
            "multi_perspectives": [],
            "resonance_points": [],
            "divergence_points": [],
            "research_summary": "",
            "risk_focus": [],
            "timing_window": "",
        }
        return {
            "status": "clarification_needed",
            "model_used": llm_result.get("_model_used") or "openai",
            "analysis": analysis,
            "routing": routing,
            "intake": {"ask_context": {}},
            "clarification": {
                "prompt": one_q,
                "asked_key": "llm_inferred",
                "current_question": {"key": "llm_inferred", "question": one_q, "required": True},
                "questions": [{"key": "llm_inferred", "question": one_q, "required": True}],
                "collected_answers": clarification_answers or {},
                "recommended_missing_fields": [],
                "target_person": {},
                "conversation_state": conversation_state or {},
                "next_step": "ask",
            },
            "conversation_state": conversation_state or {},
            "engine_registry": engine_registry,
            "classics_registry": build_classics_registry(mode),
            "internal_engine": {},
            "result": result,
            "engine": {
                "type": "awaiting_reply",
                "active": True,
                "confidence": 0.0,
                "best_candidate": None,
                "top_candidates": [],
                "adapter_status": "awaiting_context",
                "steps": [],
                "note": "",
                "birthplace_factor_used": False,
                "birthplace_factor_signature": None,
            },
            "card": one_q,
        }

    result = llm_result["result"]
    model_used = llm_result.get("_model_used") or "openai"
    return {
        "status": "ready",
        "model_used": model_used,
        "analysis": analysis,
        "routing": routing,
        "intake": {"ask_context": {}},
        "clarification": {
            "prompt": "",
            "asked_key": None,
            "current_question": None,
            "questions": [],
            "collected_answers": clarification_answers or {},
            "recommended_missing_fields": [],
            "target_person": {},
            "conversation_state": conversation_state or {},
            "next_step": "ready",
        },
        "conversation_state": conversation_state or {},
        "engine_registry": engine_registry,
        "classics_registry": build_classics_registry(mode),
        "internal_engine": {},
        "result": result,
        "engine": {
            "type": "llm_openai",
            "active": True,
            "confidence": 0.85,
            "best_candidate": {"label": f"OpenAI {model_used} 融合推演", "model": model_used},
            "top_candidates": [{"label": f"OpenAI {model_used}", "engine": "llm_openai", "model": model_used}],
            "adapter_status": "llm_engine",
            "steps": ["question_analysis", "llm_divination"],
            "note": f"由 OpenAI {model_used} 執行——{KERNEL_SOURCE_NOTE}",
            "birthplace_factor_used": True,
            "birthplace_factor_signature": "llm",
        },
        "card": _build_card(result, language),
    }
