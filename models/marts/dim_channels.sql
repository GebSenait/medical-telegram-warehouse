{{
    config(
        materialized='table',
        schema='marts'
    )
}}

with stg_messages as (
    select
        channel_name,
        message_date
    from {{ ref('stg_telegram_messages') }}
),

channel_stats as (
    select
        channel_name,
        min(message_date::date) as first_message_date,
        max(message_date::date) as last_message_date,
        count(*) as total_messages
    from stg_messages
    group by channel_name
)

select
    {{ surrogate_key(['channel_name']) }} as channel_key,
    channel_name,
    first_message_date,
    last_message_date,
    total_messages
from channel_stats
