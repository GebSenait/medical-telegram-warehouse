{{
    config(
        materialized='table',
        schema='marts'
    )
}}

with yolo_detections as (
    select
        cast(message_id as bigint) as message_id,
        cast(channel_name as varchar(255)) as channel_name,
        cast(image_path as varchar(500)) as image_path,
        cast(detected_class as varchar(100)) as detected_class,
        cast(confidence_score as numeric(5, 4)) as confidence_score,
        cast(image_category as varchar(50)) as image_category,
        cast(num_detections as integer) as num_detections
    from {{ source('raw', 'yolo_detections') }}
    where message_id is not null
      and channel_name is not null
),

fct_messages as (
    select
        message_id,
        channel_key,
        date_key,
        views,
        forwards,
        has_image,
        image_path as message_image_path
    from {{ ref('fct_messages') }}
    where has_image = true
),

dim_channels as (
    select
        channel_key,
        channel_name
    from {{ ref('dim_channels') }}
)

select
    -- Primary identifiers
    yolo.message_id,
    fct.channel_key,
    fct.date_key,

    -- Detection results
    yolo.detected_class,
    yolo.confidence_score,
    yolo.image_category,
    yolo.num_detections,

    -- Engagement metrics (for analysis)
    fct.views,
    fct.forwards,

    -- Image metadata
    yolo.image_path,
    fct.has_image

from yolo_detections yolo
inner join dim_channels dc
    on yolo.channel_name = dc.channel_name
inner join fct_messages fct
    on yolo.message_id = fct.message_id
    and dc.channel_key = fct.channel_key
