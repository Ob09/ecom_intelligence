# E-commerce BI Platform — Complete Reference Documentation
### A Step-by-Step Guide to Every Tool, Concept, Decision, and Issue

---

> **How to use this document**
> This is a living reference. Every tool is explained from first principles.
> Every code block shows real syntax with comments explaining each line.
> Every stage documents the problems we hit and how we solved them.
> No credentials or secrets appear anywhere in this document.

---

## TABLE OF CONTENTS

1. Project Overview
2. Architecture Diagram
3. The Data
4. Stage 1 — Environment Setup
5. Stage 2 — Database (PostgreSQL + Supabase)
6. Stage 3 — Data Ingestion
7. Stage 4 — Data Transformation (dbt)
8. Stage 5 — Data Quality (Great Expectations)
9. Stage 6 — Python Analytics
10. Stage 7 — Forecasting (Prophet)
11. Stage 8 — REST API (FastAPI)
12. Stage 9 — Dashboard (Plotly Dash)
13. Stage 10 — Pipeline Orchestration (Airflow + GitHub Actions)
14. Stage 11 — Deployment (Render)
15. Business Insights
16. Common Issues and Fixes
17. Key Concepts Glossary

---

# 1. PROJECT OVERVIEW

## What Problem Does This Solve?

A business with 100,000 orders has all its data sitting in a database.
But without the right tools, nobody can answer simple questions like:

- Who are our best customers?
- Is revenue growing?
- Which regions generate most sales?
- Are customers coming back?

The raw data exists but it is:
- Scattered across 9 separate tables
- Messy (wrong column names, text dates, missing values)
- Inaccessible to non-technical people
- Unvalidated (we do not know if the numbers are trustworthy)

**What we built:** A system that automatically cleans, joins, validates,
analyses, and displays all this data through an interactive dashboard —
running 24/7 without any human intervention.

## What Success Looks Like

```
BEFORE this project:
  "Can we see monthly revenue?" → 2 days of SQL writing → Excel chart → email

AFTER this project:
  "Can we see monthly revenue?" → open browser → instant chart
```

---

# 2. ARCHITECTURE DIAGRAM

## Full System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        DATA SOURCES                             │
│                                                                 │
│   9 Olist CSV files from Kaggle (100,000 real orders)           │
└─────────────────────┬───────────────────────────────────────────┘
                      │  load_olist.py (Python script, runs once)
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                   SUPABASE POSTGRESQL                           │
│                   (Cloud database, always online)               │
│                                                                 │
│  raw_orders  raw_customers  raw_products  raw_sellers           │
│  raw_payments  raw_order_items  raw_reviews                     │
│  raw_geolocation  raw_category_translation                      │
└─────────────────────┬───────────────────────────────────────────┘
                      │  dbt run (runs daily via GitHub Actions)
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    STAGING LAYER (Views)                        │
│              Clean individual tables — no joins                 │
│                                                                 │
│  stg_orders      stg_customers    stg_products                  │
│  stg_sellers     stg_payments     stg_order_items               │
│  stg_reviews                                                    │
└─────────────────────┬───────────────────────────────────────────┘
                      │  dbt run
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                 INTERMEDIATE LAYER (View)                       │
│              Join cleaned tables together                       │
│                                                                 │
│               int_orders_enriched                               │
│    (orders + customers + items + payments in one place)         │
└──────────┬──────────────────────┬────────────────────────────────┘
           │  dbt run             │  dbt run
           ▼                      ▼
┌──────────────────────┐  ┌─────────────────────────────────────┐
│   mart_sales         │  │  mart_rfm  mart_cohort               │
│   (one row/order)    │  │  mart_geo  mart_products             │
│   KPIs & revenue     │  │  (customer, retention, geo,          │
└──────────────────────┘  │   category analytics)               │
                          └─────────────────────────────────────┘
                      │  dbt test + Great Expectations
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    QUALITY VALIDATION                           │
│  27 dbt tests + 30+ Great Expectations checks                   │
│  Pipeline stops here if anything fails                          │
└─────────────────────┬───────────────────────────────────────────┘
                      │  Python analytics scripts
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                   FASTAPI REST API                              │
│              Deployed on Render (always online)                 │
│                                                                 │
│  /kpis  /rfm/segments  /cohort  /geo  /products  /forecast      │
└─────────────────────┬───────────────────────────────────────────┘
                      │  HTTP requests
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                  PLOTLY DASH DASHBOARD                          │
│              Deployed on Render (always online)                 │
│                                                                 │
│  Overview │ RFM │ Cohort │ Geography │ Products │ Trends        │
└─────────────────────────────────────────────────────────────────┘
```

## The Data Flow — Simple Version

```
Raw CSV files
     ↓ (uploaded once)
Database
     ↓ (transformed daily)
Clean analytics tables
     ↓ (validated daily)
API endpoints
     ↓ (read on demand)
Dashboard charts
```

## The Three-Layer dbt Architecture

```
┌─────────────┬──────────────────────────────────────────────────┐
│   LAYER     │  PURPOSE                                         │
├─────────────┼──────────────────────────────────────────────────┤
│  Staging    │  Clean each raw table individually               │
│  (Views)    │  Rename columns, fix types, handle nulls         │
│             │  ONE staging model per raw table                 │
│             │  NO joins allowed here                           │
├─────────────┼──────────────────────────────────────────────────┤
│ Intermediate│  Join cleaned tables together                    │
│  (Views)    │  Create enriched combined datasets               │
│             │  Calculated fields (delivery days, on-time flag) │
├─────────────┼──────────────────────────────────────────────────┤
│   Marts     │  Answer specific business questions              │
│  (Tables)   │  One mart per business question                  │
│             │  Pre-computed for fast dashboard reads           │
└─────────────┴──────────────────────────────────────────────────┘
```

---

# 3. THE DATA

## The 9 Olist Tables

```
┌─────────────────────┬────────────┬────────────────────────────────┐
│  Table              │  Rows      │  What it contains              │
├─────────────────────┼────────────┼────────────────────────────────┤
│  raw_orders         │  99,441    │  Every order placed            │
│  raw_customers      │  99,441    │  Customer details per order    │
│  raw_products       │  32,951    │  Product catalogue             │
│  raw_sellers        │  3,095     │  Seller information            │
│  raw_payments       │  103,886   │  Payment records               │
│  raw_order_items    │  112,650   │  Items within each order       │
│  raw_reviews        │  99,224    │  Customer reviews              │
│  raw_geolocation    │  1,000,163 │  Zip codes with coordinates    │
│  raw_category_trans │  71        │  Portuguese → English names    │
└─────────────────────┴────────────┴────────────────────────────────┘
```

## How the Tables Relate

```
raw_customers ──────────────────────────────────────┐
                                                     │
raw_orders ──────────────────────────────────────── JOIN → int_orders_enriched
                                                     │
raw_order_items ──── links to raw_products ──────────┤
                 └── links to raw_sellers ────────────┤
                                                     │
raw_payments ────────────────────────────────────────┘

raw_reviews ──── linked to raw_orders via order_id
raw_geolocation ─ linked to customers via zip code
raw_category_translation ─ linked to products via category name
```

## Important Data Quirk — customer_id vs customer_unique_id

```
PROBLEM: In Olist, the SAME real person gets a NEW customer_id
         for EVERY order they place.

EXAMPLE:
  Maria buys in January  → customer_id = "abc123"
  Maria buys in March    → customer_id = "def456"  (different ID!)
  Maria buys in July     → customer_id = "ghi789"  (different again!)

  But all three share:   customer_unique_id = "maria_real_id"

SOLUTION: Always use customer_unique_id for person-level analysis.
          Use customer_id only for joining orders to customers.
```

---

# 4. STAGE 1 — ENVIRONMENT SETUP

## What is a Conda Environment?

A conda environment is an isolated Python installation. Think of it as
a separate room where your project lives with its own set of tools.

```
WITHOUT environments:
  All projects share one Python installation
  Project A needs pandas version 1.0
  Project B needs pandas version 2.0
  → CONFLICT — they cannot both be installed

WITH environments:
  Project A has its own room with pandas 1.0
  Project B has its own room with pandas 2.0
  → No conflict — each project is isolated
```

## Key Commands

```bash
# Create a new environment with Python 3.11
conda create -n ecom-bi python=3.11

# Activate the environment (enter the room)
conda activate ecom-bi

# Install all required packages
pip install -r requirements.txt

# Check which environment is active
conda info --envs

# Deactivate (leave the room)
conda deactivate
```

## What is requirements.txt?

A text file listing all Python packages your project needs.
When someone else (or a cloud server) wants to run your code,
they run `pip install -r requirements.txt` and get the exact same packages.

```
# requirements.txt format:
package_name==version_number

# Example entries:
pandas==2.1.4          # Data manipulation
fastapi==0.109.0       # API framework
dash==2.16.1           # Dashboard framework
prophet==1.1.5         # Forecasting
dbt-core==1.7.4        # Data transformation
```

## Issues Faced at This Stage

```
ISSUE: Prophet installation failing
CAUSE: Prophet needs compiled C++ code (Stan library)
FIX:   Install via conda instead of pip
       conda install -c conda-forge prophet -y

ISSUE: psycopg2 installation failing on Windows  
CAUSE: Needs C compiler to build from source
FIX:   Use psycopg2-binary instead
       pip install psycopg2-binary

