"""
Pydantic Schemas for FastAPI Request/Response Models
Task-4: Type-safe API contracts

This module defines Pydantic models for request validation and response
serialization, ensuring type safety and clear API contracts.
"""

from typing import List, Optional
from datetime import datetime, date
from pydantic import BaseModel, Field, field_validator


# ============================================================================
# Response Models
# ============================================================================

class TopProductItem(BaseModel):
    """Single product/term in top products report."""
    term: str = Field(..., description="Product name or keyword")
    mention_count: int = Field(..., description="Number of times mentioned")
    total_views: int = Field(..., description="Total views across all mentions")
    total_forwards: int = Field(..., description="Total forwards across all mentions")
    channels: List[str] = Field(..., description="List of channels mentioning this product")

    class Config:
        json_schema_extra = {
            "example": {
                "term": "paracetamol",
                "mention_count": 45,
                "total_views": 125000,
                "total_forwards": 320,
                "channels": ["CheMed", "Tikvah Pharma"]
            }
        }


class TopProductsResponse(BaseModel):
    """Response for top products endpoint."""
    limit: int = Field(..., description="Requested limit")
    total_found: int = Field(..., description="Total products found")
    products: List[TopProductItem] = Field(..., description="List of top products")

    class Config:
        json_schema_extra = {
            "example": {
                "limit": 10,
                "total_found": 150,
                "products": [
                    {
                        "term": "paracetamol",
                        "mention_count": 45,
                        "total_views": 125000,
                        "total_forwards": 320,
                        "channels": ["CheMed", "Tikvah Pharma"]
                    }
                ]
            }
        }


class ActivityPeriod(BaseModel):
    """Activity data for a single time period."""
    period: str = Field(..., description="Date or week identifier")
    message_count: int = Field(..., description="Number of messages in this period")
    total_views: int = Field(..., description="Total views")
    total_forwards: int = Field(..., description="Total forwards")
    avg_views_per_message: float = Field(..., description="Average views per message")

    class Config:
        json_schema_extra = {
            "example": {
                "period": "2026-01-17",
                "message_count": 25,
                "total_views": 50000,
                "total_forwards": 150,
                "avg_views_per_message": 2000.0
            }
        }


class ChannelActivityResponse(BaseModel):
    """Response for channel activity endpoint."""
    channel_name: str = Field(..., description="Channel name")
    period_type: str = Field(..., description="'daily' or 'weekly'")
    total_messages: int = Field(..., description="Total messages in date range")
    activity: List[ActivityPeriod] = Field(..., description="Activity by period")

    class Config:
        json_schema_extra = {
            "example": {
                "channel_name": "CheMed",
                "period_type": "daily",
                "total_messages": 150,
                "activity": [
                    {
                        "period": "2026-01-17",
                        "message_count": 25,
                        "total_views": 50000,
                        "total_forwards": 150,
                        "avg_views_per_message": 2000.0
                    }
                ]
            }
        }


class MessageSearchItem(BaseModel):
    """Single message in search results."""
    message_id: int = Field(..., description="Telegram message ID")
    channel_name: str = Field(..., description="Channel name")
    message_timestamp: datetime = Field(..., description="Message timestamp")
    message_text: str = Field(..., description="Message text (truncated if long)")
    views: int = Field(..., description="Number of views")
    forwards: int = Field(..., description="Number of forwards")
    has_image: bool = Field(..., description="Whether message has image")

    class Config:
        json_schema_extra = {
            "example": {
                "message_id": 12345,
                "channel_name": "CheMed",
                "message_timestamp": "2026-01-17T10:30:00",
                "message_text": "Paracetamol available...",
                "views": 1000,
                "forwards": 50,
                "has_image": True
            }
        }


class MessageSearchResponse(BaseModel):
    """Response for message search endpoint."""
    query: str = Field(..., description="Search query")
    limit: int = Field(..., description="Requested limit")
    total_found: int = Field(..., description="Total messages found")
    messages: List[MessageSearchItem] = Field(..., description="Matching messages")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "paracetamol",
                "limit": 20,
                "total_found": 45,
                "messages": [
                    {
                        "message_id": 12345,
                        "channel_name": "CheMed",
                        "message_timestamp": "2026-01-17T10:30:00",
                        "message_text": "Paracetamol available...",
                        "views": 1000,
                        "forwards": 50,
                        "has_image": True
                    }
                ]
            }
        }


class VisualContentStats(BaseModel):
    """Visual content statistics."""
    total_images: int = Field(..., description="Total images with detections")
    total_detections: int = Field(..., description="Total object detections")
    avg_detections_per_image: float = Field(..., description="Average detections per image")
    image_categories: dict = Field(..., description="Count by image category")
    top_detected_classes: List[dict] = Field(..., description="Top detected object classes")
    engagement_by_category: dict = Field(..., description="Average views/forwards by category")

    class Config:
        json_schema_extra = {
            "example": {
                "total_images": 500,
                "total_detections": 1250,
                "avg_detections_per_image": 2.5,
                "image_categories": {
                    "promotional": 200,
                    "product_display": 150,
                    "lifestyle": 100,
                    "other": 50
                },
                "top_detected_classes": [
                    {"class": "person", "count": 300},
                    {"class": "bottle", "count": 150}
                ],
                "engagement_by_category": {
                    "promotional": {"avg_views": 2500, "avg_forwards": 75},
                    "product_display": {"avg_views": 1800, "avg_forwards": 45}
                }
            }
        }


class VisualContentResponse(BaseModel):
    """Response for visual content stats endpoint."""
    stats: VisualContentStats = Field(..., description="Visual content statistics")

    class Config:
        json_schema_extra = {
            "example": {
                "stats": {
                    "total_images": 500,
                    "total_detections": 1250,
                    "avg_detections_per_image": 2.5,
                    "image_categories": {
                        "promotional": 200,
                        "product_display": 150,
                        "lifestyle": 100,
                        "other": 50
                    },
                    "top_detected_classes": [
                        {"class": "person", "count": 300},
                        {"class": "bottle", "count": 150}
                    ],
                    "engagement_by_category": {
                        "promotional": {"avg_views": 2500, "avg_forwards": 75},
                        "product_display": {"avg_views": 1800, "avg_forwards": 45}
                    }
                }
            }
        }


# ============================================================================
# Error Models
# ============================================================================

class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Additional error details")

    class Config:
        json_schema_extra = {
            "example": {
                "error": "Channel not found",
                "detail": "Channel 'InvalidChannel' does not exist in the database"
            }
        }
