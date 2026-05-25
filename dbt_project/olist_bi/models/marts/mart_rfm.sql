-- ============================================================
-- MART: mart_rfm.sql
-- PURPOSE: RFM customer segmentation
-- GRAIN: One row per customer_unique_id
-- SOURCE: stg_orders and stg_payments
-- ============================================================

-- ── STEP 1: REFERENCE DATE ─────────────────────────────────────
-- We use the most recent order date in the dataset as "today".
-- This keeps recency scores internally consistent regardless of
-- when you run the model. If we used CURRENT_DATE, every customer
-- would look like they haven't bought in years since this is
-- historical data from 2016-2018.
with reference_date as (

    select max(purchased_at)::date as max_date
    from {{ ref('stg_orders') }}
    where order_status = 'delivered'

),

-- ── STEP 2: RAW RFM VALUES PER CUSTOMER ───────────────────────
-- One row per customer_unique_id.
-- We use customer_unique_id (not customer_id) because in Olist
-- customer_id is assigned per order — the same real person gets
-- a new customer_id for each order they place.
-- customer_unique_id is the true unique person identifier.
raw_rfm as (

    select
        c.customer_unique_id,

        -- RECENCY: how many days since their last order?
        -- Smaller number = bought more recently = better customer.
        (r.max_date - max(o.purchased_at)::date) as recency_days,

        -- FREQUENCY: how many orders did this customer place?
        -- count(distinct) avoids double counting if joins create duplicates.
        count(distinct o.order_id) as frequency,

        -- MONETARY: total money spent across all orders.
        -- We join stg_payments to get the actual payment value per order.
        sum(p.payment_value) as monetary_value

    from {{ ref('stg_orders') }} o

    -- Join customers to get customer_unique_id
    left join {{ ref('stg_customers') }} c
        on o.customer_id = c.customer_id

    -- Join payments to get revenue per order
    left join {{ ref('stg_payments') }} p
        on o.order_id = p.order_id

    -- Cross join the single-row reference_date CTE so every row
    -- can access max_date without a subquery in the SELECT clause.
    cross join reference_date r

    -- Only include completed orders in RFM.
    -- Cancelled or processing orders do not reflect real buying behaviour.
    where o.order_status = 'delivered'
      and c.customer_unique_id is not null

    group by
        c.customer_unique_id,
        r.max_date

),

-- ── STEP 3: SCORE EACH DIMENSION USING NTILE(5) ───────────────
-- NTILE(5) splits all customers into 5 equal-sized groups.
-- Group 1 = bottom 20%, Group 5 = top 20%.
--
-- RECENCY is scored in REVERSE.
-- A customer who bought 5 days ago (low recency_days) is BEST.
-- So we ORDER BY recency_days DESC — lowest days gets highest score.
--
-- FREQUENCY and MONETARY are scored NORMALLY.
-- Higher values = higher scores. ORDER BY value ASC.
rfm_scores as (

    select
        customer_unique_id,
        recency_days,
        frequency,
        monetary_value,

        -- Recency score: recent buyers score 5, old buyers score 1
        ntile(5) over (order by recency_days desc) as r_score,

        -- Frequency score: frequent buyers score 5, one-time buyers score 1
        ntile(5) over (order by frequency asc)     as f_score,

        -- Monetary score: high spenders score 5, low spenders score 1
        ntile(5) over (order by monetary_value asc) as m_score

    from raw_rfm

),

-- ── STEP 4: COMBINE SCORES AND ASSIGN SEGMENT LABELS ──────────
-- rfm_score = R + F + M combined (range: 3 to 15)
-- rfm_segment_code = string like '554' for detailed lookup
-- customer_segment = human-readable business label
final as (

    select
        customer_unique_id,
        recency_days,
        frequency,

        -- Round monetary to 2 decimal places for clean currency display
        round(monetary_value::numeric, 2) as monetary_value,

        r_score,
        f_score,
        m_score,

        -- Combined score: ranges from 3 (worst) to 15 (best)
        (r_score + f_score + m_score) as rfm_score,

        -- Three-digit code: e.g. '555' = perfect champion
        concat(r_score::text, f_score::text, m_score::text) as rfm_segment_code,

        -- ── SEGMENT LABELS ─────────────────────────────────────
        -- Rules ordered from most valuable to least valuable.
        -- A customer matches the FIRST rule they satisfy.
        -- Recency is weighted most heavily because it is the
        -- strongest predictor of future purchase behaviour.
        case
            -- Champions: bought recently, buy often, spend the most
            when r_score >= 4 and f_score >= 4 and m_score >= 4
                then 'Champions'

            -- Loyal Customers: consistent buyers with good spend
            when f_score >= 3 and m_score >= 3
                then 'Loyal Customers'

            -- Potential Loyalists: recent buyers, not yet frequent
            when r_score >= 4 and f_score <= 2
                then 'Potential Loyalists'

            -- New Customers: just arrived, only one order so far
            when r_score = 5 and f_score = 1
                then 'New Customers'

            -- Promising: recent with moderate scores across the board
            when r_score >= 3 and f_score <= 2 and m_score <= 2
                then 'Promising'

            -- Needs Attention: decent scores but starting to drift
            when r_score = 3 and f_score >= 2 and m_score >= 2
                then 'Needs Attention'

            -- At Risk: used to buy well but have gone quiet recently
            when r_score <= 2 and f_score >= 3 and m_score >= 3
                then 'At Risk'

            -- Cannot Lose Them: were your best customers, now gone quiet
            when r_score = 1 and f_score >= 4 and m_score >= 4
                then 'Cannot Lose Them'

            -- Hibernating: low scores across all three dimensions
            when r_score <= 2 and f_score <= 2 and m_score <= 2
                then 'Hibernating'

            -- Lost: very low recency, not covered by rules above
            when r_score = 1
                then 'Lost'

            -- Catch-all for any remaining combinations
            else 'Others'
        end as customer_segment

    from rfm_scores

)

select * from final