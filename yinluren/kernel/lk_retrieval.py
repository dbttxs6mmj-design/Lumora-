"""LK 語意檢索層（RAG）—— 主動偵辨用戶意圖、語意匹配最相關 LK，跨語言、處理樣板外問題。

這一層讓 Final Kernel「不把 LK 寫死」：9,626 條 LK 為語意知識庫，依用戶真實意圖
檢索最相關者作為後台候選，由大模型主動甄別融會貫通；查無匹配時自由推演、絕不受限。
全程 graceful：索引缺失 / API 失敗 → 回傳空、退回純大模型行為（不阻斷推演）。
"""
from __future__ import annotations

import functools
import json
import os
from typing import Any, Dict, List

_IDX = os.path.join(os.path.dirname(__file__), "lk_index")
_MODEL = os.environ.get("OPENAI_EMBED_MODEL", "text-embedding-3-small")


@functools.lru_cache(maxsize=1)
def _load():
    import numpy as np
    emb = np.load(os.path.join(_IDX, "embeddings.npy"))
    with open(os.path.join(_IDX, "corpus.jsonl"), encoding="utf-8") as f:
        corpus = [json.loads(line) for line in f if line.strip()]
    return emb, corpus


def available() -> bool:
    return os.path.exists(os.path.join(_IDX, "embeddings.npy"))


def retrieve(question: str, k: int = 10, min_score: float = 0.22) -> List[Dict[str, Any]]:
    """回傳與 question 語意最相近的前 k 條 LK（已過濾低分）。失敗回傳 []。"""
    if not question or not available():
        return []
    try:
        import numpy as np
        from openai import OpenAI

        emb, corpus = _load()
        client = OpenAI()  # OPENAI_API_KEY from env (.env should override stale system var)
        r = client.embeddings.create(model=_MODEL, input=[question])
        q = np.array(r.data[0].embedding, dtype=np.float32)
        q /= (np.linalg.norm(q) + 1e-8)
        sims = emb @ q
        order = np.argsort(-sims)[: max(k * 3, k)]
        out = []
        for i in order:
            s = float(sims[int(i)])
            if s < min_score:
                continue
            row = dict(corpus[int(i)])
            row["score"] = round(s, 3)
            out.append(row)
            if len(out) >= k:
                break
        return out
    except Exception:
        return []


def format_candidates(items: List[Dict[str, Any]]) -> str:
    """組成注入 prompt 的後台候選知識段（純後台、不對用戶輸出）。"""
    if not items:
        return ""
    lines = ["## 後台候選知識（語意檢索 · 僅供主動甄別參考 · 非樣板 · 絕不照搬 · 絕不外露）"]
    for it in items:
        eng = it.get("engine_cn", "")
        lines.append(f"- 〔{eng}〕{it.get('title','')}（相關度 {it.get('score','')}）")
    lines.append("（以上為依你判斷檢索之候選；主動甄別最貼合用戶真實意圖者融會貫通；"
                 "若用戶問題不在候選範圍，依引擎原理自由推演，絕不受候選侷限。）")
    return "\n".join(lines)
