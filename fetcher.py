"""天气数据采集模块: 18地市 + 3地市对比"""
import requests, json, time
from datetime import datetime

API_KEY = "f838a587c0a64bb8b7ed7d314a1ab3ed"
API_BASE = "https://nh4y3m9wcv.re.qweatherapi.com/v7/weather/72h"

CITIES_18 = [
    ("郑州","101180101"),("开封","101180801"),("洛阳","101180901"),
    ("平顶山","101180501"),("安阳","101180201"),("鹤壁","101181201"),
    ("新乡","101180301"),("焦作","101181101"),("濮阳","101181301"),
    ("许昌","101180401"),("漯河","101181501"),("三门峡","101181701"),
    ("南阳","101180701"),("商丘","101181001"),("信阳","101180601"),
    ("周口","101181401"),("驻马店","101181601"),("济源","101181801"),
]
CITIES_3 = [c for c in CITIES_18 if c[0] in ("郑州","洛阳","南阳")]  # 标杆城市对比

TARGET_HOURS = [4, 11, 16, 19]
HEADERS = {"User-Agent": "Mozilla/5.0"}

def fetch_18_cities():
    """爬取18地市72h预报，提取7个时刻"""
    results = []
    for name, code in CITIES_18:
        try:
            url = f"{API_BASE}?location={code}&key={API_KEY}"
            r = requests.get(url, headers=HEADERS, timeout=10)
            if r.status_code != 200: continue
            d = r.json()
            hours = d.get("hourly", [])
            today_tp = {"11:00": None, "16:00": None, "19:00": None}
            tmr_tp = {"04:00": None, "11:00": None, "16:00": None, "19:00": None}
            now = datetime.now()
            today_str = now.strftime("%Y-%m-%d")
            tmr_str = (now.replace(hour=0,minute=0,second=0) + __import__('datetime').timedelta(days=1)).strftime("%Y-%m-%d")

            for h in hours:
                ft = h.get("fxTime","")
                temp = h.get("temp")
                if not ft or temp is None: continue
                time_part = ft[11:16]
                date_part = ft[:10]
                if date_part == today_str and time_part in today_tp:
                    today_tp[time_part] = temp
                elif date_part == tmr_str and time_part in tmr_tp:
                    tmr_tp[time_part] = temp

            results.append({
                "地市": name, "日期": today_str,
                "今日11:00": int(today_tp["11:00"]) if today_tp["11:00"] else None,
                "今日16:00": int(today_tp["16:00"]) if today_tp["16:00"] else None,
                "今日19:00": int(today_tp["19:00"]) if today_tp["19:00"] else None,
                "明日04:00": int(tmr_tp["04:00"]) if tmr_tp["04:00"] else None,
                "明日11:00": int(tmr_tp["11:00"]) if tmr_tp["11:00"] else None,
                "明日16:00": int(tmr_tp["16:00"]) if tmr_tp["16:00"] else None,
                "明日晚峰19:00": int(tmr_tp["19:00"]) if tmr_tp["19:00"] else None,
            })
            time.sleep(0.1)
        except: pass
    return results

def fetch_3_city_compare():
    """3地市对比：使用7d预报API获取每日高低温/天气/风力"""
    results = []
    for name, code in CITIES_3:
        try:
            url = f"https://nh4y3m9wcv.re.qweatherapi.com/v7/weather/7d?location={code}&key={API_KEY}"
            r = requests.get(url, headers=HEADERS, timeout=10)
            if r.status_code != 200: continue
            d = r.json()
            daily = d.get("daily", [])
            if len(daily) >= 2:
                today = daily[0]; tmr = daily[1]
                results.append({
                    "地市": name,
                    "今日高温": today.get("tempMax"), "今日低温": today.get("tempMin"),
                    "今日天气": today.get("textDay"), "今日风力": today.get("windScaleDay"),
                    "明日高温": tmr.get("tempMax"), "明日低温": tmr.get("tempMin"),
                    "明日天气": tmr.get("textDay"), "明日风力": tmr.get("windScaleDay"),
                })
            time.sleep(0.1)
        except: pass
    return results

def fetch_all():
    return {"time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "cities_18": fetch_18_cities(),
            "cities_3": fetch_3_city_compare()}
