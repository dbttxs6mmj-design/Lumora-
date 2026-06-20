from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List


OPERATIONAL_CLASSICS: List[Dict[str, Any]] = [
    {"key": "taiyi_bamen", "name": "黃帝太一八門入式訣", "layer": "cosmic", "domains": ["situation", "career", "decision", "general"], "focus": "看長波局勢與大方向"},
    {"key": "taiyi_jinjing", "name": "太乙金鏡式經", "layer": "cosmic", "domains": ["situation", "career", "financial", "general"], "focus": "看大勢節奏與轉折"},
    {"key": "taiyi_zhenshu", "name": "太乙真數", "layer": "cosmic", "domains": ["situation", "decision", "general"], "focus": "看氣數偏向與局勢開合"},
    {"key": "taiyi_shenshu", "name": "太乙神數", "layer": "cosmic", "domains": ["fortune", "career", "general"], "focus": "看流勢強弱與長期窗口"},
    {"key": "heluolishu", "name": "河洛理數", "layer": "cosmic", "domains": ["fortune", "career", "relationship", "general"], "focus": "看數理節律與中長期結構"},
    {"key": "liuren", "name": "六壬", "layer": "spacetime", "domains": ["decision", "relationship", "career", "general"], "focus": "看時機、應期與外部條件"},
    {"key": "liuren_shenke", "name": "六壬神課", "layer": "spacetime", "domains": ["decision", "career", "health", "general"], "focus": "看事件節點與外應"},
    {"key": "dunjia_yanyi", "name": "遁甲演繹", "layer": "spacetime", "domains": ["decision", "career", "cooperation", "general"], "focus": "看方向選擇與位置優劣"},
    {"key": "zhouyi", "name": "周易", "layer": "structure", "domains": ["general", "relationship", "career", "health"], "focus": "看整體卦勢與變化骨架"},
    {"key": "zhouyi_guzhan", "name": "周易古占法", "layer": "structure", "domains": ["general", "relationship", "decision"], "focus": "看事件起落與主客互動"},
    {"key": "jingshi", "name": "京氏易傳", "layer": "structure", "domains": ["career", "financial", "general"], "focus": "看層位次序與勢能升降"},
    {"key": "jiaoshi_yilin", "name": "焦氏易林", "layer": "structure", "domains": ["relationship", "health", "general"], "focus": "看細部象意與暗線"},
    {"key": "yilin_buyi", "name": "易林補遺", "layer": "structure", "domains": ["relationship", "fortune", "general"], "focus": "看補充象義與結果偏向"},
    {"key": "meihua", "name": "梅花易數", "layer": "structure", "domains": ["decision", "general", "career"], "focus": "看眼前應象與快速轉折"},
    {"key": "taixuan", "name": "太玄經", "layer": "structure", "domains": ["fortune", "situation", "general"], "focus": "看勢能層次與內外消長"},
    {"key": "huangjince", "name": "黃金冊", "layer": "structure", "domains": ["relationship", "career", "general"], "focus": "看事理判準與斷語結構"},
    {"key": "huangjincelink", "name": "黃金策總斷千金賦直解", "layer": "structure", "domains": ["relationship", "decision", "general"], "focus": "看成敗關節與落點"},
    {"key": "bushi_zhengzong", "name": "卜筮正宗", "layer": "structure", "domains": ["general", "health", "relationship"], "focus": "看主軸吉凶與實際應事"},
    {"key": "zengshan_yibu", "name": "增刪易卜", "layer": "structure", "domains": ["general", "career", "financial"], "focus": "看取用捨與細節調整"},
    {"key": "yiyin", "name": "易隱", "layer": "structure", "domains": ["relationship", "career", "general"], "focus": "看隱性條件與未明變因"},
    {"key": "duanyi_tianji", "name": "斷易天機", "layer": "structure", "domains": ["decision", "fortune", "general"], "focus": "看臨門轉折與快慢"},
    {"key": "sanyi_beiyi", "name": "三易備遺（含連山、歸藏系統）", "layer": "structure", "domains": ["situation", "decision", "general"], "focus": "看多系統旁證與分歧點"},
    {"key": "yuanhai_ziping", "name": "淵海子平", "layer": "natal", "domains": ["career", "relationship", "health", "general"], "focus": "看命局底盤與長期氣勢"},
    {"key": "ziping_zhenquan", "name": "子平真詮", "layer": "natal", "domains": ["career", "relationship", "financial", "general"], "focus": "看格局重點與用神方向"},
    {"key": "qiongtong", "name": "窮通寶鑑評註", "layer": "natal", "domains": ["career", "health", "general"], "focus": "看節令與適性條件"},
    {"key": "ditiansui", "name": "滴天髓", "layer": "natal", "domains": ["career", "fortune", "general"], "focus": "看氣勢純雜與成局條件"},
    {"key": "lingqijing", "name": "靈棋經", "layer": "individual", "domains": ["general", "decision", "relationship", "career"], "focus": "看當下應感與即時指向"},
]

