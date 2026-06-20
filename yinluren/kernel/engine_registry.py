from __future__ import annotations

from typing import Any, Dict, List

READING_MODE_LABELS = {
    "liuyao": "問一事（六爻＋六壬）",
    "bazi": "看人生（八字命局）",
    "qimen": "選方向（奇門決策）",
    "face": "看相",
    "lingqi": "靈棋術",
}


def build_engine_registry() -> Dict[str, Any]:
    return {
        "five_layers": [
            {
                "key": "cosmic",
                "label": "氣數層",
                "classics": [
                    "黃帝太一八門入式訣",
                    "太乙金鏡式經",
                    "太乙真數",
                    "太乙神數",
                    "河洛理數",
                ],
                "role": "處理氣數、大勢、長波段局勢。",
            },
            {
                "key": "spacetime",
                "label": "時空層",
                "classics": ["六壬", "六壬神課", "遁甲演繹"],
                "role": "處理時機、方向、時空局勢與事件窗口。",
            },
            {
                "key": "structure",
                "label": "結構層",
                "classics": [
                    "周易",
                    "周易古占法",
                    "京氏易傳",
                    "焦氏易林",
                    "易林補遺",
                    "梅花易數",
                    "太玄經",
                    "黃金冊",
                    "黃金策總斷千金賦直解",
                    "卜筮正宗",
                    "增刪易卜",
                    "易隱",
                    "斷易天機",
                    "三易備遺（含連山、歸藏系統）",
                ],
                "role": "處理結構、變化、卦理與事件骨架。",
            },
            {
                "key": "natal",
                "label": "命局層",
                "classics": ["淵海子平", "子平真詮", "窮通寶鑑評註", "滴天髓"],
                "role": "處理長期命局、人生趨勢與命式交叉驗證。",
            },
            {
                "key": "individual",
                "label": "個體層",
                "classics": ["靈棋經", "麻衣神相", "麻衣相法", "神相全編", "柳莊相法"],
                "role": "處理個體當下形勢、外應與即時問占。",
            },
        ],
        "engines": [
            {
                "key": "taiyi_engine",
                "label": "太乙 / 三元 / 河洛",
                "layer": "cosmic",
                "classics": [
                    "黃帝太一八門入式訣",
                    "太乙金鏡式經",
                    "太乙真數",
                    "太乙神數",
                    "河洛理數",
                ],
                "status": "placeholder_boundary",
                "modes": ["bazi", "qimen"],
                "notes": "氣數層已切到 92 本口徑，但目前仍是 registry 與 placeholder boundary。",
            },
            {
                "key": "liuren_engine",
                "label": "六壬",
                "layer": "spacetime",
                "classics": ["六壬", "六壬神課"],
                "status": "adapter_scaffold",
                "modes": ["liuyao", "qimen"],
                "notes": "已可作為輔助校驗引擎，但仍非完整古籍內核。",
            },
            {
                "key": "qimen_engine",
                "label": "奇門",
                "layer": "spacetime",
                "classics": ["遁甲演繹"],
                "status": "adapter_scaffold",
                "modes": ["qimen"],
                "notes": "已從六爻與靈棋流程分離。",
            },
            {
                "key": "zhouyi_engine",
                "label": "周易 / 三易",
                "layer": "structure",
                "classics": [
                    "周易",
                    "周易古占法",
                    "京氏易傳",
                    "焦氏易林",
                    "易林補遺",
                    "梅花易數",
                    "太玄經",
                    "黃金冊",
                    "黃金策總斷千金賦直解",
                    "卜筮正宗",
                    "增刪易卜",
                    "易隱",
                    "斷易天機",
                    "三易備遺（含連山、歸藏系統）",
                ],
                "status": "adapter_scaffold",
                "modes": ["liuyao", "lingqi", "qimen", "bazi"],
                "notes": "作為 92 本口徑結構層的共通校驗邊界。",
            },
            {
                "key": "liuyao_engine",
                "label": "六爻",
                "layer": "structure",
                "classics": ["周易", "卜筮正宗", "增刪易卜", "易隱", "斷易天機"],
                "status": "adapter_scaffold",
                "modes": ["liuyao"],
                "notes": "已清楚與六壬、靈棋分流。",
            },
            {
                "key": "bazi_engine",
                "label": "子平 / 滴天髓",
                "layer": "natal",
                "classics": ["淵海子平", "子平真詮", "窮通寶鑑評註", "滴天髓"],
                "status": "adapter_scaffold",
                "modes": ["bazi"],
                "notes": "命局層已接進主推演鏈，但仍非完整子平推盤。",
            },
            {
                "key": "lingqi_engine",
                "label": "靈棋",
                "layer": "individual",
                "classics": ["靈棋經"],
                "status": "adapter_scaffold",
                "modes": ["lingqi"],
                "notes": "已獨立模式，不再共用六爻模板。",
            },
            {
                "key": "face_engine",
                "label": "相術",
                "layer": "individual",
                "classics": ["麻衣神相", "麻衣相法", "神相全編", "柳莊相法"],
                "status": "ui_only_boundary",
                "modes": ["face"],
                "notes": "保留個體層邊界；92 本口徑已留名，但尚未接入影像核心。",
            },
        ],
    }


def build_runtime_classics_inventory(engine_registry: Dict[str, Any]) -> Dict[str, Any]:
    connected = []
    not_connected = []

    for engine in engine_registry["engines"]:
        target = connected if engine["status"] in {"adapter_scaffold", "ui_only_boundary"} else not_connected
        target.append(
            {
                "engine_key": engine["key"],
                "label": engine["label"],
                "layer": engine["layer"],
                "classics": engine["classics"],
                "status": engine["status"],
                "notes": engine["notes"],
            }
        )

    named_classics = sorted({classic for engine in engine_registry["engines"] for classic in engine["classics"]})
    return {
        "declared_total_classics": 92,
        "named_in_current_registry": named_classics,
        "named_connected_or_scaffolded": connected,
        "not_connected": [
            {
                "group": "Unnamed classics slots",
                "remaining_count": max(92 - len(named_classics), 0),
                "status": "source_list_missing",
                "notes": "主推演鏈已改採 92 本口徑；若 registry 尚有未命名缺口，不可假裝已全部接入。",
            },
            {
                "group": "Full classical kernels",
                "status": "not_yet_implemented",
                "notes": "92 本目前多為 registry、adapter scaffold 或 UI boundary，尚未形成完整古籍演算內核；未命名缺口由《明鑑鏡心》M19 主動學習機制持續補入。",
            },
        ],
    }
