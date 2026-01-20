"""
FastAPI Analytical API - Main Application
Task-4: Expose dbt data marts through REST API

This module implements analytical endpoints that query the dbt star schema
to answer key business questions about Telegram channel activity.
"""

import logging
from typing import Optional
from datetime import datetime, date, timedelta
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

from api.database import get_db, test_connection
from api.schemas import (
    TopProductsResponse,
    TopProductItem,
    ChannelActivityResponse,
    ActivityPeriod,
    MessageSearchResponse,
    MessageSearchItem,
    VisualContentResponse,
    VisualContentStats,
    ErrorResponse
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Medical Telegram Warehouse - Analytical API",
    description="""
    **Enterprise-Grade Analytical API for Ethiopian Medical/Pharmaceutical Telegram Channel Data**

    This API exposes insights from the dbt star schema data marts, enabling:
    - Product/term frequency analysis
    - Channel activity trends
    - Message search and discovery
    - Visual content statistics (YOLO enrichment)

    **Business Context**: Inspired by fintech fraud detection thinking—analyzing behavior patterns,
    frequency anomalies, and engagement signals in medical/pharmaceutical Telegram channels.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)


# ============================================================================
# Health Check & Database Status
# ============================================================================

@app.get("/", tags=["Health"])
async def root():
    """
    Root endpoint - API information.

    **Access Swagger Documentation**: Visit http://localhost:8000/docs for interactive API documentation.
    """
    return {
        "name": "Medical Telegram Warehouse - Analytical API",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs",
        "redoc": "/redoc",
        "message": "Visit /docs for Swagger UI documentation with all endpoints",
        "endpoints": {
            "analytical": [
                "/api/reports/top-products",
                "/api/channels/{channel_name}/activity",
                "/api/search/messages",
                "/api/reports/visual-content"
            ],
            "utility": [
                "/health",
                "/docs",
                "/redoc"
            ]
        }
    }


@app.get("/health", tags=["Health"])
async def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint - verifies database connectivity.

    Returns:
        dict: Health status and database connection status
    """
    try:
        # Test database connection
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = f"error: {str(e)}"

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "database": db_status,
        "timestamp": datetime.utcnow().isoformat()
    }


# ============================================================================
# Endpoint 1: Top Products
# ============================================================================

@app.get(
    "/api/reports/top-products",
    response_model=TopProductsResponse,
    tags=["Reports"],
    summary="Get Top Products/Terms",
    description="""
    Returns the most frequently mentioned products/terms across all channels.

    **Business Use Case**: Identify trending products, popular medications, or frequently
    discussed terms in medical/pharmaceutical Telegram channels.

    **Analysis Method**:
    - Extracts terms from message_text using text search
    - Aggregates by term (case-insensitive)
    - Ranks by mention count
    - Includes engagement metrics (views, forwards) per term
    """
)
async def get_top_products(
    limit: int = Query(10, ge=1, le=100, description="Number of top products to return"),
    min_mentions: int = Query(1, ge=1, description="Minimum mention count to include"),
    db: Session = Depends(get_db)
):
    """
    Get top products/terms by mention frequency.

    Args:
        limit: Maximum number of products to return (1-100)
        min_mentions: Minimum mention count threshold
        db: Database session

    Returns:
        TopProductsResponse: Top products with engagement metrics
    """
    try:
        # Query to extract and count product mentions
        # Using PostgreSQL text search and word extraction
        query = text("""
            WITH word_counts AS (
                SELECT
                    LOWER(unnest(string_to_array(message_text, ' '))) AS term,
                    message_id,
                    channel_key,
                    views,
                    forwards
                FROM marts.fct_messages
                WHERE message_text IS NOT NULL
                  AND LENGTH(TRIM(message_text)) > 0
            ),
            term_stats AS (
                SELECT
                    term,
                    COUNT(DISTINCT message_id) AS mention_count,
                    SUM(views) AS total_views,
                    SUM(forwards) AS total_forwards,
                    array_agg(DISTINCT dc.channel_name) AS channels
                FROM word_counts wc
                INNER JOIN marts.dim_channels dc ON wc.channel_key = dc.channel_key
                WHERE LENGTH(term) >= 3  -- Filter out very short words
                  AND term !~ '^[0-9]+$'  -- Filter out pure numbers
                GROUP BY term
                HAVING COUNT(DISTINCT message_id) >= :min_mentions
            )
            SELECT
                term,
                mention_count,
                total_views,
                total_forwards,
                channels
            FROM term_stats
            ORDER BY mention_count DESC, total_views DESC
            LIMIT :limit
        """)

        result = db.execute(query, {"limit": limit, "min_mentions": min_mentions})
        rows = result.fetchall()

        # Get total count for pagination info
        count_query = text("""
            SELECT COUNT(DISTINCT term)
            FROM (
                SELECT LOWER(unnest(string_to_array(message_text, ' '))) AS term
                FROM marts.fct_messages
                WHERE message_text IS NOT NULL
                  AND LENGTH(TRIM(message_text)) > 0
            ) sub
            WHERE LENGTH(term) >= 3
              AND term !~ '^[0-9]+$'
        """)
        total_result = db.execute(count_query)
        total_found = total_result.scalar() or 0

        # Build response
        products = [
            TopProductItem(
                term=row.term,
                mention_count=row.mention_count,
                total_views=row.total_views or 0,
                total_forwards=row.total_forwards or 0,
                channels=row.channels or []
            )
            for row in rows
        ]

        return TopProductsResponse(
            limit=limit,
            total_found=total_found,
            products=products
        )

    except Exception as e:
        logger.error(f"Error in get_top_products: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve top products: {str(e)}"
        )


