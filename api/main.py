# ============================================================
# api/main.py
# PURPOSE: FastAPI REST layer serving all analytics data
# RUN FROM: project root with: uvicorn api.main:app --reload
# DOCS: visit http://localhost:8000/docs after starting
# ============================================================

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from analytics.db import get_engine

# ── CREATE THE APP ─────────────────────────────────────────────
# FastAPI() creates the application object.
# title, description, version appear in the auto-generated docs page.
app = FastAPI(
    title="E-commerce BI Platform API",
    description="REST API serving analytics from the Olist Brazilian e-commerce dataset",
    version="1.0.0"
)

# ── CORS MIDDLEWARE ────────────────────────────────────────────
# CORS = Cross Origin Resource Sharing.
# When your Dash dashboard (running on one URL) calls this API
# (running on another URL), browsers block it by default for security.
# Adding CORS middleware tells the browser: this is allowed.
# allow_origins=["*"] means any frontend can call this API.
# In production you would restrict this to your dashboard URL only.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── DATABASE CONNECTION ────────────────────────────────────────
# We create the engine once when the app starts.
# All endpoints share this single connection pool.
engine = get_engine()

# ── HELPER FUNCTION ────────────────────────────────────────────
def query(sql: str) -> list[dict]:
    """
    Runs a SQL query using SQLAlchemy directly.
    Returns results as a list of dictionaries for JSON conversion.

    We use SQLAlchemy's text() and execute() directly instead of
    pandas read_sql() to avoid version compatibility issues with
    SQLAlchemy 2.x.

    dict(zip(columns, row)) creates one dictionary per row by
    pairing each column name with its value from that row.
    Example: columns = ["state", "revenue"]
             row     = ("SP", 5000000)
             result  = {"state": "SP", "revenue": 5000000}
    """
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        columns = list(result.keys())
        rows = result.fetchall()
    return [dict(zip(columns, row)) for row in rows]


# ══════════════════════════════════════════════════════════════
# ENDPOINTS
# ══════════════════════════════════════════════════════════════

# ── HEALTH CHECK ───────────────────────────────────────────────
# Every API needs a health check endpoint.
# Monitoring tools ping this URL to confirm the API is alive.
# Returns a simple OK message — no database query needed.
@app.api_route("/health", methods=["GET", "HEAD"])
def health_check():
    return {"status": "ok"}


# ── HEADLINE KPIs ──────────────────────────────────────────────
# Returns the six headline KPI numbers for the dashboard.
# KPI cards at the top of the dashboard read from this endpoint.
@app.get("/kpis")
def get_kpis():
    rows = query("""
        SELECT
            ROUND(SUM(payment_value)::numeric, 2)          AS total_revenue,
            COUNT(order_id)                                 AS total_orders,
            COUNT(DISTINCT customer_unique_id)              AS total_customers,
            ROUND(AVG(payment_value)::numeric, 2)           AS avg_order_value,
            ROUND(AVG(fulfilment_days)::numeric, 1)         AS avg_fulfilment_days,
            ROUND(
                AVG(CASE WHEN delivered_on_time THEN 1.0 ELSE 0.0 END) * 100,
                1
            )                                               AS pct_on_time
        FROM public_marts.mart_sales
        WHERE order_status = 'delivered'
    """)
    return rows[0]


# ── MONTHLY REVENUE ────────────────────────────────────────────
# Returns monthly revenue time series for the line/bar chart.
@app.get("/revenue/monthly")
def get_monthly_revenue():
    return query("""
        SELECT
            year_month,
            COUNT(order_id)                        AS total_orders,
            ROUND(SUM(payment_value)::numeric, 2)  AS total_revenue,
            ROUND(AVG(payment_value)::numeric, 2)  AS avg_order_value,
            COUNT(DISTINCT customer_unique_id)     AS unique_customers
        FROM public_marts.mart_sales
        WHERE order_status = 'delivered'
          AND year_month IS NOT NULL
        GROUP BY year_month
        ORDER BY year_month
    """)


# ── RFM SEGMENTS ───────────────────────────────────────────────
# Returns customer count and revenue per RFM segment.
@app.get("/rfm/segments")
def get_rfm_segments():
    return query("""
        SELECT
            customer_segment,
            COUNT(*)                                    AS customer_count,
            ROUND(SUM(monetary_value)::numeric, 2)      AS total_revenue,
            ROUND(AVG(monetary_value)::numeric, 2)      AS avg_monetary_value,
            ROUND(AVG(frequency)::numeric, 2)           AS avg_frequency,
            ROUND(AVG(recency_days)::numeric, 1)        AS avg_recency_days
        FROM public_marts.mart_rfm
        GROUP BY customer_segment
        ORDER BY total_revenue DESC
    """)


# ── RFM SCORE DISTRIBUTION ─────────────────────────────────────
# Returns the distribution of combined RFM scores (3 to 15).
@app.get("/rfm/distribution")
def get_rfm_distribution():
    return query("""
        SELECT
            rfm_score,
            COUNT(*) AS customer_count
        FROM public_marts.mart_rfm
        GROUP BY rfm_score
        ORDER BY rfm_score
    """)


# ── COHORT RETENTION ───────────────────────────────────────────
# Returns the full cohort retention matrix.
@app.get("/cohort")
def get_cohort():
    return query("""
        SELECT
            cohort_label,
            months_since_first_purchase,
            cohort_size,
            retained_customers,
            retention_rate
        FROM public_marts.mart_cohort
        ORDER BY cohort_label, months_since_first_purchase
    """)


# ── GEOGRAPHIC SALES ───────────────────────────────────────────
# Returns revenue and order metrics by Brazilian state.
@app.get("/geo")
def get_geo():
    return query("""
        SELECT
            customer_state,
            total_orders,
            total_customers,
            total_revenue,
            avg_order_value,
            avg_fulfilment_days,
            pct_delivered_on_time
        FROM public_marts.mart_geo
        ORDER BY total_revenue DESC
    """)


# ── PRODUCT CATEGORIES ─────────────────────────────────────────
# Returns performance metrics per product category.
@app.get("/products")
def get_products():
    return query("""
        SELECT
            category_name,
            total_items_sold,
            total_orders,
            total_revenue,
            avg_item_price,
            avg_review_score,
            total_reviews,
            pct_five_star,
            pct_one_star
        FROM public_marts.mart_products
        ORDER BY total_revenue DESC
    """)


# ── REVENUE FORECAST ───────────────────────────────────────────
# Returns Prophet forecast with confidence intervals.
@app.get("/forecast")
def get_forecast():
    return query("""
        SELECT
            forecast_date,
            revenue_forecast,
            revenue_lower,
            revenue_upper
        FROM public_marts.mart_forecast
        ORDER BY forecast_date
    """)


# ── PAYMENT BREAKDOWN ──────────────────────────────────────────
# Returns order count and revenue by payment type.
@app.get("/payments")
def get_payments():
    return query("""
        SELECT
            payment_type,
            COUNT(order_id)                        AS order_count,
            ROUND(SUM(payment_value)::numeric, 2)  AS total_revenue,
            ROUND(AVG(payment_value)::numeric, 2)  AS avg_order_value
        FROM public_marts.mart_sales
        WHERE order_status = 'delivered'
          AND payment_type IS NOT NULL
        GROUP BY payment_type
        ORDER BY order_count DESC
    """)