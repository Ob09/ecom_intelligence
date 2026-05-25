-- ============================================================
-- STAGING: stg_products.sql
-- SOURCE: raw_products
-- PURPOSE: Clean and rename the raw products table
-- GRAIN: One row per product
-- NULL HANDLING:
--   - product_id: filtered out if null
--   - category_name: COALESCE replaces null with 'uncategorised'
--   - numeric dimensions: COALESCE replaces null with 0
--     (unknown size is treated as zero for aggregation safety)
-- ============================================================

with source as (

    select * from {{ source('olist', 'raw_products') }}

),

renamed as (

    select
        -- ── IDENTIFIER ─────────────────────────────────────────
        -- product_id is the primary key. Must exist.
        product_id,

        -- ── CATEGORY ───────────────────────────────────────────
        -- Portuguese category name from the raw data.
        -- We keep it as-is here — translation to English happens
        -- in the intermediate layer using the categories table.
        -- COALESCE replaces null with 'uncategorised' so category
        -- GROUP BY reports never silently drop uncategorised products.
        coalesce(
            lower(trim(product_category_name)),
            'uncategorised'
        ) as product_category_name,

        -- ── TEXT LENGTH METRICS ────────────────────────────────
        -- These measure how much content the product listing has.
        -- Useful for analysing whether description length affects reviews.
        -- COALESCE replaces null with 0 — no description = length of 0.
        coalesce(product_name_lenght, 0)        as product_name_length,
        coalesce(product_description_lenght, 0) as product_description_length,
        coalesce(product_photos_qty, 0)         as product_photos_qty,

        -- ── PHYSICAL DIMENSIONS ────────────────────────────────
        -- Weight and dimensions affect freight cost calculations.
        -- COALESCE replaces null with 0.
        -- Note: 0 is used as a safe default because these are used
        -- in arithmetic. NULL in arithmetic returns NULL which would
        -- break any formula that uses these columns.
        coalesce(product_weight_g,  0) as product_weight_g,
        coalesce(product_length_cm, 0) as product_length_cm,
        coalesce(product_height_cm, 0) as product_height_cm,
        coalesce(product_width_cm,  0) as product_width_cm

    from source

),

-- ── REMOVE INVALID ROWS ────────────────────────────────────────
-- A product with no ID cannot be joined to order items.
cleaned as (

    select *
    from renamed
    where product_id is not null

)

select * from cleaned