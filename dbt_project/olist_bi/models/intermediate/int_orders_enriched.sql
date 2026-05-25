-- ============================================================
-- INTERMEDIATE: int_orders_enriched.sql
-- PURPOSE: Join orders, customers, order items and payments
--          into one enriched table for the mart layer
-- SOURCE: stg_orders, stg_customers, stg_order_items, stg_payments
-- GRAIN: One row per order item
--        (an order with 3 items = 3 rows)
-- ============================================================

with orders as (

    select * from {{ ref('stg_orders') }}

),

customers as (

    select * from {{ ref('stg_customers') }}

),

order_items as (

    select * from {{ ref('stg_order_items') }}

),

payments as (

    -- Aggregate payments to order level.
    -- One order can have multiple payment rows (e.g. voucher + credit card).
    -- We sum them into one total payment value per order.
    select
        order_id,
        sum(payment_value) as total_payment,
        count(*)           as payment_count
    from {{ ref('stg_payments') }}
    group by order_id

),

enriched as (

    select
        -- ── ORDER DETAILS ──────────────────────────────────────
        o.order_id,
        o.order_status,
        o.purchased_at,
        o.approved_at,
        o.shipped_at,
        o.delivered_at,
        o.estimated_delivery_at,

        -- ── CUSTOMER DETAILS ───────────────────────────────────
        -- Column names match exactly what stg_customers outputs
        -- after our cleaning and renaming in the staging layer.
        c.customer_id,
        c.customer_unique_id,
        c.customer_city,
        c.customer_state,
        c.customer_zip_code,

        -- ── ITEM DETAILS ───────────────────────────────────────
        -- Column names match exactly what stg_order_items outputs.
        i.product_id,
        i.seller_id,
        i.price,
        i.freight_cost,
        i.item_sequence,

        -- ── PAYMENT DETAILS ────────────────────────────────────
        p.total_payment,
        p.payment_count,

        -- ── CALCULATED FIELDS ──────────────────────────────────
        -- Delivery days: how long from purchase to delivery.
        -- date_part('day', ...) extracts the day component from
        -- the interval between two timestamps.
        -- Returns null if delivered_at is null (undelivered orders).
        date_part('day',
            o.delivered_at - o.purchased_at
        ) as delivery_days,

        -- On time flag: was the order delivered by the promised date?
        -- Returns false if delivered_at is null (not yet delivered).
        case
            when o.delivered_at is null            then false
            when o.delivered_at <= o.estimated_delivery_at then true
            else false
        end as delivered_on_time

    from orders o

    left join customers c
        on o.customer_id = c.customer_id

    left join order_items i
        on o.order_id = i.order_id

    left join payments p
        on o.order_id = p.order_id

)

select * from enriched