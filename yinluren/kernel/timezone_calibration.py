"""
時區校正引擎 — 命理專用
==========================

為什麼需要：
- 命理起盤的「時辰」必須對應**當地真太陽時**，不是政治時區
- 中國大陸現在全國統一用「北京時間（UTC+8）」，但這是 1949 後的政治決定
- 命理學上，中國應該按民國時期的五時區劃分：
    長白時區 UTC+8.5（東北三省東部）
    中原時區 UTC+8  （華北、華東、華南、東南沿海）
    隴蜀時區 UTC+7  （甘肅、四川、雲南、貴州大部）
    新藏時區 UTC+6  （新疆東部、西藏東部）
    崑崙時區 UTC+5.5（新疆西部、帕米爾高原）
- 用戶在大陸時通常只知道自己的出生時間（北京時間），
  本模組會根據出生地省份/城市，自動換算回當地真時間

對其他地區（台灣、港澳、海外）：
- 直接用該地區的 IANA 時區（Asia/Taipei、Asia/Hong_Kong、America/Los_Angeles 等）
- 不做任何民國時區轉換
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # type: ignore


# ─────────────────────────────────────────────────────────────
# 民國五時區定義
# ─────────────────────────────────────────────────────────────

ROC_FIVE_ZONES = {
    "長白時區": {"utc_offset": 8.5, "central_meridian": 127.5},
    "中原時區": {"utc_offset": 8.0, "central_meridian": 120.0},
    "隴蜀時區": {"utc_offset": 7.0, "central_meridian": 105.0},
    "新藏時區": {"utc_offset": 6.0, "central_meridian": 90.0},
    "崑崙時區": {"utc_offset": 5.5, "central_meridian": 82.5},
}


# ─────────────────────────────────────────────────────────────
# 中國大陸省份 / 城市 → 民國時區 對照表
# 依據 1948 年《全國各地標準時間推行辦法》
# ─────────────────────────────────────────────────────────────

PROVINCE_TO_ROC_ZONE: Dict[str, str] = {
    # ===== 長白時區（UTC+8:30）=====
    # 東北三省東部 + 內蒙東部
    "黑龍江": "長白時區",
    "吉林": "長白時區",

    # ===== 中原時區（UTC+8:00）=====
    # 華北、華東、華中、華南、東南
    "遼寧": "中原時區",
    "河北": "中原時區",
    "北京": "中原時區",
    "天津": "中原時區",
    "山東": "中原時區",
    "江蘇": "中原時區",
    "上海": "中原時區",
    "浙江": "中原時區",
    "安徽": "中原時區",
    "江西": "中原時區",
    "福建": "中原時區",
    "河南": "中原時區",
    "湖北": "中原時區",
    "湖南": "中原時區",
    "廣東": "中原時區",
    "廣西": "中原時區",
    "海南": "中原時區",
    "山西": "中原時區",

    # ===== 隴蜀時區（UTC+7:00）=====
    # 西北、西南大部
    "陝西": "隴蜀時區",
    "甘肅": "隴蜀時區",
    "寧夏": "隴蜀時區",
    "四川": "隴蜀時區",
    "重慶": "隴蜀時區",
    "雲南": "隴蜀時區",
    "貴州": "隴蜀時區",
    "青海": "隴蜀時區",
    # 內蒙古橫跨長白/中原/隴蜀，以中部為準歸中原；極東/極西另處理
    "內蒙古": "中原時區",

    # ===== 新藏時區（UTC+6:00）=====
    # 西藏大部 + 新疆東部
    "西藏": "新藏時區",

    # ===== 崑崙時區（UTC+5:30）=====
    # 新疆橫跨新藏/崑崙，預設用新藏，城市級別另判
    "新疆": "新藏時區",
}

# 城市級別的細分（省份粗劃不夠時用這個覆蓋）
CITY_TO_ROC_ZONE: Dict[str, str] = {
    # 新疆西部 → 崑崙
    "喀什": "崑崙時區",
    "和田": "崑崙時區",
    "阿克蘇": "崑崙時區",
    "克孜勒蘇": "崑崙時區",
    # 新疆中部/東部 → 新藏
    "烏魯木齊": "新藏時區",
    "吐魯番": "新藏時區",
    "哈密": "新藏時區",
    # 內蒙古最東端 → 長白
    "呼倫貝爾": "長白時區",
    "滿洲里": "長白時區",
    # 內蒙古最西端 → 隴蜀
    "阿拉善": "隴蜀時區",
    # 黑龍江極東 → 仍長白但靠近東九區
    "佳木斯": "長白時區",
    "雞西": "長白時區",
    "牡丹江": "長白時區",
    "綏芬河": "長白時區",
}


# ─────────────────────────────────────────────────────────────
# 中國主要城市的經度（用來做真太陽時校正）
# 越精確越好，這裡列常見出生大城市
# ─────────────────────────────────────────────────────────────

CITY_LONGITUDES: Dict[str, float] = {
    # 長白時區
    "哈爾濱": 126.63, "長春": 125.32, "瀋陽": 123.43, "牡丹江": 129.60,
    "佳木斯": 130.36, "齊齊哈爾": 123.95, "大連": 121.62,
    # 中原時區
    "北京": 116.41, "天津": 117.20, "上海": 121.47, "南京": 118.78,
    "杭州": 120.15, "廣州": 113.26, "深圳": 114.06, "香港": 114.17,
    "澳門": 113.55, "武漢": 114.30, "長沙": 112.94, "合肥": 117.28,
    "福州": 119.30, "廈門": 118.09, "濟南": 117.02, "青島": 120.38,
    "鄭州": 113.63, "石家莊": 114.51, "太原": 112.55, "南昌": 115.89,
    "海口": 110.35, "南寧": 108.37, "貴陽": 106.71,
    # 隴蜀時區
    "成都": 104.07, "重慶": 106.55, "昆明": 102.83, "西安": 108.94,
    "蘭州": 103.82, "銀川": 106.23, "西寧": 101.78, "遵義": 106.91,
    # 新藏時區
    "烏魯木齊": 87.62, "拉薩": 91.14, "吐魯番": 89.18, "哈密": 93.51,
    # 崑崙時區
    "喀什": 75.99, "和田": 79.92, "阿克蘇": 80.27,
    # 台灣
    "台北": 121.56, "高雄": 120.31, "台中": 120.68, "台南": 120.21,
    "新竹": 120.97, "基隆": 121.74, "花蓮": 121.60, "台東": 121.15,
}


# ─────────────────────────────────────────────────────────────
# 核心函數
# ─────────────────────────────────────────────────────────────


def resolve_roc_zone(province: Optional[str], city: Optional[str]) -> str:
    """
    判斷中國大陸出生地屬於民國五時區的哪一區。
    優先順序：城市覆蓋 > 省份對照 > 預設中原時區
    """
    if city:
        city_clean = city.strip().replace("市", "").replace("縣", "")
        for known_city, zone in CITY_TO_ROC_ZONE.items():
            if known_city in city_clean:
                return zone

    if province:
        province_clean = province.strip().replace("省", "").replace("自治區", "").replace("市", "")
        for known_prov, zone in PROVINCE_TO_ROC_ZONE.items():
            if known_prov in province_clean:
                return zone

    return "中原時區"


def is_mainland_china(country: Optional[str]) -> bool:
    """判斷是否為中國大陸（不含港澳台）"""
    if not country:
        return False
    c = country.strip()
    mainland_markers = ["中國大陸", "中国大陆", "中國", "中国", "大陸", "大陆", "China", "CN", "PRC"]
    exclude = ["台灣", "台湾", "臺灣", "Taiwan", "TW", "香港", "Hong Kong", "HK", "澳門", "澳门", "Macau", "Macao", "MO"]
    if any(e in c for e in exclude):
        return False
    return any(m in c for m in mainland_markers)


def city_longitude(city: Optional[str], zone_name: str) -> float:
    """取得城市經度；找不到就返回該時區中央子午線"""
    if city:
        city_clean = city.strip().replace("市", "").replace("縣", "")
        for known_city, lon in CITY_LONGITUDES.items():
            if known_city in city_clean:
                return lon
    return ROC_FIVE_ZONES.get(zone_name, ROC_FIVE_ZONES["中原時區"])["central_meridian"]


def correct_mainland_china_time(
    birth_datetime_beijing: datetime,
    province: Optional[str],
    city: Optional[str],
) -> Dict[str, Any]:
    """
    把用戶填寫的「北京時間」換算成民國時區的真太陽時校正時間（命理用）。

    輸入：birth_datetime_beijing — 天真的 datetime（用戶以為是當地時間實則是北京時間）
    輸出：包含五時區歸屬、校正後時間、校正量的 dict

    步驟：
    1. 判斷屬哪個民國時區
    2. 北京時間 → 該民國時區的區時
    3. 再做經度真太陽時校正（每 1° = 4 分鐘）
    """
    zone_name = resolve_roc_zone(province, city)
    zone_info = ROC_FIVE_ZONES[zone_name]

    # Step 1: 北京時間（UTC+8）換算到民國區時
    beijing_offset = 8.0
    roc_offset = zone_info["utc_offset"]
    offset_hours = roc_offset - beijing_offset  # 負值：往西調
    zone_adjusted = birth_datetime_beijing + timedelta(hours=offset_hours)

    # Step 2: 真太陽時校正（經度校正）
    lon = city_longitude(city, zone_name)
    central = zone_info["central_meridian"]
    longitude_diff = lon - central  # 正值：該地比中央子午線更東
    solar_minutes = longitude_diff * 4  # 經度差每 1° = 4 分鐘
    true_solar_time = zone_adjusted + timedelta(minutes=solar_minutes)

    return {
        "is_mainland": True,
        "roc_zone_name": zone_name,
        "roc_utc_offset": roc_offset,
        "central_meridian": central,
        "city_longitude": lon,
        "longitude_diff_degrees": round(longitude_diff, 3),
        "input_beijing_time": birth_datetime_beijing.isoformat(),
        "zone_adjusted_time": zone_adjusted.isoformat(),
        "true_solar_time": true_solar_time.isoformat(),
        "total_correction_minutes": round(offset_hours * 60 + solar_minutes, 2),
        "note": f"以北京時間為輸入，校正為{zone_name}（UTC+{roc_offset}）並按經度{lon}°做真太陽時校正",
    }


def correct_non_mainland_time(
    birth_datetime: datetime,
    country: Optional[str],
    iana_timezone: Optional[str] = None,
) -> Dict[str, Any]:
    """
    非大陸地區：直接信任用戶的當地時間，記錄其時區。
    不做民國時區校正（因為他們的標準時間就是當地時間）。
    """
    tz_str = iana_timezone or _guess_iana_timezone(country)
    try:
        tz = ZoneInfo(tz_str)
        aware = birth_datetime.replace(tzinfo=tz) if birth_datetime.tzinfo is None else birth_datetime.astimezone(tz)
        utc_offset = aware.utcoffset()
        offset_hours = utc_offset.total_seconds() / 3600 if utc_offset else 0
    except Exception:
        tz_str = "Asia/Taipei"
        offset_hours = 8

    return {
        "is_mainland": False,
        "roc_zone_name": None,
        "iana_timezone": tz_str,
        "utc_offset": offset_hours,
        "input_local_time": birth_datetime.isoformat(),
        "true_solar_time": birth_datetime.isoformat(),
        "note": f"用戶填寫的即為當地標準時間（{tz_str}, UTC{offset_hours:+g}）",
    }


def _guess_iana_timezone(country: Optional[str]) -> str:
    """由國家字串粗略猜 IANA 時區"""
    if not country:
        return "Asia/Taipei"
    c = country.lower()
    mapping = {
        "台灣": "Asia/Taipei", "臺灣": "Asia/Taipei", "taiwan": "Asia/Taipei",
        "香港": "Asia/Hong_Kong", "hong kong": "Asia/Hong_Kong", "hk": "Asia/Hong_Kong",
        "澳門": "Asia/Macau", "澳门": "Asia/Macau", "macau": "Asia/Macau", "macao": "Asia/Macau",
        "日本": "Asia/Tokyo", "japan": "Asia/Tokyo",
        "韓國": "Asia/Seoul", "korea": "Asia/Seoul",
        "新加坡": "Asia/Singapore", "singapore": "Asia/Singapore",
        "馬來西亞": "Asia/Kuala_Lumpur", "malaysia": "Asia/Kuala_Lumpur",
        "泰國": "Asia/Bangkok", "thailand": "Asia/Bangkok",
        "越南": "Asia/Ho_Chi_Minh", "vietnam": "Asia/Ho_Chi_Minh",
        "印尼": "Asia/Jakarta", "indonesia": "Asia/Jakarta",
        "菲律賓": "Asia/Manila", "philippines": "Asia/Manila",
        "印度": "Asia/Kolkata", "india": "Asia/Kolkata",
        "英國": "Europe/London", "uk": "Europe/London", "united kingdom": "Europe/London",
        "法國": "Europe/Paris", "france": "Europe/Paris",
        "德國": "Europe/Berlin", "germany": "Europe/Berlin",
        "美國": "America/New_York", "usa": "America/New_York", "us": "America/New_York",
        "加拿大": "America/Toronto", "canada": "America/Toronto",
        "澳洲": "Australia/Sydney", "australia": "Australia/Sydney",
        "紐西蘭": "Pacific/Auckland", "new zealand": "Pacific/Auckland",
    }
    for key, val in mapping.items():
        if key.lower() in c:
            return val
    return "Asia/Taipei"


def calibrate_birth_time(
    birth_date: str,
    birth_hour: int,
    birth_minute: int,
    country: Optional[str] = None,
    province: Optional[str] = None,
    city: Optional[str] = None,
    iana_timezone_hint: Optional[str] = None,
) -> Dict[str, Any]:
    """
    對外主入口：不論何地出生，都回傳完整的時區校正資訊。

    大陸用戶：輸入的是北京時間 → 自動換算民國時區真太陽時
    其他地區：輸入的是當地時間 → 記錄 IANA 時區即可
    """
    try:
        y, m, d = map(int, birth_date.split("-"))
        dt = datetime(y, m, d, birth_hour, birth_minute)
    except Exception as exc:
        return {"error": f"無法解析出生日期/時間：{exc}", "calibrated": False}

    if is_mainland_china(country):
        result = correct_mainland_china_time(dt, province, city)
    else:
        result = correct_non_mainland_time(dt, country, iana_timezone_hint)

    result["calibrated"] = True
    result["birth_input"] = {
        "date": birth_date,
        "hour": birth_hour,
        "minute": birth_minute,
        "country": country,
        "province": province,
        "city": city,
    }
    return result


# ─────────────────────────────────────────────────────────────
# 單元自測（可直接 python 這個檔案跑）
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import json

    tests = [
        {"date": "1990-06-15", "hour": 14, "minute": 30, "country": "中國", "province": "北京", "city": "北京"},
        {"date": "1990-06-15", "hour": 14, "minute": 30, "country": "中國", "province": "新疆", "city": "烏魯木齊"},
        {"date": "1990-06-15", "hour": 14, "minute": 30, "country": "中國", "province": "新疆", "city": "喀什"},
        {"date": "1990-06-15", "hour": 14, "minute": 30, "country": "中國", "province": "黑龍江", "city": "哈爾濱"},
        {"date": "1990-06-15", "hour": 14, "minute": 30, "country": "中國", "province": "四川", "city": "成都"},
        {"date": "1990-06-15", "hour": 14, "minute": 30, "country": "台灣", "province": "台北", "city": "台北"},
        {"date": "1990-06-15", "hour": 14, "minute": 30, "country": "香港", "province": None, "city": "香港"},
        {"date": "1990-06-15", "hour": 14, "minute": 30, "country": "日本", "province": None, "city": "東京"},
        {"date": "1990-06-15", "hour": 14, "minute": 30, "country": "美國", "province": "California", "city": "Los Angeles", "iana_timezone_hint": "America/Los_Angeles"},
    ]

    for t in tests:
        print("=" * 60)
        print(f"輸入：{t}")
        out = calibrate_birth_time(
            birth_date=t["date"],
            birth_hour=t["hour"],
            birth_minute=t["minute"],
            country=t.get("country"),
            province=t.get("province"),
            city=t.get("city"),
            iana_timezone_hint=t.get("iana_timezone_hint"),
        )
        print(json.dumps(out, ensure_ascii=False, indent=2))
