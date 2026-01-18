{{
    config(
        materialized='table',
        schema='marts'
    )
}}

with stg_messages as (
    select *
    from {{ ref('stg_telegram_messages') }}
),

dim_channels as (
    select *
    from {{ ref('dim_channels') }}
),

dim_dates as (
    select *
    from {{ ref('dim_dates') }}
),

messages_with_keys as (
    select
        stg.message_id,
        dc.channel_key,
        dd.date_key,
        stg.message_date as message_timestamp,
        stg.message_text,
        stg.message_length,
        stg.views,
        stg.forwards,
        stg.has_media,
        stg.has_image,
        stg.image_path
    from stg_messages stg
    inner join dim_channels dc
        on stg.channel_name = dc.channel_name
    inner join dim_dates dd
        on stg.message_date::date = dd.full_date
)

select *
from messages_with_keys
