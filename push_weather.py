"""本地天气推送到PythonAnywhere"""
import requests, json
from fetcher import fetch_all

URL = "https://cqkinteresting.pythonanywhere.com/api/push"
SECRET = "henan2026"

data = fetch_all()
data["secret"] = SECRET
print(f"Pushing {len(data.get('cities_18',[]))} cities...")
r = requests.post(URL, json=data, timeout=30)
print(f"Response: {r.status_code} {r.text}")
