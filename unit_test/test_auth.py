import pytest
from fastapi.testclient import TestClient

def test_register_user(client: TestClient):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Test User",
            "email": "test@example.com",
            "password": "password123",
            "phone": "1234567890"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["ok"] is True
    assert data["data"]["email"] == "test@example.com"

def test_register_duplicate_user(client: TestClient):
    user_data = {
        "full_name": "Test User",
        "email": "duplicate@example.com",
        "password": "password123",
    }
    client.post("/api/v1/auth/register", json=user_data)
    
    # Try again
    response = client.post("/api/v1/auth/register", json=user_data)
    assert response.status_code == 400
    assert response.json()["ok"] is False

def test_login_user(client: TestClient):
    client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Test User 2",
            "email": "test2@example.com",
            "password": "password123",
            "phone": "1234567890"
        }
    )
    
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "test2@example.com",
            "password": "password123"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert "accessToken" in data["data"]
    assert "refreshToken" in data["data"]

def test_login_invalid_password(client: TestClient):
    client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Test User 3",
            "email": "test3@example.com",
            "password": "password123",
        }
    )
    
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "test3@example.com",
            "password": "wrongpassword"
        }
    )
    assert response.status_code == 401
    assert response.json()["ok"] is False
