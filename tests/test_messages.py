import pytest
import json
import hmac
import hashlib
import os
from fastapi.testclient import TestClient
from app.main import app

# Set test webhook secret
os.environ["WEBHOOK_SECRET"] = "test_secret_key_12345"


def compute_signature(body: bytes, secret: str) -> str:
    """Compute HMAC-SHA256 signature"""
    return hmac.new(
        secret.encode("utf-8"),
        body,
        hashlib.sha256
    ).hexdigest()


@pytest.fixture
def client():
    """Test client fixture"""
    return TestClient(app)


@pytest.fixture
def sample_messages(client):
    """Create sample messages for testing"""
    messages = [
        {
            "message_id": f"msg_{i}",
            "timestamp": f"2024-01-0{i+1}T00:00:00Z",
            "source": "source_a" if i % 2 == 0 else "source_b",
            "raw_data": {"index": i}
        }
        for i in range(5)
    ]
    
    secret = os.getenv("WEBHOOK_SECRET")
    for msg in messages:
        body = json.dumps(msg).encode("utf-8")
        signature = compute_signature(body, secret)
        client.post(
            "/webhook",
            content=body,
            headers={"X-Signature": signature, "Content-Type": "application/json"}
        )
    
    return messages


def test_get_messages_default(client, sample_messages):
    """Test getting messages with default pagination"""
    response = client.get("/messages")
    
    assert response.status_code == 200
    data = response.json()
    assert "messages" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert "total_pages" in data
    assert len(data["messages"]) <= 10
    assert data["page"] == 1
    assert data["page_size"] == 10


def test_get_messages_pagination(client, sample_messages):
    """Test pagination"""
    response = client.get("/messages?page=1&page_size=2")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["messages"]) == 2
    assert data["page"] == 1
    assert data["page_size"] == 2


def test_get_messages_filter_by_source(client, sample_messages):
    """Test filtering by source"""
    response = client.get("/messages?source=source_a")
    
    assert response.status_code == 200
    data = response.json()
    assert all(msg["source"] == "source_a" for msg in data["messages"])


def test_get_messages_filter_by_date(client, sample_messages):
    """Test filtering by date range"""
    response = client.get("/messages?start_date=2024-01-02T00:00:00Z&end_date=2024-01-04T00:00:00Z")
    
    assert response.status_code == 200
    data = response.json()
    # All messages should be within the date range
    for msg in data["messages"]:
        assert "2024-01-02" <= msg["timestamp"] <= "2024-01-04"

