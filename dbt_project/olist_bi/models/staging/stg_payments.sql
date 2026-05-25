-- ============================================================
-- STAGING: stg_payments.sql
-- SOURCE: raw_payments (actual table name: raw_order_payments)
-- PURPOSE: Clean and rename the raw payments table
-- GRAIN: One row per payment instalment per order
--        (one order can have multiple payment rows)
-- NULL HANDLING:
--   - order_id: filtered out if null
--   - payment_value: COALESCE replaces null with 0
--   - payment_type: COALESCE replaces null with 'unknown'
--   - installments: COALESCE replaces null with 1
-- ============================================================

with source as (

    select * from {{ source('olist', 'raw_payments') }}

),

renamed as (

    select
        -- ── IDENTIFIER ─────────────────────────────────────────
        -- Links this payment to an order. Must exist.
        order_id,

        -- ── PAYMENT SEQUENCE ───────────────────────────────────
        -- When an order has multiple payment methods, each gets
        -- a sequential number: 1, 2, 3...
        -- COALESCE replaces null with 1 as a safe default.
        coalesce(payment_sequential, 1) as payment_sequential,

        -- ── PAYMENT TYPE ───────────────────────────────────────
        -- How the customer paid: credit_card, boleto, voucher, debit_card.
        -- COALESCE replaces null with 'unknown'.
        -- LOWER ensures consistent casing e.g. 'Credit_Card' → 'credit_card'
        coalesce(
            lower(trim(payment_type)),
            'unknown'
        ) as payment_type,

        -- ── INSTALLMENTS ───────────────────────────────────────
        -- How many monthly instalments the customer chose.
        -- 1 = paid in full. Higher numbers = split payments.
        -- COALESCE replaces null with 1 — assume full payment if unknown.
        coalesce(payment_installments, 1) as payment_installments,

        -- ── PAYMENT VALUE ──────────────────────────────────────
        -- The money amount for this payment row.
        -- This is the most critical column for revenue analysis.
        -- COALESCE replaces null with 0 so SUM() never returns null.
        -- ROUND to 2 decimal places for clean currency values.
        round(
            coalesce(payment_value, 0)::numeric,
            2
        ) as payment_value

    from source

),

-- ── REMOVE INVALID ROWS ────────────────────────────────────────
-- Payments with no order_id cannot be linked to any order.
-- They would corrupt revenue totals if included.
cleaned as (

    select *
    from renamed
    where order_id is not null

)

select * from cleaned