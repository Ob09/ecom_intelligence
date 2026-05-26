# ============================================================
# analytics/forecast.py
# PURPOSE: 30-day revenue forecast using Prophet
# OUTPUT:  Forecast chart saved to reports/
#          Forecast data saved to Supabase as mart_forecast
# RUN FROM: project root (e_com_analyser)
# ============================================================

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from prophet import Prophet
from sqlalchemy import text
from analytics.db import get_engine

os.makedirs("reports", exist_ok=True)

print("="*60)
print("  30-DAY REVENUE FORECAST USING PROPHET")
print("="*60)

# ── STEP 1: LOAD HISTORICAL REVENUE DATA ──────────────────────
# We read the monthly_kpis.csv that kpi_analysis.py saved.
# This gives us one revenue value per month.
print("\nLoading historical revenue data...")

monthly = pd.read_csv("reports/monthly_kpis.csv")

# Remove the first row (2016-09) which has zero revenue —
# the platform had not launched yet and it would confuse Prophet
monthly = monthly[monthly["revenue"] > 0].copy()

# Convert year_month string to a proper date
# We use the 1st of each month as the date
# e.g. '2017-11' becomes 2017-11-01
monthly["ds"] = pd.to_datetime(monthly["year_month"] + "-01")
monthly["y"]  = monthly["revenue"]

print(f"Historical data: {len(monthly)} months")
print(f"From: {monthly['ds'].min().strftime('%Y-%m')}")
print(f"To:   {monthly['ds'].max().strftime('%Y-%m')}")
print(f"Total revenue in history: R${monthly['y'].sum():,.2f}")

# ── STEP 2: FIT THE PROPHET MODEL ─────────────────────────────
# We initialise Prophet with some settings:
#
# yearly_seasonality=True  — learn annual patterns (e.g. Black Friday in Nov)
# weekly_seasonality=False — we have monthly data, not daily, so no weekly pattern
# daily_seasonality=False  — same reason
# interval_width=0.95      — 95% confidence interval
#                            meaning the true value should fall within the
#                            upper/lower band 95% of the time
print("\nFitting Prophet model to historical data...")

model = Prophet(
    yearly_seasonality=False,  # not enough data for reliable yearly patterns
    weekly_seasonality=False,
    daily_seasonality=False,
    interval_width=0.95,
    seasonality_mode="additive",  # safer for short datasets
    changepoint_prior_scale=0.05  # controls how flexible the trend is
    # lower value = smoother trend = less overfitting
)

# fit() is where Prophet actually learns from your data.
# It analyses the trend, detects seasonal patterns, and
# builds a mathematical model of your revenue history.
model.fit(monthly[["ds", "y"]])
print("Model fitted successfully.")

# ── STEP 3: CREATE FUTURE DATES ───────────────────────────────
# We tell Prophet to create a forecast for 30 periods ahead.
# freq="MS" means Monthly Start — one row per month.
print("\nGenerating 30-day forecast...")

future = model.make_future_dataframe(
    periods=2,   # 2 months ahead — more reliable than 3 on short data
    freq="MS"
)

print(f"Forecasting from {future['ds'].min().strftime('%Y-%m')} "
      f"to {future['ds'].max().strftime('%Y-%m')}")

# ── STEP 4: GENERATE THE FORECAST ─────────────────────────────
# predict() applies the fitted model to the future dates
# and returns a DataFrame with these key columns:
# ds         — the date
# yhat       — the predicted value (most likely revenue)
# yhat_lower — lower bound (pessimistic scenario)
# yhat_upper — upper bound (optimistic scenario)
forecast = model.predict(future)

# ── STEP 5: SHOW FORECAST RESULTS ─────────────────────────────
print("\n--- FORECAST RESULTS ---")

# Show only the future rows (not the historical fitted values)
future_only = forecast[forecast["ds"] > monthly["ds"].max()][[
    "ds", "yhat", "yhat_lower", "yhat_upper"
]].copy()

future_only.columns = ["month", "forecast", "lower_bound", "upper_bound"]
future_only["month"] = future_only["month"].dt.strftime("%Y-%m")
future_only["forecast"]    = future_only["forecast"].round(2)
future_only["lower_bound"] = future_only["lower_bound"].round(2)
future_only["upper_bound"] = future_only["upper_bound"].round(2)

print(future_only.to_string(index=False))

# ── STEP 6: EVALUATE MODEL ACCURACY ───────────────────────────
# We calculate how accurate the model is on historical data.
# MAE = Mean Absolute Error
# How far off is the forecast from actual, in R$ on average?
#
# MAPE = Mean Absolute Percentage Error
# How far off is the forecast as a percentage of actual?
# A MAPE of 10% means the model is off by 10% on average.
print("\n--- MODEL ACCURACY ON HISTORICAL DATA ---")

