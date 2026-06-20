from fastapi.testclient import TestClient
from main import app
from api.auth_user.security import require_admin

# Mock require_admin
class MockUser:
    id = "123"
    full_name = "Admin"

app.dependency_overrides[require_admin] = lambda: MockUser()

client = TestClient(app)
response = client.get("/api/v1/admin/reports/stock-in")
print(response.status_code)
print(response.json())
