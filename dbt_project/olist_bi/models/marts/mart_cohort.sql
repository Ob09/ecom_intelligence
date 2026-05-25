-- ============================================================
-- MART: mart_cohort.sql
-- PURPOSE: Monthly cohort retention analysis
-- GRAIN: One row per cohort-month combination
-- SOURCE: stg_orders and stg_customers
-- ============================================================

-- ── STEP 1: FIND EACH CUSTOMER'S FIRST PURCHASE MONTH ─────────
-- We need to know which cohort each customer belongs to.
-- A customer's cohort = the month they placed their very first order.
-- We use customer_unique_id because that is the true unique person.
with first_purchase as (

    select
        c.customer_unique_id,

        -- DATE_TRUNC('month', ...) rounds a date down to the 1st of that month.
        -- e.g. 2017-11-15 becomes 2017-11-01.
        -- This groups all purchases in the same month together.
        date_trunc('month', min(o.purchased_at))::date as cohort_month

    from {{ ref('stg_orders') }} o

    left join {{ ref('stg_customers') }} c
        on o.customer_id = c.customer_id

    -- Only count delivered orders as real purchases
    where o.order_status = 'delivered'
      and c.customer_unique_id is not null

    -- min(purchased_at) gives us the earliest order per customer
    group by c.customer_unique_id

),

-- ── STEP 2: GET ALL PURCHASES PER CUSTOMER ────────────────────
-- Now we get every single purchase each customer ever made.
-- We will compare these against their cohort month to calculate
-- how many months after joining they made each purchase.
all_purchases as (

    select
        c.customer_unique_id,
        date_trunc('month', o.purchased_at)::date as purchase_month

    from {{ ref('stg_orders') }} o

    left join {{ ref('stg_customers') }} c
        on o.customer_id = c.customer_id

    where o.order_status = 'delivered'
      and c.customer_unique_id is not null

    -- distinct removes duplicates: if a customer bought twice in
    -- the same month we still only count them once for retention.
    group by
        c.customer_unique_id,
        date_trunc('month', o.purchased_at)::date

),

-- ── STEP 3: CALCULATE MONTHS SINCE FIRST PURCHASE ─────────────
-- Join every purchase back to the customer's cohort month.
-- Then calculate how many months after joining each purchase was.
-- Month 0 = the cohort month itself (first purchase).
-- Month 1 = one month after joining. Month 2 = two months after. Etc.
cohort_activity as (

    select
        f.cohort_month,
        a.customer_unique_id,

        -- EXTRACT months between purchase and cohort start.
        -- We calculate year difference * 12 + month difference
        -- to get the total number of months elapsed.
        -- This handles purchases that span across years correctly.
        (
            (extract(year  from a.purchase_month) -
             extract(year  from f.cohort_month)) * 12
            +
            (extract(month from a.purchase_month) -
             extract(month from f.cohort_month))
        )::integer as months_since_first_purchase

    from all_purchases a

    -- Join each purchase to that customer's cohort information
    left join first_purchase f
        on a.customer_unique_id = f.customer_unique_id

),

-- ── STEP 4: COUNT COHORT SIZE AND RETAINED CUSTOMERS ──────────
-- Group by cohort month and months_since_first_purchase.
-- Count how many unique customers appear in each cell.
-- Divide by cohort size to get retention percentage.
cohort_counts as (

    select
        cohort_month,
        months_since_first_purchase,

        -- How many customers from this cohort bought in this month
        count(distinct customer_unique_id) as retained_customers

    from cohort_activity

    -- Only include months 0 through 12 (first year of retention)
    where months_since_first_purchase between 0 and 12

    group by
        cohort_month,
        months_since_first_purchase

),

-- ── STEP 5: ADD COHORT SIZE AND RETENTION RATE ────────────────
-- Cohort size = number of customers at month 0 (their first purchase).
-- Retention rate = retained customers / cohort size * 100.
final as (

    select
        c.cohort_month,
        c.months_since_first_purchase,
        c.retained_customers,

        -- Cohort size: how many customers were in this cohort originally.
        -- We get this by looking at month 0 for each cohort.
        -- first_value() is a window function that looks at the first row
        -- in the partition (month 0) and returns its customer count.
        first_value(c.retained_customers) over (
            partition by c.cohort_month
            order by c.months_since_first_purchase
        ) as cohort_size,

        -- Retention rate as a percentage rounded to 1 decimal place.
        -- We cast to numeric before dividing to avoid integer division.
        round(
            c.retained_customers::numeric /
            nullif(
                first_value(c.retained_customers) over (
                    partition by c.cohort_month
                    order by c.months_since_first_purchase
                ),
                0
            ) * 100,
            1
        ) as retention_rate,

        -- A readable label for the cohort e.g. '2017-11'
        to_char(c.cohort_month, 'YYYY-MM') as cohort_label

    from cohort_counts c

)

select * from final
order by cohort_month, months_since_first_purchase