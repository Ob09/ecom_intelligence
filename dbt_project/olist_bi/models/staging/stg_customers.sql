-- ============================================================
-- STAGING: stg_customers.sql
-- SOURCE: raw_customers
-- PURPOSE: Clean and rename the raw customers table
-- GRAIN: One row per customer_id (not unique customer — see note)
-- NULL HANDLING:
--   - customer_id: filtered out if null
--   - customer_unique_id: filtered out if null
--   - city, state: COALESCE replaces null with 'unknown'
--   - zip_code: cast to integer, null if missing
-- NOTE: customer_id is per-order in Olist. customer_unique_id
--       is the true unique customer identifier.
-- ============================================================

with source as (

    select * from {{ source('olist', 'raw_customers') }}

),

renamed as (

    select
        -- ── IDENTIFIERS ────────────────────────────────────────
        -- customer_id links to orders — one per order in Olist.
        -- customer_unique_id is the real unique person identifier.
        -- Both must exist for this row to be useful.
        customer_id,
        customer_unique_id,

        -- ── LOCATION ───────────────────────────────────────────
        -- Zip code is a number. We cast it to integer.
        -- NULLIF handles empty strings before casting.
        -- If zip is missing we keep it as null — better than a fake value.
        nullif(customer_zip_code_prefix::text, '')::integer as customer_zip_code,

        -- City and state power the geographic analysis module.
        -- LOWER() standardises casing — the raw data has inconsistent
        -- capitalisation e.g. 'Sao Paulo', 'sao paulo', 'SAO PAULO'.
        -- COALESCE replaces any remaining nulls with 'unknown'
        -- so geographic GROUP BY queries never silently drop rows.
        coalesce(lower(trim(customer_city)),  'unknown') as customer_city,
        coalesce(upper(trim(customer_state)), 'unknown') as customer_state

        -- TRIM() removes accidental leading/trailing spaces from strings.
        -- UPPER() on state gives consistent 2-letter codes e.g. 'SP', 'RJ'.
        -- LOWER() on city gives consistent lowercase e.g. 'sao paulo'.

    from source

),

-- ── REMOVE INVALID ROWS ────────────────────────────────────────
-- Without both IDs this row cannot be joined to orders or used
-- in RFM segmentation or any customer-level analysis.
cleaned as (

    select *
    from renamed
    where customer_id        is not null
      and customer_unique_id is not null

)

select * from cleaned