-- Custom test: No messages should have negative view counts
-- This test returns 0 rows if valid, non-zero rows if invalid

select
    message_id,
    channel_name,
    views
from {{ ref('stg_telegram_messages') }}
where views < 0
