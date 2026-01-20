# Task-4: Analytical API Documentation

**Status**: ✅ Complete
**Branch**: `task-4-dev`
**Implementation Date**: 2026-01-17

---

## Overview

Task-4 exposes the dbt data marts through a **FastAPI REST API** that answers key business questions clearly, safely, and efficiently. This API layer enables decision-makers to access trusted analytical insights from Telegram data.

---

## Architecture

```
┌─────────────────┐
│   FastAPI App   │
│  (api/main.py)  │
└────────┬────────┘
         │
         │ SQLAlchemy
         ▼
┌─────────────────┐
│   PostgreSQL    │
│  (dbt marts)    │
│  - dim_channels │
│  - dim_dates    │
│  - fct_messages │
│  - fct_image_   │
│    detections   │
└─────────────────┘
```

**Key Design Decisions**:

1. **Query dbt Marts Only**: All endpoints query the `marts` schema (star schema), not raw data
2. **Efficient Joins**: Leverages foreign keys (channel_key, date_key) for fast joins
3. **Aggregation at Database**: Heavy lifting done in PostgreSQL, not Python
4. **Type Safety**: Pydantic schemas ensure type-safe request/response handling
5. **Error Handling**: Graceful handling of missing data, invalid inputs, database errors

---

## API Endpoints

### 1. Health Check

**Endpoint**: `GET /health`

**Description**: Verifies database connectivity and API health status.

**Response**:
```json
{
  "status": "healthy",
  "database": "connected",
  "timestamp": "2026-01-17T10:30:00"
}
```

---

### 2. Top Products

**Endpoint**: `GET /api/reports/top-products`

**Business Question**: What are the most frequently mentioned products/terms across all channels?

**Query Logic**:
- Extracts terms from `message_text` using PostgreSQL text functions
- Aggregates by term (case-insensitive)
- Ranks by mention count
- Includes engagement metrics (views, forwards) per term
- Filters out very short words and pure numbers

**Parameters**:
- `limit` (query, default: 10, min: 1, max: 100): Number of top products to return
- `min_mentions` (query, default: 1, min: 1): Minimum mention count threshold

**Example Request**:
```bash
GET /api/reports/top-products?limit=10&min_mentions=5
```

**Example Response**:
```json
{
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
```

---

### 3. Channel Activity

**Endpoint**: `GET /api/channels/{channel_name}/activity`

**Business Question**: What are the posting volume and engagement trends for a specific channel?

**Query Logic**:
- Joins `fct_messages` with `dim_dates` and `dim_channels`
- Groups messages by day or week
- Calculates message counts, total views/forwards
- Computes average engagement per message
- Supports configurable date range

**Parameters**:
- `channel_name` (path, required): Name of the Telegram channel
- `period` (query, default: "daily"): Aggregation period - "daily" or "weekly"
- `days_back` (query, default: 30, min: 1, max: 365): Number of days to look back

**Example Request**:
```bash
GET /api/channels/CheMed/activity?period=daily&days_back=30
```

**Example Response**:
```json
{
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
```

---

### 4. Message Search

**Endpoint**: `GET /api/search/messages`

**Business Question**: Find specific products, medications, or topics mentioned across channels.

**Query Logic**:
- Full-text search in `message_text` (case-insensitive LIKE)
- Joins with `dim_channels` for channel names
- Supports optional channel filtering
- Returns matching messages with engagement metrics
- Orders by timestamp (most recent first)

**Parameters**:
- `query` (query, required, min_length: 1): Search keyword
- `limit` (query, default: 20, min: 1, max: 100): Maximum number of results
- `channel_name` (query, optional): Filter by channel name

**Example Request**:
```bash
GET /api/search/messages?query=paracetamol&limit=20&channel_name=CheMed
```

**Example Response**:
```json
{
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
      "has_image": true
    }
  ]
}
```

---

### 5. Visual Content Stats

**Endpoint**: `GET /api/reports/visual-content`

**Business Question**: What are the image usage patterns and YOLO object detection insights?

**Query Logic**:
- Aggregates data from `fct_image_detections`
- Groups by image category and detected class
- Calculates total images, detections, averages
- Computes engagement metrics by category
- Identifies top detected object classes

**Example Request**:
```bash
GET /api/reports/visual-content
```