ISSUE: Package version conflicts
CAUSE: Two packages need different versions of the same dependency
FIX:   Pin exact versions in requirements.txt
       Use specific versions that are known to work together
```

---

# 5. STAGE 2 — DATABASE (PostgreSQL + SUPABASE)

## What is a Database?

A database is a structured way to store large amounts of data
that can be queried quickly and accessed by many users simultaneously.

```
WITHOUT a database:
  Data in CSV files on your laptop
  Only you can access it
  Slow to query large files
  No concurrent access
  No validation rules

WITH a database:
  Data on a cloud server
  Anyone with credentials can access
  Fast queries with indexes
  Multiple users simultaneously
  Enforces data types and constraints
```

## What is PostgreSQL?

PostgreSQL (Postgres) is a free, open-source relational database.
"Relational" means data is stored in tables that relate to each other.

Used by: Instagram, Spotify, Reddit, GitHub, and thousands of companies.

## What is Supabase?

Supabase is a hosted PostgreSQL service. Instead of managing your own
database server, Supabase runs it for you in the cloud.

```
YOU                    SUPABASE
────                   ────────
Write SQL queries  →   Executes them on its servers
Store credentials  →   Keeps your data secure
Connect via URL    →   Always available 24/7
Pay nothing        →   Free tier: 500MB database
```

## Connection String Format

A connection string tells Python where and how to connect to the database.

```
Format:
postgresql://[username]:[password]@[host]:[port]/[database_name]

Parts explained:
  postgresql://  → the type of database
  username       → who you are logging in as
  password       → your database password (NEVER put in code)
  host           → the server address
  port           → which door on the server to knock on (5432 is default)
  database_name  → which database on that server

Real format (with placeholders, not real values):
  postgresql://postgres.YOUR_PROJECT_ID:YOUR_PASSWORD@aws-0-region.pooler.supabase.com:5432/postgres
```

## Session Pooler vs Direct Connection

```
DIRECT CONNECTION:
  → Uses IPv6 (not supported on all networks, especially Windows)
  → Better for long-running processes

SESSION POOLER:
  → Uses IPv4 (works everywhere)
  → Better for short queries from many connections
  → We used this — it solved Windows compatibility issues

How to identify:
  Direct:  db.YOUR_PROJECT_ID.supabase.co
  Pooler:  aws-0-REGION.pooler.supabase.com  ← we used this
```

## Key SQL Concepts Used in This Project

### SELECT — Getting Data
```sql
-- Get everything from a table
SELECT * FROM raw_orders;

-- Get specific columns
SELECT order_id, order_status, order_purchase_timestamp
FROM raw_orders;

-- Get unique values only
SELECT DISTINCT order_status FROM raw_orders;
```

### WHERE — Filtering Rows
```sql
-- Only delivered orders
SELECT * FROM raw_orders
WHERE order_status = 'delivered';

-- Multiple conditions
SELECT * FROM raw_orders
WHERE order_status = 'delivered'
  AND order_purchase_timestamp > '2017-01-01';
```

### GROUP BY — Aggregating Data
```sql
-- Count orders per status
SELECT order_status, COUNT(*) as order_count
FROM raw_orders
GROUP BY order_status;

-- Revenue per month
SELECT
    TO_CHAR(order_purchase_timestamp::timestamp, 'YYYY-MM') as month,
    SUM(payment_value) as total_revenue
FROM raw_payments
GROUP BY month
ORDER BY month;
```

### JOIN — Combining Tables
```sql
-- INNER JOIN: only rows with matches in BOTH tables
SELECT o.order_id, c.customer_city
FROM raw_orders o
INNER JOIN raw_customers c ON o.customer_id = c.customer_id;

-- LEFT JOIN: all rows from left table, matching from right
-- If no match on right side, those columns are NULL
SELECT o.order_id, r.review_score
FROM raw_orders o
LEFT JOIN raw_reviews r ON o.order_id = r.order_id;
-- Orders with no review still appear, with NULL review_score
```

### Window Functions — Calculations Across Related Rows
```sql
-- NTILE(5): split all rows into 5 equal groups
-- Used in RFM scoring
SELECT
    customer_id,
    monetary_value,
    NTILE(5) OVER (ORDER BY monetary_value ASC) as m_score
FROM customer_monetary;

-- FIRST_VALUE: get the first value in a group
-- Used in cohort retention calculation
SELECT
    cohort_month,
    FIRST_VALUE(customer_count) OVER (
        PARTITION BY cohort_month
        ORDER BY month_number
    ) as cohort_size
FROM cohort_data;
```

## Issues Faced at This Stage

```
ISSUE: Connection failing with IPv6 error
CAUSE: Windows does not support IPv6 by default
FIX:   Use session pooler connection string instead of direct connection
       Look for: aws-0-eu-west-1.pooler.supabase.com
       Instead of: db.YOUR_PROJECT_ID.supabase.co

ISSUE: "too many connections" error
CAUSE: Each script was creating a new connection pool
FIX:   Create one shared engine in db.py and import it everywhere
       Use engine.connect() as a context manager so connections return to pool

ISSUE: Credentials accidentally committed to GitHub
CAUSE: Connection string hardcoded in great_expectations.yml
FIX:   
  1. Remove from file (replace with ${db_url} variable)
  2. git rm --cached the file
  3. Add to .gitignore
  4. Commit and push
  → GitHub security scanner sent email alert — good catch!
```

---

# 6. STAGE 3 — DATA INGESTION

## What is Data Ingestion?

Moving data from its original location (CSV files) into your database.
This is a one-time operation for historical data.

## Python Script Structure (load_olist.py)

```python
# ── IMPORTS ────────────────────────────────────────────────────
import pandas as pd              # for reading CSV files
from sqlalchemy import create_engine  # for connecting to database
from dotenv import load_dotenv   # for reading .env file
import os                        # for reading environment variables

# ── LOAD CREDENTIALS FROM .env FILE ───────────────────────────
# NEVER put credentials directly in code
# Store them in a .env file that is in .gitignore
load_dotenv()
db_url = os.getenv("DATABASE_URL")  # reads from .env file

# ── CREATE DATABASE CONNECTION ─────────────────────────────────
engine = create_engine(db_url)

# ── DEFINE TABLES TO LOAD ─────────────────────────────────────
tables = {
    "raw_orders": "data/olist_orders_dataset.csv",
    "raw_customers": "data/olist_customers_dataset.csv",
    # ... more tables
}

# ── LOAD EACH TABLE ────────────────────────────────────────────
for table_name, csv_path in tables.items():
    print(f"Loading {table_name}...")

    # Read CSV into pandas DataFrame
    df = pd.read_csv(csv_path)

    # Write DataFrame to database
    # if_exists="replace" drops and recreates the table
    # if_exists="append" would add rows without dropping
    df.to_sql(
        name=table_name,
        con=engine,
        if_exists="replace",
        index=False          # don't write the DataFrame row numbers
    )

    print(f"  Loaded {len(df):,} rows")
```

## The .env File Pattern

```bash
# .env file (NEVER commit this to GitHub)
DATABASE_URL=postgresql://username:password@host:5432/database

# .env.example file (SAFE to commit — no real values)
DATABASE_URL=postgresql://username:your_password_here@your_host:5432/postgres
```

```bash
# .gitignore — tells Git to ignore the .env file
.env
*.env
```

## Issues Faced at This Stage

```
ISSUE: CSV files have encoding errors
CAUSE: Some Brazilian characters (ã, ç, é) not reading correctly
FIX:   Specify encoding when reading
       pd.read_csv(path, encoding='utf-8')
       or
       pd.read_csv(path, encoding='latin-1')

ISSUE: Loading 1 million geolocation rows is very slow
CAUSE: Default to_sql writes one row at a time
FIX:   Use chunksize parameter
       df.to_sql(name, engine, chunksize=10000)
       This writes 10,000 rows at a time, much faster

ISSUE: Wrong data types in database
CAUSE: pandas guesses column types, sometimes wrong
FIX:   Let dbt handle typing in the staging layer
       Use ::integer and ::timestamp casts in SQL
```

---

# 7. STAGE 4 — DATA TRANSFORMATION (dbt)

## What is dbt?

dbt (data build tool) organises SQL transformations into a structured,
tested, documented project. It replaces ad-hoc SQL scripts.

```
WITHOUT dbt:
  analyst_query_v1.sql
  analyst_query_v2_FINAL.sql
  analyst_query_v2_FINAL_fixed.sql
  analyst_query_v2_FINAL_fixed_USE_THIS_ONE.sql
  → No version control, no testing, no documentation

WITH dbt:
  models/marts/mart_sales.sql
  → Version controlled in Git
  → Tested with schema.yml
  → Documented automatically
  → Dependencies tracked and enforced
```

## dbt Project Structure

```
dbt_project/olist_bi/
├── dbt_project.yml          ← main config file
├── profiles.yml             ← database connection (in ~/.dbt/, not here)
├── models/
│   ├── staging/
│   │   ├── schema.yml       ← source definitions + staging tests
│   │   ├── stg_orders.sql
│   │   ├── stg_customers.sql
│   │   └── ... (7 files)
│   ├── intermediate/
│   │   └── int_orders_enriched.sql
│   └── marts/
│       ├── schema.yml       ← mart tests
│       ├── mart_sales.sql
│       ├── mart_rfm.sql
│       ├── mart_cohort.sql
│       ├── mart_geo.sql
│       └── mart_products.sql
└── tests/
    └── assert_no_negative_payments.sql  ← custom test
