# E-commerce BI Platform — Complete Analytics Documentation
## Weeks 1 through 4 — Everything Explained Simply

---

# PART 1 — WHAT WE BUILT AND WHY

## The Business Problem

Olist is a Brazilian e-commerce marketplace. They have 100,000 real orders from real customers
spanning 2016 to 2018. The raw data sits in 9 separate CSV files. On its own, this data is
almost useless for making business decisions because:

- It is spread across 9 different tables with messy column names
- Dates are stored as text strings, not actual dates
- Some columns have missing values
- There is no way to ask "who are my best customers?" without writing complex SQL every time
- There are no charts, no KPIs, no trends

**What we built:** A full business intelligence platform that takes this messy raw data and
transforms it into clean, tested, documented analytics tables and charts that answer real
business questions automatically every day.

---

# PART 2 — THE DATABASE (SUPABASE)

## What is a Database?

A database is a structured place to store data so it can be queried quickly. Think of it like
a collection of Excel sheets stored on a server that anyone can access at any time.

We use **Supabase** which gives us a free PostgreSQL database hosted in West EU Ireland.
PostgreSQL is the actual database software. Supabase is the hosting platform that runs it
for us in the cloud.

## Where the Raw Data Lives

We uploaded all 9 Olist CSV files into Supabase using a Python script called `load_olist.py`.
After that, the raw data lives permanently in these 9 tables:

| Table | What it contains | Rows |
|---|---|---|
| raw_orders | Every order placed on Olist | ~100,000 |
| raw_customers | Every customer who placed an order | ~100,000 |
| raw_products | Every product listed on Olist | ~33,000 |
| raw_sellers | Every seller on the platform | ~3,000 |
| raw_payments | Every payment made for every order | ~100,000 |
| raw_order_items | Every item within every order | ~112,000 |
| raw_reviews | Every review left by customers | ~100,000 |
| raw_geolocation | Brazilian zip codes with coordinates | ~1,000,000 |
| raw_category_translation | Portuguese to English category names | ~71 |

These tables never change. They are the permanent source of truth.

---

# PART 3 — DATA TRANSFORMATION WITH dbt

## What is dbt?

dbt (data build tool) is a tool that lets you write SQL transformations as organised, tested,
documented files. Instead of writing ad-hoc SQL queries every time you need something,
you write your transformations once, dbt runs them in the correct order, and the results
are stored as clean tables ready for analysis.

Think of it like a factory production line:
- Raw materials go in one end (raw tables)
- Each machine does one specific job (each SQL model)
- Finished products come out the other end (mart tables)
- Quality checks happen at every stage (tests)

## The Three-Layer Architecture

We organised all transformations into three layers:

### Layer 1 — Staging (Views)

**Job:** Clean and standardise each raw table individually.
**Rule:** One staging model per raw table. No joins allowed here.
**Stored as:** Views (saved SQL queries, no data physically stored)

A view is like a window into the raw data. Every time something reads from a staging view,
PostgreSQL runs the cleaning SQL fresh. Nothing is stored — the view just remembers the
instructions.

### Layer 2 — Intermediate (View)

**Job:** Join cleaned staging tables together into one enriched table.
**Rule:** No aggregation here. Just joining.
**Stored as:** View

### Layer 3 — Marts (Tables)

**Job:** Answer specific business questions. Pre-computed results.
**Rule:** One mart per business question.
**Stored as:** Physical tables (data is actually stored, reads are instant)

---

## The Cleaning We Did in Staging

### Why Clean at All?

Raw data from the real world is always messy:
- Dates stored as text: "2017-10-02 10:56:33" needs to become an actual timestamp
- Inconsistent casing: "Sao Paulo", "SAO PAULO", "sao paulo" all mean the same city
- Empty strings instead of nulls: "" and NULL both mean "no value" but cause different errors
- Missing values in important columns like order_id that make rows useless

If we do not clean this data, all our calculations will produce wrong results or crash.

### What NULLIF Does

```
NULLIF(column, '') 
```

This says: "if this value is an empty string, return NULL instead."

Why do we need this? Because in PostgreSQL you cannot cast an empty string to a timestamp.
If you try `''::timestamp` it crashes. But `NULL::timestamp` safely returns NULL.

