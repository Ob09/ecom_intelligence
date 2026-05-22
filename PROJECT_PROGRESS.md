# E-commerce BI Platform — Project Progress & Architecture

---

## What Each Layer Does

| Layer | Purpose | Status |
|---|---|---|
| **Raw data** | 9 Olist CSV files loaded into Supabase | ✅ Complete |
| **Staging** | Data cleaned, renamed, typed | ✅ Complete |
| **Intermediate** | Tables joined into one enriched model | ✅ Complete |
| **Marts** | Business analytics tables | 🔄 In progress |
| **Quality** | Great Expectations validation | ⏳ Coming |
| **Orchestration** | GitHub Actions pipeline | ⏳ Coming |
| **API** | FastAPI REST layer on Render | ⏳ Coming |
| **Forecasting** | Prophet 30-day revenue forecast | ⏳ Coming |
| **Dashboard** | Plotly Dash on Render | ⏳ Coming |

---

## Is the Data Clean?

**Yes.** Cleaning happened in the staging layer.

- **Staging models** = raw data in, clean data out. Columns renamed, data types cast, nulls handled.
- **Intermediate model** = clean staging tables joined together.
- **Mart models** = enriched data shaped into business-ready analytics tables.

By the time any table reaches the marts layer, it is already clean.

---

## Full Data Flow

```
9 Olist CSV files (Kaggle)
        ↓  load_olist.py
Supabase PostgreSQL (West EU Ireland)
        ↓  dbt run
┌─────────────────────────────────────────┐
│           STAGING LAYER (views)         │
│  stg_orders · stg_customers             │
│  stg_products · stg_sellers             │
│  stg_payments · stg_order_items         │
│  stg_reviews                            │
└─────────────────────────────────────────┘
        ↓  dbt run
┌─────────────────────────────────────────┐
│        INTERMEDIATE LAYER (view)        │
│        int_orders_enriched              │
│  (orders + customers + payments + items)│
└─────────────────────────────────────────┘
        ↓  dbt run
┌─────────────────────────────────────────┐
│           MARTS LAYER (tables)          │
│  mart_sales      ✅  One row per order  │
│  mart_rfm        ← NEXT                 │
│  mart_cohort     ⏳                     │
│  mart_geo        ⏳                     │
│  mart_products   ⏳                     │
└─────────────────────────────────────────┘
        ↓
Great Expectations (data quality checks)
        ↓
GitHub Actions (runs everything on a schedule, cloud only)
        ↓
FastAPI on Render (REST API serving analytics data)
Prophet (30-day revenue forecast)
        ↓
Plotly Dash Dashboard on Render (public URL, 24/7, no PC needed)
```

---

## Deployment — Does It Need My PC?

**No.** Once deployed, nothing depends on your local machine.

| Component | Runs Where | Cost |
|---|---|---|
| PostgreSQL database | Supabase (always online) | Free |
| dbt transformations | GitHub Actions (cloud scheduler) | Free |
| Data quality checks | GitHub Actions | Free |
| Prophet forecasting | GitHub Actions | Free |
| FastAPI REST API | Render | Free |
| Plotly Dash dashboard | Render | Free |
| dbt documentation | GitHub Pages | Free |

**Apache Airflow** is used locally during development only — to learn
pipeline orchestration for your CV and interviews. GitHub Actions is
the real production scheduler and runs entirely in the cloud.

---

## Mart Models — What Each One Does

### mart_sales ✅
- **One row per order**
- Answers: revenue, AOV, fulfilment time, geographic distribution
- Powers: KPI dashboard, revenue charts, time-series analysis

### mart_rfm ← Next
- **One row per customer**
- Scores every customer: Recency + Frequency + Monetary (1–5 each)
- Segments customers: Champions, Loyal, At Risk, Lost, etc.
- Powers: customer segmentation dashboard

### mart_cohort ⏳
- **One row per cohort-month combination**
- Tracks what % of customers from each month are still buying
- Powers: retention analysis charts

### mart_geo ⏳
- **One row per state**
- Revenue, order volume, and AOV broken down by Brazilian state
- Powers: geographic map dashboard

### mart_products ⏳
- **One row per product category**
- Revenue, review scores, return rates by category
- Powers: product performance dashboard

---

## Tech Stack Summary

```
Language:      Python 3.11
Environment:   Conda (ecom-bi)
Database:      PostgreSQL via Supabase
Transformation: dbt Core 1.7.4
Quality:       Great Expectations
Orchestration: GitHub Actions (cloud) + Airflow (local dev)
API:           FastAPI
Forecasting:   Prophet
Dashboard:     Plotly Dash
Hosting:       Render (API + Dashboard) + GitHub Pages (docs)
```

---

*Last updated: Week 2 — mart_sales complete, mart_rfm in progress*