```

## dbt_project.yml — The Config File

```yaml
name: 'olist_bi'          # project name
version: '1.0.0'

models:
  olist_bi:
    staging:
      +materialized: view  # staging = views (no data stored)
      +schema: staging     # creates tables in public_staging schema
    intermediate:
      +materialized: view  # intermediate = views
      +schema: intermediate
    marts:
      +materialized: table # marts = physical tables (data stored)
      +schema: marts       # creates tables in public_marts schema
```

## profiles.yml — The Database Connection

```yaml
# Location: C:\Users\YourName\.dbt\profiles.yml
# NOT inside your project folder (keeps credentials separate)

olist_bi:
  outputs:
    dev:
      type: postgres
      host: your-host.supabase.com
      port: 5432
      dbname: postgres
      user: postgres.your_project_id
      pass: "{{ env_var('DB_PASSWORD') }}"  # reads from environment variable
      schema: public
      threads: 4
  target: dev
```

## schema.yml — Defining Sources and Tests

```yaml
version: 2

# Sources tell dbt where your raw tables are
sources:
  - name: olist            # the source name you use in {{ source() }}
    schema: public         # which database schema
    tables:
      - name: raw_orders   # the actual table name
        description: "One row per order placed on Olist"
      - name: raw_customers
        description: "One row per customer record"

# Models define tests for your transformed tables
models:
  - name: mart_sales
    columns:
      - name: order_id
        tests:
          - unique      # no duplicates
          - not_null    # never empty
      - name: order_status
        tests:
          - accepted_values:
              values: ['delivered', 'shipped', 'canceled', 'processing']
```

## Staging Model Pattern

```sql
-- stg_orders.sql — the standard staging model structure

with source as (
    -- {{ source('olist', 'raw_orders') }} references the raw table
    -- defined in schema.yml under sources
    select * from {{ source('olist', 'raw_orders') }}
),

renamed as (
    select
        -- Keep important columns with clean names
        order_id,
        customer_id,

        -- COALESCE: if null, use the default value instead
        coalesce(order_status, 'unknown') as order_status,

        -- NULLIF: converts empty string '' to NULL
        -- Needed before casting because '' cannot be cast to timestamp
        -- ::timestamp: converts text to a proper datetime value
        nullif(order_purchase_timestamp, '')::timestamp as purchased_at,

        -- Same pattern for all date columns
        nullif(order_delivered_customer_date, '')::timestamp as delivered_at

    from source
),

cleaned as (
    -- Remove rows that are completely unusable
    -- A row without order_id cannot be joined to anything
    select *
    from renamed
    where order_id is not null
      and customer_id is not null
      and purchased_at is not null
)

-- This final select is the output of the model
-- dbt saves this as a view or table in your database
select * from cleaned
```

## Intermediate Model Pattern

```sql
-- int_orders_enriched.sql

with orders as (
    -- {{ ref('stg_orders') }} references another dbt model
    -- dbt builds stg_orders FIRST because of this dependency
    select * from {{ ref('stg_orders') }}
),

customers as (
    select * from {{ ref('stg_customers') }}
),

payments as (
    -- Aggregate payments to order level BEFORE joining
    -- One order can have multiple payment rows
    -- If we join without aggregating, we get duplicate order rows
    select
        order_id,
        sum(payment_value) as total_payment,
        count(*) as payment_count
    from {{ ref('stg_payments') }}
    group by order_id
),

final as (
    select
        o.order_id,
        o.order_status,
        o.purchased_at,
        o.delivered_at,

        c.customer_unique_id,  -- true unique person identifier
        c.customer_city,
        c.customer_state,

        p.total_payment,
        p.payment_count,

        -- Calculate derived fields once here
        -- Every mart that needs delivery days inherits this calculation
        date_part('day', o.delivered_at - o.purchased_at) as delivery_days,

        case
            when o.delivered_at <= o.estimated_delivery_at then true
            else false
        end as delivered_on_time

    from orders o
    left join customers c on o.customer_id = c.customer_id
    left join payments p on o.order_id = p.order_id
)

select * from final
```

## RFM Mart — Key SQL Concepts

```sql
-- mart_rfm.sql

-- STEP 1: Reference date
-- We use max(purchased_at) instead of CURRENT_DATE
-- because this is historical data (2016-2018)
-- Using today's date would make ALL customers look like they
-- haven't bought in years, making recency meaningless
with reference_date as (
    select max(purchased_at)::date as max_date
    from {{ ref('stg_orders') }}
    where order_status = 'delivered'
),

-- STEP 2: Calculate raw values
raw_rfm as (
    select
        customer_unique_id,
        -- Recency: how many days since last purchase?
        (r.max_date - max(o.purchased_at)::date) as recency_days,
        -- Frequency: how many orders?
        count(distinct o.order_id) as frequency,
        -- Monetary: total spend?
        sum(p.payment_value) as monetary_value

    from stg_orders o
    left join stg_customers c on o.customer_id = c.customer_id
    left join stg_payments p on o.order_id = p.order_id
    -- CROSS JOIN on a single-row CTE makes max_date available to every row
    cross join reference_date r
    where o.order_status = 'delivered'
    group by customer_unique_id, r.max_date
),

-- STEP 3: Score with NTILE(5)
scores as (
    select
        customer_unique_id,
        recency_days,
        frequency,
        monetary_value,

        -- NTILE(5) splits all rows into 5 equal groups (20% each)
        -- Assigns 1 to bottom 20%, 5 to top 20%

        -- RECENCY: ORDER BY DESC because fewer days = better customer
        -- Customer who bought yesterday (5 days) gets score 5 (best)
        -- Customer who bought 2 years ago (730 days) gets score 1 (worst)
        ntile(5) over (order by recency_days desc) as r_score,

        -- FREQUENCY: ORDER BY ASC because more orders = better
        ntile(5) over (order by frequency asc) as f_score,

        -- MONETARY: ORDER BY ASC because more spend = better
        ntile(5) over (order by monetary_value asc) as m_score
    from raw_rfm
)

select
    customer_unique_id,
    recency_days,
    frequency,
    round(monetary_value::numeric, 2) as monetary_value,
    r_score,
    f_score,
    m_score,
    (r_score + f_score + m_score) as rfm_score,

    -- Segment labels based on score combinations
    -- Rules are checked in order — first match wins
    case
        when r_score >= 4 and f_score >= 4 and m_score >= 4 then 'Champions'
        when f_score >= 3 and m_score >= 3                   then 'Loyal Customers'
        when r_score >= 4 and f_score <= 2                   then 'Potential Loyalists'
        when r_score = 1  and f_score >= 4 and m_score >= 4  then 'Cannot Lose Them'
        when r_score <= 2 and f_score >= 3 and m_score >= 3  then 'At Risk'
        when r_score <= 2 and f_score <= 2 and m_score <= 2  then 'Hibernating'
        when r_score = 1                                     then 'Lost'
        else 'Others'
    end as customer_segment
from scores
```

## Cohort Retention — The Month Calculation

```sql
-- How to calculate months between two dates correctly
-- Simple subtraction does not work across year boundaries

-- WRONG approach (breaks across years):
-- delivered_month - cohort_month = -10 for Nov 2017 to Jan 2018

-- CORRECT approach:
(
    -- Year difference converted to months
    (extract(year from purchase_month) - extract(year from cohort_month)) * 12
    +
    -- Plus the month difference
    (extract(month from purchase_month) - extract(month from cohort_month))
)

-- Example:
-- cohort_month = November 2017 (year=2017, month=11)
-- purchase_month = January 2018 (year=2018, month=1)
-- = (2018 - 2017) * 12 + (1 - 11)
-- = 1 * 12 + (-10)
-- = 12 - 10
-- = 2 months ✓
```

## dbt Commands Reference

```bash
# Must be run from inside dbt_project/olist_bi/

# Build all models in dependency order
dbt run

# Build only one specific model
dbt run --select mart_sales

# Build a model AND everything that depends on it
dbt run --select mart_sales+

# Build everything from staging upward
dbt run --select staging+

# Run all tests
dbt test

# Run tests for one model only
dbt test --select mart_rfm

# Preview data from a model (first 5 rows)
dbt show --select int_orders_enriched --limit 5

# Preview as JSON (shows all columns and exact values)
dbt show --select int_orders_enriched --limit 1 --output json

# Generate documentation
dbt docs generate

# Serve documentation locally
dbt docs serve --port 8081
```

## Issues Faced at This Stage

```
ISSUE: "column does not exist" errors when building mart models
CAUSE: Staging models renamed columns but mart models used old names
EXAMPLE: order_purchase_timestamp renamed to purchased_at in staging
         but mart_sales.sql still referenced order_purchase_timestamp
FIX:   Run: dbt show --select int_orders_enriched --limit 1 --output json
       This shows the exact column names that exist
       Update all references to match

ISSUE: "source not found" error for raw_order_payments
CAUSE: Table in database is called raw_payments, not raw_order_payments
FIX:   Check schema.yml to see the exact source names defined
       Match {{ source('olist', 'EXACT_NAME_FROM_SCHEMA_YML') }}

ISSUE: stg_reviews.sql file named stq_reviews.sql (typo)
CAUSE: Typo when creating the file (q instead of g)
FIX:   Rename the file in VS Code
       Run dbt run --select stg_reviews to create the view with correct name
       The old stq_reviews view remains in database but is not used

