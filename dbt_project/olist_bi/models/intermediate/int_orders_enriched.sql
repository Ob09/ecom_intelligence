-- int_orders_enriched.sql
-- Joins orders, customers, order items and payments together
-- Creates one rich table with everything needed for analytics
-- This model is queried by mart models -- never by the dashboard directly

with orders as (

    -- Pull from staging, not raw tables
    select * from {{ ref('stg_orders') }}

),

customers as (

    select * from {{ ref('stg_customers') }}

),

order_items as (

    select * from {{ ref('stg_order_items') }}

),

payments as (

    -- Aggregate payments to order level
    -- One order can have multiple payment rows
    -- We sum them into one total payment per order
    select
        order_id,
        sum(payment_amount)  as total_payment,
        count(*)             as payment_count
    from {{ ref('stg_payments') }}
    group by order_id

),

enriched as (

    select
        -- Order details
        o.order_id,
        o.order_status,
        o.purchased_at,
        o.approved_at,
        o.shipped_at,
        o.delivered_at,
        o.estimated_delivery_at,

        -- Customer details
        c.customer_id,
        c.customer_unique_id,
        c.city                    as customer_city,
        c.state                   as customer_state,
        c.zip_code                as customer_zip_code,

        -- Item details
        i.product_id,
        i.seller_id,
        i.price,
        i.freight_cost,
        i.item_sequence,

        -- Payment details
        p.total_payment,
        p.payment_count,

        -- Calculated fields
        -- How many days did delivery take?
        -- We calculate this here once so every mart can use it
        date_part('day',
            o.delivered_at - o.purchased_at
        )                         as delivery_days,

        -- Was the order delivered on time?
        case
            when o.delivered_at <= o.estimated_delivery_at
            then true
            else false
        end                       as delivered_on_time

    from orders o

    -- Join customers on customer_id
    left join customers c
        on o.customer_id = c.customer_id

    -- Join order items on order_id
    left join order_items i
        on o.order_id = i.order_id

    -- Join payments on order_id
    left join payments p
        on o.order_id = p.order_id

)

select * from enriched