# Week 4 & 5 — Python Analytics and Prophet Forecasting
## Complete Documentation — Everything Explained Simply

---

# PART 1 — WHY PYTHON ANALYTICS ON TOP OF SQL?

## What SQL Does vs What Python Does

SQL is excellent at:
- Grouping and aggregating data
- Joining tables together
- Filtering rows
- Storing results as tables

SQL cannot:
- Draw charts
- Calculate complex statistical metrics
- Build forecasting models
- Format professional reports
- Feed data into machine learning libraries

Python bridges this gap. Our analytics scripts read the clean mart tables from Supabase
using SQL, then use Python libraries to analyse, visualise, and model the data.

## The Libraries We Used

**pandas** — works with tables of data in Python. Think of it as Excel in code.
Every table from the database becomes a pandas DataFrame — rows and columns you
can filter, group, sort, and calculate on.

**matplotlib** — draws charts. Bar charts, line charts, heatmaps, pie charts.
Every PNG in your reports folder was created by matplotlib.

**numpy** — mathematical operations on arrays of numbers.
Used for calculating MAE, MAPE, and array masking in the forecast accuracy section.

**SQLAlchemy** — connects Python to PostgreSQL databases.
The `create_engine()` function creates a connection pool that pandas uses to run
SQL queries and return results as DataFrames.

**Prophet** — Facebook's time series forecasting library.
Fits a mathematical trend + seasonality model to historical data and predicts future values.

---

# PART 2 — THE SHARED DATABASE CONNECTION (db.py)

## Why a Shared Module?

Instead of writing the database connection code in every script, we created one
shared module at `analytics/db.py`. Every analytics script imports `get_engine()`
from this module.

This means:
- If the connection string changes, you fix it in one place
- Every script connects the same way — no inconsistencies
- The credentials come from the `.env` file — never hardcoded

## How the Connection Works

```python
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
```

`create_engine` creates a connection pool — a set of reusable connections to Supabase.
`pool_pre_ping=True` means before each query, Python checks the connection is still alive.
This prevents errors from idle connections timing out.

The `DATABASE_URL` is read from your `.env` file using `python-dotenv`:
```
DATABASE_URL=postgresql://postgres.xxx:password@aws-0-eu-west-1.pooler.supabase.com:5432/postgres
```

---

# PART 3 — SCRIPT 1: RFM ANALYSIS (rfm_analysis.py)

## What This Script Does

Reads the `mart_rfm` table and produces a business-level analysis of customer segments.

## Step by Step Explanation

### Step 1 — Load the Data

```python
df = pd.read_sql("SELECT * FROM public_marts.mart_rfm", engine)
```

This runs the SQL query against Supabase and loads all 93,358 rows into a pandas
DataFrame called `df`. Every row is one customer.

### Step 2 — Group by Segment

```python
segment_summary = df.groupby("customer_segment").agg(
    customer_count  = ("customer_unique_id", "count"),
    avg_spend       = ("monetary_value",     "mean"),
    total_revenue   = ("monetary_value",     "sum"),
    avg_orders      = ("frequency",          "mean"),
    avg_recency_days = ("recency_days",      "mean"),
)
```

`groupby("customer_segment")` splits the 93,358 customers into groups by segment label.
`.agg()` applies multiple aggregation functions to each group simultaneously:
- `count` = how many customers in this segment
- `mean` = average value across customers in this segment
- `sum` = total value across all customers in this segment

This is the pandas equivalent of a SQL GROUP BY with multiple aggregate functions.

### Step 3 — Calculate Percentages

```python
segment_summary["pct_customers"] = (
    segment_summary["customer_count"] / total_customers * 100
).round(1)
```

For each segment: divide segment customer count by total customers, multiply by 100.
This gives the percentage of total customers in each segment.

Same formula for `pct_revenue` using total_revenue.

### Step 4 — Draw Charts

Two horizontal bar charts:
- Left chart: number of customers per segment (sorted ascending so longest bar is at top)
- Right chart: total revenue per segment (same sorting)

