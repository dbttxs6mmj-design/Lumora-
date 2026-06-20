from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, List


def build_research_queries(ask_context: Dict[str, Any]) -> List[str]:
    profile = ask_context.get("active_profile", {})
    birthplace = ask_context.get("birthplace", {})
    question = ask_context.get("question", {})
    queries = [question.get("text", "")]

    if birthplace.get("city") and birthplace.get("country"):
        queries.append(f"{birthplace['city']} {birthplace['country']} {question.get('domain', 'general')}")
    if profile.get("occupation"):
        queries.append(f"{profile['occupation']} {question.get('domain', 'general')} trend")
    return [query.strip() for query in queries if query and query.strip()]


def _local_fallback_findings(ask_context: Dict[str, Any]) -> List[Dict[str, str]]:
    birthplace = ask_context.get("birthplace", {})
    profile = ask_context.get("active_profile", {})
    question = ask_context.get("question", {})
    findings = []
    if birthplace.get("city") or birthplace.get("country"):
        findings.append(
            {
                "title": "地區脈絡",
                "snippet": f"目前會優先把 {birthplace.get('city') or birthplace.get('country')} 的城市與地區條件納入對照。",
                "source": "local_context",
                "url": "",
            }
        )
    if profile.get("occupation"):
        findings.append(
            {
                "title": "職業脈絡",
                "snippet": f"這題會把 {profile.get('occupation')} 的產業節奏與現實條件一併比對。",
                "source": "local_context",
                "url": "",
            }
        )
    findings.append(
        {
            "title": "問題焦點",
            "snippet": f"外部研究會優先對照 {question.get('domain', 'general')} 類問題常見的時間、地區與現實條件。",
            "source": "local_context",
            "url": "",
        }
    )
    return findings


def _run_tavily(queries: List[str], api_key: str) -> List[Dict[str, str]]:
    findings: List[Dict[str, str]] = []
    for query in queries[:3]:
        payload = json.dumps(
            {
                "api_key": api_key,
                "query": query,
                "search_depth": "advanced",
                "max_results": 3,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            "https://api.tavily.com/search",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=8) as response:  # noqa: S310
            data = json.loads(response.read().decode("utf-8"))
        for item in data.get("results", []):
            findings.append(
                {
                    "title": item.get("title", ""),
                    "snippet": item.get("content", ""),
                    "source": "tavily",
                    "url": item.get("url", ""),
                }
            )
    return findings


def run_research_pipeline(ask_context: Dict[str, Any]) -> Dict[str, Any]:
    queries = build_research_queries(ask_context)
    provider = os.getenv("LUMORA_RESEARCH_PROVIDER", "tavily").strip().lower() or "tavily"
    api_key = os.getenv("TAVILY_API_KEY", "").strip()
    pipeline_required = bool(ask_context.get("research", {}).get("required"))
    fallback_findings = _local_fallback_findings(ask_context)

    if not pipeline_required:
        return {
            "pipeline_started": True,
            "required": False,
            "provider": provider,
            "provider_configured": bool(api_key),
            "used_external_results": False,
            "queries": queries,
            "findings": [],
            "fallback_findings": fallback_findings,
            "status": "internal_only",
            "summary": "這一題以命局與題目本身的脈絡為主，外部資料只作低權重旁證。",
        }

    if provider == "tavily" and api_key:
        try:
            findings = _run_tavily(queries, api_key)
            return {
                "pipeline_started": True,
                "required": True,
                "provider": provider,
                "provider_configured": True,
                "used_external_results": bool(findings),
                "queries": queries,
                "findings": findings,
                "fallback_findings": fallback_findings,
                "status": "external_results_ready" if findings else "external_empty",
                "summary": "已把外部公開資料一起拉進來對照命理推演。",
            }
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            return {
                "pipeline_started": True,
                "required": True,
                "provider": provider,
                "provider_configured": True,
                "used_external_results": False,
                "queries": queries,
                "findings": [],
                "fallback_findings": fallback_findings,
                "status": "external_failed",
                "summary": "外部資料查詢未成功，這次先以命局、地氣與題目脈絡完成推演。",
            }

    return {
        "pipeline_started": True,
        "required": True,
        "provider": provider,
        "provider_configured": False,
        "used_external_results": False,
        "queries": queries,
        "findings": [],
        "fallback_findings": fallback_findings,
        "status": "provider_not_configured",
        "summary": "研究流程已啟動，但目前沒有可用的外部搜尋金鑰；這次先以命局、地氣與本地脈絡比對。",
    }
