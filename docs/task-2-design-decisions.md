# Task-2: Star Schema Design Decisions

**Author**: Senior Data Scientist & Data Engineer
**Date**: 2026-01-17
**Task**: Data Modeling & Transformation

---

## Executive Summary

This document explains the star schema design decisions for the medical Telegram warehouse transformation layer. The design prioritizes analytical query performance, business user comprehension, and scalability.

---

## Why Star Schema?

### 1. Analytical Performance

Star schema is optimized for analytical workloads (OLAP). The design separates:
- **Measures** (facts): Numeric values to aggregate (views, forwards, counts)
- **Dimensions** (context): Descriptive attributes for filtering and grouping

This separation enables:
- Efficient aggregation queries (COUNT, SUM, AVG)
- Fast joins (fact table ↔ dimensions via foreign keys)
- Optimized indexes on dimension keys

### 2. Business User Friendly

Star schemas are intuitive:
- **Fact table** = Events/Transactions (messages)
- **Dimensions** = Context (channels, dates)

Business users can easily understand: "Show me message counts by channel by month" = `fct_messages` joined to `dim_channels` and `dim_dates`.

### 3. Query Simplicity

Simple join patterns:
```sql
SELECT
    dc.channel_name,
    dd.month,
    COUNT(*) as message_count,
    SUM(fm.views) as total_views
FROM fct_messages fm
JOIN dim_channels dc ON fm.channel_key = dc.channel_key
JOIN dim_dates dd ON fm.date_key = dd.date_key
GROUP BY dc.channel_name, dd.month
```

### 4. Scalability

- Dimensions can be enriched independently (add columns without touching fact table)
- Fact table can grow indefinitely (append-only)
- Supports slowly changing dimensions (SCD Type 2) if needed later

---

## Dimension Design

### dim_channels

**Grain**: One row per unique channel

**Purpose**: Channel-level analytics, comparisons, metadata

**Attributes**:
- `channel_key` (PK): Surrogate key (MD5 hash of `channel_name`)
- `channel_name` (Business Key): Telegram channel name
- `first_message_date`: Earliest message from channel
- `last_message_date`: Most recent message from channel
- `total_messages`: Total message count (for quick lookups)

**Design Rationale**:
- Surrogate key enables SCD Type 2 if channel names change
- Aggregated stats (`total_messages`) enable fast channel-level queries without joining to fact table
- Simple grain (1 row per channel) prevents duplication

**Use Cases**:
- "Which channels are most active?"
- "Compare message volumes across channels"
- "Channel metadata dashboard"

---

### dim_dates

**Grain**: One row per calendar day (2020-2030)

**Purpose**: Time-based analysis, trending, seasonality detection

**Attributes**:
- `date_key` (PK): Surrogate key (YYYYMMDD integer, e.g., 20240115)
- `full_date`: Full date (DATE type)
- `year`, `quarter`, `month`, `week`: Temporal hierarchies
- `day_of_month`: Day number (1-31)
- `day_of_week`: ISO day (1=Monday, 7=Sunday)
- `day_name`: Day name ("Monday", "Tuesday", etc.)
- `is_weekend`: Boolean flag

**Design Rationale**:
- Date dimension is a best practice for analytical databases
- Enables easy time-based filtering and grouping
- Pre-computed attributes avoid runtime calculations
- ISO day-of-week standardizes week calculations
- Date range (2020-2030) covers historical and future data

**Use Cases**:
- "Show message volume trends by month"
- "Compare weekday vs weekend activity"
- "Seasonality analysis (quarterly patterns)"
- "Anomaly detection (spikes on specific dates)"

---

## Fact Table Design

### fct_messages

**Grain**: One row per message

**Purpose**: Message-level analytics, engagement metrics, content analysis

**Attributes**:
- `message_id` (PK): Business key (Telegram message ID)
- `channel_key` (FK): Foreign key to `dim_channels`
- `date_key` (FK): Foreign key to `dim_dates`
- `message_timestamp`: Full timestamp (for precise time analysis)
- `message_text`: Text content
- `message_length`: Character length (derived in staging)
- `views`: Number of views
- `forwards`: Number of forwards
- `has_media`: Boolean flag
- `has_image`: Boolean flag (derived in staging)
- `image_path`: Path to image file

**Design Rationale**:
- **Grain**: One message = one row. This is the atomic unit of analysis.
- **Primary Key**: `message_id` is business key (unique per Telegram message)
- **Foreign Keys**: Connect to dimensions for analytical queries
- **Measures**: `views`, `forwards` are additive measures (can be summed)
- **Flags**: `has_media`, `has_image` enable filtering and counting
- **Text**: Stored in fact table for simplicity (not normalized to separate dimension)

**Why Not Normalize Message Attributes?**

Message attributes (text, length, media flags) are stored directly in the fact table because:
1. **One-to-one relationship**: Each message has exactly one text/length/media flag
2. **Query simplicity**: No additional joins needed
3. **Performance**: Avoids join overhead for simple text filtering
4. **Analytical needs**: Text analysis often happens at message level