historical_forecast = forecast[forecast["ds"] <= monthly["ds"].max()]
actuals = monthly["y"].values
predicted = historical_forecast["yhat"].values[:len(actuals)]

# Only calculate accuracy on months where revenue > R$100k
# Early months with near-zero revenue skew MAPE enormously
mask = actuals > 100000
mae  = np.mean(np.abs(actuals[mask] - predicted[mask]))
mape = np.mean(np.abs(
    (actuals[mask] - predicted[mask]) / actuals[mask]
)) * 100

print(f"MAE  (Mean Absolute Error):      R${mae:,.2f}")
print(f"MAPE (Mean Absolute % Error):    {mape:.1f}%")
print(f"Interpretation: on average the model is off by {mape:.1f}%")

# ── STEP 7: SAVE FORECAST TO SUPABASE ─────────────────────────
print("\nSaving forecast to Supabase...")

engine = get_engine()

forecast_to_save = forecast[[
    "ds", "yhat", "yhat_lower", "yhat_upper"
]].copy()

forecast_to_save.columns = [
    "forecast_date", "revenue_forecast",
    "revenue_lower", "revenue_upper"
]

forecast_to_save["revenue_forecast"] = forecast_to_save["revenue_forecast"].round(2)
forecast_to_save["revenue_lower"]    = forecast_to_save["revenue_lower"].round(2)
forecast_to_save["revenue_upper"]    = forecast_to_save["revenue_upper"].round(2)

# Use SQLAlchemy directly instead of pandas to_sql
# This avoids version compatibility issues with the engine object
with engine.begin() as conn:

    # Drop table if it already exists
    conn.execute(text(
        "DROP TABLE IF EXISTS public_marts.mart_forecast"
    ))

    # Create the table with correct column types
    conn.execute(text("""
        CREATE TABLE public_marts.mart_forecast (
            forecast_date     DATE,
            revenue_forecast  NUMERIC(12,2),
            revenue_lower     NUMERIC(12,2),
            revenue_upper     NUMERIC(12,2)
        )
    """))

    # Insert all rows
    for _, row in forecast_to_save.iterrows():
        conn.execute(text("""
            INSERT INTO public_marts.mart_forecast
            VALUES (:forecast_date, :revenue_forecast,
                    :revenue_lower, :revenue_upper)
        """), {
            "forecast_date"    : row["forecast_date"],
            "revenue_forecast" : row["revenue_forecast"],
            "revenue_lower"    : row["revenue_lower"],
            "revenue_upper"    : row["revenue_upper"]
        })

print(f"Saved {len(forecast_to_save)} rows to public_marts.mart_forecast")

# ── STEP 8: DRAW THE FORECAST CHART ───────────────────────────
print("\nGenerating forecast chart...")

fig, ax = plt.subplots(figsize=(14, 6))

# Plot historical actual revenue
ax.plot(
    monthly["ds"],
    monthly["y"],
    color="#1D9E75",
    linewidth=2.5,
    marker="o",
    markersize=5,
    label="Actual revenue",
    zorder=3
)

# Plot the forecast line (includes both historical fit and future)
ax.plot(
    forecast["ds"],
    forecast["yhat"],
    color="#534AB7",
    linewidth=2,
    linestyle="--",
    label="Forecast",
    zorder=2
)

# Shade the confidence interval band
ax.fill_between(
    forecast["ds"],
    forecast["yhat_lower"],
    forecast["yhat_upper"],
    alpha=0.15,
    color="#534AB7",
    label="95% confidence interval"
)

# Add a vertical line showing where history ends and forecast begins
last_date = monthly["ds"].max()
ax.axvline(
    x=last_date,
    color="#E8593C",
    linewidth=1.5,
    linestyle=":",
    label="Forecast start"
)

ax.set_title(
    "Olist Revenue — Historical + 3-Month Forecast",
    fontsize=14, fontweight="bold"
)
ax.set_xlabel("Month")
ax.set_ylabel("Monthly Revenue (R$)")
ax.legend(loc="upper left")
ax.grid(axis="y", alpha=0.3)
ax.yaxis.set_major_formatter(
    plt.FuncFormatter(lambda x, _: f"R${x/1000:.0f}k")
)

plt.tight_layout()
chart_path = "reports/revenue_forecast.png"
plt.savefig(chart_path, dpi=150, bbox_inches="tight")
print(f"Chart saved to {chart_path}")

print("\n" + "="*60)
print("  FORECAST COMPLETE")
print("="*60 + "\n")