ISSUE: int_orders_enriched producing wrong row count
CAUSE: Grain mismatch — model was at order-item grain, not order grain
EXPLANATION:
  raw_order_items has ONE ROW PER ITEM
  An order with 3 items = 3 rows in order_items
  Joining orders to items without aggregating = 3 rows per order
  Mart models reading from this get inflated counts
FIX:   Aggregate in mart models using GROUP BY order_id
       Use MAX() for order-level fields (same value on every row)
       Use COUNT() for item_sequence to get item count

ISSUE: ZIP code column NULLIF failing with type error
CAUSE: Column stored as INTEGER in database, not text
       NULLIF(column, '') fails because you cannot compare integer to ''
FIX:   Cast to text first, then apply NULLIF
       nullif(customer_zip_code_prefix::text, '')::integer
       Step 1: ::text converts the integer to text
       Step 2: NULLIF can now compare text to ''
       Step 3: ::integer converts the result back to integer

ISSUE: "No dbt_project.yml found" when running dbt commands
CAUSE: Running dbt from wrong directory
FIX:   Must run from inside dbt_project/olist_bi/
       NOT from e_com_analyser/
       NOT from dbt_project/olist_bi/models/staging/
       CORRECT: cd dbt_project/olist_bi && dbt run
```

---

# 8. STAGE 5 — DATA QUALITY (GREAT EXPECTATIONS)

## What is Great Expectations?

A Python library that validates data by running automated checks called "expectations."

```
Think of it like a checklist an inspector uses before approving a product:

  □ Does this shipment have at least 1000 units?
  □ Are all units within weight tolerance?
  □ Are all values positive?
  □ Do all items have valid barcodes?

Great Expectations:
  □ Does mart_sales have at least 90,000 rows?
  □ Are all payment values zero or above?
  □ Do all review scores fall between 1 and 5?
  □ Does mart_geo have exactly 27 rows?
```

## Why Both dbt Tests AND Great Expectations?

```
DBT TESTS — check data structure:
  ✓ Is order_id unique?
  ✓ Is payment_value never null?
  ✓ Are order statuses only known values?
  Runs at: transformation time (during dbt run)

GREAT EXPECTATIONS — check business logic:
  ✓ Does the table have enough rows (not just present, but realistic)?
  ✓ Are values within physically possible ranges?
  ✓ Do the numbers make business sense?
  Runs at: validation time (after dbt run, before dashboard updates)

TOGETHER: If dbt run succeeds but produces an empty table somehow,
dbt tests would catch null values but GE catches the row count problem.
```

## Key GE Concepts

```python
import great_expectations as gx

# ── DATA CONTEXT ───────────────────────────────────────────────
# The context is the central object that manages everything
# It reads from the gx/ folder created by great_expectations init
context = gx.get_context()

# ── DATASOURCE ─────────────────────────────────────────────────
# Tells GE where your data lives (connects to Supabase)
datasource = context.sources.add_or_update_sql(
    name="my_datasource_name",
    connection_string=DATABASE_URL  # from environment variable, not hardcoded
)

# ── ASSET ──────────────────────────────────────────────────────
# A specific table you want to validate
asset = datasource.add_table_asset(
    name="mart_sales",       # what to call this asset
    schema_name="public_marts",  # which database schema
    table_name="mart_sales"   # the actual table name
)

# ── BATCH REQUEST ──────────────────────────────────────────────
# Tells GE which data to validate (all rows in this case)
batch_request = asset.build_batch_request()

# ── EXPECTATION SUITE ──────────────────────────────────────────
# A named collection of expectations (rules)
suite = context.add_expectation_suite("mart_sales_suite")

# ── VALIDATOR ──────────────────────────────────────────────────
# The object you use to write and run expectations
validator = context.get_validator(
    batch_request=batch_request,
    expectation_suite=suite
)
```

## Expectation Types Reference

```python
# ── ROW COUNT EXPECTATIONS ─────────────────────────────────────
# At least 90,000 rows (catches empty or near-empty tables)
validator.expect_table_row_count_to_be_between(min_value=90000)

# Exactly 27 rows (Brazil has exactly 27 states)
validator.expect_table_row_count_to_equal(value=27)

# ── NULL EXPECTATIONS ──────────────────────────────────────────
# This column must never contain NULL
validator.expect_column_values_to_not_be_null(column="order_id")

# ── RANGE EXPECTATIONS ─────────────────────────────────────────
# Values must be within this range
validator.expect_column_values_to_be_between(
    column="payment_value",
    min_value=0      # payment can never be negative
)

validator.expect_column_values_to_be_between(
    column="review_score",
    min_value=1,
    max_value=5      # star ratings are 1-5 only
)

# ── UNIQUENESS EXPECTATIONS ────────────────────────────────────
# No two rows can have the same value in this column
validator.expect_column_values_to_be_unique(column="order_id")

# ── SET MEMBERSHIP EXPECTATIONS ────────────────────────────────
# Values must be from this approved list
validator.expect_column_values_to_be_in_set(
    column="customer_segment",
    value_set=["Champions", "At Risk", "Lost", "Hibernating", ...]
)

# ── MOSTLY PARAMETER ───────────────────────────────────────────
# 99% of values must meet this condition (allows for 1% edge cases)
validator.expect_column_values_to_be_between(
    column="fulfilment_days",
    min_value=0,
    max_value=180,
    mostly=0.99  # 99% of rows — 1% allowed to be outside range
)
```

## GE Folder Structure

```
gx/                              # created by: great_expectations init
├── great_expectations.yml       # main config
│   datasources: {}              # we configure datasource in Python code
├── expectations/                # expectation suites stored here
├── checkpoints/                 # checkpoint configs
└── uncommitted/                 # NEVER committed to GitHub
    ├── config_variables.yml     # stores db_url variable (gitignored)
    └── validations/             # validation results
```

## The config_variables.yml File

```yaml
# gx/uncommitted/config_variables.yml
# This file is automatically gitignored by Great Expectations
# The uncommitted/ folder is listed in gx/.gitignore

db_url: postgresql://username:password@host:5432/database
# Your actual connection string goes here
# It is safe because the uncommitted/ folder is never pushed to GitHub
```

## Issues Faced at This Stage

```
ISSUE: "Cannot initialize datasource" password authentication failed
CAUSE: Wrong password in config_variables.yml
FIX:   Copy exact connection string from Supabase dashboard
       Settings → Database → Connection String

ISSUE: "The command datasource does not exist" CLI error
CAUSE: GE v0.18 changed the CLI commands
FIX:   Use Python API instead of CLI
       Write a Python script (setup_expectations.py) to configure GE
       This is more reliable and reproducible anyway

ISSUE: credentials hardcoded in great_expectations.yml and pushed to GitHub
CAUSE: Manually added datasource config to the YAML file
FIX:   Replace hardcoded URL with ${db_url} variable reference
       This tells GE to look in config_variables.yml for the value
       Then run: git rm --cached gx/great_expectations.yml
       Add gx/great_expectations.yml to .gitignore
       Commit and push the fix

ISSUE: "Trying to update datasource but it is not the correct type"
CAUSE: setup_expectations.py used add_or_update_sql
       validate_expectations.py used add_or_update_postgres
       These are different datasource types — they conflict
FIX:   Use the same method in both scripts
       Both should use: context.sources.add_or_update_sql(...)
```

---

# 9. STAGE 6 — PYTHON ANALYTICS

## The Analytics Stack

```
pandas  → manipulate tabular data (like Excel in Python)
numpy   → mathematical operations on arrays of numbers
plotly  → create interactive charts
SQLAlchemy → connect Python to the database
```

## pandas — Key Concepts

```python
import pandas as pd

# ── READING DATA ───────────────────────────────────────────────
# Read from database
df = pd.read_sql("SELECT * FROM public_marts.mart_rfm", engine)

# Read from CSV
df = pd.read_csv("reports/monthly_kpis.csv")

# ── EXPLORING DATA ─────────────────────────────────────────────
df.head()        # first 5 rows
df.tail()        # last 5 rows
df.shape         # (rows, columns)
df.dtypes        # data type of each column
df.describe()    # summary statistics for numeric columns
df.info()        # column info and null counts

# ── SELECTING DATA ─────────────────────────────────────────────
# One column (returns a Series)
revenue = df["payment_value"]

# Multiple columns (returns a DataFrame)
subset = df[["order_id", "payment_value", "year_month"]]

# ── FILTERING ROWS ─────────────────────────────────────────────
delivered = df[df["order_status"] == "delivered"]
high_value = df[df["payment_value"] > 500]
champions = df[df["customer_segment"] == "Champions"]

# Multiple conditions (use & for AND, | for OR)
delivered_sp = df[
    (df["order_status"] == "delivered") &
    (df["customer_state"] == "SP")
]

# ── AGGREGATING ────────────────────────────────────────────────
total_revenue = df["payment_value"].sum()
avg_order = df["payment_value"].mean()
max_order = df["payment_value"].max()
customer_count = df["customer_unique_id"].nunique()  # count distinct values

# ── GROUP BY ───────────────────────────────────────────────────
# Group and apply multiple aggregations at once
monthly = df.groupby("year_month").agg(
    revenue      = ("payment_value", "sum"),
    orders       = ("order_id", "count"),
    avg_order    = ("payment_value", "mean"),
    unique_cust  = ("customer_unique_id", "nunique")
)

