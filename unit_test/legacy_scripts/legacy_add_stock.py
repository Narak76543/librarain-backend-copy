from fastapi.testclient import TestClient
from main import app
from api.auth_user.security import require_admin
from core.db import Session
from api.books.models import TBL_BOOK

# Mock admin
class MockUser:
    id = "00000000-0000-0000-0000-000000000001"
    full_name = "Admin"

app.dependency_overrides[require_admin] = lambda: MockUser()

db = Session()
book = db.query(TBL_BOOK).first()
db.close()

if book:
    client = TestClient(app)
    payload = {
        "quantity": 10,
        "cost_price": 5.0,
        "sale_price": 10.0,
        "notes": "Testing the new stock in history feature!"
    }
    response = client.post(f"/api/v1/books/{book.id}/stock-in", json=payload)
    print("Stock In Response:", response.json())
else:
    print("No books found to test.")