**Example Response**:
```json
{
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
      "promotional": {
        "avg_views": 2500,
        "avg_forwards": 75
      },
      "product_display": {
        "avg_views": 1800,
        "avg_forwards": 45
      }
    }
  }
}
```

---

## Setup & Execution

### Prerequisites

1. PostgreSQL running with dbt marts populated
2. Python 3.11+
3. Dependencies installed: `pip install -r requirements.txt`

### Start API Server

**Option 1: Using uvicorn directly**
```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

**Option 2: Using convenience script**
```bash
python run_api.py
```

### Access API Documentation

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

---

## Error Handling

The API implements comprehensive error handling:

1. **HTTP 404**: Channel not found, resource not found
2. **HTTP 400**: Invalid request parameters (validated by Pydantic)
3. **HTTP 500**: Internal server errors (database connection issues, query failures)

**Error Response Format**:
```json
{
  "error": "Error message",
  "status_code": 404
}
```

---

## Performance Considerations

1. **Connection Pooling**: SQLAlchemy connection pool (pool_size=5, max_overflow=10)
2. **Indexed Foreign Keys**: Fast joins via channel_key and date_key
3. **Database Aggregation**: Heavy computation in PostgreSQL, not Python
4. **Pagination**: LIMIT clauses prevent large result sets
5. **Text Search**: Uses PostgreSQL native functions (no external search engine)

---

## Security

1. **No SQL Injection**: All queries use parameterized statements via SQLAlchemy
2. **Input Validation**: Pydantic and FastAPI Query parameters validate all inputs
3. **Environment Credentials**: Database credentials loaded from `.env` (never hardcoded)
4. **Type Safety**: Pydantic schemas ensure type-safe request/response handling

---

## Testing

### Manual Testing

1. **Health Check**:
   ```bash
   curl http://localhost:8000/health
   ```

2. **Top Products**:
   ```bash
   curl "http://localhost:8000/api/reports/top-products?limit=10"
   ```

3. **Channel Activity**:
   ```bash
   curl "http://localhost:8000/api/channels/CheMed/activity?period=daily&days_back=30"
   ```

4. **Message Search**:
   ```bash
   curl "http://localhost:8000/api/search/messages?query=paracetamol&limit=20"
   ```

5. **Visual Content Stats**:
   ```bash
   curl http://localhost:8000/api/reports/visual-content
   ```

### Using Swagger UI

Navigate to `http://localhost:8000/docs` and use the interactive API explorer to test all endpoints.

---

## Business Value

1. **Decision-Making**: Executives can query top products, channel activity, and trends via REST API
2. **Integration Ready**: API can be consumed by dashboards, BI tools, or other applications
3. **Real-Time Insights**: Fast queries on pre-aggregated dbt marts (no raw data scanning)
4. **Scalable**: Connection pooling and efficient queries support concurrent users
5. **Trusted Data**: Only queries validated dbt marts (star schema), ensuring data quality

---

## Future Enhancements

1. **Authentication**: Add API key or OAuth2 authentication
2. **Rate Limiting**: Implement rate limiting to prevent abuse
3. **Caching**: Add Redis caching for frequently accessed endpoints
4. **Advanced Search**: Implement full-text search with PostgreSQL tsvector
5. **WebSocket Support**: Real-time updates for channel activity
6. **GraphQL**: Alternative API interface for flexible queries

---

## Files Created

- `api/main.py` - FastAPI application with all endpoints
- `api/database.py` - Database connection layer
- `api/schemas.py` - Pydantic request/response models
- `api/__init__.py` - Package initialization
- `run_api.py` - Convenience script to start API server
- `docs/task-4-api-documentation.md` - This documentation file

---

## Validation Checklist

- [x] FastAPI application starts without errors
- [x] Database connection verified on startup
- [x] All 4 analytical endpoints implemented and functional
- [x] Pydantic schemas validate requests/responses
- [x] Error handling for missing data and invalid inputs
- [x] OpenAPI documentation auto-generated
- [x] Health check endpoint working
- [x] README updated with Task-4 documentation
- [x] All endpoints query dbt marts (not raw data)
- [x] Type-safe request/response handling
- [x] Production-ready error handling

---

**Task-4 Status**: ✅ Complete
