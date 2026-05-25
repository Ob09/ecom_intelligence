# ============================================================
# analytics/kpi_analysis.py
# PURPOSE: Calculate business KPIs from mart_sales
# OUTPUT:  KPI summary and trend charts saved to reports/
# RUN FROM: project root (e_com_analyser)
# ============================================================

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from analytics.db import get_engine

os.makedirs("reports", exist_ok=True)

print("="*60)
print("  BUSINESS KPI ANALYSIS")
print("="*60)

# ── LOAD DATA ──────────────────────────────────────────────────
# Read only delivered orders from mart_sales.
# Cancelled or processing orders should not count toward KPIs.
print("\nLoading mart_sales from Supabase...")
engine = get_engine()

df = pd.read_sql(
    """
    SELECT * FROM public_marts.mart_sales
    WHERE order_status = 'delivered'
    """,
    engine
)

print(f"Loaded {len(df):,} delivered orders")

# ── HEADLINE KPIs ──────────────────────────────────────────────
# These six numbers are the top-line health metrics of the business.
# Every e-commerce business tracks these as their core dashboard.
print("\n--- HEADLINE KPIs ---")

total_revenue   = df["payment_value"].sum()
total_orders    = len(df)
total_customers = df["customer_unique_id"].nunique()
avg_order_value = df["payment_value"].mean()
avg_fulfilment  = df["fulfilment_days"].mean()
pct_on_time     = df["delivered_on_time"].mean() * 100

print(f"\nTotal Revenue:         R${total_revenue:>12,.2f}")
print(f"Total Orders:          {total_orders:>12,}")
print(f"Unique Customers:      {total_customers:>12,}")
print(f"Average Order Value:   R${avg_order_value:>12,.2f}")
print(f"Avg Fulfilment Days:   {avg_fulfilment:>12.1f} days")
print(f"On-time Delivery:      {pct_on_time:>12.1f}%")

# ── MONTHLY TRENDS ─────────────────────────────────────────────
# Group by year_month to see how each KPI changes over time.
# This powers the time-series charts on the dashboard.
print("\n--- MONTHLY TRENDS ---")

monthly = (
    df.groupby("year_month")
    .agg(
        revenue      = ("payment_value",      "sum"),
        orders       = ("order_id",           "count"),
        customers    = ("customer_unique_id", "nunique"),
        avg_order    = ("payment_value",      "mean"),
        avg_delivery = ("fulfilment_days",    "mean"),
    )
    .round(2)
    .reset_index()
)

# Month over month revenue growth percentage
# pct_change() calculates the % difference between each row and the one above it
monthly["revenue_growth_pct"] = (
    monthly["revenue"].pct_change() * 100
).round(1)

print(monthly[[
    "year_month", "revenue", "orders",
    "avg_order", "revenue_growth_pct"
]].to_string(index=False))

# ── BEST AND WORST MONTHS ──────────────────────────────────────
print("\n--- BEST AND WORST MONTHS ---")

best_month  = monthly.loc[monthly["revenue"].idxmax()]
worst_month = monthly.loc[monthly["revenue"].idxmin()]

print(f"\nBest revenue month:  {best_month['year_month']} "
      f"— R${best_month['revenue']:,.2f} "
      f"({best_month['orders']:,} orders)")
print(f"Worst revenue month: {worst_month['year_month']} "
      f"— R${worst_month['revenue']:,.2f} "
      f"({worst_month['orders']:,} orders)")

# ── PAYMENT TYPE BREAKDOWN ─────────────────────────────────────
print("\n--- PAYMENT TYPE BREAKDOWN ---")

payment_breakdown = (
    df.groupby("payment_type")
    .agg(
        order_count = ("order_id",       "count"),
        total_value = ("payment_value",  "sum"),
    )
    .assign(
        pct_orders = lambda x: (
            x["order_count"] / total_orders * 100
        ).round(1)
    )
    .sort_values("order_count", ascending=False)
)

print(payment_breakdown.to_string())

# ── CHART 1: MONTHLY REVENUE BAR CHART ────────────────────────
print("\nGenerating charts...")

fig, axes = plt.subplots(2, 2, figsize=(16, 10))
fig.suptitle(
    "E-commerce Business KPI Dashboard",
    fontsize=16, fontweight="bold"
)

# Monthly revenue
axes[0, 0].bar(
    monthly["year_month"],
    monthly["revenue"],
    color="#1D9E75", edgecolor="white"
)
axes[0, 0].set_title("Monthly Revenue (R$)", fontsize=12)
axes[0, 0].set_xlabel("Month")
axes[0, 0].set_ylabel("Revenue (R$)")
axes[0, 0].tick_params(axis="x", rotation=45)
axes[0, 0].yaxis.set_major_formatter(
    mticker.FuncFormatter(lambda x, _: f"R${x/1000:.0f}k")
)
axes[0, 0].grid(axis="y", alpha=0.3)

# Monthly order volume
axes[0, 1].bar(
    monthly["year_month"],
    monthly["orders"],
    color="#5DCAA5", edgecolor="white"
)
axes[0, 1].set_title("Monthly Order Volume", fontsize=12)
axes[0, 1].set_xlabel("Month")
axes[0, 1].set_ylabel("Number of Orders")
axes[0, 1].tick_params(axis="x", rotation=45)
axes[0, 1].yaxis.set_major_formatter(
    mticker.FuncFormatter(lambda x, _: f"{x:,.0f}")
)
axes[0, 1].grid(axis="y", alpha=0.3)

# Average order value over time
axes[1, 0].plot(
    monthly["year_month"],
    monthly["avg_order"],
    color="#534AB7", linewidth=2.5,
    marker="o", markersize=5
)
axes[1, 0].set_title("Average Order Value (R$)", fontsize=12)
axes[1, 0].set_xlabel("Month")
axes[1, 0].set_ylabel("AOV (R$)")
axes[1, 0].tick_params(axis="x", rotation=45)
axes[1, 0].grid(axis="y", alpha=0.3)

# Payment type pie chart
payment_plot = payment_breakdown[payment_breakdown["pct_orders"] > 0]
axes[1, 1].pie(
    payment_plot["order_count"],
    labels=payment_plot.index,
    autopct="%1.1f%%",
    colors=["#1D9E75", "#5DCAA5", "#9FE1CB", "#E1F5EE"],
    startangle=90
)
axes[1, 1].set_title("Orders by Payment Type", fontsize=12)

plt.tight_layout()
chart_path = "reports/kpi_dashboard.png"
plt.savefig(chart_path, dpi=150, bbox_inches="tight")
print(f"Chart saved to {chart_path}")

# ── SAVE MONTHLY TRENDS TO CSV ─────────────────────────────────
# This CSV will be used by Prophet for revenue forecasting
csv_path = "reports/monthly_kpis.csv"
monthly.to_csv(csv_path, index=False)
print(f"Monthly KPIs saved to {csv_path}")

print("\n" + "="*60)
print("  KPI ANALYSIS COMPLETE")
print("="*60 + "\n")