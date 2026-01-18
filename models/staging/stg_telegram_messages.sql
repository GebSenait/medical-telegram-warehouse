{{
    config(
        materialized='view',
        schema='staging'
    )
}}

with raw_messages as (
    select
        message_id,
        channel_name,
        message_date,
        message_text,
        views,
        forwards,
        has_media,
        image_path,
        loaded_at
    from {{ source('raw', 'telegram_messages') }}
    where message_id is not null
      and channel_name is not null
      and message_date is not null
)

select
    -- Primary keys and identifiers
    cast(message_id as bigint) as message_id,
    cast(channel_name as varchar(255)) as channel_name,

    -- Timestamps
    cast(message_date as timestamp) as message_date,
    cast(loaded_at as timestamp) as loaded_at,

    -- Text content
    cast(coalesce(message_text, '') as text) as message_text,

    -- Metrics (cast and handle nulls)
    cast(coalesce(views, 0) as integer) as views,
    cast(coalesce(forwards, 0) as integer) as forwards,

    -- Boolean flags
    cast(coalesce(has_media, false) as boolean) as has_media,

    -- Image path
    cast(image_path as varchar(500)) as image_path,

    -- Derived fields
    length(coalesce(message_text, '')) as message_length,
    case
        when image_path is not null and trim(image_path) != '' then true
        else false
    end as has_image

from raw_messages
