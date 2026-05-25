# Week 2 — Data Modelling with dbt

## What is dbt and Why We Used It

dbt (data build tool) is a transformation framework for SQL-based data pipelines. It sits between your raw database and your analytics layer and does one job extremely well: it takes raw data and turns it into clean, tested, documented, analysis-ready tables.

Before dbt existed, data analysts would write ad-hoc SQL queries directly against raw tables. Every analyst wrote their own version of the same calculation. There was no testing, no documentation, no version control, and no way to know if the numbers were right. dbt solves all of these problems.

**What dbt gives you:**
- Every transformation is a `.sql` file committed to Git — full version control
- Models are built in dependency order automatically
- Tests run automatically to validate data quality
- Documentation is generated automatically from your code
- Every model is reusable — write it once, use it everywhere

**What dbt does NOT do:**
- dbt does not move data. It does not ingest CSVs or call APIs.
- dbt only transforms data that is already in your database.
- In this project, `load_olist.py` loads the raw data. dbt transforms it.

---

## The Three-Layer Architecture

We organised all dbt models into three layers. Each layer has a specific job and a specific materialisation type.

```
raw tables (Supabase)
      ↓
staging layer     → views    → clean individual tables
      ↓
intermediate layer → views   → joined enriched table  
      ↓
marts layer       → tables   → business analytics tables
```

### Why Three Layers?

**Separation of concerns.** Each layer does exactly one thing. If a column name changes in the raw data, you fix it in one staging model and every model above it inherits the fix automatically. Without layers, you would need to hunt through dozens of queries and fix them all manually.

**Materialisation strategy.** Staging and intermediate models are views — they are saved SQL queries that run on demand. They are lightweight and cheap. Mart models are physical tables — they are pre-computed and stored. Dashboards read from mart tables which makes them instant, even with 100,000 rows.

---

## Layer 1 — Staging Models

**Location:** `models/staging/`  
**Materialisation:** Views  
**Purpose:** Clean and standardise raw data. One staging model per raw table.

### What Staging Models Do

Each staging model takes one raw table as input and produces one clean table as output. The rules are strict:

- Rename columns to readable snake_case names
- Cast all data types (text to timestamp, text to integer, etc.)
- Handle nulls — filter critical nulls, replace optional nulls with defaults
- Standardise text casing (UPPER for state codes, lower for city names)
- No joins. Staging models never join two tables together.

### The Seven Staging Models

#### stg_orders.sql
Cleans the raw orders table. The most important staging model because orders are the foundation of all analytics.

Key transformations:
- Renamed `order_purchase_timestamp` → `purchased_at`
- Renamed `order_delivered_customer_date` → `delivered_at`
- All date columns cast from text to timestamp using `::timestamp`
- `NULLIF(column, '')` applied before every timestamp cast to handle empty strings
- `COALESCE(order_status, 'unknown')` ensures status is never null
- Rows with null `order_id`, `customer_id`, or `purchased_at` are filtered out in a `cleaned` CTE

Why we filter rows here: an order with no ID or no purchase date cannot be used in any join or time-series analysis. Removing it at the source means it never contaminates any downstream model.

#### stg_customers.sql
Cleans the raw customers table. Important note about Olist's data model: `customer_id` is assigned per order — the same real person gets a new `customer_id` every time they order. `customer_unique_id` is the true unique person identifier. This distinction is critical for RFM analysis.

Key transformations:
- `LOWER(TRIM(customer_city))` standardises city names — raw data has inconsistent capitalisation
- `UPPER(TRIM(customer_state))` standardises state codes to consistent 2-letter uppercase
- `NULLIF(customer_zip_code_prefix::text, '')::integer` — zip code required cast to text before NULLIF because the column is stored as a number in Supabase, not text
- Rows with null `customer_id` or `customer_unique_id` filtered out

#### stg_products.sql
Cleans the raw products table.

Key transformations:
- `COALESCE(product_category_name, 'uncategorised')` — products without categories still appear in analysis
- All dimension columns (weight, length, height, width) use `COALESCE(column, 0)` — zero is safe for arithmetic; NULL in arithmetic returns NULL which would break calculations
- Fixed typos in raw column names: `product_name_lenght` → `product_name_length`

#### stg_sellers.sql
Cleans the raw sellers table. Mirrors the customer location handling exactly — same LOWER/UPPER/TRIM logic for city and state fields.

#### stg_payments.sql
Cleans the raw payments table. This table has one row per payment instalment per order. An order paid in 3 instalments has 3 rows here.

Key transformations:
- `ROUND(COALESCE(payment_value, 0)::numeric, 2)` — currency values always rounded to 2 decimal places; null replaced with 0 so SUM() never returns null
- `COALESCE(payment_type, 'unknown')` with `LOWER(TRIM(...))` — normalises payment type strings
- `COALESCE(payment_installments, 1)` — assumes single payment if installment count is missing

#### stg_order_items.sql
Cleans the raw order items table. One row per item within an order — an order with 3 products has 3 rows here.

