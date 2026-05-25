-- ============================================================
-- STAGING: stg_reviews.sql
-- SOURCE: raw_reviews (actual table name: raw_order_reviews)
-- PURPOSE: Clean and rename the raw reviews table
-- GRAIN: One row per review
-- NULL HANDLING:
--   - order_id: filtered out if null
--   - review_score: filtered out if null (useless without a score)
--   - comment columns: COALESCE replaces null with empty string
--   - dates: NULLIF guards empty string before timestamp cast
-- ============================================================

with source as (

    select * from {{ source('olist', 'raw_reviews') }}

),

renamed as (

    select
        -- ── IDENTIFIERS ────────────────────────────────────────
        -- review_id uniquely identifies this review.
        -- order_id links the review back to the order it belongs to.
        review_id,
        order_id,

        -- ── REVIEW SCORE ───────────────────────────────────────
        -- The star rating: 1 (worst) to 5 (best).
        -- This is the most important column in this table.
        -- We cast to integer — scores are whole numbers only.
        -- Null scores are filtered out in the cleaned CTE below
        -- because a review without a score has no analytical value.
        review_score::integer as review_score,

        -- ── REVIEW TEXT ────────────────────────────────────────
        -- The written title and body of the customer's review.
        -- These are frequently null — many customers only leave
        -- a star rating and write nothing.
        -- COALESCE replaces null with '' (empty string) so string
        -- functions like LENGTH() and LOWER() never crash on null.
        coalesce(review_comment_title,   '') as review_title,
        coalesce(review_comment_message, '') as review_body,

        -- ── HAS COMMENT FLAG ───────────────────────────────────
        -- A simple boolean: did this customer write any text at all?
        -- Useful for filtering to text reviews in the dashboard.
        -- We check the raw column BEFORE the COALESCE above,
        -- because after COALESCE it is never null.
        (review_comment_message is not null
         and trim(review_comment_message) != '') as has_comment,

        -- ── DATES ──────────────────────────────────────────────
        -- When the review request was sent to the customer.
        nullif(review_creation_date, '')::timestamp    as review_created_at,

        -- When the customer actually submitted their review.
        nullif(review_answer_timestamp, '')::timestamp as review_answered_at

    from source

),

-- ── REMOVE INVALID ROWS ────────────────────────────────────────
-- Reviews with no order_id cannot be linked to an order.
-- Reviews with no score have no analytical value at all.
cleaned as (

    select *
    from renamed
    where order_id     is not null
      and review_score is not null

)

select * from cleaned