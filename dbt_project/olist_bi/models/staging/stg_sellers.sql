-- ============================================================
-- STAGING: stg_sellers.sql
-- SOURCE: raw_sellers
-- PURPOSE: Clean and rename the raw sellers table
-- GRAIN: One row per seller
-- NULL HANDLING:
--   - seller_id: filtered out if null
--   - city, state: COALESCE replaces null with 'unknown'
--   - zip_code: cast to integer, null if missing
-- ============================================================

with source as (

    select * from {{ source('olist', 'raw_sellers') }}

),

renamed as (

    select
        -- ── IDENTIFIER ─────────────────────────────────────────
        -- seller_id is the primary key. Must exist.
        seller_id,

        -- ── LOCATION ───────────────────────────────────────────
        -- Same logic as stg_customers location handling.
        -- Seller location is used in geographic analysis to compare
        -- where sellers are vs where customers are.
        nullif(seller_zip_code_prefix::text, '')::integer as seller_zip_code,

        coalesce(lower(trim(seller_city)),  'unknown') as seller_city,
        coalesce(upper(trim(seller_state)), 'unknown') as seller_state

    from source

),

-- ── REMOVE INVALID ROWS ────────────────────────────────────────
-- A seller with no ID cannot be joined to order items.
cleaned as (

    select *
    from renamed
    where seller_id is not null

)

select * from cleaned