Key transformations:
- `price` and `freight_value` both use `ROUND(COALESCE(column, 0)::numeric, 2)`
- `order_item_id` renamed to `item_sequence` — clearer name showing it is a position number (1, 2, 3...) within an order
- Rows missing `order_id`, `product_id`, or `seller_id` filtered out — all three are required for joins

#### stg_reviews.sql
Cleans the raw order reviews table.

Key transformations:
- `review_score::integer` — cast to integer; scores are always whole numbers (1-5)
- `COALESCE(review_comment_title, '')` and `COALESCE(review_comment_message, '')` — replace nulls with empty string so `LENGTH()` and `LOWER()` never crash on null text
- `has_comment` boolean flag — derived from whether the raw comment message was non-null and non-empty before the COALESCE
- Rows with null `order_id` or null `review_score` filtered out

---

## Layer 2 — Intermediate Model

**Location:** `models/intermediate/`  
**Materialisation:** View  
**Purpose:** Join clean staging models together into one enriched table.

### int_orders_enriched.sql

This is the central join model. It combines four staging models into one wide table that downstream marts can build from.

**Sources joined:**
- `stg_orders` — order lifecycle dates and status
- `stg_customers` — customer location details
- `stg_order_items` — product, seller, price, freight per item
- `stg_payments` — aggregated payment total per order

**Important: this model is at order-item grain.** One row per item in an order. An order with 3 items produces 3 rows. This is because we join order items which has one row per item. Mart models that need order-grain data (like mart_sales) must aggregate this model with GROUP BY.

**Payments aggregation:** Because payments has one row per instalment, we aggregate payments to order level inside a CTE before joining:
```sql
select order_id, sum(payment_value) as total_payment, count(*) as payment_count
from stg_payments
group by order_id
```
This prevents row multiplication when joining a multi-row payments table to orders.

**Calculated fields added here:**
- `delivery_days` — calculated once here so every mart inherits it without recalculating
- `delivered_on_time` — boolean flag comparing actual delivery to estimated delivery

---

## Layer 3 — Mart Models

**Location:** `models/marts/`  
**Materialisation:** Tables (physical, stored data)  
**Purpose:** Answer specific business questions. These are the tables your dashboard reads from.

### Why Marts are Tables, Not Views

Mart models are read constantly by dashboards, APIs, and analysts. If they were views, every dashboard load would re-run complex joins and aggregations across 100,000 rows. Making them physical tables means dbt computes them once (via GitHub Actions on a daily schedule) and every subsequent read is instant.

### mart_sales.sql

**Grain:** One row per order  
**Built from:** `int_orders_enriched` + `stg_payments`  
**Rows:** ~100,000

This is the core sales fact table. Every revenue KPI, every time-series chart, every fulfilment metric in your dashboard reads from this table.

Because `int_orders_enriched` is at order-item grain, `mart_sales` must aggregate it to order grain using `GROUP BY order_id`. Order-level fields that are the same across all items (like `purchased_at` and `delivered_at`) use `MAX()` to safely collapse multiple rows into one.

`payment_type` is not available in `int_orders_enriched` so we join `stg_payments` directly in this mart to get it.

Key columns produced:
- `payment_value` — total order revenue (COALESCE to 0 for orders with no payment record)
- `fulfilment_days` — delivery time in days
- `delivered_on_time` — boolean
- `item_count` — number of items in the order
- `year_month` — formatted period label e.g. '2017-11' for time-series grouping
- `order_year`, `order_month` — numeric year and month for filtering

### mart_rfm.sql

**Grain:** One row per unique customer  
**Built from:** `stg_orders`, `stg_customers`, `stg_payments`  
**Rows:** ~93,358

RFM (Recency, Frequency, Monetary) is a standard customer segmentation technique used across e-commerce. Every customer is scored on three dimensions and assigned to a named business segment.

**Reference date:** We use `MAX(purchased_at)` from the orders table as our reference "today". This is essential for historical datasets — using `CURRENT_DATE` would make all recency scores meaningless since the data is from 2016-2018.

**Scoring with NTILE(5):** `NTILE(5)` is a PostgreSQL window function that splits all customers into 5 equal-sized buckets and assigns a score 1-5. Critically, recency scoring is reversed — `ORDER BY recency_days DESC` — so customers who bought recently (low recency_days) get the highest score (5).

**The 11 customer segments:**

| Segment | Rule |
|---|---|
| Champions | R≥4, F≥4, M≥4 |
| Loyal Customers | F≥3, M≥3 |
| Potential Loyalists | R≥4, F≤2 |
| New Customers | R=5, F=1 |
| Promising | R≥3, F≤2, M≤2 |
| Needs Attention | R=3, F≥2, M≥2 |
| At Risk | R≤2, F≥3, M≥3 |
| Cannot Lose Them | R=1, F≥4, M≥4 |
| Hibernating | R≤2, F≤2, M≤2 |
| Lost | R=1 |
| Others | catch-all |

### mart_cohort.sql

**Grain:** One row per cohort month × months-since-first-purchase combination  
**Built from:** `stg_orders`, `stg_customers`  
**Rows:** 188

Cohort retention analysis groups customers by the month they first purchased (their cohort) and then tracks what percentage of them came back in each subsequent month.

