import os
import hmac
import hashlib
import logging
from fastapi import Request, HTTPException, status

logger = logging.getLogger(__name__)


def get_webhook_secret() -> str:
    """Get webhook secret from environment"""
    secret = os.getenv("WEBHOOK_SECRET")
    if not secret:
        raise ValueError("WEBHOOK_SECRET environment variable not set")
    return secret


async def validate_hmac_signature(request: Request) -> bytes:
    """
    Validate HMAC-SHA256 signature using raw request body.
    Returns the raw body bytes.
    """
    signature_header = request.headers.get("X-Signature")
    if not signature_header:
        logger.warning("Missing X-Signature header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Signature header"
        )
    
    # Get raw body
    body = await request.body()
    
    # Get secret
    try:
        secret = get_webhook_secret()
    except ValueError as e:
        logger.error(f"Webhook secret not configured: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook secret not configured"
        )
    
    # Compute expected signature
    expected_signature = hmac.new(
        secret.encode("utf-8"),
        body,
        hashlib.sha256
    ).hexdigest()
    
    # Compare signatures (constant-time comparison)
    if not hmac.compare_digest(signature_header, expected_signature):
        logger.warning(f"Invalid HMAC signature. Expected: {expected_signature[:16]}..., Got: {signature_header[:16]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature"
        )
    
    logger.debug("HMAC signature validated successfully")
    return body

