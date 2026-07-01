import requests

BASE_URL = "http://127.0.0.1:8000"

def test_system_logs():
    print("1. Attempting login as admin...")
    login_data = {
        "email": "admin@example.com",
        "password": "password123"
    }
    # It might be an OAuth2 form or JSON
    # Let's try form data (standard FastAPI OAuth2PasswordRequestForm)
    r = requests.post(f"{BASE_URL}/api/v1/auth/login", json=login_data)
    
    if r.status_code != 200:
        print(f"Login failed: {r.status_code}")
        print(r.text)
        return
    
    print("Login successful.")
    data = r.json()
    print("Login response data:", data)
    token = data.get("data", {}).get("accessToken")
    if not token:
        token = data.get("access_token")
        
    print("2. Fetching system logs...")
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(f"{BASE_URL}/api/v1/admin/logs?limit=5", headers=headers)
    
    if r.status_code != 200:
        print(f"Fetch logs failed: {r.status_code}")
        print(r.text)
        return
        
    logs = r.json()
    print("\n--- System Logs ---")
    if isinstance(logs, dict) and "data" in logs:
        log_list = logs["data"].get("logs", [])
    else:
        log_list = logs
        
    for log in log_list:
        if isinstance(log, dict):
            print(f"[{log.get('created_at')}] {log.get('module')} - {log.get('action')}: {log.get('description')}")
        else:
            print(log)

if __name__ == "__main__":
    test_system_logs()