# ── PIVOT TABLE ────────────────────────────────────────────────
# Reshape data: rows become one axis, columns become another
# Used for cohort retention matrix
matrix = df.pivot_table(
    index="cohort_label",                    # rows
    columns="months_since_first_purchase",   # columns
    values="retention_rate"                  # values in cells
)

# ── ROLLING CALCULATIONS ───────────────────────────────────────
# 3-month moving average
df["moving_avg_3m"] = df["total_revenue"].rolling(window=3).mean()

# Month-over-month percentage change
df["mom_growth"] = df["total_revenue"].pct_change() * 100
```

## Plotly — Creating Charts

```python
import plotly.express as px
import plotly.graph_objects as go

# ── BAR CHART ──────────────────────────────────────────────────
fig = px.bar(
    df,                            # the data
    x="year_month",                # x-axis column
    y="total_revenue",             # y-axis column
    title="Monthly Revenue (R$)",  # chart title
    color_discrete_sequence=["#1D9E75"],  # bar colour
    labels={                       # rename axis labels
        "year_month": "Month",
        "total_revenue": "Revenue (R$)"
    }
)
fig.update_layout(
    plot_bgcolor="white",    # white chart background
    paper_bgcolor="white",   # white surrounding area
    margin=dict(t=50, b=60, l=60, r=20)  # top/bottom/left/right margins
)

# ── LINE CHART ─────────────────────────────────────────────────
fig = px.line(df, x="year_month", y="avg_order_value", markers=True)

# ── SCATTER PLOT ───────────────────────────────────────────────
fig = px.scatter(
    df,
    x="total_revenue",
    y="avg_review_score",
    size="total_orders",       # bubble size = order volume
    hover_name="category_name" # what shows on hover
)

# ── HEATMAP ────────────────────────────────────────────────────
fig = go.Figure(go.Heatmap(
    z=matrix.values,           # the data (2D array)
    x=column_labels,           # x-axis labels
    y=row_labels,              # y-axis labels
    colorscale=[[0, "white"], [1, "#1D9E75"]],  # white to green
    zmin=0, zmax=100           # value range for colour scale
))

# ── ADDING ANNOTATIONS ─────────────────────────────────────────
# Add a text annotation pointing to a specific data point
fig.add_annotation(
    x="2017-11",          # x position
    y=1153528,            # y position
    text="Black Friday",  # annotation text
    showarrow=True,       # draw arrow pointing to the point
    arrowhead=2
)

# ── SAVING CHARTS ──────────────────────────────────────────────
fig.write_image("reports/chart_name.png", scale=2)  # high resolution PNG
```

## Issues Faced at This Stage

```
ISSUE: ModuleNotFoundError: No module named 'analytics'
CAUSE: Python does not automatically search parent directories for modules
FIX:   Add the project root to Python's search path at the top of each script
       import sys, os
       sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
       Now Python looks in e_com_analyser/ for the analytics package

ISSUE: __init__.py missing, analytics not recognised as a package
CAUSE: Python requires an __init__.py file to treat a folder as a package
FIX:   Create an empty file named __init__.py in the analytics/ folder
       The file can be completely empty — its presence is what matters

ISSUE: AttributeError: 'Engine' object has no attribute 'cursor'
CAUSE: pandas read_sql and to_sql changed in SQLAlchemy 2.x
       They no longer accept raw engine objects in the same way
FIX:   Use engine.connect() as a context manager
       with engine.connect() as conn:
           df = pd.read_sql(sql, conn)
       Or for writing: use engine.begin() for auto-commit
       with engine.begin() as conn:
           df.to_sql(name, conn, ...)
```

---

# 10. STAGE 7 — FORECASTING (PROPHET)

## What is Time Series Forecasting?

Using historical data to predict future values.

```
HISTORICAL DATA:
  Jan 2017: R$127k
  Feb 2017: R$271k
  Mar 2017: R$414k
  ...
  Aug 2018: R$985k

FORECAST:
  Sep 2018: R$1,314k (predicted)
  Oct 2018: R$1,366k (predicted)
```

## Why Prophet (Not a Traditional ML Model)?

```
TRADITIONAL ML (e.g. XGBoost):
  Needs multiple input features (columns)
  Needs manual feature engineering:
    - lag values (revenue 1 month ago)
    - rolling averages
    - month-of-year encoding
    - seasonality indicators
  Does not naturally produce confidence intervals
  Requires train/test split setup

PROPHET:
  Only needs two columns: date and value
  Automatically learns trend, seasonality, holidays
  Automatically produces confidence intervals
  Designed specifically for business time series
  Works well with limited data (22 months in our case)

RULE OF THUMB:
  Forecasting one number over time → Prophet
  Predicting outcome from many features → XGBoost/Random Forest
```

## How Prophet Decomposes a Time Series

```
                    ACTUAL REVENUE
                         │
            ┌────────────┼─────────────────┐
            │            │                 │
         TREND      SEASONALITY      RANDOM NOISE
            │            │                 │
   Overall direction  Repeating      Unpredictable
   (growing or       patterns       variation
   declining)        (Black Friday
                     every Nov)
```

## Prophet Syntax Reference

```python
from prophet import Prophet
import pandas as pd

# ── DATA FORMAT ────────────────────────────────────────────────
# Prophet requires EXACTLY these two column names:
# ds = dates (datestamp)
# y = values to forecast
df = pd.DataFrame({
    "ds": pd.to_datetime(["2017-01-01", "2017-02-01", "2017-03-01"]),
    "y":  [127545, 271298, 414369]
})

# ── CREATE THE MODEL ───────────────────────────────────────────
model = Prophet(
    yearly_seasonality=True,   # learn annual patterns (needs 2+ years)
    weekly_seasonality=False,  # no weekly pattern (monthly data)
    daily_seasonality=False,   # no daily pattern (monthly data)
    interval_width=0.95,       # 95% confidence interval
    seasonality_mode="additive"  # safer for short datasets
    # "multiplicative" can cause wild oscillations on limited data
)

# ── FIT THE MODEL ──────────────────────────────────────────────
# This is where Prophet learns from your historical data
model.fit(df)

# ── CREATE FUTURE DATES ────────────────────────────────────────
# periods=2 means 2 future months to forecast
# freq="MS" means Monthly Start (first day of each month)
future = model.make_future_dataframe(periods=2, freq="MS")

# ── GENERATE FORECAST ──────────────────────────────────────────
forecast = model.predict(future)

# forecast contains these key columns:
# ds         → the date
# yhat       → predicted value (most likely)
# yhat_lower → lower bound (pessimistic scenario)
# yhat_upper → upper bound (optimistic scenario)
# trend      → the trend component
# yearly     → the yearly seasonal component
```

## Evaluation Metrics

```python
import numpy as np

actuals = historical_data["y"].values
predicted = forecast_on_historical["yhat"].values

# ── MAE: Mean Absolute Error ───────────────────────────────────
# Average absolute difference between actual and predicted
# In same units as your data (R$ in our case)
# MAE = R$93,000 means model is off by R$93k on average
mae = np.mean(np.abs(actuals - predicted))

# ── MAPE: Mean Absolute Percentage Error ───────────────────────
# Average percentage difference between actual and predicted
# 14.9% means model is off by about 15% on average
# Industry benchmarks:
#   < 10%  → excellent
#   10-20% → good (acceptable for business forecasting)
#   20-50% → reasonable, use with caution
#   > 50%  → poor, not reliable
mape = np.mean(np.abs((actuals - predicted) / actuals)) * 100
```

## Issues Faced at This Stage

```
ISSUE: Prophet giving negative revenue forecast for November 2018
CAUSE: seasonality_mode="multiplicative" with only 22 months of data
       One Black Friday spike caused multiplicative seasonality to amplify
       wildly, producing negative values
FIX:   Switch to seasonality_mode="additive"
       Additive: forecast = trend + seasonal_amount (fixed addition)
       Multiplicative: forecast = trend × seasonal_factor (can amplify)
       Additive is safer when data is limited

ISSUE: MAPE of 46,000% on first run
CAUSE: Early months had near-zero revenue (R$19, R$46k)
       Dividing a small error by a tiny actual value = enormous percentage
       Example: actual=19, predicted=100, error=81, MAPE = 81/19 * 100 = 426%
FIX:   Filter to months with revenue > R$100,000 before calculating MAPE
       mask = actuals > 100000
       mape = np.mean(np.abs((actuals[mask] - predicted[mask]) / actuals[mask])) * 100

ISSUE: Prophet model producing perfectly straight line forecast
CAUSE: All seasonality turned off, only trend component active
EXPLANATION: This is technically correct but visually unimpressive
       With only 22 months, one November spike is not enough to teach
       Prophet that November is always bigger (might be coincidence)
DECISION: Keep the straight trend line and document the limitation
           A conservative honest forecast is better than an overconfident wrong one
           Turned off yearly seasonality because it caused overfitting

