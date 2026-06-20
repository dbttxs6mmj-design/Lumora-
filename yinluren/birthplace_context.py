from __future__ import annotations

import hashlib
import re
from typing import Any, Dict


_WHITESPACE_RE = re.compile(r"\s+")

COUNTRY_CANONICAL_ALIASES = {
    "taiwan": "Taiwan",
    "taiwan, province of china": "Taiwan",
    "台灣": "Taiwan",
    "臺灣": "Taiwan",
    "tw": "Taiwan",
    "hong kong": "Hong Kong",
    "香港": "Hong Kong",
    "hk": "Hong Kong",
    "macau": "Macau",
    "macao": "Macau",
    "澳門": "Macau",
    "mo": "Macau",
    "china": "China",
    "中國": "China",
    "cn": "China",
    "japan": "Japan",
    "日本": "Japan",
    "jp": "Japan",
    "united states": "United States",
    "united states of america": "United States",
    "usa": "United States",
    "us": "United States",
    "美國": "United States",
}

PROVINCE_CANONICAL_ALIASES = {
    "台北": "Taipei",
    "台北市": "Taipei",
    "臺北": "Taipei",
    "臺北市": "Taipei",
    "taipei": "Taipei",
    "新北": "New Taipei",
    "新北市": "New Taipei",
    "new taipei": "New Taipei",
    "香港": "Hong Kong",
    "hong kong": "Hong Kong",
    "tokyo": "Tokyo",
    "東京": "Tokyo",
    "california": "California",
    "ca": "California",
}

CITY_CANONICAL_ALIASES = {
    "台北": "Taipei",
    "台北市": "Taipei",
    "臺北": "Taipei",
    "臺北市": "Taipei",
    "taipei": "Taipei",
    "hong kong": "Hong Kong",
    "香港": "Hong Kong",
    "tokyo": "Tokyo",
    "東京": "Tokyo",
    "san francisco": "San Francisco",
    "sf": "San Francisco",
}

REGION_GROUPS = {
    "Taiwan": "east_asia",
    "Hong Kong": "east_asia",
    "Macau": "east_asia",
    "China": "east_asia",
    "Japan": "east_asia",
    "United States": "north_america",
}

CLIMATE_GROUPS = {
    "Taipei": "humid_subtropical",
    "New Taipei": "humid_subtropical",
    "Hong Kong": "humid_subtropical",
    "Tokyo": "temperate_monsoon",
    "California": "mediterranean",
    "San Francisco": "mediterranean",
}

ELEMENT_GROUPS = {
    "east_asia": "wood",
    "north_america": "metal",
}

DIRECTION_GROUPS = {
    "Taiwan": "east",
    "Hong Kong": "south",
    "Macau": "south",
    "China": "central",
    "Japan": "east",
    "United States": "west",
}


def _clean(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return _WHITESPACE_RE.sub(" ", text)


def _canonicalize(value: Any, aliases: Dict[str, str]) -> str:
    cleaned = _clean(value)
    if not cleaned:
        return ""
    lowered = cleaned.lower()
    return aliases.get(lowered, cleaned)


def canonicalize_birthplace(country: Any, province: Any, city: Any) -> Dict[str, str]:
    canonical_country = _canonicalize(country, COUNTRY_CANONICAL_ALIASES)
    canonical_province = _canonicalize(province, PROVINCE_CANONICAL_ALIASES)
    canonical_city = _canonicalize(city, CITY_CANONICAL_ALIASES)
    region_group = REGION_GROUPS.get(canonical_country, "global")
    direction = DIRECTION_GROUPS.get(canonical_country, "center")
    climate = (
        CLIMATE_GROUPS.get(canonical_city)
        or CLIMATE_GROUPS.get(canonical_province)
        or "temperate"
    )
    element = ELEMENT_GROUPS.get(region_group, "earth")

    return {
        "country": canonical_country,
        "province": canonical_province,
        "city": canonical_city,
        "region_group": region_group,
        "direction": direction,
        "climate": climate,
        "element": element,
    }


def build_birthplace_factor(country: Any, province: Any, city: Any) -> Dict[str, Any]:
    canonical = canonicalize_birthplace(country, province, city)
    normalized_lineage = " / ".join(
        part for part in (canonical["country"], canonical["province"], canonical["city"]) if part
    )
    signature = hashlib.sha256(normalized_lineage.encode("utf-8")).hexdigest()[:12] if normalized_lineage else "unknown"
    resonance_bias = (int(signature[:2], 16) / 255.0) if signature != "unknown" else 0.0
    weighting_bias = round((resonance_bias - 0.5) * 0.12, 4)

    return {
        "used": bool(normalized_lineage),
        "signature": signature,
        "normalized": canonical,
        "lineage": normalized_lineage,
        "qi_profile": {
            "region_group": canonical["region_group"],
            "direction": canonical["direction"],
            "climate": canonical["climate"],
            "element": canonical["element"],
            "resonance_bias": round(resonance_bias, 4),
            "weighting_bias": weighting_bias,
        },
    }