Example:
- Raw value: '' (empty string)
- After NULLIF: NULL
- After ::timestamp cast: NULL (safe, no crash)

### What COALESCE Does

```
COALESCE(column, 'unknown')
```

This says: "if this value is NULL, return 'unknown' instead."

Why do we need this? Because NULL values in GROUP BY operations are silently dropped.
If a customer has no city recorded (NULL), they disappear from geographic reports.
By replacing NULL with 'unknown' they stay in the data and appear in a group called 'unknown'.

### What TRIM and LOWER/UPPER Do

```
LOWER(TRIM(customer_city))
UPPER(TRIM(customer_state))
```

TRIM removes spaces from the start and end of a string.
"  Sao Paulo  " becomes "Sao Paulo"

LOWER converts all letters to lowercase.
"Sao Paulo" becomes "sao paulo"

UPPER converts all letters to uppercase.
"sp" becomes "SP"

Why: The raw data has inconsistent casing. "Sao Paulo", "SAO PAULO", "sao paulo" are
treated as three different cities by SQL. After standardising, they are all "sao paulo"
and correctly grouped together.

### Null Filtering

Some rows are completely useless and must be removed:

```sql
WHERE order_id IS NOT NULL
  AND customer_id IS NOT NULL
  AND purchased_at IS NOT NULL
```

An order with no order_id cannot be joined to anything.
An order with no purchase date has no time dimension — useless for any trend analysis.
Removing them here means they never appear in any downstream model.

---

## The Five Mart Models

### Mart 1 — mart_sales (One Row Per Order)

This is the core sales fact table. Every order in the business has one row here.

**What it contains:**

| Column | What it means | How it is calculated |
|---|---|---|
| order_id | Unique order identifier | Directly from staging |
| order_status | delivered, shipped, cancelled etc | Directly from staging |
| purchased_at | When the customer clicked buy | Directly from staging |
| delivered_at | When the parcel arrived | Directly from staging |
| fulfilment_days | How many days delivery took | MAX(delivery_days) from intermediate |
| payment_value | Total money paid for this order | COALESCE(MAX(total_payment), 0) |
| payment_type | Credit card, boleto etc | From stg_payments directly |
| item_count | Number of items in the order | COUNT(item_sequence) |
| customer_city | City of the customer | From intermediate |
| customer_state | State of the customer | From intermediate |
| year_month | Period label e.g. '2017-11' | TO_CHAR(purchased_at, 'YYYY-MM') |
| order_year | Numeric year e.g. 2017 | EXTRACT(year FROM purchased_at) |
| order_month | Numeric month e.g. 11 | EXTRACT(month FROM purchased_at) |
| delivered_on_time | Was it on time? True/False | delivered_at <= estimated_delivery_at |

**Why we aggregate from order-item grain:**
The intermediate model has one row per item in an order. An order with 3 items has 3 rows.
mart_sales needs one row per order, so we use GROUP BY order_id and MAX() to collapse
multiple item rows into one order row.

MAX() is safe here because order-level fields like purchased_at and delivered_at are the
same value on every item row — MAX() just picks that value once.

---

### Mart 2 — mart_rfm (One Row Per Customer)

RFM stands for Recency, Frequency, Monetary. It is a customer segmentation technique
used by every serious e-commerce business in the world.

**The Three Dimensions:**

**Recency** — How many days since this customer last bought?
- Formula: reference_date - MAX(purchased_at)
- reference_date = the most recent order date in the entire dataset (not today, because
  this is historical data — using today would make everyone look like they have not bought
  in years)
- Lower number = bought more recently = better

**Frequency** — How many orders has this customer placed?
- Formula: COUNT(DISTINCT order_id)
- Higher number = orders more often = better

**Monetary** — How much total money has this customer spent?
- Formula: SUM(payment_value)
- Higher number = spends more = better

**The Scoring — NTILE(5)**

After calculating the raw values, we score each dimension from 1 to 5.

NTILE(5) is a PostgreSQL window function. It takes all customers, sorts them by the metric,
and splits them into 5 equal groups of 20% each. Group 1 = bottom 20%, Group 5 = top 20%.

CRITICAL — Recency is scored in REVERSE:
- A customer who bought 5 days ago has LOW recency_days but is a GREAT customer
- So we sort recency DESCENDING: ORDER BY recency_days DESC
- This means the customer with the fewest days (most recent) gets score 5 (best)
- The customer with the most days (least recent) gets score 1 (worst)