ISSUE: AttributeError: 'Prophet' object has no attribute 'stan_backend'
CAUSE: CmdStan (Prophet's statistical engine) not properly installed
FIX:   Install via conda instead of pip
       conda install -c conda-forge prophet -y
       Conda handles all compiled C++ dependencies automatically
```

---

# 11. STAGE 8 — REST API (FASTAPI)

## What is a REST API?

An API lets programs talk to each other over the internet.
REST is a standard set of rules for how that conversation should work.

```
ANALOGY: Restaurant
  Customer (Dashboard) → asks waiter (API) for the bill
  Waiter (API) → goes to kitchen (Database) → gets the data
  Waiter (API) → brings back the bill (JSON data)
  Customer (Dashboard) → reads the bill → displays it

WHY NOT go directly to the kitchen?
  → Security: kitchen credentials not needed by customer
  → Control: waiter decides what can be ordered
  → Flexibility: any customer (app, website, mobile) uses same waiter
```

## HTTP Methods

```
GET    → Read data       (most common, what we use)
POST   → Create data
PUT    → Update data
DELETE → Remove data

Our API uses ONLY GET because we never modify data
```

## FastAPI Application Structure

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

# ── CREATE APP ─────────────────────────────────────────────────
app = FastAPI(
    title="My API",           # appears in /docs
    description="What it does",
    version="1.0.0"
)

# ── CORS MIDDLEWARE ────────────────────────────────────────────
# CORS = Cross-Origin Resource Sharing
# Problem: browser blocks requests between different URLs
#   Dashboard at: https://myapp.onrender.com (port 443)
#   API at:       https://myapi.onrender.com (port 443)
#   Even though same protocol, different domains → blocked
# Solution: tell the browser this is intentional
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # allow any origin (relax in production)
    allow_methods=["*"],      # allow GET, POST, etc.
    allow_headers=["*"]       # allow any headers
)

# ── HELPER FUNCTION ────────────────────────────────────────────
def query(sql: str) -> list[dict]:
    """
    Run SQL and return results as list of dictionaries.
    FastAPI automatically converts list of dicts to JSON array.
    """
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        columns = list(result.keys())      # get column names
        rows = result.fetchall()            # get all rows
    # zip pairs column names with values: [("col1", val1), ("col2", val2)]
    # dict() converts pairs to dictionary: {"col1": val1, "col2": val2}
    return [dict(zip(columns, row)) for row in rows]

# ── DEFINING ENDPOINTS ─────────────────────────────────────────
# @app.get("/path") is a decorator
# It tells FastAPI: when someone sends GET /path, call this function

@app.get("/health")
def health_check():
    # Return dict → FastAPI converts to JSON
    return {"status": "ok"}

@app.get("/kpis")
def get_kpis():
    rows = query("SELECT SUM(payment_value) AS revenue FROM mart_sales")
    return rows[0]  # return first (only) row as a single dict

@app.get("/revenue/monthly")
def get_monthly_revenue():
    return query("""
        SELECT year_month, SUM(payment_value) AS revenue
        FROM public_marts.mart_sales
        GROUP BY year_month
        ORDER BY year_month
    """)
    # returns list of dicts → FastAPI converts to JSON array
```

## Running FastAPI

```bash
# Development (with hot reload — restarts when code changes)
uvicorn api.main:app --reload

# Production (on Render)
uvicorn api.main:app --host 0.0.0.0 --port $PORT
# --host 0.0.0.0 means listen on all network interfaces (required for cloud)
# --port $PORT uses the port Render assigns (not fixed port 8000)
```

## Testing Your API

```bash
# In a browser or terminal:
http://localhost:8000/health         # should return {"status": "ok"}
http://localhost:8000/kpis           # should return KPI numbers
http://localhost:8000/docs           # interactive documentation (Swagger UI)
http://localhost:8000/redoc          # alternative documentation style
```

## Issues Faced at This Stage

```
ISSUE: 500 Internal Server Error on all endpoints
CAUSE: pandas read_sql failing with SQLAlchemy 2.x engine object
ERROR: AttributeError: 'Connection' object has no attribute 'cursor'
FIX:   Stop using pandas for the API entirely
       Use SQLAlchemy directly instead:
       with engine.connect() as conn:
           result = conn.execute(text(sql))
       Convert rows to dicts manually using zip()
       This is actually cleaner and avoids the pandas/SQLAlchemy version conflict
```

---

# 12. STAGE 9 — DASHBOARD (PLOTLY DASH)

## What is Plotly Dash?

Dash lets you build interactive web dashboards using only Python.
No HTML, CSS, or JavaScript required.

```
Under the hood, Dash is built on:
  Flask → the web server (serves HTML to browsers)
  React → the JavaScript framework (makes it interactive)
  Plotly → the charting library (draws the charts)

You write Python → Dash converts it to all of the above
```

## Dash Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    USER'S BROWSER                       │
│                                                         │
│  User clicks "RFM" tab                                  │
│         │                                               │
│         ▼                                               │
│  Dash sends Input event to Python server                │
└─────────────────────────────────────────────────────────┘
                        │
                        ▼ (via HTTP)
┌─────────────────────────────────────────────────────────┐
│                   DASH/FLASK SERVER                     │
│                                                         │
│  Callback function runs: render_tab("rfm")             │
│  → build_rfm() calls fetch("/rfm/segments")            │
│  → FastAPI queries Supabase                             │
│  → Returns JSON data                                    │
│  → Dash builds Plotly charts from data                 │
│  → Returns HTML to browser                             │
└─────────────────────────────────────────────────────────┘
```

## Key Dash Components

```python
from dash import dcc, html
import dash_bootstrap_components as dbc

# ── html.* — standard HTML elements ────────────────────────────
html.Div(children=[...], style={"color": "red"})  # container
html.H1("Big Heading")                            # heading
html.P("Paragraph text")                          # paragraph
html.Span("Inline text")                          # inline
html.Ul([html.Li("item 1"), html.Li("item 2")])  # list

# ── dcc.* — Dash Core Components (interactive) ─────────────────
dcc.Graph(figure=fig)          # renders a Plotly chart
dcc.Tabs(id="tabs", ...)       # tab navigation
dcc.Tab(label="Name", value="key")   # individual tab
dcc.Dropdown(options=[...])    # dropdown menu
dcc.DatePickerRange(...)       # date picker

# ── dbc.* — Dash Bootstrap Components (layout) ─────────────────
dbc.Row([col1, col2])          # horizontal row
dbc.Col(content, width=6)      # column (max 12 per row)
dbc.Navbar(...)                # navigation bar
dbc.Container(content)         # responsive container
```

## Bootstrap Grid System

```
Bootstrap uses a 12-column grid.
Each row has 12 units of width to distribute.

width=12  → full width (one column taking entire row)
width=6   → half width (two columns side by side)
width=4   → one-third width (three columns side by side)
width=3   → one-quarter width (four columns)
width=2   → one-sixth width (six columns, like KPI cards)

EXAMPLE: Two charts side by side
dbc.Row([
    dbc.Col(left_chart, width=6),   # 6/12 = 50%
    dbc.Col(right_chart, width=6)   # 6/12 = 50%
])

EXAMPLE: Three charts in a row
dbc.Row([
    dbc.Col(chart1, width=4),  # 4/12 = 33%
    dbc.Col(chart2, width=4),  # 4/12 = 33%
    dbc.Col(chart3, width=4)   # 4/12 = 33%
])
```

## Callbacks — Making it Interactive

```python
from dash.dependencies import Input, Output

# @app.callback decorator connects components
# When an Input changes → run this function → update the Output

@app.callback(
    Output("tab-content", "children"),  # update the 'children' of this component
    Input("tabs", "value")              # when the 'value' of this component changes
)
def render_tab(selected_tab_value):
    # selected_tab_value is whatever tab the user clicked
    if selected_tab_value == "overview":
        return build_overview()  # return the overview page layout
    if selected_tab_value == "rfm":
        return build_rfm()
    # etc.
```

## Deploying Dash with Gunicorn

```python
# In app.py, you must expose the Flask server object:
app = dash.Dash(__name__, ...)
server = app.server  # THIS LINE is required for production deployment

# Gunicorn needs 'server', not 'app'
# Because gunicorn is a WSGI server that works with Flask
# Dash wraps Flask — server exposes the underlying Flask app

# Start command for Render:
# gunicorn dashboard.app:server --bind 0.0.0.0:$PORT
#          ^              ^
#          module         attribute (the Flask server object)
```

## Issues Faced at This Stage

```
ISSUE: Brazil states not showing on choropleth map
CAUSE: Plotly's built-in choropleth does not have Brazilian state boundaries
       locationmode="geojson-id" with state codes like "SP", "RJ" not recognised
FIX:   Replace choropleth with treemap
       Treemap shows the same information (relative revenue by state)
       More visually impactful — SP dominance immediately obvious
       No external GeoJSON file needed

ISSUE: RFM bar chart labels cut off ("46" instead of "46,254")
CAUSE: Chart margin too small — labels extend beyond chart boundary
FIX:   Increase right margin and extend x-axis range
       fig.update_layout(margin=dict(r=100))
       fig.update_xaxes(range=[0, max_value * 1.25])

ISSUE: AOV chart showing spike down to R$0 at start
CAUSE: Early months had near-zero revenue (one order worth R$19)
       Average of one tiny order = tiny AOV
FIX:   Filter to months with revenue > R$50,000 for AOV chart
       df_clean = df[df["total_revenue"] > 50000].copy()
       Plot df_clean instead of df for AOV chart
       Also fix y-axis range: yaxis_range=[100, 220]
```

---

# 13. STAGE 10 — PIPELINE ORCHESTRATION

## What is Orchestration?

Orchestration means automating a sequence of tasks and managing
what happens when things succeed or fail.

```
WITHOUT orchestration:
  Every morning, manually:
    1. Open terminal
    2. cd dbt_project/olist_bi
    3. Run dbt run
    4. Wait 3 minutes
    5. Run dbt test
    6. Wait 1 minute
    7. Run python great_expectations/validate_expectations.py
    8. Wait 2 minutes
    9. Run python analytics/forecast.py
    10. Wait 2 minutes
    Human error possible at any step

WITH orchestration:
  Happens automatically at 6am every day
  Stops immediately if any step fails
  Logs everything for debugging
  No human involvement needed
```

## Airflow Concepts

```
DAG (Directed Acyclic Graph):
  A pipeline defined in Python code
  "Directed" = tasks flow in one direction
  "Acyclic" = no loops (cannot go backwards)
  "Graph" = connected nodes (tasks)

TASK:
  One unit of work in a pipeline
  Can be: run a shell command, call a Python function, query a database

OPERATOR:
  The type of task
  BashOperator → runs a shell command
  PythonOperator → runs a Python function
  SQLOperator → runs SQL

DEPENDENCY:
  task_a >> task_b  means "run task_b after task_a"
  task_a >> [task_b, task_c]  means "run both after task_a"
```

## Airflow DAG Syntax

```python
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

# Default settings applied to all tasks
default_args = {
    "owner": "your-name",
    "retries": 1,                        # retry once if it fails
    "retry_delay": timedelta(minutes=5)  # wait 5 minutes before retry
}

# Create the DAG
with DAG(
    dag_id="my_pipeline",        # unique name
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    schedule_interval="0 6 * * *",  # cron: run at 6am daily
    catchup=False                   # don't run for missed days
) as dag:

    # Define tasks
    task_1 = BashOperator(
        task_id="run_dbt",
        bash_command="cd /path/to/dbt && dbt run"
    )

    task_2 = BashOperator(
        task_id="test_dbt",
        bash_command="cd /path/to/dbt && dbt test"
    )

    task_3 = BashOperator(
        task_id="validate_data",
        bash_command="python /path/to/validate_expectations.py"
    )

    # Set execution order
    task_1 >> task_2 >> task_3
    # task_1 runs first, then task_2, then task_3
```

## GitHub Actions — The Production Scheduler

### Why GitHub Actions Instead of Airflow for Production?

```
AIRFLOW:
  Needs a server to run on (not free)
  Complex setup, especially on Windows
  Excellent for complex enterprise pipelines
  Great for learning and CV

GITHUB ACTIONS:
  Runs on GitHub's free cloud servers
  Simple YAML configuration
  Automatic when you push code
  Free for public repositories
  → Used for actual production scheduling in this project
```

### YAML Syntax for Workflows

```yaml
# Pipeline runs at 6am UTC every day
# Also can be triggered manually from GitHub UI

name: My Pipeline              # Name shown in GitHub Actions tab

on:                            # When to trigger this workflow
  schedule:
    - cron: "0 6 * * *"       # cron expression (see below)
  workflow_dispatch:           # adds a manual "Run workflow" button

jobs:                          # What to do when triggered
  run_pipeline:                # job name (can be anything)
    runs-on: ubuntu-latest     # what type of machine to use

    steps:                     # ordered list of tasks
      - name: Step description # what shows in the logs
        uses: action/name@v4   # use a pre-built action
        # OR
        run: shell command      # run a terminal command
```

### Understanding Cron Expressions

```
Format: minute  hour  day_of_month  month  day_of_week

0  6  *  *  *
│  │  │  │  └─ any day of week (* = Monday through Sunday)
│  │  │  └──── any month (* = January through December)
│  │  └─────── any day of month (* = 1st through 31st)
│  └────────── hour 6 (6am)
└───────────── minute 0 (exactly on the hour)

Result: runs at 6:00am every single day

Other examples:
  0 */6 * * *   → every 6 hours (midnight, 6am, noon, 6pm)
  0 9 * * 1     → every Monday at 9am (1 = Monday)
  0 0 1 * *     → first day of every month at midnight
  */15 * * * *  → every 15 minutes
```

### GitHub Secrets

```
Secrets are encrypted credentials stored in your GitHub repository.
They are:
  - Encrypted when saved (GitHub cannot read them)
  - Only decrypted inside running Actions workflows
  - Never visible in logs (GitHub masks them with ***)
  - Safe in public repositories

How to add a secret:
  1. GitHub repo → Settings → Secrets and variables → Actions
  2. Click "New repository secret"
  3. Name: DB_PASSWORD
  4. Value: your actual password
  5. Click "Add secret"

How to use in workflow:
  ${{ secrets.DB_PASSWORD }}

Example in pipeline.yml:
  - name: Create .env file
    run: echo "DATABASE_URL=${{ secrets.DATABASE_URL }}" > .env
    # The actual value is injected at runtime
    # The log shows: echo "DATABASE_URL=***" > .env
```

## Issues Faced at This Stage

```
ISSUE: Airflow db init failing with SQLite path error on Windows
ERROR: Cannot use relative path: sqlite:///C:\Users\Name/airflow/airflow.db
CAUSE: Airflow uses Unix-style paths internally, Windows uses backslashes
       The combination creates an invalid path
FIX ATTEMPTS:
  1. set AIRFLOW_HOME=C:\Users\Name\airflow → still failed
  2. set AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=sqlite:////C:/... → partially worked
  3. Still hitting connection errors
FINAL DECISION:
  Write the Airflow DAG code (demonstrates knowledge)
  Skip running it locally (Windows limitation)
  Use GitHub Actions for actual automation (cloud-native, no Windows issues)

ISSUE: GitHub Actions "Failed to queue workflow run"
CAUSE: GitHub Actions service was experiencing a platform-wide outage
EVIDENCE: githubstatus.com showed:
  Actions: 🔴 Incident — degraded availability
  Pages: 🟡 Degraded
  Started: May 26, 2026 at 10:57 UTC
FIX: Wait for GitHub to resolve the outage
     All workflow files were correct — not a code issue
LESSON: Always check githubstatus.com before debugging your workflow files
```

---

# 14. STAGE 11 — DEPLOYMENT (RENDER)

## What is Deployment?

Taking code that works on your laptop and making it available
to everyone on the internet, running 24/7 without your laptop.

```
BEFORE deployment:
  http://localhost:8050       → only you can see this
  Requires your laptop to be on
  Requires the server script to be running

AFTER deployment:
  https://yourapp.onrender.com → anyone in the world can see this
  Runs on Render's servers 24/7
  Your laptop can be completely off
```

## Render — The Hosting Platform

```
RENDER FREE TIER:
  ✓ 2 Web Services (we used both)
  ✓ Automatic GitHub deployment
  ✓ HTTPS by default
  ✓ 750 hours/month (enough for 24/7)

LIMITATION:
  Services spin down after 15 minutes of inactivity
  First request after sleeping = 30-50 seconds wake-up time
  Paid tier stays awake permanently

HOW AUTO-DEPLOY WORKS:
  1. You push code to GitHub
  2. Render detects new commit (via webhook)
  3. Render clones your repository
  4. Render runs your build command
  5. Render starts your app with the start command
  6. New version is live
```

## Service 1 — FastAPI Deployment

```
Name: ecom-bi-api
Build command: pip install -r requirements.txt
Start command: uvicorn api.main:app --host 0.0.0.0 --port $PORT

Why --host 0.0.0.0?
  Default: listens on 127.0.0.1 (only localhost, only your machine)
  With 0.0.0.0: listens on all network interfaces (required for Render)

Why --port $PORT?
  Render assigns a random port number
  $PORT is an environment variable Render sets automatically
  We cannot hardcode port 8000 — Render's load balancer handles that

Environment variables to add in Render:
  DATABASE_URL = your Supabase connection string
  (stored encrypted in Render, never in code)
```

## Service 2 — Dash Dashboard Deployment

```
Name: ecom-bi-dashboard
Build command: pip install -r requirements.txt
Start command: gunicorn dashboard.app:server --bind 0.0.0.0:$PORT

Why gunicorn instead of python app.py?
  python app.py → development server, not designed for production traffic
  gunicorn → production WSGI server, handles concurrent requests properly

Why 'server' not 'app'?
  gunicorn works with WSGI (Web Server Gateway Interface) applications
  Dash is built on Flask (a WSGI framework)
  'server = app.server' exposes the underlying Flask WSGI app
  gunicorn serves the Flask app, not the Dash wrapper

Environment variables to add in Render:
  API_URL = https://ecom-bi-api.onrender.com
  (tells the dashboard where the API lives)
```

## The Python Version Fix

```
PROBLEM:
  Render uses latest Python by default (Python 3.14)
  pandas 2.1.4 does not support Python 3.14 yet
  Build fails with Cython compilation errors

SOLUTION:
  Create .python-version file in project root
  Contents: 3.11.0
  This single file tells Render exactly which Python to use

File location: e_com_analyser/.python-version
File contents: 3.11.0
```

## Issues Faced at This Stage

```
ISSUE: Build failed — pandas compilation error
ERROR: FAILED: pandas/_libs/tslibs/base.cpython-314-x86_64-linux-gnu.so
CAUSE: Render used Python 3.14, pandas 2.1.4 not yet compatible
FIX:   Add .python-version file to project root
       Contents: 3.11.0
       Render reads this file and uses Python 3.11 instead

ISSUE: "gunicorn: command not found"
CAUSE: gunicorn not in requirements.txt
FIX:   Add to requirements.txt: gunicorn==21.2.0
       Push to GitHub, Render auto-redeploys

ISSUE: "Failed to find attribute 'server' in 'dashboard.app'"
CAUSE: server = app.server line was missing from app.py
FIX:   Add right after app = dash.Dash(...):
       server = app.server
       This is REQUIRED for gunicorn to work with Dash

ISSUE: Dashboard showing no data / charts empty
CAUSE: API_URL environment variable not set in Render
       Dashboard defaulted to http://localhost:8000 (doesn't exist on Render)
FIX:   Add environment variable in Render dashboard:
       API_URL = https://ecom-bi-api.onrender.com
       Code uses: API_URL = os.getenv("API_URL", "http://localhost:8000")
       Locally: uses localhost (the default)
       On Render: uses the live API URL (from environment variable)
```

---

# 15. BUSINESS INSIGHTS

## What the Data Tells Us

```
┌─────────────────────────────────────────────────────────────────┐
│                    HEADLINE KPIs                                │
├─────────────────────────┬───────────────────────────────────────┤
│  Total Revenue          │  R$15,422,462                        │
│  Total Orders           │  96,478 (delivered only)             │
│  Unique Customers       │  93,358                              │
│  Avg Order Value        │  R$159.85                            │
│  Avg Delivery Time      │  12.1 days                           │
│  On-time Delivery Rate  │  91.9%                               │
└─────────────────────────┴───────────────────────────────────────┘
```

## Insight 1 — Single Purchase Business

```
FINDING:
  96,478 orders from 93,358 customers
  = average 1.03 orders per customer
  Cohort retention under 1% after Month 0

WHAT THIS MEANS:
  Almost every customer buys exactly once
  There is no repeat purchase engine
  Every R$1 of future revenue needs a new customer

BUSINESS DECISION:
  Do NOT invest in loyalty programmes or CRM tools
  DO invest in customer acquisition marketing
  Focus on conversion rate and first-order experience
```

## Insight 2 — Champion Concentration

```
FINDING:
  Champions = 10.2% of customers, 23.4% of revenue
  Champion avg spend: R$377 vs platform avg R$160

WHAT THIS MEANS:
  A small loyal minority drives disproportionate value
  Losing 20% of Champions = losing ~4.7% of total revenue

BUSINESS DECISION:
  Identify and treat Champions differently
  Priority customer support
  Early access to new products
  Personalised loyalty rewards
```

## Insight 3 — Black Friday Dependency

```
FINDING:
  November 2017: R$1,153,528 (best month)
  October 2017:  R$751,140
  Growth: +53.6% in one month

WHAT THIS MEANS:
  Business is dangerously dependent on one annual event
  If Black Friday underperforms, the annual target is at risk

BUSINESS DECISION:
  Diversify revenue through non-seasonal campaigns
  Build a Q1/Q2 promotion strategy
  Don't rely on November to save the year
```

## Insight 4 — Geographic Concentration

```
FINDING:
  São Paulo (SP): R$5,998,227 (39% of all revenue)
  Rio de Janeiro (RJ): R$2,144,380 (14%)
  All other 25 states: R$7,280,000 (47%)

WHAT THIS MEANS:
  Top 2 states = 53% of revenue
  Massive untapped potential in other regions

BUSINESS DECISION:
  Regional expansion strategy
  Target: RS, MG, PR for growth (already showing revenue)
  North/Northeast logistics improvement needed first
```

## Insight 5 — The Delivery Inequality

```
FASTEST:
  São Paulo region: ~8 days

SLOWEST:
  Roraima (RR): 29 days
  Amapá (AP): 27 days
  Amazonas (AM): 26 days

PATTERN: All slowest states are in North/Northeast Brazil
         These states are geographically far from São Paulo
         where most sellers are based

WHAT THIS MEANS:
  Customers in remote states wait 3.5x longer than SP customers
  This suppresses demand in those regions
  People in RR may avoid Olist because delivery is too slow

BUSINESS DECISION:
  Partner with regional logistics providers in the North
  Set up distribution centres outside São Paulo
  Consider different delivery promises per region
```

## Insight 6 — The Boleto Market

```
FINDING:
  19.9% of orders paid by boleto
  (Brazilian bank slip payment, used by unbanked population)

WHAT THIS MEANS:
  1 in 5 Olist customers does not have a credit card
  Olist is reaching a demographic competitors ignore
  This is a social impact story AND a competitive advantage

BUSINESS DECISION:
  Double down on boleto acceptance
  Market specifically to unbanked population
  Don't remove boleto to "simplify payments" — it would cut 20% of revenue
```

---

# 16. COMMON ISSUES AND FIXES REFERENCE

## Database Connection Issues

```
SYMPTOM: Connection timeout or refused
CHECK:   Is the database URL correct?
         Are you using session pooler URL (not direct connection)?
         Is your .env file being loaded? (python-dotenv installed?)

SYMPTOM: Password authentication failed
CHECK:   Did you copy the exact password from Supabase?
         Did you reset the password after a security incident?
         Is the password URL-encoded? (@ in password needs %40)

SYMPTOM: SSL/TLS errors
CHECK:   Add ?sslmode=require to the end of your connection string
```

## dbt Issues

```
SYMPTOM: No dbt_project.yml found
CHECK:   Are you running from inside dbt_project/olist_bi/?
         Not from e_com_analyser/ or deeper into models/

SYMPTOM: Column X does not exist
CHECK:   Run dbt show --select model_name --limit 1 --output json
         This shows exact column names that actually exist
         Update your SQL to use these exact names

SYMPTOM: Source 'olist.table_name' not found
CHECK:   Open schema.yml and check the exact table name listed there
         Your {{ source('olist', 'NAME') }} must match schema.yml exactly

SYMPTOM: PASS=0 WARN=0 ERROR=0 (nothing happened)
CHECK:   Are you running dbt run --select wrong_model_name?
         Does that model file actually exist?
         Check the file name matches exactly
```

## Python/pandas Issues

```
SYMPTOM: ModuleNotFoundError: No module named 'X'
CHECK:   Is the conda environment active? (conda activate ecom-bi)
         Is the package in requirements.txt?
         pip install package_name --break-system-packages

SYMPTOM: AttributeError on SQLAlchemy operations
CHECK:   SQLAlchemy 2.x changed many APIs
         Use engine.connect() or engine.begin() as context managers
         Use text() wrapper for raw SQL strings

SYMPTOM: pandas read_sql gives 'cursor' attribute error
CHECK:   Use engine.connect() context manager when passing to read_sql
         with engine.connect() as conn:
             df = pd.read_sql(sql, conn)
```

## Deployment Issues

```
SYMPTOM: Build fails on Render with Python 3.14 errors
FIX:     Add .python-version file with content: 3.11.0

SYMPTOM: gunicorn command not found
FIX:     Add gunicorn==21.2.0 to requirements.txt

SYMPTOM: "Failed to find attribute 'server'"
FIX:     Add server = app.server to dashboard/app.py after creating app

SYMPTOM: Dashboard shows no data / all charts empty
CHECK:   Is API_URL environment variable set in Render?
         Should be: https://your-api-name.onrender.com
```

---

# 17. KEY CONCEPTS GLOSSARY

```
API          Application Programming Interface
             A way for programs to communicate with each other

CRON         A time scheduling format
             "0 6 * * *" means "run at 6:00am every day"

CSV          Comma-Separated Values
             A simple text file format for tabular data

DAG          Directed Acyclic Graph
             A pipeline of tasks flowing in one direction with no loops

DataFrame    A table of data in Python (from pandas library)
             Rows and columns, like an Excel spreadsheet

dbt          Data Build Tool
             Organises SQL transformations into tested, documented models

Endpoint     A URL that your API responds to
             GET /kpis → returns KPI data as JSON

ENV          Environment variable
             A way to pass configuration/credentials to a program
             without putting them in the code

Git          Version control system
             Tracks all changes to your code over time

GitHub       Website that hosts Git repositories
             Also provides Actions (automation) and Pages (hosting)

Gunicorn     Production Python web server
             More robust than running python app.py directly

JSON         JavaScript Object Notation
             Standard format for data between programs
             {"key": "value", "number": 42}

MAPE         Mean Absolute Percentage Error
             Average percentage error of a forecasting model

Mart         A business-ready analytics table in dbt
             Pre-computed, one row per business entity

Materialize  When dbt saves a model as a view or table in the database

Null         A missing/unknown value in a database
             Different from zero, different from empty string

Orchestration Managing a sequence of automated tasks
             Ensuring correct order and handling failures

pandas       Python library for data manipulation
             DataFrames, filtering, aggregation, time series

PostgreSQL   Open-source relational database
             Industry standard for analytics workloads

Prophet      Facebook's time series forecasting library
             Automatically learns trend and seasonality

REST         Representational State Transfer
             Standard rules for web APIs

RFM          Recency, Frequency, Monetary
             Customer segmentation technique using 3 dimensions

Schema       Organisation structure for database tables
             Like folders: public_staging, public_marts, etc.

SQLAlchemy   Python library for connecting to databases
             Provides engine, session, and connection objects

Supabase     Hosted PostgreSQL service
             Database in the cloud without managing your own server

View         A saved SQL query in the database
             No data stored — runs the query each time it is read

WSGI         Web Server Gateway Interface
             Standard for Python web applications (used by Flask/Dash)

YAML         Yet Another Markup Language
             Human-readable configuration format (indentation matters!)
```

---

*This document is a complete reference for the E-commerce BI Platform project.*
*No credentials or secrets appear anywhere in this document.*
*All code examples use placeholder values or environment variable patterns.*

*Built by Obedh — MSc Data Analytics, Dublin*
*GitHub: https://github.com/Ob09/ecom_intelligence*
