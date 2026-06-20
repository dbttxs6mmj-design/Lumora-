"""
補問流程（已停用）— 由 LLM 引擎直接處理。
保留介面以維持 import 相容性。
"""
from __future__ import annotations
from typing import Any, Dict


def build_clarification(
    question: str,
    mode: str,
    profile: Dict[str, Any],
    answers: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    return {
        "needs_clarification": False,
        "prompt": "",
        "questions": [],
        "intake": {},
        "routing": {},
        "current_timestamp": "",
    }
