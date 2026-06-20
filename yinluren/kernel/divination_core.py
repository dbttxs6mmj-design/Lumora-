from typing import Dict, Any
from .relationship_model import infer_scenario
from .time_reverse_engine import reverse_time_infer

def divine_for_profile(profile: Dict[str, Any], question: str, language: str) -> Dict[str, Any]:
    assistant_name = "Lumora" if language == "en" else "引路人"
    scenario = infer_scenario(question)

    reverse_mode = False
    reverse_result = None

    if profile.get("birth_time_slot") == "不確定" and not profile.get("is_self", False):
        reverse_mode = True
        reverse_result = reverse_time_infer(profile, question)

    verdict = f"{assistant_name} 已收到問題，正在推演。"
    if reverse_mode:
        verdict += "（已啟動時程反推法專業流程）"

    return {
        "ok": True,
        "assistant": assistant_name,
        "question": question,
        "used_profile": profile,
        "scenario": scenario,
        "time_reverse_inference": reverse_mode,
        "reverse_engine": reverse_result,
        "verdict": verdict,
        "visualization": {
            "style": "warm",
            "note": "下一版將輸出完整推演圖像"
        },
        "pro": {
            "locked": True,
            "reason": "訂閱用戶可查看完整推演C與事件反演過程"
        }
    }
