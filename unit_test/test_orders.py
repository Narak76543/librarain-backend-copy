import pytest
from fastapi.testclient import TestClient
from main import app
from api.auth_user.security import get_current_user
import uuid

class MockUser:
    id = uuid.uuid4()
    full_name = "Order User"
    email = "order@example.com"

@pytest.fixture
def auth_client(client: TestClient):
    app.dependency_overrides[get_current_user] = lambda: MockUser()
    yield client
    app.dependency_overrides.pop(get_current_user, None)

def test_get_orders_empty(auth_client: TestClient):
    response = auth_client.get("/api/v1/orders")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert len(data["data"]["orders"]) == 0

def test_create_order_empty_cart(auth_client: TestClient):
    # Try to place order without any items in cart
    response = auth_client.post(
        "/api/v1/orders",
        json={
            "delivery_way": "Pick Up",
            "payment_method": "COD"
        }
    )
    # Should fail because cart is empty
    assert response.status_code == 400
    assert response.json()["ok"] is False