If message text becomes large or we need complex text analysis, we could create `dim_messages` later (SCD Type 2 for message edits).

**Use Cases**:
- "Count messages by channel"
- "Average views per message by month"
- "Messages with images vs without images"
- "Engagement metrics (views + forwards)"
- "Content analysis (message length distribution)"

---

## Surrogate Keys

### Why Surrogate Keys?

Surrogate keys (non-business keys) are used instead of business keys (e.g., `channel_name`, `message_date`) for foreign keys because:

1. **Performance**: Integer/hash keys are faster for joins than strings/dates
2. **Stability**: Business keys can change (channel name changes), surrogate keys don't
3. **SCD Support**: Enables slowly changing dimensions (Type 2) if needed
4. **Consistency**: Standard practice in dimensional modeling

### Implementation

- **`channel_key`**: MD5 hash of `channel_name`
  - Consistent: Same channel_name always generates same hash
  - Immutable: Hash doesn't change even if channel_name changes
  - Fast: Hash is computed once, stored in dimension

- **`date_key`**: YYYYMMDD integer (e.g., 20240115)
  - Human-readable: Can be converted to date easily
  - Efficient: Integer comparison is fast
  - Standard: Common pattern in date dimensions

---

## Data Quality Considerations

### Staging Layer

The staging model (`stg_telegram_messages`) enforces:
- **Null checks**: Filters out messages with null `message_id`, `channel_name`, or `message_date`
- **Type casting**: Ensures all fields have correct data types
- **Default values**: Sets defaults for nullable fields (views=0, forwards=0, has_media=false)

### Tests

**Schema Tests**:
- `unique`: Ensures no duplicate message_ids
- `not_null`: Ensures required fields are populated
- `relationships`: Ensures foreign keys reference valid dimension keys

**Custom Business Tests**:
- `test_no_future_dated_messages`: No messages dated in the future
- `test_no_negative_views`: No negative view counts

These tests ensure data quality and catch data issues early.

---

## Query Patterns Enabled

### Example 1: Message Volume by Channel by Month

```sql
SELECT
    dc.channel_name,
    dd.year,
    dd.month,
    COUNT(*) as message_count
FROM fct_messages fm
JOIN dim_channels dc ON fm.channel_key = dc.channel_key
JOIN dim_dates dd ON fm.date_key = dd.date_key
GROUP BY dc.channel_name, dd.year, dd.month
ORDER BY dd.year, dd.month, dc.channel_name;
```

### Example 2: Engagement Metrics (Views + Forwards)

```sql
SELECT
    dc.channel_name,
    SUM(fm.views) as total_views,
    SUM(fm.forwards) as total_forwards,
    AVG(fm.views) as avg_views_per_message
FROM fct_messages fm
JOIN dim_channels dc ON fm.channel_key = dc.channel_key
GROUP BY dc.channel_name
ORDER BY total_views DESC;
```

### Example 3: Media Content Analysis

```sql
SELECT
    dc.channel_name,
    COUNT(*) FILTER (WHERE fm.has_image = true) as messages_with_images,
    COUNT(*) FILTER (WHERE fm.has_image = false) as messages_without_images,
    COUNT(*) as total_messages
FROM fct_messages fm
JOIN dim_channels dc ON fm.channel_key = dc.channel_key
GROUP BY dc.channel_name;
```

### Example 4: Time-Based Anomaly Detection

```sql
-- Daily message counts (for detecting spikes)
SELECT
    dd.full_date,
    COUNT(*) as message_count
FROM fct_messages fm
JOIN dim_dates dd ON fm.date_key = dd.date_key
WHERE dd.full_date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY dd.full_date
ORDER BY dd.full_date;
```

---

## Future Enhancements

### Possible Extensions

1. **SCD Type 2 for Channels**: If channel names change, add effective dates
2. **Message Dimension**: Separate dimension for message attributes if text analysis becomes complex
3. **Time Dimension**: Add hour/minute if time-of-day analysis is needed
4. **Content Categories**: Add dimension for message categories/topics (via NLP/classification)
5. **User Dimension**: If we track message authors/editors

### Scalability Considerations

- **Fact Table Partitioning**: Partition `fct_messages` by `date_key` for better performance
- **Indexes**: Add indexes on foreign keys and frequently queried columns
- **Materialized Views**: Pre-aggregate common queries (e.g., daily summaries)
- **Incremental Models**: Use dbt incremental models for large fact tables

---

## Conclusion

The star schema design provides:
- ✅ **Performance**: Optimized for analytical queries
- ✅ **Clarity**: Easy to understand for business users
- ✅ **Scalability**: Can grow with data volume
- ✅ **Flexibility**: Easy to extend with new dimensions/attributes
- ✅ **Quality**: Built-in data quality tests

This foundation supports fraud-style analytics (anomaly detection, pattern recognition) on medical Telegram channel data.

---

**Design Status**: ✅ Complete
**Implementation**: `models/marts/`
**Documentation**: `dbt docs generate`
**Last Updated**: 2026-01-17
