from typing import Dict, Any, List
from .types import TIME_SLOTS
from .relationship_model import infer_scenario

def _health_score(slot: Dict[str, str], question: str) -> float:
    q = question or ""
    base = 50.0
    if any(k in q for k in ["健康", "身體", "疾病", "病", "住院", "檢查", "醫院", "恢復", "體力"]):
        if slot["branch"] in ["子", "丑", "寅"]:
            base += 16
        elif slot["branch"] in ["卯", "辰", "巳"]:
            base += 10
        elif slot["branch"] in ["午", "未"]:
            base += 6
    if any(k in q for k in ["睡", "失眠", "精神", "壓力", "焦慮", "情緒", "心神"]):
        if slot["branch"] in ["子", "丑", "寅", "亥"]:
            base += 14
        elif slot["branch"] in ["申", "酉"]:
            base += 6
    if any(k in q for k in ["長期", "慢性", "反覆", "恢復慢", "調養"]):
        if slot["branch"] in ["丑", "辰", "未", "戌"]:
            base += 10
    if any(k in q for k in ["突然", "突發", "急性", "忽然"]):
        if slot["branch"] in ["寅", "巳", "申", "亥"]:
            base += 10
    base += (ord(slot["branch"]) % 7) * 1.1
    return round(base, 2)

def _relationship_score(slot: Dict[str, str], question: str) -> float:
    q = question or ""
    base = 50.0
    if any(k in q for k in ["感情", "分手", "復合", "曖昧", "婚姻", "伴侶", "喜歡", "戀愛", "夫妻", "結婚", "離婚"]):
        if slot["branch"] in ["酉", "戌", "亥", "子"]:
            base += 15
    base += (ord(slot["branch"]) % 7) * 1.3
    return round(base, 2)

def _career_score(slot: Dict[str, str], question: str) -> float:
    q = question or ""
    base = 50.0
    if any(k in q for k in ["工作", "升職", "跳槽", "面試", "薪水", "裁員", "主管", "老闆", "事業", "職涯"]):
        if slot["branch"] in ["辰", "巳", "午", "未"]:
            base += 15
    base += (ord(slot["branch"]) % 7) * 1.2
    return round(base, 2)

def _general_score(slot: Dict[str, str], question: str) -> float:
    return round(50.0 + (ord(slot["branch"]) % 7) * 1.0, 2)

def _score_slot(slot: Dict[str, str], question: str, scenario: str) -> float:
    if scenario == "health":
        return _health_score(slot, question)
    if scenario == "relationship":
        return _relationship_score(slot, question)
    if scenario == "career":
        return _career_score(slot, question)
    return _general_score(slot, question)

def reverse_time_infer(profile: Dict[str, Any], question: str) -> Dict[str, Any]:
    scenario = infer_scenario(question)
    candidates: List[Dict[str, Any]] = []
    for slot in TIME_SLOTS:
        score = _score_slot(slot, question, scenario)
        candidates.append({
            "birth_time_slot": slot["birth_time_slot"],
            "branch": slot["branch"],
            "zodiac": slot["zodiac"],
            "score": score,
        })
    candidates.sort(key=lambda x: x["score"], reverse=True)
    top = candidates[:4]

    if scenario == "health":
        verify_questions = [
            "她的問題更偏向睡眠／精神／壓力，還是身體器官／慢性疾病？",
            "症狀通常在夜間加重，還是白天更明顯？",
            "是長期慢慢累積，還是近期突然出現？",
        ]
    elif scenario == "relationship":
        verify_questions = [
            "關係重大轉折通常發生在夜晚還是白天？",
            "她在人際互動上偏壓抑還是直接？",
            "過往重要感情事件是否多集中在某些年份？",
        ]
    elif scenario == "career":
        verify_questions = [
            "她的職涯壓力更偏人際，還是偏績效與責任？",
            "重大工作轉折多在白天決策，還是長期醞釀後突然發生？",
            "她的工作節奏偏穩定規律，還是高波動高壓？",
        ]
    else:
        verify_questions = [
            "是否能把問題明確成健康、感情或事業其中一類？",
            "能否補充一兩個已發生的重要事件做交叉驗證？",
        ]

    return {
        "method": "time_reverse_inference",
        "scenario": scenario,
        "profile_label": profile.get("label"),
        "steps": [
            "建立所有可能時辰集合（12地支）",
            "辨識問題場景類型",
            "逐時辰模擬推演並建立一致性分數",
            "排除低分與矛盾時辰",
            "保留最可能命盤並提出驗證問題",
        ],
        "best_candidate": top[0] if top else None,
        "top_candidates": top,
        "all_candidates": candidates,
        "verify_questions": verify_questions,
        "note": "此為健康/關係/工作反推骨架；下一版可接 Final Kernel 做更細緻校驗。",
    }
