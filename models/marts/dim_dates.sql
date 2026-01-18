{{
    config(
        materialized='table',
        schema='marts'
    )
}}

with date_spine as (
    select
        generate_series(
            '2020-01-01'::date,
            '2030-12-31'::date,
            '1 day'::interval
        )::date as date_day
),

enriched_dates as (
    select
        date_day as full_date,
        extract(year from date_day) as year,
        extract(quarter from date_day) as quarter,
        extract(month from date_day) as month,
        extract(week from date_day) as week,
        extract(day from date_day) as day_of_month,
        extract(dow from date_day) as day_of_week,
        to_char(date_day, 'Day') as day_name,
        case
            when extract(dow from date_day) in (0, 6) then true
            else false
        end as is_weekend
    from date_spine
)

select
    cast(to_char(full_date, 'YYYYMMDD') as integer) as date_key,
    full_date,
    cast(year as integer) as year,
    cast(quarter as integer) as quarter,
    cast(month as integer) as month,
    cast(week as integer) as week,
    cast(day_of_month as integer) as day_of_month,
    -- PostgreSQL DOW: 0=Sunday, 6=Saturday. Convert to ISO: 1=Monday, 7=Sunday
    case
        when day_of_week = 0 then 7
        else cast(day_of_week as integer)
    end as day_of_week,
    trim(day_name) as day_name,
    is_weekend
from enriched_dates
