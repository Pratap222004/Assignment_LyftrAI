import os
import hmac
import hashlib
import logging
from fastapi import Request, HTTPException, status

logger = logging.getLogger(__name__)


async def validate_hmac_signature(request: Request) -> bytes:
    signature_header = request.headers.get("X-Signature")
    if not signature_header:
        logger.warning("Missing X-Signature header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Signature"
        )

    body = await request.body()

    secret = os.getenv("WEBHOOK_SECRET")
    if not secret:
        logger.warning("WEBHOOK_SECRET not set")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature"
        )

    expected_signature = hmac.new(
        secret.encode("utf-8"),
        body,
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(signature_header, expected_signature):
        logger.warning("Invalid HMAC signature")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature"
        )

    return body