Frequency and Monetary are scored NORMALLY:
- Higher frequency = higher score: ORDER BY frequency ASC
- Higher monetary = higher score: ORDER BY monetary_value ASC

**Example scoring:**

| Customer | Recency Days | Frequency | Monetary | R Score | F Score | M Score |
|---|---|---|---|---|---|---|
| Alice | 5 | 8 | R$1,200 | 5 | 5 | 5 |
| Bob | 45 | 3 | R$450 | 4 | 3 | 3 |
| Carol | 180 | 1 | R$89 | 2 | 1 | 1 |
| Dave | 365 | 1 | R$45 | 1 | 1 | 1 |

**The Combined Score:**
rfm_score = R + F + M
- Minimum: 1+1+1 = 3 (worst possible customer)
- Maximum: 5+5+5 = 15 (best possible customer)

**The Segment Labels:**

Each customer gets a human-readable label based on their scores:

| Segment | Rule | Business Meaning |
|---|---|---|
| Champions | R≥4, F≥4, M≥4 | Best customers. Buy often, recently, spend most |
| Loyal Customers | F≥3, M≥3 | Consistent buyers with good spend |
| Potential Loyalists | R≥4, F≤2 | Recent buyers not yet frequent |
| New Customers | R=5, F=1 | Just arrived, only one order |
| Promising | R≥3, F≤2, M≤2 | Recent but low frequency and spend |
| Needs Attention | R=3, F≥2, M≥2 | Good scores but starting to drift |
| At Risk | R≤2, F≥3, M≥3 | Used to buy well but gone quiet |
| Cannot Lose Them | R=1, F≥4, M≥4 | Were best customers, now disappeared |
| Hibernating | R≤2, F≤2, M≤2 | Low scores across all three dimensions |
| Lost | R=1 (not covered above) | Completely inactive |
| Others | catch-all | Any combination not covered above |

**Our Results:**
- 93,358 unique customers scored and segmented
- Champions: 9,550 customers (10.2%) generating 23.4% of revenue
- Lost: only 89 customers (0.1%) — most inactive customers fall in Hibernating

---

### Mart 3 — mart_cohort (One Row Per Cohort-Month Combination)

**What is a Cohort?**

A cohort is a group of customers who made their first purchase in the same month.
- The November 2017 cohort = everyone who bought for the first time in November 2017
- The January 2018 cohort = everyone who bought for the first time in January 2018

**What is Retention?**

Retention measures what percentage of a cohort came back and bought again in later months.

Month 0 = the cohort month itself = always 100% (by definition)
Month 1 = what % of those customers bought again one month later
Month 2 = what % bought again two months later
And so on.

**How We Calculate It:**

Step 1 — Find each customer's cohort month:
```
cohort_month = DATE_TRUNC('month', MIN(purchased_at))
```
DATE_TRUNC rounds a date down to the first of the month.
MIN(purchased_at) finds the customer's earliest ever order.
So if a customer first bought on 2017-11-15, their cohort_month = 2017-11-01.

Step 2 — Calculate months since first purchase for every order:
```
months_since = (year_of_purchase - year_of_cohort) × 12
             + (month_of_purchase - month_of_cohort)
```
Example: Purchase in January 2018, cohort November 2017:
= (2018 - 2017) × 12 + (1 - 11)
= 12 + (-10)
= 2 months

We multiply years by 12 and add months to handle year boundaries correctly.

Step 3 — Count customers active in each cohort-month cell:
```
COUNT(DISTINCT customer_unique_id) per cohort and months_since
```

Step 4 — Calculate retention rate:
```
retention_rate = (customers active in this cell / cohort size at month 0) × 100
```

**The FIRST_VALUE() Window Function:**

To get the cohort size (month 0 count) for every row without a self-join, we use:
```sql
FIRST_VALUE(retained_customers) OVER (
    PARTITION BY cohort_month
    ORDER BY months_since_first_purchase
)
```
PARTITION BY cohort_month = look within this cohort only
ORDER BY months_since = sort by month number
FIRST_VALUE = return the value from the first row (month 0)

This gives us the cohort size on every row so we can divide by it.

