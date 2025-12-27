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
def webhook_payload():
    """Sample webhook payload"""
    return {
        "message_id": "msg_123",
        "timestamp": "2024-01-01T00:00:00Z",
        "source": "test_source",
        "raw_data": {"key": "value"}
    }


def test_webhook_success(client, webhook_payload):
    """Test successful webhook submission"""
    body = json.dumps(webhook_payload).encode("utf-8")
    signature = compute_signature(body, os.getenv("WEBHOOK_SECRET"))
    
    response = client.post(
        "/webhook",
        content=body,
        headers={"X-Signature": signature, "Content-Type": "application/json"}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["message"] == "Webhook received"
    assert data["message_id"] == "msg_123"
    assert data["duplicate"] is False


def test_webhook_idempotency(client, webhook_payload):
    """Test webhook idempotency - same message_id should be ignored"""
    body = json.dumps(webhook_payload).encode("utf-8")
    signature = compute_signature(body, os.getenv("WEBHOOK_SECRET"))
    
    # First request
    response1 = client.post(
        "/webhook",
        content=body,
        headers={"X-Signature": signature, "Content-Type": "application/json"}
    )
    assert response1.status_code == 201
    assert response1.json()["duplicate"] is False
    
    # Second request with same message_id
    response2 = client.post(
        "/webhook",
        content=body,
        headers={"X-Signature": signature, "Content-Type": "application/json"}
    )
    assert response2.status_code == 201
    assert response2.json()["duplicate"] is True


def test_webhook_invalid_signature(client, webhook_payload):
    """Test webhook with invalid signature"""
    body = json.dumps(webhook_payload).encode("utf-8")
    
    response = client.post(
        "/webhook",
        content=body,
        headers={"X-Signature": "invalid_signature", "Content-Type": "application/json"}
    )
    
    assert response.status_code == 401
    assert "Invalid signature" in response.json()["detail"] or "Missing X-Signature" in response.json()["detail"]


def test_webhook_missing_signature(client, webhook_payload):
    """Test webhook without signature header"""
    body = json.dumps(webhook_payload).encode("utf-8")
    
    response = client.post(
        "/webhook",
        content=body,
        headers={"Content-Type": "application/json"}
    )
    
    assert response.status_code == 401


def test_webhook_invalid_json(client):
    """Test webhook with invalid JSON"""
    body = b"invalid json"
    signature = compute_signature(body, os.getenv("WEBHOOK_SECRET"))
    
    response = client.post(
        "/webhook",
        content=body,
        headers={"X-Signature": signature, "Content-Type": "application/json"}
    )
    
    assert response.status_code == 400

