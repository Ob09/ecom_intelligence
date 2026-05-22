-- ============================================================
-- MART: mart_sales.sql
-- PURPOSE: Core sales fact table for business KPI reporting
-- SOURCE: int_orders_enriched + stg_payments
-- GRAIN: One row per order (aggregated from order-item grain)
-- ============================================================

with orders_enriched as (

    select * from {{ ref('int_orders_enriched') }}

),

-- We need payment_type from stg_payments because it was not
-- carried through into the intermediate model.
-- We take the most common payment type per order using max()
-- which in most cases is the only payment type used.
payments as (

    select
        order_id,
        max(payment_type) as payment_type
    from {{ ref('stg_payments') }}
    group by order_id

),

-- AGGREGATE FROM ORDER-ITEM GRAIN TO ORDER GRAIN
-- int_orders_enriched has one row per item in an order.
-- An order with 3 items has 3 rows in that model.
-- mart_sales needs one row per order, so we group by order_id
-- and aggregate the item-level columns up to order level.
order_grain as (

    select
        -- ── ORDER IDENTIFIERS ──────────────────────────────────
        order_id,
        customer_id,
        customer_unique_id,

        -- ── ORDER STATUS ───────────────────────────────────────
        order_status,

        -- ── DATES ──────────────────────────────────────────────
        -- These are order-level fields, same value on every item row.
        -- We use max() to collapse them safely during aggregation.
        purchased_at,
        estimated_delivery_at,
        delivered_at,

        -- ── FULFILMENT PERFORMANCE ─────────────────────────────
        -- delivery_days is already calculated in the intermediate model.
        -- It is the same value on every row for a given order.
        max(delivery_days) as fulfilment_days,

        -- ── ON TIME FLAG ───────────────────────────────────────
        -- Boolean: was this order delivered on or before the estimate?
        -- Same value on every row for a given order.
        max(delivered_on_time::int)::boolean as delivered_on_time,

        -- ── REVENUE ────────────────────────────────────────────
        -- total_payment is the full order payment value.
        -- It is already at order level in the intermediate model
        -- (same value repeated on each item row), so max() is safe.
        max(total_payment) as payment_value,

        -- ── ORDER SIZE ─────────────────────────────────────────
        -- item_sequence numbers items 1, 2, 3... within an order.
        -- The highest sequence number = total number of items.
        -- count() here gives us the actual item count per order.
        count(item_sequence) as item_count,

        -- ── CUSTOMER LOCATION ──────────────────────────────────
        customer_city,
        customer_state,

        -- ── TIME DIMENSIONS ────────────────────────────────────
        -- year_month gives a sortable period label like '2017-11'
        to_char(purchased_at, 'YYYY-MM') as year_month,

        extract(year from purchased_at)::int as order_year,
        extract(month from purchased_at)::int as order_month

    from orders_enriched

    -- Group by all non-aggregated columns.
    -- Every column that is NOT inside an aggregation function
    -- must appear in the GROUP BY clause. This is a SQL rule.
    group by
        order_id,
        customer_id,
        customer_unique_id,
        order_status,
        purchased_at,
        estimated_delivery_at,
        delivered_at,
        customer_city,
        customer_state

),

-- JOIN PAYMENT TYPE ONTO THE ORDER-GRAIN TABLE
final as (

    select
        o.order_id,
        o.customer_id,
        o.customer_unique_id,
        o.order_status,
        o.purchased_at,
        o.estimated_delivery_at,
        o.delivered_at,
        o.fulfilment_days,
        o.delivered_on_time,
        o.payment_value,
        p.payment_type,
        o.item_count,
        o.customer_city,
        o.customer_state,
        o.year_month,
        o.order_year,
        o.order_month

    from order_grain o

    -- Left join so orders with no payment record are still included.
    -- In clean data every order has a payment, but left join is safer.
    left join payments p on o.order_id = p.order_id

)

select * from final