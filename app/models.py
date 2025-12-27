from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class WebhookPayload(BaseModel):
    """Webhook payload model"""
    message_id: str = Field(..., description="Unique message identifier")
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    source: str = Field(..., description="Source of the message")
    raw_data: dict = Field(..., description="Raw message data")


class MessageResponse(BaseModel):
    """Message response model"""
    message_id: str
    timestamp: str
    source: str
    raw_data: dict
    created_at: str


class MessageListResponse(BaseModel):
    """Paginated message list response"""
    messages: list[MessageResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class HealthResponse(BaseModel):
    """Health check response"""
    status: str

