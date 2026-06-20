import pytest
from fastapi.testclient import TestClient
from main import app
from api.auth_user.security import get_current_user
import uuid

class MockUser:
    id = uuid.uuid4()
    full_name = "Normal User"
    email = "user@example.com"

@pytest.fixture
def auth_client(client: TestClient):
    app.dependency_overrides[get_current_user] = lambda: MockUser()
    yield client
    app.dependency_overrides.pop(get_current_user, None)

def test_get_cart_empty(auth_client: TestClient):
    response = auth_client.get("/api/v1/cart")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert len(data["data"]["items"]) == 0

def test_add_to_cart_invalid_book(auth_client: TestClient):
    response = auth_client.post(
        "/api/v1/cart/items",
        json={
            "book_id": str(uuid.uuid4()), # Non-existent book
            "quantity": 1
        }
    )
    # Should return 404 because book doesn't exist
    assert response.status_code == 404
