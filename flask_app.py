"""气象数据网站 v2 - SQLite存历史 + 图表API"""
import sys, os, json, sqlite3
sys.path.insert(0, os.path.dirname(__file__))
from flask import Flask, render_template, jsonify, request
from fetcher import fetch_all
from datetime import datetime, timedelta

app = Flask(__name__)
DB = os.path.join(os.path.dirname(__file__), "data", "weather.db")

def init_db():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    conn = sqlite3.connect(DB)
    conn.execute("""CREATE TABLE IF NOT EXISTS daily_18 (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT, city TEXT, time_period TEXT, temp INTEGER,
        weather TEXT, wind TEXT, fetched_at TEXT)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS daily_3 (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT, city TEXT, high_temp INTEGER, low_temp INTEGER,
        weather TEXT, wind TEXT, fetched_at TEXT)""")
    conn.commit(); conn.close()

def do_fetch():
    print(f"[{datetime.now()}] Fetching...")
    data = fetch_all()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    today = datetime.now().strftime("%Y-%m-%d")

    conn = sqlite3.connect(DB)
    # 删今日旧数据再插入
    conn.execute("DELETE FROM daily_18 WHERE date=?", (today,))
    conn.execute("DELETE FROM daily_3 WHERE date=?", (today,))

    for c in data.get("cities_18", []):
        for tp in ["今日11:00","今日16:00","今日19:00","明日04:00","明日11:00","明日16:00","明日晚峰19:00"]:
            v = c.get(tp)
            if v is not None:
                conn.execute("INSERT INTO daily_18 VALUES (NULL,?,?,?,?,?,?,?)",
                    (today, c["地市"], tp.replace("明日晚峰19:00","明日19:00"), int(v), "", "", now))

    for c in data.get("cities_3", []):
        conn.execute("INSERT INTO daily_3 VALUES (NULL,?,?,?,?,?,?,?)",
            (today, c["地市"], c.get("今日高温"), c.get("今日低温"), c.get("今日天气"), c.get("今日风力"), now))
        conn.execute("INSERT INTO daily_3 VALUES (NULL,?,?,?,?,?,?,?)",
            (today+"_明日", c["地市"], c.get("明日高温"), c.get("明日低温"), c.get("明日天气"), c.get("明日风力"), now))
    conn.commit(); conn.close()

    # Also save JSON for quick loading
    with open(os.path.join(os.path.dirname(__file__), "data", "latest.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data

init_db()
if not os.path.exists(os.path.join(os.path.dirname(__file__), "data", "latest.json")):
    do_fetch()

@app.route("/")
def dashboard():
    conn = sqlite3.connect(DB)
    today = datetime.now().strftime("%Y-%m-%d")
    # 18 cities today
    c18 = conn.execute("SELECT city,time_period,temp FROM daily_18 WHERE date=? ORDER BY city,time_period", (today,)).fetchall()
    c3 = conn.execute("SELECT * FROM daily_3 WHERE date=? OR date=?", (today, today+"_明日")).fetchall()
    dates = [r[0] for r in conn.execute("SELECT DISTINCT date FROM daily_18 ORDER BY date DESC LIMIT 30").fetchall()]
    conn.close()

    # Pivot 18 cities data
    cities_18 = {}
    for row in c18:
        city, tp, temp = row
        if city not in cities_18: cities_18[city] = {}
        cities_18[city][tp] = temp

    # Pivot 3 cities
    cities_3 = {}
    for row in c3:
        _, date, city, hi, lo, wx, wind, _ = row
        key = f"{city}_{date}"
        cities_3[key] = {"地市": city, "高温": hi, "低温": lo, "天气": wx, "风力": wind,
                         "日期": date.replace("_明日","")}

    return render_template("dashboard.html",
        cities_18=cities_18, cities_3=cities_3, dates=dates, today=today)

@app.route("/api/refresh")
def refresh():
    data = do_fetch()
    return jsonify({"status": "ok", "time": data["time"]})

@app.route("/api/history")
def history():
    date = request.args.get("date", datetime.now().strftime("%Y-%m-%d"))
    conn = sqlite3.connect(DB)
    c18 = conn.execute("SELECT city,time_period,temp FROM daily_18 WHERE date=? ORDER BY city", (date,)).fetchall()
    c3 = conn.execute("SELECT city,high_temp,low_temp,weather,wind FROM daily_3 WHERE date=? OR date=?", (date, date+"_明日")).fetchall()
    conn.close()

    result = {"date": date, "cities_18": {}, "cities_3": []}
    for row in c18:
        city, tp, temp = row
        if city not in result["cities_18"]: result["cities_18"][city] = {}
        result["cities_18"][city][tp] = temp
    for row in c3:
        result["cities_3"].append({"city": row[0], "high": row[1], "low": row[2], "weather": row[3], "wind": row[4]})
    return jsonify(result)

@app.route("/api/trend")
def trend():
    """3城市30天温度趋势"""
    conn = sqlite3.connect(DB)
    cities = ["郑州","洛阳","南阳"]
    result = {}
    for city in cities:
        rows = conn.execute("SELECT date,high_temp,low_temp FROM daily_3 WHERE city=? AND date NOT LIKE '%明日%' ORDER BY date LIMIT 30", (city,)).fetchall()
        result[city] = [{"date": r[0], "high": r[1], "low": r[2]} for r in rows]
    conn.close()
    return jsonify(result)

@app.route("/api/hourly")
def hourly():
    """3地市(郑州/信阳/安阳)今明两日9-24时逐小时温度"""
    import requests as req, time
    from datetime import timezone, timedelta
    API_KEY = "f838a587c0a64bb8b7ed7d314a1ab3ed"
    API_BASE = "https://nh4y3m9wcv.re.qweatherapi.com/v7/weather/72h"
    CITIES = [("郑州","101180101"),("信阳","101180601"),("安阳","101180201")]
    CST = timezone(timedelta(hours=8))
    HOURS = list(range(9, 25))
    result = {}

    for name, code in CITIES:
        try:
            r = req.get(f"{API_BASE}?location={code}&key={API_KEY}", timeout=10)
            if r.status_code != 200: continue
            d = r.json()
            hour_data = d.get("hourly", [])
            time_map = {}
            for h in hour_data:
                try: time_map[h.get("fxTime","")] = int(h.get("temp", 0))
                except: pass
            today = datetime.now(CST)
            city_data = {"today": [], "tomorrow": []}
            for offset, key in [(0,"today"),(1,"tomorrow")]:
                for hr in HOURS:
                    if hr == 24:
                        t = today + timedelta(days=offset+1, hours=0)
                    else:
                        t = today + timedelta(days=offset, hours=hr)
                    k = t.strftime("%Y-%m-%dT%H:00+08:00")
                    city_data[key].append(time_map.get(k))
            result[name] = city_data
            time.sleep(0.1)
        except: pass
    return jsonify({"labels": [f"{h}:00" for h in HOURS[:-1]]+["24:00"], "data": result})

@app.route("/debug")
def debug_fetch():
    data = fetch_all()
    return jsonify({"c18": len(data.get("cities_18",[])), "c3": len(data.get("cities_3",[]))})

@app.route("/health")
def health():
    return "OK"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