Month 0 is always 100% — it is the cohort month itself. Month 1 shows what percentage returned one month later. This reveals how sticky the business is and whether retention is improving over time.

**How months are calculated:**
```sql
(extract(year from purchase_month) - extract(year from cohort_month)) * 12
+ (extract(month from purchase_month) - extract(month from cohort_month))
```
This handles year boundaries correctly — December 2017 to January 2018 is correctly calculated as 1 month, not -11.

**`FIRST_VALUE()` window function** is used to get the cohort size (month 0 customer count) for every row in a cohort without a self-join. It looks back to the first row in the partition (ordered by months_since_first_purchase) and returns its customer count.

### mart_geo.sql

**Grain:** One row per Brazilian state  
**Built from:** `mart_sales`  
**Rows:** 27 (26 states + 1 federal district)

Geographic sales breakdown by state. Powers the choropleth map on the dashboard. Note that this mart reads from `mart_sales` rather than from staging or intermediate models — this is acceptable because `mart_sales` is already a physical table and is the cleanest source for order-level data.

Key metrics per state: total orders, total customers, total revenue, average order value, average fulfilment days, percentage delivered on time.

### mart_products.sql

**Grain:** One row per product category (English name)  
**Built from:** `stg_order_items`, `stg_products`, `stg_reviews`, `stg_orders`, `raw_category_translation`  
**Rows:** ~70 categories

Category performance analysis combining sales volume, revenue, and review scores. Uses the `raw_category_translation` table to translate Portuguese category names to English.

Reviews are at order level in Olist, not item level. When we join reviews to items via `order_id`, all items in the same order receive the same review score. This is a known limitation of the Olist dataset.

---

## dbt Tests

**Location:** `models/marts/schema.yml` (generic tests), `tests/` (singular tests)

### Why We Test

Without tests, bad data silently reaches your dashboard. A corrupted join could duplicate rows and double your reported revenue. A null in a key column could cause your KPI cards to show nothing. Tests catch these problems before they reach anyone looking at the dashboard.

### Generic Tests (schema.yml)

dbt has four built-in generic tests configured in YAML:

| Test | What it checks |
|---|---|
| `unique` | No two rows have the same value in this column |
| `not_null` | No nulls allowed in this column |
| `accepted_values` | Column only contains values from a specified list |
| `relationships` | A foreign key value must exist in another table |

We applied 26 generic tests across all 5 mart models covering: uniqueness of primary keys, not-null on all critical columns, RFM scores always between 1 and 5, and order statuses only containing known valid values.

### Singular Tests (tests/)

`assert_no_negative_payments.sql` — custom SQL test that queries `mart_sales` for any row where `payment_value < 0`. If the query returns any rows, the test fails. A negative payment value makes no business sense and would indicate corrupt or incorrectly joined data.

### Test Results

All 27 tests pass against the current data:
```
PASS=27 WARN=0 ERROR=0 SKIP=0 TOTAL=27
```

One fix was required during testing: `payment_value` had 1 null row (an order with no matching payment record). Fixed by adding `COALESCE(max(total_payment), 0)` in `mart_sales.sql`.

---

## dbt Documentation

Running `dbt docs generate` reads all your model SQL files and schema.yml descriptions and compiles them into a static documentation website. Running `dbt docs serve` hosts it locally.

The documentation site includes:
- Description of every model and what it does
- Every column with its description and data type
- All tests applied to each column
- A lineage graph showing the full data flow from raw sources to mart tables

This site is hosted publicly on GitHub Pages as part of the deployment. The URL is shared in the project README so anyone can browse the full data model without needing database access.

---

## Running the Full Pipeline

All commands run from inside `dbt_project/olist_bi`:

```bash
# Build all models
dbt run

# Build one specific model
dbt run --select mart_rfm

# Build a model and everything downstream of it
dbt run --select mart_sales+

# Build everything from staging upward
dbt run --select staging+

# Run all tests
dbt test

# Run tests for one model only
dbt test --select mart_sales

# Generate and serve documentation
dbt docs generate
dbt docs serve --port 8081
```

---

## Key Design Decisions

**Why session pooler connection for Supabase?**  
Supabase's direct connection uses IPv6 which is not supported on all networks. The session pooler connection string uses IPv4 and works reliably from any machine including Windows with Anaconda.

**Why customer_unique_id instead of customer_id for RFM?**  
Olist assigns a new `customer_id` to the same real person for every order they place. Using `customer_id` for RFM would treat one customer as multiple customers and produce completely wrong segmentation. `customer_unique_id` is the stable identifier for the actual person.

**Why is the intermediate model a view and not a table?**  
`int_orders_enriched` is only ever read by mart models during the dbt build process. It is never queried by the dashboard directly. Keeping it as a view saves storage and means it is always computed fresh when marts are rebuilt, reflecting any upstream changes immediately.

**Why does mart_geo read from mart_sales instead of raw tables?**  
`mart_sales` is already the cleanest, most complete order-level table in the project. It has already handled all the grain aggregation, null handling, and joins. Reading from it in `mart_geo` avoids duplicating that logic and ensures geographic analysis is always consistent with the KPI numbers shown on the dashboard.
