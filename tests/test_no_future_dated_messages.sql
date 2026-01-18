-- Custom test: No future-dated messages should exist
-- This test returns 0 rows if valid, non-zero rows if invalid

select
    message_id,
    channel_name,
    message_date
from {{ ref('stg_telegram_messages') }}
where message_date > current_timestamp
