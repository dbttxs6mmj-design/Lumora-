REL_KEYWORDS = {
    "relationship": ["感情", "分手", "復合", "曖昧", "婚姻", "伴侶", "喜歡", "戀愛", "夫妻", "結婚", "離婚"],
    "career": ["工作", "升職", "跳槽", "面試", "薪水", "裁員", "主管", "老闆", "事業", "職涯"],
    "health": ["健康", "身體", "疾病", "病", "住院", "檢查", "醫院", "恢復", "體力", "失眠", "焦慮", "精神"],
}

def infer_scenario(question: str) -> str:
    q = question or ""
    for scenario, kws in REL_KEYWORDS.items():
        if any(k in q for k in kws):
            return scenario
    return "general"
