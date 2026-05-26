# E-commerce Business Intelligence and Analytics Platform

A complete, production-grade Business Intelligence platform built on 100,000 real Brazilian e-commerce orders from the Olist dataset. Every component is deployed and running live — no local machine required.

---

## Live URLs

| Service | URL |
|---|---|
| **Interactive Dashboard** | https://ecom-bi-dashboard.onrender.com |
| **REST API** | https://ecom-bi-api.onrender.com |
| **API Documentation** | https://ecom-bi-api.onrender.com/docs |
| **GitHub Repository** | https://github.com/Ob09/ecom_intelligence |

> **Note:** Free tier Render services sleep after 15 minutes of inactivity. First load may take 30-50 seconds to wake up. Subsequent loads are instant.

---

## What This Platform Does

This platform transforms raw e-commerce transaction data into actionable business intelligence through a fully automated pipeline. It answers six core business questions:

1. **Who are our best customers?** — RFM segmentation scores all 93,358 customers
2. **Are customers coming back?** — Monthly cohort retention analysis
3. **How is the business performing?** — Live KPI dashboard with revenue trends
4. **Where are our customers?** — Geographic sales analysis across all 27 Brazilian states
5. **Which products perform best?** — Category revenue and review analysis
6. **What does the future look like?** — Revenue trend analysis with moving averages

---

## Key Business Findings

| Finding | Data |
|---|---|
| Total Revenue | R$15,422,462 across 96,478 delivered orders |
| Champions (top customers) | 10.2% of customers generate 23.4% of revenue |
| Customer retention | Under 1% return after Month 0 — acquisition-driven business |
| Best month | November 2017 — R$1,153,528 (Black Friday, +53.6% MoM) |
| Delivery performance | 91.9% on-time despite 12.1 day average fulfilment |
| Payment mix | 74.8% credit card, 19.9% boleto (unbanked market) |
| Growth | Near-zero revenue in late 2016 → R$1M/month by 2018 |

---

## Architecture

```
Raw Data (9 Olist CSVs, 100k rows)
        ↓ load_olist.py
Supabase PostgreSQL (West EU Ireland)
        ↓ dbt run
┌─────────────────────────────────────┐
│  Staging Layer (7 views)            │
│  stg_orders, stg_customers, etc.    │
└─────────────────────────────────────┘
        ↓
┌─────────────────────────────────────┐
│  Intermediate Layer (1 view)        │
│  int_orders_enriched                │
└─────────────────────────────────────┘
        ↓
┌─────────────────────────────────────┐
│  Mart Layer (5 tables)              │
│  mart_sales, mart_rfm, mart_cohort  │
│  mart_geo, mart_products            │
└─────────────────────────────────────┘
        ↓ validation
Great Expectations (30+ checks)
        ↓
FastAPI REST API → Render (live)
        ↓
Plotly Dash Dashboard → Render (live)
```

---

## Tech Stack

| Category | Technology |
|---|---|
| Database | PostgreSQL via Supabase |
| Transformation | dbt Core 1.7.4 |
| Data Quality | Great Expectations 0.18.8 |
| Forecasting | Prophet |
| API | FastAPI + Uvicorn |
| Dashboard | Plotly Dash + Bootstrap |
| Orchestration | GitHub Actions (cloud) + Airflow DAG (local) |
| Hosting | Render (free tier) |
| Language | Python 3.11 |

---

## Dashboard Pages

| Page | What it shows |
|---|---|
| **Overview** | 6 KPI cards + monthly revenue + AOV trend |
| **RFM** | Customer segments, revenue per segment, score distribution |
| **Cohort** | Monthly retention heatmap across all cohorts |
| **Geography** | Revenue treemap + delivery performance by state |
| **Products** | Category revenue + review score scatter + payment breakdown |
| **Trends** | Moving average + MoM growth + year-over-year comparison |

---

## API Endpoints

| Endpoint | Returns |
|---|---|
| `GET /health` | API status |
| `GET /kpis` | 6 headline business metrics |
| `GET /revenue/monthly` | Monthly revenue time series |
| `GET /rfm/segments` | Customer count and revenue per RFM segment |
| `GET /rfm/distribution` | RFM score histogram data |
| `GET /cohort` | Full cohort retention matrix |
| `GET /geo` | Sales metrics by Brazilian state |
| `GET /products` | Category performance with review scores |
| `GET /forecast` | Prophet revenue forecast with confidence intervals |
| `GET /payments` | Revenue and volume by payment method |

---

## Project Structure

```
e_com_analyser/
├── .github/workflows/     # GitHub Actions pipeline
├── airflow/dags/          # Airflow DAG for local orchestration
├── analytics/             # Python analytics scripts
│   ├── db.py              # Shared database connection
│   ├── rfm_analysis.py    # RFM segmentation analysis
│   ├── cohort_analysis.py # Cohort retention analysis
│   ├── kpi_analysis.py    # Business KPI calculations
│   └── forecast.py        # Prophet revenue forecasting
├── api/                   # FastAPI REST layer
│   └── main.py            # All 9 API endpoints
├── dashboard/             # Plotly Dash dashboard
│   └── app.py             # All 6 dashboard pages
├── dbt_project/olist_bi/  # dbt transformation project
│   ├── models/staging/    # 7 staging models
│   ├── models/intermediate/ # 1 intermediate model
│   ├── models/marts/      # 5 mart models
│   └── tests/             # Custom singular tests
├── great_expectations/    # Data quality validation
├── ingestion/             # Data loading scripts
├── docs/                  # Full project documentation
└── reports/               # Generated charts and CSVs
```

---

## Running Locally

```bash
# 1. Clone the repository
git clone https://github.com/Ob09/ecom_intelligence.git
cd ecom_intelligence

# 2. Create conda environment
conda create -n ecom-bi python=3.11
conda activate ecom-bi

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up .env file
cp .env.example .env
# Add your DATABASE_URL to .env

# 5. Run dbt pipeline
cd dbt_project/olist_bi
set DB_PASSWORD=your_password
dbt run
dbt test

# 6. Start FastAPI (Terminal 1)
cd ../..
uvicorn api.main:app --reload

# 7. Start Dashboard (Terminal 2)
python dashboard/app.py

# 8. Open dashboard
# http://localhost:8050
```

---

## Data Source

[Olist Brazilian E-commerce Dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) — 100,000 real orders from 2016-2018 across 9 relational tables.

---

*Built by Obedh — MSc Data Analytics, Dublin*
*Project: E-commerce Business Intelligence and Analytics Platform*
