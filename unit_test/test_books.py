import pytest
from fastapi.testclient import TestClient
from main import app
from api.auth_user.security import require_admin, get_current_user
from api.auth_user.models import TBL_AUTH_USER
import uuid

class MockAdminUser:
    id = uuid.uuid4()
    full_name = "Admin User"
    email = "admin@example.com"
    is_active = True
    is_admin = True # Assuming admin check

@pytest.fixture
def admin_client(client: TestClient):
    app.dependency_overrides[require_admin] = lambda: MockAdminUser()
    app.dependency_overrides[get_current_user] = lambda: MockAdminUser()
    yield client
    app.dependency_overrides.pop(require_admin, None)
    app.dependency_overrides.pop(get_current_user, None)

def test_get_books_empty(client: TestClient):
    response = client.get("/api/v1/books")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert len(data["data"]["books"]) == 0

def test_create_book(admin_client: TestClient):
    response = admin_client.post(
        "/api/v1/books",
        json={
            "title": "Test Book",
            "author": "John Doe",
            "description": "A great book",
            "price": 19.99,
            "cost_price": 10.00,
            "stock": 100,
            "isbn": "1234567890123"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["ok"] is True
    assert data["data"]["title"] == "Test Book"
    
def test_get_books_not_empty(admin_client: TestClient):
    # Create book
    admin_client.post(
        "/api/v1/books",
        json={
            "title": "Test Book 2",
            "author": "Jane Doe",
            "price": 15.99,
            "cost_price": 5.00,
            "stock": 50
        }
    )
    
    # List books
    response = admin_client.get("/api/v1/books")
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]["books"]) >= 1
