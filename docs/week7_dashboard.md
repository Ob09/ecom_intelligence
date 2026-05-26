# Week 7 — Plotly Dash Dashboard
## Complete Documentation — Everything Explained Simply

---

# PART 1 — WHAT IS PLOTLY DASH?

## The Simple Explanation

Plotly Dash is a Python framework for building interactive web dashboards.
You write everything in Python — no HTML, no CSS, no JavaScript needed.
Dash converts your Python code into a fully interactive web application
that runs in any browser.

It is built on three technologies underneath:
- **Plotly** — the library that draws the charts
- **React** — the JavaScript framework that makes it interactive
- **Flask** — the web server that serves the pages

You never touch React or Flask directly. Dash handles all of that for you.

## Why Dash and Not Power BI or Tableau?

| Tool | Cost | Code | Customisation | Portfolio Value |
|---|---|---|---|---|
| Power BI | Paid | No | Limited | Low for data engineers |
| Tableau | Paid | No | Limited | Medium |
| Plotly Dash | Free | Python | Unlimited | High — shows coding ability |
| Streamlit | Free | Python | Medium | Medium |

Dash is the right choice for this portfolio because:
- It is free to build and host
- Everything is Python code — demonstrable and version controlled
- It connects directly to your FastAPI endpoints
- The output is a real web application, not a drag-and-drop report
- It proves you can build production-grade analytics applications

---

# PART 2 — HOW THE DASHBOARD CONNECTS TO EVERYTHING

## The Data Flow

```
User opens http://localhost:8050 in browser
        ↓
Dash app serves the HTML page
        ↓
User clicks a tab
        ↓
Dash callback fires
        ↓
Python calls fetch("/kpis") or fetch("/rfm/segments") etc.
        ↓
FastAPI endpoint receives the request
        ↓
FastAPI queries Supabase PostgreSQL
        ↓
Returns JSON data
        ↓
Dash builds Plotly charts from the JSON
        ↓
Charts render in the browser
```

The dashboard never touches the database directly.
It only ever speaks to FastAPI endpoints.
FastAPI handles all database communication.

## The fetch() Helper Function

```python
def fetch(endpoint: str) -> list | dict:
    try:
        response = requests.get(f"{API_URL}{endpoint}", timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching {endpoint}: {e}")
        return []
```

Every page builder function calls fetch() to get its data.
The `try/except` means if the API is down, the dashboard
returns an empty list instead of crashing — graceful degradation.

---

# PART 3 — THE ARCHITECTURE OF A DASH APP

## Three Core Concepts

### 1. Layout
The layout defines what the page looks like — the HTML structure.
In Dash you build this using Python components:

```python
app.layout = html.Div([
    html.H1("Title"),
    dcc.Graph(figure=fig),
    dcc.Tabs(id="tabs", children=[...])
])
```

`html.Div` = a `<div>` tag in HTML
`html.H1` = a `<h1>` heading
`dcc.Graph` = a Plotly chart
`dcc.Tabs` = a tab navigation component

### 2. Callbacks
Callbacks are the mechanism that makes Dash interactive.
When a user does something (clicks a tab, changes a dropdown),
Dash automatically calls a Python function and updates the page.

```python
@app.callback(
    Output("tab-content", "children"),  # what to update
    Input("tabs", "value")              # what triggers the update
)
def render_tab(tab):
    if tab == "overview": return build_overview()
    if tab == "rfm":      return build_rfm()
    ...
```

When the user clicks the RFM tab:
1. The `tabs` component's `value` changes to "rfm"
2. Dash detects this Input changed
3. Dash calls `render_tab("rfm")`
4. The function returns `build_rfm()`
5. Dash puts the result into `tab-content`
6. The RFM page appears

### 3. Components
Components are the building blocks of the layout.
Two main libraries:

**html.*** — standard HTML elements
- `html.Div` — container box
- `html.H1, H2, H3` — headings
- `html.P` — paragraph text
- `html.Ul, html.Li` — lists
- `html.Span` — inline text

