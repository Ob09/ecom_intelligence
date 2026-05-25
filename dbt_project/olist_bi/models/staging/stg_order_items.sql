-- ============================================================
-- STAGING: stg_order_items.sql
-- SOURCE: raw_order_items
-- PURPOSE: Clean and rename the raw order items table
-- GRAIN: One row per item within an order
--        (one order with 3 items = 3 rows)
-- NULL HANDLING:
--   - order_id, product_id, seller_id: filtered out if null
--   - price, freight_value: COALESCE replaces null with 0
--   - shipping_limit_date: NULLIF guards empty string before cast
-- ============================================================

with source as (

    select * from {{ source('olist', 'raw_order_items') }}

),

renamed as (

    select
        -- ── IDENTIFIERS ────────────────────────────────────────
        -- order_id: links this item to its order
        -- product_id: what was bought
        -- seller_id: who sold it
        -- All three are foreign keys needed for joins.
        order_id,
        product_id,
        seller_id,

        -- ── ITEM SEQUENCE ──────────────────────────────────────
        -- The position of this item within the order.
        -- Item 1, Item 2, Item 3 etc.
        -- Used to count items per order in the mart layer.
        coalesce(order_item_id, 1) as item_sequence,

        -- ── SHIPPING DEADLINE ──────────────────────────────────
        -- The date by which the seller must ship this item.
        -- NULLIF protects against empty string before timestamp cast.
        nullif(shipping_limit_date, '')::timestamp as shipping_limit_date,

        -- ── PRICE ──────────────────────────────────────────────
        -- The price of this individual item.
        -- COALESCE replaces null with 0 so SUM() never returns null.
        -- ROUND to 2 decimal places for clean currency values.
        round(coalesce(price, 0)::numeric,         2) as price,

        -- ── FREIGHT COST ───────────────────────────────────────
        -- The shipping cost for this item.
        -- Also needed for total order cost calculations.
        round(coalesce(freight_value, 0)::numeric, 2) as freight_cost

    from source

),

-- ── REMOVE INVALID ROWS ────────────────────────────────────────
-- An item with no order_id cannot be linked to an order.
-- An item with no product_id cannot be linked to a product.
-- An item with no seller_id cannot be linked to a seller.
-- All three are required for joins in downstream models.
cleaned as (

    select *
    from renamed
    where order_id   is not null
      and product_id is not null
      and seller_id  is not null

)

select * from cleaned