-- ============================================================
-- MART: mart_geo.sql
-- PURPOSE: Geographic sales analysis by Brazilian state
-- GRAIN: One row per customer state
-- SOURCE: mart_sales
-- ============================================================

with sales as (

    -- We read from mart_sales because it is already at order grain
    -- with all the fields we need. No need to go back to raw tables.
    select * from {{ ref('mart_sales') }}

),

final as (

    select
        -- ── LOCATION ───────────────────────────────────────────
        customer_state,

        -- ── VOLUME METRICS ─────────────────────────────────────
        -- How many orders came from this state
        count(order_id)                              as total_orders,

        -- How many unique customers are in this state
        count(distinct customer_unique_id)           as total_customers,

        -- ── REVENUE METRICS ────────────────────────────────────
        -- Total revenue from this state
        round(sum(payment_value)::numeric, 2)        as total_revenue,

        -- Average order value for this state
        -- This shows us whether customers in some states
        -- tend to spend more per order than others
        round(avg(payment_value)::numeric, 2)        as avg_order_value,

        -- ── FULFILMENT METRICS ─────────────────────────────────
        -- Average delivery time in days for this state
        -- States far from São Paulo (where most sellers are)
        -- tend to have much longer delivery times
        round(avg(fulfilment_days)::numeric, 1)      as avg_fulfilment_days,

        -- Percentage of orders delivered on time in this state
        -- Useful for identifying geographic fulfilment problems
        round(
            sum(case when delivered_on_time then 1 else 0 end)::numeric
            / nullif(count(order_id), 0) * 100,
            1
        )                                            as pct_delivered_on_time,

        -- ── ORDER SIZE ─────────────────────────────────────────
        -- Average number of items per order in this state
        round(avg(item_count)::numeric, 2)           as avg_items_per_order,

        -- ── FILTER ─────────────────────────────────────────────
        -- We only include delivered orders for revenue analysis.
        -- Cancelled orders would distort revenue and fulfilment numbers.
        count(case when order_status = 'delivered'
                   then 1 end)                       as delivered_orders

    from sales

    -- Remove rows with no state — cannot be placed on a map
    where customer_state is not null
      and customer_state != 'unknown'

    group by customer_state

)

select * from final
order by total_revenue desc