# ============================================================================
# Endpoint 2: Channel Activity
# ============================================================================

@app.get(
    "/api/channels/{channel_name}/activity",
    response_model=ChannelActivityResponse,
    tags=["Channels"],
    summary="Get Channel Activity Trends",
    description="""
    Returns posting volume and engagement trends for a specific channel.

    **Business Use Case**: Track channel activity patterns, identify posting frequency
    anomalies, and analyze engagement trends over time.

    **Analysis Method**:
    - Groups messages by day or week
    - Calculates message counts, total views/forwards
    - Computes average engagement per message
    """
)
async def get_channel_activity(
    channel_name: str,
    period: str = Query("daily", regex="^(daily|weekly)$", description="Aggregation period: 'daily' or 'weekly'"),
    days_back: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    db: Session = Depends(get_db)
):
    """
    Get activity trends for a specific channel.

    Args:
        channel_name: Name of the Telegram channel
        period: Aggregation period ('daily' or 'weekly')
        days_back: Number of days to look back
        db: Database session

    Returns:
        ChannelActivityResponse: Activity trends by period
    """
    try:
        # Verify channel exists
        channel_check = text("""
            SELECT channel_key, channel_name
            FROM marts.dim_channels
            WHERE channel_name = :channel_name
        """)
        channel_result = db.execute(channel_check, {"channel_name": channel_name})
        channel_row = channel_result.fetchone()

        if not channel_row:
            raise HTTPException(
                status_code=404,
                detail=f"Channel '{channel_name}' not found"
            )

        channel_key = channel_row.channel_key

        # Calculate date range
        end_date = date.today()
        start_date = end_date - timedelta(days=days_back)

        # Build query based on period type
        if period == "daily":
            date_group = "dd.full_date"
            date_format = "YYYY-MM-DD"
        else:  # weekly
            date_group = f"DATE_TRUNC('week', dd.full_date)"
            date_format = "YYYY-MM-DD"

        query = text(f"""
            SELECT
                TO_CHAR({date_group}, :date_format) AS period,
                COUNT(DISTINCT fm.message_id) AS message_count,
                SUM(fm.views) AS total_views,
                SUM(fm.forwards) AS total_forwards,
                CASE
                    WHEN COUNT(DISTINCT fm.message_id) > 0
                    THEN AVG(fm.views::numeric)
                    ELSE 0
                END AS avg_views_per_message
            FROM marts.fct_messages fm
            INNER JOIN marts.dim_dates dd ON fm.date_key = dd.date_key
            WHERE fm.channel_key = :channel_key
              AND dd.full_date >= :start_date
              AND dd.full_date <= :end_date
            GROUP BY {date_group}
            ORDER BY {date_group} ASC
        """)

        result = db.execute(query, {
            "channel_key": channel_key,
            "start_date": start_date,
            "end_date": end_date,
            "date_format": date_format
        })
        rows = result.fetchall()

        # Get total message count
        total_query = text("""
            SELECT COUNT(DISTINCT message_id)
            FROM marts.fct_messages
            WHERE channel_key = :channel_key
              AND date_key IN (
                  SELECT date_key
                  FROM marts.dim_dates
                  WHERE full_date >= :start_date
                    AND full_date <= :end_date
              )
        """)
        total_result = db.execute(total_query, {
            "channel_key": channel_key,
            "start_date": start_date,
            "end_date": end_date
        })
        total_messages = total_result.scalar() or 0

        # Build response
        activity = [
            ActivityPeriod(
                period=str(row.period),
                message_count=row.message_count,
                total_views=row.total_views or 0,
                total_forwards=row.total_forwards or 0,
                avg_views_per_message=float(row.avg_views_per_message or 0)
            )
            for row in rows
        ]

        return ChannelActivityResponse(
            channel_name=channel_name,
            period_type=period,
            total_messages=total_messages,
            activity=activity
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_channel_activity: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve channel activity: {str(e)}"
        )


