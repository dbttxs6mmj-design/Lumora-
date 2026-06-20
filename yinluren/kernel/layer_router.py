from __future__ import annotations

from typing import Any, Dict, List

LAYER_ORDER = ["cosmic", "spacetime", "structure", "natal", "individual"]

LAYER_LABELS = {
    "cosmic": "氣數層",
    "spacetime": "時空層",
    "structure": "結構層",
    "natal": "命局層",
    "individual": "個體層",
}

SCOPE_WEIGHTS = {
    "personal": {"natal": 3, "structure": 2, "individual": 2, "spacetime": 1},
    "pair": {"structure": 3, "spacetime": 2, "natal": 1, "individual": 1},
    "family": {"structure": 3, "natal": 2, "spacetime": 1},
    "team": {"spacetime": 3, "structure": 2, "cosmic": 1},
    "organization": {"spacetime": 3, "cosmic": 2, "structure": 2},
    "regional": {"cosmic": 3, "spacetime": 2, "structure": 2},
    "national": {"cosmic": 4, "spacetime": 3, "structure": 2},
    "general": {"structure": 2, "spacetime": 2, "natal": 1, "individual": 1},
}

DOMAIN_WEIGHTS = {
    "relationship": {"structure": 3, "spacetime": 2, "natal": 1, "individual": 1},
    "career": {"natal": 3, "structure": 2, "cosmic": 1},
    "financial": {"natal": 2, "structure": 2, "cosmic": 2},
    "health": {"natal": 3, "individual": 2, "structure": 1},
    "family": {"natal": 2, "structure": 2, "spacetime": 1},
    "cooperation": {"spacetime": 3, "structure": 2, "cosmic": 1},
    "decision": {"spacetime": 3, "structure": 2, "individual": 1},
    "fortune": {"natal": 3, "cosmic": 2, "structure": 1},
    "situation": {"cosmic": 4, "spacetime": 3, "structure": 2},
    "general": {"structure": 2, "spacetime": 1, "natal": 1},
}

MODE_WEIGHTS = {
    "liuyao": {"structure": 4, "spacetime": 3},
    "bazi": {"natal": 4, "structure": 2, "cosmic": 1},
    "qimen": {"spacetime": 4, "structure": 2},
    "face": {"individual": 4, "structure": 1},
    "lingqi": {"individual": 4, "structure": 2},
}

LAYER_REQUIREMENTS = {
    "cosmic": {"event_background": True, "time_reference": True, "location_reference": True},
    "spacetime": {"time_reference": True, "location_reference": False},
    "structure": {"event_background": True},
    "natal": {"subject_birth_data": True},
    "individual": {"subject_context": True},
}


def _accumulate(scores: Dict[str, int], weights: Dict[str, int]) -> None:
    for layer, weight in weights.items():
        scores[layer] += weight


def route_layers(analysis: Dict[str, Any], mode: str) -> Dict[str, Any]:
    scores = {layer: 0 for layer in LAYER_ORDER}
    _accumulate(scores, SCOPE_WEIGHTS.get(analysis["scope"], SCOPE_WEIGHTS["general"]))
    _accumulate(scores, DOMAIN_WEIGHTS.get(analysis["domain"], DOMAIN_WEIGHTS["general"]))
    _accumulate(scores, MODE_WEIGHTS.get(mode, {}))

    ranked = sorted(LAYER_ORDER, key=lambda layer: scores[layer], reverse=True)
    primary_layers = ranked[:2]
    support_layers = ranked[2:4]

    requirements = {
        "time_reference": False,
        "location_reference": False,
        "subject_birth_data": False,
        "event_background": False,
        "subject_context": False,
    }
    for layer in primary_layers + support_layers:
        for key, enabled in LAYER_REQUIREMENTS.get(layer, {}).items():
            requirements[key] = requirements[key] or enabled

    return {
        "mode": mode,
        "scores": scores,
        "primary_layers": primary_layers,
        "support_layers": support_layers,
        "requirements": requirements,
        "summary": {
            "primary": [LAYER_LABELS[layer] for layer in primary_layers],
            "support": [LAYER_LABELS[layer] for layer in support_layers],
        },
    }
