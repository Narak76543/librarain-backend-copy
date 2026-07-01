import requests
try:
    print("Pinging...")
    r = requests.get("http://localhost:8000/docs", timeout=3)
    print("Status:", r.status_code)
except Exception as e:
    print("Error:", e)