# ============================================================================
# Endpoint 3: Message Search
# ============================================================================

@app.get(
    "/api/search/messages",
    response_model=MessageSearchResponse,
    tags=["Search"],
    summary="Search Messages by Keyword",
    description="""
    Search messages by keyword in message text.

    **Business Use Case**: Find specific products, medications, or topics mentioned
    across channels. Useful for competitive intelligence and content discovery.

    **Analysis Method**:
    - Full-text search in message_text (case-insensitive)
    - Returns matching messages with engagement metrics
    - Supports pagination via limit parameter
    """
)
async def search_messages(
    query: str = Query(..., min_length=1, description="Search keyword"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
    channel_name: Optional[str] = Query(None, description="Filter by channel name (optional)"),
    db: Session = Depends(get_db)
):
    """
    Search messages by keyword.

    Args:
        query: Search keyword
        limit: Maximum number of results to return
        channel_name: Optional channel filter
        db: Database session

    Returns:
        MessageSearchResponse: Matching messages
    """
    try:
        # Build query with optional channel filter
        if channel_name:
            # Verify channel exists
            channel_check = text("""
                SELECT channel_key
                FROM marts.dim_channels
                WHERE channel_name = :channel_name
            """)
            channel_result = db.execute(channel_check, {"channel_name": channel_name})
            channel_row = channel_result.fetchone()

            if not channel_row:
                raise HTTPException(
                    status_code=404,
                    detail=f"Channel '{channel_name}' not found"
                )

            channel_key_filter = "AND fm.channel_key = :channel_key"
            params = {
                "query": f"%{query.lower()}%",
                "limit": limit,
                "channel_key": channel_row.channel_key
            }
        else:
            channel_key_filter = ""
            params = {
                "query": f"%{query.lower()}%",
                "limit": limit
            }

        search_query = text(f"""
            SELECT
                fm.message_id,
                dc.channel_name,
                fm.message_timestamp,
                LEFT(fm.message_text, 500) AS message_text,  -- Truncate for response
                fm.views,
                fm.forwards,
                fm.has_image
            FROM marts.fct_messages fm
            INNER JOIN marts.dim_channels dc ON fm.channel_key = dc.channel_key
            WHERE LOWER(fm.message_text) LIKE :query
              {channel_key_filter}
            ORDER BY fm.message_timestamp DESC
            LIMIT :limit
        """)

        result = db.execute(search_query, params)
        rows = result.fetchall()

        # Get total count
        count_query = text(f"""
            SELECT COUNT(*)
            FROM marts.fct_messages fm
            WHERE LOWER(fm.message_text) LIKE :query
              {channel_key_filter}
        """)
        total_result = db.execute(count_query, params)
        total_found = total_result.scalar() or 0

        # Build response
        messages = [
            MessageSearchItem(
                message_id=row.message_id,
                channel_name=row.channel_name,
                message_timestamp=row.message_timestamp,
                message_text=row.message_text or "",
                views=row.views,
                forwards=row.forwards,
                has_image=row.has_image or False
            )
            for row in rows
        ]

        return MessageSearchResponse(
            query=query,
            limit=limit,
            total_found=total_found,
            messages=messages
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in search_messages: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to search messages: {str(e)}"
        )


# ============================================================================
# Endpoint 4: Visual Content Stats
# ============================================================================

@app.get(
    "/api/reports/visual-content",
    response_model=VisualContentResponse,
    tags=["Reports"],
    summary="Get Visual Content Statistics",
    description="""
    Returns statistics about visual content and YOLO object detection results.

    **Business Use Case**: Analyze image usage patterns, object detection insights,
    and engagement correlation with visual content types.

    **Analysis Method**:
    - Aggregates YOLO detection results from fct_image_detections
    - Groups by image category and detected class
    - Calculates engagement metrics by category
    """
)
async def get_visual_content_stats(db: Session = Depends(get_db)):
    """
    Get visual content statistics from YOLO enrichment.

    Args:
        db: Database session

    Returns:
        VisualContentResponse: Visual content statistics
    """
    try:
        # Main stats query
        stats_query = text("""
            SELECT
                COUNT(DISTINCT fid.message_id) AS total_images,
                SUM(fid.num_detections) AS total_detections,
                CASE
                    WHEN COUNT(DISTINCT fid.message_id) > 0
                    THEN AVG(fid.num_detections::numeric)
                    ELSE 0
                END AS avg_detections_per_image
            FROM marts.fct_image_detections fid
        """)

        stats_result = db.execute(stats_query)
        stats_row = stats_result.fetchone()

        # Category distribution
        category_query = text("""
            SELECT
                fid.image_category,
                COUNT(DISTINCT fid.message_id) AS count
            FROM marts.fct_image_detections fid
            WHERE fid.image_category IS NOT NULL
            GROUP BY fid.image_category
        """)

        category_result = db.execute(category_query)
        category_rows = category_result.fetchall()

        image_categories = {row.image_category: row.count for row in category_rows}

        # Top detected classes
        class_query = text("""
            SELECT
                fid.detected_class,
                COUNT(*) AS count
            FROM marts.fct_image_detections fid
            WHERE fid.detected_class IS NOT NULL
            GROUP BY fid.detected_class
            ORDER BY count DESC
            LIMIT 10
        """)

        class_result = db.execute(class_query)
        class_rows = class_result.fetchall()

        top_detected_classes = [
            {"class": row.detected_class, "count": row.count}
            for row in class_rows
        ]

        # Engagement by category
        engagement_query = text("""
            SELECT
                fid.image_category,
                AVG(fid.views::numeric) AS avg_views,
                AVG(fid.forwards::numeric) AS avg_forwards
            FROM marts.fct_image_detections fid
            WHERE fid.image_category IS NOT NULL
            GROUP BY fid.image_category
        """)

        engagement_result = db.execute(engagement_query)
        engagement_rows = engagement_result.fetchall()

        engagement_by_category = {
            row.image_category: {
                "avg_views": float(row.avg_views or 0),
                "avg_forwards": float(row.avg_forwards or 0)
            }
            for row in engagement_rows
        }

        # Build response
        stats = VisualContentStats(
            total_images=stats_row.total_images or 0,
            total_detections=stats_row.total_detections or 0,
            avg_detections_per_image=float(stats_row.avg_detections_per_image or 0),
            image_categories=image_categories,
            top_detected_classes=top_detected_classes,
            engagement_by_category=engagement_by_category
        )

        return VisualContentResponse(stats=stats)

    except Exception as e:
        logger.error(f"Error in get_visual_content_stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve visual content stats: {str(e)}"
        )


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """Custom HTTP exception handler."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "status_code": exc.status_code}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """General exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )


# ============================================================================
# Startup Event
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Verify database connection on startup."""
    logger.info("Starting FastAPI application...")
    if test_connection():
        logger.info("Database connection verified")
    else:
        logger.warning("Database connection failed - API may not function correctly")
