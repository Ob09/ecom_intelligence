-- ============================================================
-- STAGING: stg_orders.sql
-- SOURCE: raw_orders
-- PURPOSE: Clean, rename, and type-cast the raw orders table
-- GRAIN: One row per order
-- NULL HANDLING:
--   - order_id, customer_id, purchased_at: filtered out if null
--   - date columns: NULLIF guards against empty strings
--   - order_status: COALESCE replaces null with 'unknown'
-- ============================================================

with source as (

    select * from {{ source('olist', 'raw_orders') }}

),

renamed as (

    select
        -- ── IDENTIFIERS ────────────────────────────────────────
        -- Primary and foreign keys. Must never be null.
        -- Rows missing these cannot be joined to anything useful.
        order_id,
        customer_id,

        -- ── ORDER STATUS ───────────────────────────────────────
        -- Every order must have a status.
        -- COALESCE replaces any unexpected null with 'unknown'
        -- so GROUP BY and filters never break in downstream models.
        coalesce(order_status, 'unknown') as order_status,

        -- ── TIMESTAMPS ─────────────────────────────────────────
        -- NULLIF(column, '') converts empty strings to NULL.
        -- This prevents a crash when PostgreSQL tries to cast
        -- an empty string '' to a timestamp.
        -- After NULLIF, casting NULL::timestamp returns NULL safely.
        -- Null dates are valid: cancelled orders never get delivered.

        -- When the customer placed the order — should always exist
        nullif(order_purchase_timestamp, '')::timestamp      as purchased_at,

        -- When payment was confirmed — null for immediately cancelled orders
        nullif(order_approved_at, '')::timestamp             as approved_at,

        -- When the carrier collected the parcel — null if never shipped
        nullif(order_delivered_carrier_date, '')::timestamp  as shipped_at,

        -- When the customer received the parcel — null if not yet delivered
        nullif(order_delivered_customer_date, '')::timestamp as delivered_at,

        -- The delivery date promised to the customer
        nullif(order_estimated_delivery_date, '')::timestamp as estimated_delivery_at

    from source

),

-- ── REMOVE INVALID ROWS ────────────────────────────────────────
-- Rows missing order_id or customer_id cannot be used in any join.
-- Rows missing purchased_at have no time dimension — useless for analytics.
-- Removing them here keeps every downstream model clean automatically.
cleaned as (

    select *
    from renamed
    where order_id     is not null
      and customer_id  is not null
      and purchased_at is not null

)

select * from cleaned