**dcc.*** — Dash Core Components (interactive)
- `dcc.Graph` — renders a Plotly figure
- `dcc.Tabs, dcc.Tab` — tab navigation
- `dcc.Dropdown` — dropdown selector
- `dcc.DatePickerRange` — date picker

**dbc.*** — Dash Bootstrap Components (layout)
- `dbc.Row, dbc.Col` — grid layout (12 columns)
- `dbc.Navbar` — navigation bar
- `dbc.Container` — responsive container

---

# PART 4 — THE SIX DASHBOARD PAGES

## Page 1 — Overview

**Purpose:** High-level business health at a glance

**Data sources:**
- `fetch("/kpis")` — 6 headline numbers
- `fetch("/revenue/monthly")` — monthly time series

**What it shows:**

Six KPI cards across the top:
- Total Revenue: R$15,422,462
- Total Orders: 96,478
- Unique Customers: 93,358
- Avg Order Value: R$159.85
- Avg Fulfilment: 12.1 days
- On-time Delivery: 91.9%

Each card has a coloured top border identifying its category.
The colour system: green = revenue/volume, purple = customer,
orange = operational risk, teal = performance.

Monthly Revenue bar chart with Black Friday annotation:
- Shows the full growth story from 2016 to 2018
- Red annotation arrow pointing to November 2017 spike
- Labels this explicitly as Black Friday for any viewer

Average Order Value line chart:
- Filtered to months with revenue > R$50,000
- This removes the early 2016 months with near-zero revenue
  that caused a misleading spike down to R$0
- Y-axis range fixed to 100-220 for better readability

Last updated timestamp in the navbar:
- Shows when the pipeline last ran
- Demonstrates the system is alive and active
- Important for demonstrating automated pipeline to viewers

---

## Page 2 — RFM

**Purpose:** Customer segmentation intelligence

**Data sources:**
- `fetch("/rfm/segments")` — segment metrics
- `fetch("/rfm/distribution")` — score histogram

**What it shows:**

Customers per Segment horizontal bar chart:
- Sorted ascending so the longest bar (Loyal Customers: 46,254) is at the top
- Colour coded: green = Champions/Loyal, grey = neutral, red = at risk
- Labels show exact customer counts with full numbers (fixed from earlier)

Revenue per Segment horizontal bar chart:
- Same colour coding as customers chart
- Reveals the Pareto pattern: Champions generate 23.4% of revenue
  despite being only 10.2% of customers

RFM Score Distribution histogram:
- Shows how 93,358 customers are spread across combined scores 3-15
- Right-skewed toward higher scores — most customers are mid-to-high value
- Exact counts on each bar

Key Insight card:
- Plain English explanation of the Champion concentration finding
- Explains the At Risk segment business implication
- Gives any non-technical viewer the business interpretation immediately

---

## Page 3 — Cohort

**Purpose:** Customer retention analysis

**Data source:** `fetch("/cohort")`

**What it shows:**

Monthly Cohort Retention Heatmap:
- Rows = cohort months (when customers first purchased)
- Columns = Month 0, Month 1, Month 2 ... Month 12
- Cells = what percentage of that cohort is still purchasing
- Colour: dark green = high retention, light = low
- Month 0 always shows 100% — this is the definition of the cohort

Key Insight card:
- Explains that near-zero retention after Month 0 is not a bug
- Explains what it means for the business model
- Recommends acquisition-focused strategy

**The pivoting explained:**

The mart_cohort table has one row per cohort-month combination.
The dashboard uses pandas pivot_table() to reshape this into
a matrix format (rows = cohorts, columns = months) which
Plotly's Heatmap chart can then visualise directly.

---

## Page 4 — Geography

**Purpose:** Regional sales and delivery performance

**Data source:** `fetch("/geo")`

**What it shows:**

