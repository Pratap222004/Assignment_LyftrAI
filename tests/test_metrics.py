import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Test client fixture"""
    return TestClient(app)


def test_metrics_endpoint(client):
    """Test Prometheus metrics endpoint"""
    response = client.get("/metrics")
    
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"] or "text/plain; version=0.0.4" in response.headers["content-type"]
    
    content = response.text
    # Check for Prometheus-style metrics
    assert "http_requests_total" in content or "# HELP" in content

