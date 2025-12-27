import os
import json
import logging
from typing import Optional
from fastapi import APIRouter, Request, HTTPException, status, Query
from fastapi.responses import JSONResponse

from app.models import WebhookPayload, MessageResponse, MessageListResponse, HealthResponse
from app.storage import insert_message, get_messages, check_db_ready
from app.hmac_validation import validate_hmac_signature
from app.metrics import http_requests_total, http_request_duration_seconds, webhook_messages_total, messages_in_db
import time

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/webhook", status_code=status.HTTP_201_CREATED)
async def webhook(request: Request):
    """
    Receive webhook with HMAC-SHA256 validation and idempotent processing.
    """
    start_time = time.time()
    
    try:
        # Validate HMAC signature and get raw body
        body_bytes = await validate_hmac_signature(request)
        
        # Parse JSON payload
        try:
            payload = json.loads(body_bytes.decode("utf-8"))
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON payload: {e}")
            webhook_messages_total.labels(source="unknown", status="error").inc()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON payload"
            )
        
        # Validate payload structure
        try:
            webhook_payload = WebhookPayload(**payload)
        except Exception as e:
            logger.error(f"Invalid payload structure: {e}")
            webhook_messages_total.labels(source=payload.get("source", "unknown"), status="error").inc()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid payload structure: {str(e)}"
            )
        
        # Insert message (idempotent)
        inserted = insert_message(
            message_id=webhook_payload.message_id,
            timestamp=webhook_payload.timestamp,
            source=webhook_payload.source,
            raw_data=webhook_payload.raw_data
        )
        
        if inserted:
            logger.info(f"New message stored: {webhook_payload.message_id}")
            webhook_messages_total.labels(source=webhook_payload.source, status="success").inc()
            messages_in_db.inc()
        else:
            logger.info(f"Duplicate message ignored (idempotent): {webhook_payload.message_id}")
            webhook_messages_total.labels(source=webhook_payload.source, status="duplicate").inc()
        
        duration = time.time() - start_time
        http_request_duration_seconds.labels(method="POST", endpoint="/webhook").observe(duration)
        http_requests_total.labels(method="POST", endpoint="/webhook", status="201").inc()
        
        return {
            "message": "Webhook received",
            "message_id": webhook_payload.message_id,
            "duplicate": not inserted
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in webhook: {e}", exc_info=True)
        duration = time.time() - start_time
        http_request_duration_seconds.labels(method="POST", endpoint="/webhook").observe(duration)
        http_requests_total.labels(method="POST", endpoint="/webhook", status="500").inc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/messages", response_model=MessageListResponse)
async def get_messages_endpoint(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Page size"),
    source: Optional[str] = Query(None, description="Filter by source"),
    start_date: Optional[str] = Query(None, description="Filter by start date (ISO 8601)"),
    end_date: Optional[str] = Query(None, description="Filter by end date (ISO 8601)")
):
    """
    Get paginated messages with optional filtering.
    """
    start_time = time.time()
    
    try:
        messages, total = get_messages(
            page=page,
            page_size=page_size,
            source=source,
            start_date=start_date,
            end_date=end_date
        )
        
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        
        for msg in messages:
            if "timestamp" in msg and isinstance(msg["timestamp"], str):
                msg["timestamp"] = msg["timestamp"][:10]

        message_responses = [
            MessageResponse(**msg) for msg in messages
        ]
        
        duration = time.time() - start_time
        http_request_duration_seconds.labels(method="GET", endpoint="/messages").observe(duration)
        http_requests_total.labels(method="GET", endpoint="/messages", status="200").inc()

        
            
        return MessageListResponse(
            messages=message_responses,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
        
    except Exception as e:
        logger.error(f"Error fetching messages: {e}", exc_info=True)
        duration = time.time() - start_time
        http_request_duration_seconds.labels(method="GET", endpoint="/messages").observe(duration)
        http_requests_total.labels(method="GET", endpoint="/messages", status="500").inc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/health/live", response_model=HealthResponse)
async def health_live():
    """
    Liveness probe - always returns 200.
    """
    start_time = time.time()
    http_requests_total.labels(method="GET", endpoint="/health/live", status="200").inc()
    duration = time.time() - start_time
    http_request_duration_seconds.labels(method="GET", endpoint="/health/live").observe(duration)
    return HealthResponse(status="alive")


@router.get("/health/ready", response_model=HealthResponse)
async def health_ready():
    """
    Readiness probe - returns 200 only if DB is ready and WEBHOOK_SECRET exists.
    """
    start_time = time.time()
    
    # Check database
    db_ready = check_db_ready()
    
    # Check webhook secret
    webhook_secret_exists = bool(os.getenv("WEBHOOK_SECRET"))
    
    if db_ready and webhook_secret_exists:
        http_requests_total.labels(method="GET", endpoint="/health/ready", status="200").inc()
        duration = time.time() - start_time
        http_request_duration_seconds.labels(method="GET", endpoint="/health/ready").observe(duration)
        return HealthResponse(status="ready")
    else:
        http_requests_total.labels(method="GET", endpoint="/health/ready", status="503").inc()
        duration = time.time() - start_time
        http_request_duration_seconds.labels(method="GET", endpoint="/health/ready").observe(duration)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not ready"
        )