Revenue Treemap:
- Each rectangle represents one Brazilian state
- Rectangle SIZE = revenue (bigger = more revenue)
- Rectangle COLOUR = revenue (darker green = more revenue)
- SP (São Paulo) dominates — R$5,998,227 out of R$15M total
- Immediately shows the geographic concentration of the business

Why treemap instead of choropleth map?
Plotly's built-in choropleth map does not have Brazilian state
boundaries built in — it would require a custom GeoJSON file.
The treemap provides the same information (relative revenue by state)
in a more visually impactful way without external dependencies.

Top 10 States bar chart (coloured by delivery days):
- Height = revenue (what matters for the business)
- Colour = delivery performance (green = fast, red = slow)
- Reveals the correlation: high-revenue states tend to be faster
  because they are closer to the main distribution centres

Slowest Delivery States chart:
- Roraima (RR) slowest at 29 days — remote northern state
- Amapá (AP) second at 27 days
- All slowest states are in the North/Northeast regions
- Far from São Paulo where most sellers are based
- Clear operational insight: logistics investment needed in these regions

---

## Page 5 — Products

**Purpose:** Category performance and payment analysis

**Data sources:**
- `fetch("/products")` — category metrics
- `fetch("/payments")` — payment method breakdown

**What it shows:**

Top 15 Categories by Revenue bar chart:
- health_beauty leads at R$1,237,440
- watches_gifts second at R$1,167,247
- Shows which product verticals drive the most value

Revenue vs Review Score scatter plot:
- Each bubble = one product category
- X-axis = total revenue
- Y-axis = average review score (1-5)
- Bubble size = total order volume
- Reveals whether high-revenue categories also have good reviews
- High revenue + high reviews = strengthen this category
- High revenue + low reviews = quality/fulfilment problem to fix
- Low revenue + high reviews = underexplored growth opportunity

Payment Method donut chart:
- Credit card: 74.8%
- Boleto: 19.9% — the unbanked population insight
- Voucher: 3.81%
- Debit card: 1.54%

---

## Page 6 — Trends

**Purpose:** Deep revenue trend analysis replacing the straight Prophet forecast

**Data source:** `fetch("/revenue/monthly")`

**Why this replaced the Forecast tab:**
The Prophet model on 22 months of monthly data produced a straight
trend line — not meaningfully different from a simple linear regression.
The three charts on this page tell a richer, more actionable story
using the actual data without relying on a model with limited predictive power.

**What it shows:**

Monthly Revenue with 3-Month Moving Average:
- Light green bars = actual monthly revenue
- Dark green line = 3-month rolling average (smooths out noise)
- Moving average formula: average of this month + last 2 months
- Removes the visual noise of month-to-month fluctuations
- Reveals the true underlying trend direction
- Black Friday annotation with star emoji

3-Month Moving Average Formula:
```
MA(month_n) = (revenue(n) + revenue(n-1) + revenue(n-2)) / 3
```
Implemented in pandas: `df["total_revenue"].rolling(window=3).mean()`

Month-over-Month Growth Rate:
- Green bars = positive growth months
- Red bars = negative/declining months
- Labels show exact percentage growth on every bar
- +112.7% in January 2017 = launch hypergrowth
- +53.6% in November 2017 = Black Friday
- -26.9% in December 2017 = post-Black Friday correction
- 2018 pattern: small fluctuations around zero = mature stable business

MoM Growth Formula:
```
growth(month_n) = (revenue(n) - revenue(n-1)) / revenue(n-1) × 100
```
Implemented: `df["total_revenue"].pct_change() * 100`

Year-over-Year Comparison (2017 vs 2018):
- Side-by-side bars for the same month in different years
- Only shows Jan-Aug where both years have data
- 2018 (dark green) consistently above 2017 (light green)
- Confirms genuine year-over-year growth
- The gap between 2018 and 2017 bars = the growth achieved