PHYSIOGNOMY_CLASSICS: List[Dict[str, Any]] = [
    {"key": "maiyi_shenxiang", "name": "麻衣神相", "layer": "individual"},
    {"key": "maiyi_xiangfa", "name": "麻衣相法", "layer": "individual"},
    {"key": "shenxiang_quanbian", "name": "神相全編", "layer": "individual"},
    {"key": "liuzhuang_xiangfa", "name": "柳莊相法", "layer": "individual"},
]

STANCE_BY_LAYER = {
    "cosmic": ["大勢偏開", "大勢偏守", "外局仍在變", "宜先看長線", "轉折未完", "順勢比硬衝更有利"],
    "spacetime": ["時機未滿", "先守後動", "窗口正在靠近", "方位與節點要選準", "外部條件仍在移動", "先觀察再落子"],
    "structure": ["主線已成形", "局面有反覆", "關鍵在取捨", "表面與實際有落差", "先理順結構再談結果", "變化點還在中段"],
    "natal": ["命局底盤可承接", "命局有條件但不能躁進", "適合走長線累積", "短期容易受外力牽動", "真正優勢在結構不是速度", "要避開和自身節奏相反的選擇"],
    "individual": ["眼前感受很真", "先處理當下訊號", "外應偏明顯", "直覺可用但不能只靠直覺", "先收心再定下一步", "局面會先從小處鬆動"],
}


def build_classics_registry(mode: str) -> Dict[str, Any]:
    active = PHYSIOGNOMY_CLASSICS if mode == "face" else OPERATIONAL_CLASSICS
    return {
        "operational_total_classics": len(OPERATIONAL_CLASSICS),
        "physiognomy_total_classics": len(PHYSIOGNOMY_CLASSICS),
        "active_total_classics": len(active),
        "active_classics": active,
        "excluded_physiognomy_classics": [] if mode == "face" else PHYSIOGNOMY_CLASSICS,
    }


def _seed_value(
    question: str,
    ask_context: Dict[str, Any],
    classic: Dict[str, Any],
    birthplace_factor: Dict[str, Any],
) -> int:
    payload = json.dumps(
        {
            "question": question,
            "profile": ask_context.get("active_profile", {}),
            "classic": classic["key"],
            "birthplace_signature": birthplace_factor.get("signature"),
            "known_background": ask_context.get("known_background", {}),
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def _layer_weight(classic: Dict[str, Any], routing: Dict[str, Any]) -> float:
    layer = classic["layer"]
    if layer in routing.get("primary_layers", []):
        return 1.35
    if layer in routing.get("support_layers", []):
        return 1.12
    return 0.92


def run_classics_reasoning(
    *,
    question: str,
    ask_context: Dict[str, Any],
    analysis: Dict[str, Any],
    routing: Dict[str, Any],
    birthplace_factor: Dict[str, Any],
    mode: str,
) -> Dict[str, Any]:
    classics = build_classics_registry(mode)["active_classics"]
    if mode == "face":
        return {
            "active_total": len(classics),
            "views": [],
            "top_views": [],
            "resonance_points": [],
            "divergence_points": [],
        }

    domain = analysis.get("domain", "general")
    qi = birthplace_factor.get("qi_profile", {})
    views = []
    for classic in classics:
        seed_value = _seed_value(question, ask_context, classic, birthplace_factor)
        stance_pool = STANCE_BY_LAYER[classic["layer"]]
        stance = stance_pool[seed_value % len(stance_pool)]
        domain_weight = 1.18 if domain in classic["domains"] or "general" in classic["domains"] else 0.95
        qi_weight = 1 + abs(float(qi.get("weighting_bias", 0.0))) / 2
        weight = round(_layer_weight(classic, routing) * domain_weight * qi_weight, 4)
        views.append(
            {
                "classic": classic["name"],
                "layer": classic["layer"],
                "focus": classic["focus"],
                "stance": stance,
                "weight": weight,
                "signal": seed_value % 6,
            }
        )

    views.sort(key=lambda item: item["weight"], reverse=True)
    top_views = views[:6]

    stance_groups: Dict[str, List[str]] = {}
    for item in top_views:
        stance_groups.setdefault(item["stance"], []).append(item["classic"])
    resonance_points = [
        f"{stance}：{', '.join(classics[:3])}"
        for stance, classics in stance_groups.items()
        if len(classics) >= 2
    ][:3]
    divergence_points = [
        f"{item['classic']}偏向「{item['stance']}」"
        for item in top_views
        if sum(1 for other in top_views if other["stance"] == item["stance"]) == 1
    ][:3]

    return {
        "active_total": len(classics),
        "views": views,
        "top_views": top_views,
        "resonance_points": resonance_points,
        "divergence_points": divergence_points,
    }
