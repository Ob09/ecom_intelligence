# ============================================================
# Great Expectations — Validation Script
# PURPOSE: Run data quality checks against all mart tables
# RUN FROM: project root (e_com_analyser)
# ============================================================

import great_expectations as gx
from dotenv import load_dotenv
import os

load_dotenv()
DB_URL = os.getenv("DATABASE_URL")

print("Loading context and connecting...")
context = gx.get_context()

# ── CONNECT DATASOURCE ─────────────────────────────────────────
datasource = context.sources.add_or_update_sql(
    name="supabase_postgres",
    connection_string=DB_URL,
)

# ── HELPER FUNCTION ────────────────────────────────────────────
# Runs a set of expectations against one table and prints results
def validate_table(schema, table, expectations_fn):
    print(f"\nValidating {schema}.{table}...")

    asset = datasource.add_table_asset(
        name=f"{schema}__{table}",
        schema_name=schema,
        table_name=table,
    )

    batch_request = asset.build_batch_request()
    suite_name = f"{table}_suite"

    # Create or update expectation suite
    try:
        suite = context.add_expectation_suite(suite_name)
    except Exception:
        suite = context.get_expectation_suite(suite_name)

    validator = context.get_validator(
        batch_request=batch_request,
        expectation_suite=suite,
    )

    # Run the expectations specific to this table
    expectations_fn(validator)

    results = validator.validate()

    passed = sum(1 for r in results.results if r.success)
    total  = len(results.results)
    status = "PASS" if results.success else "FAIL"

    print(f"  Status : {status}")
    print(f"  Results: {passed}/{total} expectations passed")

    if not results.success:
        for r in results.results:
            if not r.success:
                print(f"  FAILED : {r.expectation_config.expectation_type} "
                      f"on column '{r.expectation_config.kwargs.get('column', 'N/A')}'")
                print(f"           {r.result}")

    return results.success


# ── MART SALES EXPECTATIONS ────────────────────────────────────
def expect_mart_sales(v):
    # Table must have at least 90,000 rows
    v.expect_table_row_count_to_be_between(min_value=90000)

    # Critical columns must never be null
    for col in ["order_id", "customer_id", "order_status",
                "payment_value", "year_month"]:
        v.expect_column_values_to_not_be_null(column=col)

    # order_id must be unique — no duplicate orders
    v.expect_column_values_to_be_unique(column="order_id")

    # Payment value must always be zero or positive
    v.expect_column_values_to_be_between(
        column="payment_value", min_value=0
    )

    # order_status must only contain known valid values
    v.expect_column_values_to_be_in_set(
        column="order_status",
        value_set=["delivered", "shipped", "canceled", "unavailable",
                   "processing", "invoiced", "created", "approved", "unknown"]
    )

    # Fulfilment days should be realistic: 0 to 180 days
    v.expect_column_values_to_be_between(
        column="fulfilment_days", min_value=0, max_value=180,
        mostly=0.99  # 99% of rows — allows for rare edge cases
    )


# ── MART RFM EXPECTATIONS ──────────────────────────────────────
def expect_mart_rfm(v):
    # Must have at least 90,000 unique customers
    v.expect_table_row_count_to_be_between(min_value=90000)

    # customer_unique_id must be unique — one row per customer
    v.expect_column_values_to_be_unique(column="customer_unique_id")
    v.expect_column_values_to_not_be_null(column="customer_unique_id")

    # All three RFM scores must be between 1 and 5
    for col in ["r_score", "f_score", "m_score"]:
        v.expect_column_values_to_be_between(
            column=col, min_value=1, max_value=5
        )

    # Monetary value must be positive
    v.expect_column_values_to_be_between(
        column="monetary_value", min_value=0
    )

    # Segment must be a known value
    v.expect_column_values_to_be_in_set(
        column="customer_segment",
        value_set=["Champions", "Loyal Customers", "Potential Loyalists",
                   "New Customers", "Promising", "Needs Attention",
                   "At Risk", "Cannot Lose Them", "Hibernating",
                   "Lost", "Others"]
    )


# ── MART COHORT EXPECTATIONS ───────────────────────────────────
def expect_mart_cohort(v):
    v.expect_column_values_to_not_be_null(column="cohort_month")
    v.expect_column_values_to_not_be_null(column="retention_rate")

    # Retention rate must be between 0 and 100 percent
    v.expect_column_values_to_be_between(
        column="retention_rate", min_value=0, max_value=100
    )

    # Month 0 is always the cohort month — must exist
    v.expect_column_values_to_be_between(
        column="months_since_first_purchase", min_value=0, max_value=12
    )


# ── MART GEO EXPECTATIONS ──────────────────────────────────────
def expect_mart_geo(v):
    # Brazil has 27 states — table must have exactly 27 rows
    v.expect_table_row_count_to_equal(value=27)

    v.expect_column_values_to_not_be_null(column="customer_state")
    v.expect_column_values_to_be_unique(column="customer_state")

    # Revenue must be positive for every state
    v.expect_column_values_to_be_between(
        column="total_revenue", min_value=0
    )


# ── MART PRODUCTS EXPECTATIONS ─────────────────────────────────
def expect_mart_products(v):
    v.expect_column_values_to_not_be_null(column="category_name")
    v.expect_column_values_to_be_unique(column="category_name")

    # Review scores must be between 1 and 5
    v.expect_column_values_to_be_between(
        column="avg_review_score", min_value=1, max_value=5
    )

    # 5 star percentage must be between 0 and 100
    v.expect_column_values_to_be_between(
        column="pct_five_star", min_value=0, max_value=100
    )


# ── RUN ALL VALIDATIONS ────────────────────────────────────────
print("\n" + "="*55)
print("  GREAT EXPECTATIONS — DATA QUALITY VALIDATION")
print("="*55)

results = {
    "mart_sales"    : validate_table("public_marts", "mart_sales",    expect_mart_sales),
    "mart_rfm"      : validate_table("public_marts", "mart_rfm",      expect_mart_rfm),
    "mart_cohort"   : validate_table("public_marts", "mart_cohort",   expect_mart_cohort),
    "mart_geo"      : validate_table("public_marts", "mart_geo",      expect_mart_geo),
    "mart_products" : validate_table("public_marts", "mart_products", expect_mart_products),
}

# ── SUMMARY ────────────────────────────────────────────────────
print("\n" + "="*55)
print("  SUMMARY")
print("="*55)
all_passed = all(results.values())
for table, passed in results.items():
    status = "PASS" if passed else "FAIL"
    print(f"  {status}  {table}")

print("="*55)
print(f"  Overall: {'ALL PASSED' if all_passed else 'SOME FAILURES — check above'}")
print("="*55 + "\n")