Key Insights card:
- Four bullet points summarising the business story
- Written in plain English for any stakeholder
- Revenue from R$127k to R$1.13M in 10 months = 791% growth
- Black Friday +53.6% = biggest single growth event
- Stabilised at R$1M/month = transition to maturity
- 2018 consistently above 2017 = sustained growth confirmed

---

# PART 5 — TECHNICAL DECISIONS

## Why dbc.Row and dbc.Col for Layout?

Bootstrap's 12-column grid system is the industry standard for
responsive web layouts. `dbc.Row` creates a horizontal container.
`dbc.Col(width=6)` takes up 6 of 12 columns = half the width.

```python
dbc.Row([
    dbc.Col(left_chart, width=6),   # 50% width
    dbc.Col(right_chart, width=6),  # 50% width
])
```

This ensures charts sit side by side on desktop and stack
vertically on mobile automatically.

## Why config={"displayModeBar": False}?

Every dcc.Graph has this setting. By default Plotly shows a toolbar
above every chart (zoom, pan, download, etc.). For a clean dashboard
aesthetic we hide this toolbar. Users can still hover and interact
with the charts — they just cannot see the toolbar icons.

## Why suppress_callback_exceptions=True?

When the app loads, only the Overview tab is visible. The RFM,
Cohort, Geography, Products, and Trends pages do not exist in
the DOM yet — they only get created when the user clicks their tab.

Without this setting, Dash would throw an error when it tries
to register callbacks for components that do not yet exist.
This setting tells Dash: "trust me, these components will exist
when they are needed."

## Why CARD_STYLE as a Dictionary?

Instead of writing the same CSS inline on every card, we defined
one dictionary with all the card styling:

```python
CARD_STYLE = {
    "backgroundColor": "#ffffff",
    "borderRadius": "12px",
    "padding": "20px",
    "marginBottom": "20px",
    "boxShadow": "0 1px 3px rgba(0,0,0,0.08)",
    "border": "1px solid #e5e5e0"
}
```

Then every card uses `style=CARD_STYLE`. If we want to change
the card design globally, we change it in one place.
This is the DRY principle — Don't Repeat Yourself.

---

# PART 6 — RUNNING THE DASHBOARD

## Requirements

Both servers must be running simultaneously in separate terminals:

**Terminal 1 — FastAPI:**
```cmd
cd C:\Users\Obedh\Desktop\e_com_analyser
conda activate ecom-bi
set DB_PASSWORD=your_password
uvicorn api.main:app --reload
```

**Terminal 2 — Dash:**
```cmd
cd C:\Users\Obedh\Desktop\e_com_analyser
conda activate ecom-bi
python dashboard/app.py
```

**View dashboard:**
```
http://localhost:8050
```

**View API docs:**
```
http://localhost:8000/docs
```

## What Happens When You Open the Dashboard

1. Browser sends GET request to localhost:8050
2. Dash serves the HTML layout with Overview tab selected
3. The `render_tab` callback fires with value="overview"
4. `build_overview()` runs
5. `fetch("/kpis")` and `fetch("/revenue/monthly")` call FastAPI
6. FastAPI queries Supabase and returns JSON
7. Pandas builds DataFrames from the JSON
8. Plotly creates chart figures from the DataFrames
9. Dash renders the figures as interactive HTML charts
10. User sees the dashboard

---

# PART 7 — DEPLOYMENT PLAN (WEEK 9)

When deployed to Render:

- FastAPI deploys as one Web Service: `https://ecom-bi-api.onrender.com`
- Dash deploys as another Web Service: `https://ecom-bi-dashboard.onrender.com`

In `dashboard/app.py`, change:
```python
API_URL = "http://localhost:8000"
```
to:
```python
API_URL = "https://ecom-bi-api.onrender.com"
```

That single change makes the dashboard read from the live deployed API
instead of your local machine. The dashboard will then be live 24/7
at a public URL with no dependency on your PC.

---

*Documentation covers Week 7. Last updated after dashboard completion.*