**Our Results:**
- Near-zero retention after Month 0 across all cohorts
- Average Month 1 retention is under 1%
- This confirms Olist is a single-purchase marketplace
- Business insight: revenue must come from new customer acquisition, not retention

---

### Mart 4 — mart_geo (One Row Per State)

**What it contains:**

| Column | Formula |
|---|---|
| total_orders | COUNT(order_id) |
| total_customers | COUNT(DISTINCT customer_unique_id) |
| total_revenue | SUM(payment_value) |
| avg_order_value | AVG(payment_value) |
| avg_fulfilment_days | AVG(fulfilment_days) |
| pct_delivered_on_time | SUM(delivered_on_time=true) / COUNT(*) × 100 |
| avg_items_per_order | AVG(item_count) |

**Result:** 27 rows — one per Brazilian state/federal district

---

### Mart 5 — mart_products (One Row Per Category)

**What it contains:**

| Column | Formula |
|---|---|
| total_items_sold | COUNT(*) |
| total_orders | COUNT(DISTINCT order_id) |
| total_revenue | SUM(price) |
| avg_item_price | AVG(price) |
| avg_freight_cost | AVG(freight_cost) |
| avg_review_score | AVG(review_score) |
| total_reviews | COUNT(review_score) |
| pct_five_star | SUM(review_score=5) / COUNT(*) × 100 |
| pct_one_star | SUM(review_score=1) / COUNT(*) × 100 |

**Note on reviews:** Reviews in Olist are at order level, not item level. An order with
3 items all gets the same review score. When we join reviews to items by order_id,
all three items inherit that single score. This is a known limitation of the dataset.

---

# PART 4 — DATA QUALITY

## Why Data Quality Matters

Without quality checks, bad data silently reaches your dashboard.

Example: A dbt join accidentally duplicates rows. Every order now appears twice.
Your revenue chart shows R$30 million instead of R$15 million. A business makes
a decision based on numbers that are double what they should be. By the time someone
notices, damage is done.

Quality checks are automated guards that catch this before it reaches anyone.

## dbt Tests (27 Tests)

dbt has four built-in test types:

**unique** — checks no two rows have the same value
Example: unique on order_id ensures no order appears twice

**not_null** — checks a column never contains NULL
Example: not_null on payment_value ensures every order has a revenue figure

**accepted_values** — checks a column only contains values from a list
Example: accepted_values on order_status ensures only known statuses exist

**singular test** — a custom SQL query; if it returns any rows, the test fails
Example: assert_no_negative_payments queries for payment_value < 0

All 27 tests pass: PASS=27 WARN=0 ERROR=0

## Great Expectations (30+ Checks)

Great Expectations adds business logic checks that dbt cannot do:

**Row count checks** — does the table have enough rows to be realistic?
Example: mart_sales should have at least 90,000 rows. If dbt broke and built an
empty table, the row count check catches it immediately.

**Range checks** — are numeric values within realistic bounds?
Example: review_score between 1 and 5. A score of 0 or 99 is impossible.
Example: fulfilment_days between 0 and 180. A 500-day delivery is clearly corrupt.

**Business rule checks** — do the numbers make sense together?
Example: payment_value >= 0. A negative payment makes no business sense.
Example: retention_rate between 0 and 100. A 150% retention rate is mathematically
impossible.

All checks pass: ALL PASSED across all 5 mart tables.

---

# PART 5 — PYTHON ANALYTICS

## How Python Reads from the Database

We use SQLAlchemy to connect Python to Supabase:

```python
engine = create_engine(DATABASE_URL)
df = pd.read_sql("SELECT * FROM public_marts.mart_sales", engine)
```

create_engine creates a connection to the database.
pd.read_sql runs the SQL query and loads the result into a pandas DataFrame.
A DataFrame is a table in Python — rows and columns, exactly like Excel.

## Script 1 — rfm_analysis.py

**What it calculates:**

For each customer segment it calculates:
- customer_count = number of customers in this segment
- pct_customers = customer_count / total_customers × 100
- total_revenue = sum of monetary_value for all customers in this segment
- pct_revenue = total_revenue / overall_total_revenue × 100
- avg_spend = mean of monetary_value for customers in this segment
- avg_orders = mean of frequency for customers in this segment

