import pytest
import os
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Test client fixture"""
    return TestClient(app)


def test_health_live(client):
    """Test liveness endpoint - should always return 200"""
    response = client.get("/health/live")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"


def test_health_ready_with_secret(client):
    """Test readiness endpoint with WEBHOOK_SECRET set"""
    os.environ["WEBHOOK_SECRET"] = "test_secret"
    
    response = client.get("/health/ready")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"


def test_health_ready_without_secret(client):
    """Test readiness endpoint without WEBHOOK_SECRET"""
    if "WEBHOOK_SECRET" in os.environ:
        del os.environ["WEBHOOK_SECRET"]
    
    response = client.get("/health/ready")
    
    assert response.status_code == 503

