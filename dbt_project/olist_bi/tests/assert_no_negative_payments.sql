-- ============================================================
-- SINGULAR TEST: assert_no_negative_payments.sql
-- PURPOSE: Ensure no order has a negative payment value
-- HOW IT WORKS: If this query returns ANY rows, the test fails.
--               A payment value below zero makes no business sense
--               and indicates corrupt or incorrectly joined data.
-- ============================================================

select
    order_id,
    payment_value
from {{ ref('mart_sales') }}
where payment_value < 0