**Key findings:**
- Total customers: 93,358
- Champions: 9,550 customers (10.2% of base) generating 23.4% of revenue
- Average champion spend: R$377.16
- Lost customers: only 89 (0.1%)

**Business insight:** A small loyal minority drives disproportionate revenue.
The top 10% of customers generate nearly a quarter of all revenue. This is the
Pareto principle (80/20 rule) in action — in this case slightly less extreme
but the pattern is clear.

## Script 2 — cohort_analysis.py

**What it calculates:**

Pivot table:
- Rows = cohort months (2016-09 through 2018-08)
- Columns = Month 0, Month 1, Month 2 ... Month 12
- Values = retention_rate from mart_cohort

Average Month 1 retention = mean of all Month 1 values across all cohorts
Best cohort = cohort with highest Month 1 retention
Worst cohort = cohort with lowest Month 1 retention

**Key findings:**
- Average Month 1 retention: under 1%
- All cohorts show near-zero retention after Month 0
- The platform is entirely acquisition-driven

**Business insight:** With near-zero retention, every single revenue target depends
entirely on finding new customers. There is no retention engine to rely on.
This makes the business fragile — one bad acquisition month means one bad revenue month.

## Script 3 — kpi_analysis.py

**What it calculates:**

Headline KPIs:
- total_revenue = SUM(payment_value) for all delivered orders
- total_orders = COUNT(order_id)
- total_customers = COUNT(DISTINCT customer_unique_id)
- avg_order_value = total_revenue / total_orders = R$15,422,461.77 / 96,478 = R$159.85
- avg_fulfilment_days = AVG(fulfilment_days) = 12.1 days
- pct_on_time = SUM(delivered_on_time=True) / COUNT(*) × 100 = 91.9%

Monthly trends:
- GROUP BY year_month
- Calculate all KPIs per month
- revenue_growth_pct = (this_month_revenue - last_month_revenue) / last_month_revenue × 100
  This is calculated by pandas pct_change() function

**Key findings:**

| KPI | Value |
|---|---|
| Total Revenue | R$15,422,461.77 |
| Total Orders | 96,478 |
| Unique Customers | 93,358 |
| Average Order Value | R$159.85 |
| Avg Fulfilment | 12.1 days |
| On-time Delivery | 91.9% |

Best month: November 2017 — R$1,153,528 (Black Friday effect)
Platform growth: Near zero in late 2016 → R$1 million/month by 2018

Payment breakdown:
- Credit card: 74.8% of orders
- Boleto: 19.9% (Brazilian bank slip — used by unbanked population)
- Voucher: 3.8%
- Debit card: 1.5%

**Business insight:** The 20% boleto usage tells you Olist serves a significant
unbanked population — customers who cannot use credit cards. This is a market
access story unique to Brazil and an important context for the business model.

---

# PART 6 — REPORTS GENERATED

All outputs are saved in the `reports/` folder:

| File | What it shows |
|---|---|
| rfm_segments.png | Bar charts: customers and revenue per RFM segment |
| rfm_score_distribution.png | Histogram of combined RFM scores 3-15 |
| rfm_segment_summary.csv | Full table of segment metrics |
| cohort_retention_heatmap.png | Green heatmap of retention rates by cohort and month |
| cohort_retention_curve.png | Average retention curve across all cohorts |
| cohort_retention_matrix.csv | Full retention matrix as a spreadsheet |
| kpi_dashboard.png | Four-chart dashboard: revenue, orders, AOV, payment types |
| monthly_kpis.csv | Monthly revenue and KPI trends |

---

# PART 7 — THE COMPLETE DATA FLOW

```
Kaggle CSV Files (9 files, 100k rows)
            ↓  load_olist.py
Supabase raw tables (permanent original data)
            ↓  dbt run
Staging views (7 models — cleaned, typed, null-handled)
            ↓  dbt run
int_orders_enriched view (joined: orders + customers + items + payments)
            ↓  dbt run
Mart tables (5 models — business analytics tables, physically stored)
            ↓  dbt test + Great Expectations
Quality validated (27 dbt tests + 30+ GE checks — all passing)
            ↓  Python analytics scripts
Reports folder (8 files — charts and CSVs)
            ↓  (coming next)
Prophet forecast → FastAPI → Plotly Dash Dashboard → Public URL on Render
```

---

*Documentation covers Weeks 1-4. Updated as project progresses.*