Colour coding:
- Dark green (#1D9E75) = Champions — best customers
- Orange-red (#E8593C) = At Risk, Cannot Lose Them, Lost — danger segments
- Light green (#5DCAA5) = Loyal Customers, Potential Loyalists — healthy segments
- Grey (#B4B2A9) = all other segments — neutral

## Results and Business Interpretation

| Metric | Value | What it means |
|---|---|---|
| Total customers | 93,358 | Unique people who ever bought |
| Champions | 9,550 (10.2%) | Bought recently, often, spent most |
| Champions revenue | 23.4% of total | Top 10% drive nearly 25% of revenue |
| Champion avg spend | R$377.16 | 2.4x the platform average of R$159.85 |
| Lost customers | 89 (0.1%) | Very few fully lost — most are Hibernating |

**The Pareto Pattern:** The top 10% of customers (Champions) generate 23.4% of revenue.
This is a weaker version of the classic 80/20 rule but the principle holds — a small loyal
minority drives disproportionate business value.

**Business actions by segment:**
- Champions → loyalty programme, early access, personalised offers
- At Risk → win-back campaign, "we miss you" discount
- Potential Loyalists → second purchase incentive
- Cannot Lose Them → urgent personal outreach
- Hibernating → low-cost reactivation email campaign
- Lost → write off or minimal-cost broad campaign only

---

# PART 4 — SCRIPT 2: COHORT ANALYSIS (cohort_analysis.py)

## What This Script Does

Reads `mart_cohort` and builds a retention heatmap showing how many customers
from each monthly cohort returned to buy again in subsequent months.

## Step by Step Explanation

### Step 1 — Load the Data

```python
df = pd.read_sql(
    "SELECT * FROM public_marts.mart_cohort ORDER BY cohort_month, months_since_first_purchase",
    engine
)
```

Loads 188 rows — one per cohort-month combination.

### Step 2 — Build the Retention Matrix (Pivot Table)

```python
retention_matrix = df.pivot_table(
    index="cohort_label",
    columns="months_since_first_purchase",
    values="retention_rate"
)
```

`pivot_table` reshapes the data from long format to wide format.

**Before pivot (long format):**
```
cohort_label | months_since | retention_rate
2017-01      | 0            | 100.0
2017-01      | 1            | 0.5
2017-01      | 2            | 0.3
2017-02      | 0            | 100.0
2017-02      | 1            | 0.8
```

**After pivot (wide format — the matrix):**
```
             | Month 0 | Month 1 | Month 2 | ...
2017-01      | 100.0   | 0.5     | 0.3     | ...
2017-02      | 100.0   | 0.8     | 0.4     | ...
```

This matrix format is what gets displayed as the heatmap — rows are cohorts,
columns are months, cells are retention percentages.

### Step 3 — Draw the Heatmap

Each cell is coloured based on its retention rate value:
- Dark green = high retention (close to 100%)
- Light grey/white = low retention (close to 0%)

The colour scale uses a custom linear gradient from white (#f5f5f2) to dark green (#1D9E75).

Text inside each cell shows the retention percentage. Dark text on light cells,
white text on dark cells (for readability).

### Step 4 — Draw the Average Retention Curve

Takes the column mean of the retention matrix — the average retention rate at each
month across all cohorts — and plots it as a line chart.

This shows the "typical" retention shape: starts at 100% at Month 0, drops sharply
at Month 1, then continues declining slowly.

## Results and Business Interpretation

**The main finding: near-zero retention across all cohorts.**

Average Month 1 retention is under 1%. This means fewer than 1 in 100 customers
returns the month after their first purchase.

**Why this happens on Olist:**
Olist is a marketplace connecting many individual sellers to customers. Customers
do not develop loyalty to Olist as a brand — they find a specific product, buy it,
and may never need that product again. They also have no particular reason to return
to Olist specifically for their next purchase.

**What this means for the business:**
1. Revenue growth is entirely acquisition-driven — every new R$1 of revenue requires
   finding a new customer
2. The cost to acquire a customer cannot be recovered through repeat purchases
3. Customer lifetime value is essentially equal to first order value
4. Marketing spend must focus almost entirely on acquisition, not retention
5. The Champions segment (10% of customers who did return) is extremely rare and
   disproportionately valuable

**This is a genuine, valuable business insight** — not a flaw in our analysis.
Knowing this, a business would:
- Focus investment on acquisition channels rather than CRM/retention tools
- Price products to be profitable on first purchase alone
- Consider subscription or membership models to create a retention mechanism

---

# PART 5 — SCRIPT 3: KPI ANALYSIS (kpi_analysis.py)

## What This Script Does

Reads `mart_sales` and calculates all headline business KPIs plus monthly trends.

## Step by Step Explanation

### Step 1 — Load Delivered Orders Only

```python
df = pd.read_sql(
    "SELECT * FROM public_marts.mart_sales WHERE order_status = 'delivered'",
    engine
)
```

We filter to delivered orders only. Including cancelled orders would distort revenue
figures — a cancelled order should not count as revenue.

### Step 2 — Calculate Headline KPIs

Each formula explained:

**Total Revenue:**
```python
total_revenue = df["payment_value"].sum()
```
Sum of all payment values across all delivered orders.
Result: R$15,422,461.77

**Total Orders:**
```python
total_orders = len(df)
```
Number of rows in the DataFrame = number of delivered orders.
Result: 96,478

**Unique Customers:**
```python
total_customers = df["customer_unique_id"].nunique()
```
`nunique()` counts distinct values. Because Olist assigns a new customer_id per order,
we use customer_unique_id which is the true unique person identifier.
Result: 93,358

**Average Order Value (AOV):**
```python
avg_order_value = df["payment_value"].mean()
```
Mean of all payment values = total revenue / total orders = R$15,422,461 / 96,478.
Result: R$159.85

**Average Fulfilment Days:**
```python
avg_fulfilment = df["fulfilment_days"].mean()
```
Mean of delivery time in days across all delivered orders.
Result: 12.1 days

**On-time Delivery Rate:**
```python
pct_on_time = df["delivered_on_time"].mean() * 100
```
`delivered_on_time` is a boolean (True/False). The mean of a boolean column gives
the proportion of True values (0.919 = 91.9%). Multiply by 100 for percentage.
Result: 91.9%

### Step 3 — Monthly Trends

```python
monthly = df.groupby("year_month").agg(
    revenue      = ("payment_value",      "sum"),
    orders       = ("order_id",           "count"),
    customers    = ("customer_unique_id", "nunique"),
    avg_order    = ("payment_value",      "mean"),
    avg_delivery = ("fulfilment_days",    "mean"),
)
```

Groups all orders by month and calculates all KPIs per month.
This produces one row per month showing the platform's performance that month.

**Month over month growth:**
```python
monthly["revenue_growth_pct"] = monthly["revenue"].pct_change() * 100
```
`pct_change()` calculates the percentage change between each row and the previous row.
Formula: (this_month - last_month) / last_month × 100

Example: October 2017 revenue = R$751,140, September 2017 = R$701,170
Growth = (751,140 - 701,170) / 701,170 × 100 = 7.1% ✓

## Results and Business Interpretation

### Headline KPIs

| KPI | Value | Context |
|---|---|---|
| Total Revenue | R$15,422,461.77 | Across entire dataset period |
| Total Orders | 96,478 | Delivered orders only |
| Unique Customers | 93,358 | Confirms ~1 order per customer |
| Average Order Value | R$159.85 | Per order revenue |
| Avg Fulfilment | 12.1 days | Purchase to delivery |
| On-time Delivery | 91.9% | Strong for Brazilian logistics |

### Monthly Revenue Story

**2016 (late):** Platform just launching. R$0-46k per month.

**Early 2017:** Rapid growth phase. R$127k → R$567k in 5 months.
Month over month growth frequently above 50%. Classic early-stage hypergrowth.

**November 2017:** R$1,153,528 — the biggest month in the dataset.
This is Black Friday. Brazilian Black Friday falls in November and drives
massive e-commerce volume. The 53.6% month-over-month jump confirms this.

**2018:** Platform stabilised at R$966k-R$1.1M per month.
Growth slowed from hypergrowth to steady state. This is natural maturation.

### Payment Type Breakdown

| Method | Share | Meaning |
|---|---|---|
| Credit card | 74.8% | Standard for banked customers |
| Boleto | 19.9% | Brazilian bank slip for unbanked |
| Voucher | 3.8% | Promotional credits |
| Debit card | 1.5% | Direct bank payment |

**The Boleto insight:** 20% of orders use boleto — a payment method where customers
receive a printed or digital slip and pay it at a bank or convenience store.
Boleto is used by people without credit cards, which represents a large segment
of the Brazilian population. This tells us Olist serves beyond the banked middle class
and reaches lower-income demographics who are typically underserved by e-commerce.
This is a significant market access story unique to Brazil.

---

# PART 6 — PROPHET REVENUE FORECASTING (forecast.py)

## What is Forecasting?

Forecasting means using historical data to predict what will happen in the future.
Every business needs forecasts to plan inventory, staffing, marketing spend, and
financial targets.

## What is Prophet?

Prophet is a forecasting library built by Facebook's data science team and open-sourced
in 2017. It was designed specifically for business time series data.

**Why Prophet and not a traditional ML model:**

Traditional ML models (Random Forest, XGBoost) need many features (columns) to predict
from. They answer questions like "will this customer churn based on these 20 attributes?"

Prophet needs only two things: a date and a value. No feature engineering required.

For our problem — predict future monthly revenue from a history of monthly revenue —
Prophet is the correct tool. Using XGBoost here would require manually engineering
all the features (lag values, rolling averages, month of year) that Prophet handles
automatically.

## How Prophet Works Mathematically

Prophet decomposes your time series into three components added together:

```
revenue(t) = trend(t) + seasonality(t) + error(t)
```

**Trend component:**
The overall direction of the data. Is revenue growing, declining, or flat?
Prophet detects "changepoints" — moments where the growth rate changed — and
fits a piecewise linear trend through them.

In our data: clear upward trend from R$0 in late 2016 to R$1M/month in 2018.

**Seasonality component:**
Repeating patterns within a year. November always bigger due to Black Friday.
Prophet uses Fourier series (a mathematical technique for representing periodic patterns)
to model seasonality without you specifying what the pattern looks like.

**Error component:**
The random variation that cannot be explained by trend or seasonality.

## Model Configuration Decisions

```python
model = Prophet(
    yearly_seasonality=False,
    weekly_seasonality=False,
    daily_seasonality=False,
    interval_width=0.95,
    seasonality_mode="additive",
    changepoint_prior_scale=0.05
)
```

**yearly_seasonality=False:**
We turned this off because we only have 22 months of data — not enough to reliably
detect yearly patterns. With more data (3+ years) we would turn this on.

**seasonality_mode="additive":**
Additive means the seasonal effect is a fixed amount added to the trend.
Multiplicative means the seasonal effect scales with the trend level.
We use additive because our dataset is short. Multiplicative seasonality
caused wild overfitting (negative revenue forecast) on 22 months of data.

**changepoint_prior_scale=0.05:**
Controls how flexible the trend is. Lower = smoother trend = less overfitting.
Default is 0.05 — we kept the default which prevents the trend from bending
too aggressively to fit early low-revenue months.

**interval_width=0.95:**
The confidence interval covers 95% of probable outcomes. There is a 95% chance
the true future value falls between `yhat_lower` and `yhat_upper`.

## What "Fitting" Means

When we call `model.fit(data)` Prophet uses a statistical method called
MAP estimation (Maximum A Posteriori) via the Stan statistical computing library.

It finds the parameter values for trend, seasonality, and changepoints that best
describe the historical data. This is not the same as training a neural network —
it is fitting a mathematical curve to data points.

## Train/Test and Model Evaluation

**In-sample evaluation:**
We measured accuracy by comparing Prophet's fitted values on historical data
to the actual historical values.

**MAE (Mean Absolute Error):**
```
MAE = mean(|actual - predicted|) for each month
```
Average absolute difference in R$ between actual and predicted revenue.
Our result: R$93,349 — the model is off by about R$93k per month on average.
Context: average monthly revenue in the stable period is ~R$1M, so R$93k is ~9%.

**MAPE (Mean Absolute Percentage Error):**
```
MAPE = mean(|actual - predicted| / actual) × 100
```
Average percentage error. We only calculated this on months where revenue > R$100k
to exclude the early startup months where near-zero revenue causes division by
near-zero which inflates the percentage enormously.
Our result: 14.9% — the model is off by about 15% on average.

**Industry benchmarks for MAPE:**
- Under 10%: excellent
- 10-20%: good — acceptable for business forecasting
- 20-50%: reasonable — usable with caution
- Over 50%: poor — not reliable

**Our 14.9% MAPE is good** — solidly within acceptable range for a business forecast
built on only 22 months of data.

**Why not use train/test split?**
For time series forecasting, the correct evaluation method is time series
cross-validation — train on past, test on future — never the reverse.
Prophet has a built-in `cross_validation()` function that does this properly.
For this project we used in-sample evaluation which is simpler but less rigorous.
In a production system you would use Prophet's cross-validation.

## Forecast Results

| Month | Forecast | Lower Bound | Upper Bound |
|---|---|---|---|
| 2018-09 | R$1,313,914 | R$1,043,023 | R$1,583,124 |
| 2018-10 | R$1,366,271 | R$1,104,396 | R$1,625,014 |

**Interpreting the confidence bands:**
The gap between lower and upper is ~R$540,000. This is wide — about 40% of the
forecast value. This reflects genuine uncertainty. With only 22 months of data
and one Black Friday event, Prophet cannot be certain whether November 2018 will
spike or not, so the bands are wide to reflect that uncertainty.

A wider band is more honest than a narrow one on limited data. Overconfident
narrow intervals would be misleading.

**The forecast direction is upward** — Prophet learned the growth trend from 2017-2018
and expects it to continue. Whether this is correct depends on business conditions
beyond what the data shows.

## The Forecast Table in Supabase

The full forecast (historical fitted values + 2 future months) is saved to
`public_marts.mart_forecast` in Supabase with these columns:

| Column | What it contains |
|---|---|
| forecast_date | The month (first day of each month) |
| revenue_forecast | The predicted revenue (yhat) |
| revenue_lower | Lower confidence bound (yhat_lower) |
| revenue_upper | Upper confidence bound (yhat_upper) |

The dashboard reads from this table to draw the forecast chart.

---

# PART 7 — ALL REPORTS GENERATED

After running all four analytics scripts, your `reports/` folder contains:

| File | Script | What it shows |
|---|---|---|
| rfm_segments.png | rfm_analysis.py | Bar charts: customers and revenue per segment |
| rfm_score_distribution.png | rfm_analysis.py | Histogram of combined RFM scores 3-15 |
| rfm_segment_summary.csv | rfm_analysis.py | Full segment metrics table |
| cohort_retention_heatmap.png | cohort_analysis.py | Green heatmap: retention by cohort and month |
| cohort_retention_curve.png | cohort_analysis.py | Average retention curve across all cohorts |
| cohort_retention_matrix.csv | cohort_analysis.py | Full retention matrix as spreadsheet |
| kpi_dashboard.png | kpi_analysis.py | Four-chart KPI dashboard |
| monthly_kpis.csv | kpi_analysis.py | Monthly revenue and KPI trends |
| revenue_forecast.png | forecast.py | Historical revenue + forecast + confidence band |

---

# PART 8 — KEY BUSINESS FINDINGS SUMMARY

## Finding 1 — Single Purchase Marketplace
Near-zero cohort retention confirms Olist is entirely acquisition-driven.
Less than 1% of customers return the month after their first purchase.
Every revenue target depends on finding new customers.

## Finding 2 — A Loyal Minority Drives Disproportionate Revenue
10.2% of customers (Champions) generate 23.4% of revenue.
Average Champion spend (R$377) is 2.4x the platform average (R$160).
These customers must be identified and treated differently.

## Finding 3 — Strong Growth Trajectory
Revenue grew from near-zero in late 2016 to R$1M/month by 2018 — roughly 14 months.
This is strong early-stage growth. The forecast suggests continued growth into late 2018.

## Finding 4 — Black Friday Dominance
November 2017 was the single biggest month (R$1.15M) — 53.6% above October.
This concentration of revenue in one month creates planning risk. Missing Black Friday
could mean missing the annual target.

## Finding 5 — Boleto Reveals Market Access
20% boleto usage tells us Olist serves a significant unbanked population.
This is a competitive advantage and a social impact story — not just a payment method stat.

## Finding 6 — Delivery Performance is Strong
91.9% on-time delivery despite 12.1 average delivery days is solid performance
for Brazilian logistics infrastructure in 2016-2018.
This is a genuine operational strength worth highlighting.

---

*Documentation covers Weeks 4 and 5. Last updated after Prophet forecasting completion.*
