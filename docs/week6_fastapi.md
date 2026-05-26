# Week 6 — FastAPI REST Layer
## Complete Documentation — Everything Explained Simply

---

# PART 1 — WHAT IS AN API AND WHY DO WE NEED ONE?

## The Restaurant Analogy

Think of the data system like a restaurant:

- You (the dashboard) are the customer sitting at a table
- The kitchen (Supabase database) has all the food (data)
- You cannot walk into the kitchen yourself — it is restricted
- The waiter (FastAPI) takes your order, goes to the kitchen,
  and brings back exactly what you asked for in the right format

In technical terms:
- The Dash dashboard sends a request to a URL like `/kpis`
- FastAPI receives that request, runs the right SQL query against Supabase
- FastAPI returns the result as JSON
- The dashboard reads that JSON and draws the chart

## Why Not Connect the Dashboard Directly to the Database?

This is the most common question. Here is why the API layer exists:

| Direct DB Connection | Via FastAPI |
|---|---|
| Database password sits in dashboard code | Password only in the API server |
| Every dashboard user hits the database | API handles all DB calls centrally |
| No control over what queries run | API controls exactly what is exposed |
| Hard to add security later | Easy to add API keys or rate limiting |
| Tightly coupled — change DB, break dashboard | Decoupled — change DB, only fix API |
| Cannot serve multiple frontends | Any app can call the same API |

The API is a contract between your data and everything that consumes it.
The dashboard does not need to know or care what database technology you use —
it just calls `/kpis` and gets numbers back.

---

# PART 2 — WHAT IS JSON?

JSON (JavaScript Object Notation) is the universal language for sending data
between systems over the internet. Every programming language can read and
write JSON.

A single record looks like a dictionary:
```json
{
  "total_revenue": 15422461.77,
  "total_orders": 96478,
  "avg_order_value": 159.85
}
```

A list of records looks like an array of dictionaries:
```json
[
  {"customer_state": "SP", "total_revenue": 5823421.50},
  {"customer_state": "RJ", "total_revenue": 2145320.75},
  {"customer_state": "MG", "total_revenue": 1432100.20}
]
```

FastAPI automatically converts Python dictionaries and lists to JSON.
You just return a dict or list from your endpoint function and FastAPI
handles the conversion and sets the correct response headers.

---

# PART 3 — WHAT IS FASTAPI?

FastAPI is a modern Python web framework for building APIs. It was released
in 2019 and has quickly become the most popular Python API framework.

Key features that make it ideal for this project:

**Automatic JSON conversion:**
Return a Python dict → FastAPI converts it to JSON automatically.
No manual serialisation needed.

**Auto-generated documentation:**
FastAPI reads your code and generates an interactive documentation website
at `/docs`. Every endpoint, every description, every parameter is documented
without you writing a single line of documentation HTML.

**Fast:**
FastAPI is built on Starlette and uses async Python under the hood.
It is one of the fastest Python web frameworks available.

**Type hints:**
FastAPI uses Python type hints to validate inputs and generate documentation.
If you define a function parameter as `int`, FastAPI automatically validates
that the input is actually an integer.

## What is Uvicorn?

Uvicorn is the server that runs your FastAPI application. Think of it like this:

- FastAPI defines what your API does (the logic)
- Uvicorn listens for HTTP requests and passes them to FastAPI (the engine)

When you run `uvicorn api.main:app --reload`:
- `api.main` = the Python file to load (`api/main.py`)
- `app` = the FastAPI object inside that file
- `--reload` = restart automatically whenever you save a code change

---

# PART 4 — THE CODE EXPLAINED

## The Application Object

```python
app = FastAPI(
    title="E-commerce BI Platform API",
    description="REST API serving analytics from the Olist dataset",
    version="1.0.0"
)
```

`FastAPI()` creates the application. The title, description, and version appear
on the auto-generated `/docs` page. This is what makes your docs page look
professional with your project name and description.

## CORS Middleware

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    ...
)
```

CORS = Cross-Origin Resource Sharing.

When your Dash dashboard (running on `http://localhost:8050`) calls your API
(running on `http://localhost:8000`), they are on different "origins" (different ports).
Browsers block these cross-origin requests by default for security reasons.

Adding CORS middleware tells the browser: "this API allows requests from any origin."
`allow_origins=["*"]` means any website can call this API.

In production you would change this to your dashboard's specific URL:
`allow_origins=["https://your-dashboard.onrender.com"]`

## The Database Connection

```python
engine = get_engine()
```

We create the database engine once when the app starts. This creates a connection
pool — a set of reusable connections to Supabase. All 9 endpoints share this
single pool. Creating a new connection for every request would be slow and
wasteful.

## The Query Helper Function

```python
def query(sql: str) -> list[dict]:
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        columns = list(result.keys())
        rows = result.fetchall()
    return [dict(zip(columns, row)) for row in rows]
```

This function is called by every endpoint. It:

1. Opens a connection from the pool
2. Executes the SQL query using SQLAlchemy's `text()` wrapper
3. Gets the column names from `result.keys()`
4. Fetches all rows with `result.fetchall()`
5. Converts each row to a dictionary using `dict(zip(columns, row))`
6. Returns a list of dictionaries which FastAPI converts to JSON

**Why `text(sql)`?**
SQLAlchemy 2.x requires all raw SQL strings to be wrapped in `text()`.
This prevents SQL injection attacks and ensures proper query handling.

**Why `dict(zip(columns, row))`?**
`zip(columns, row)` pairs each column name with its value:
```
columns = ["state", "revenue", "orders"]
row     = ("SP", 5823421.50, 32145)
zip     = [("state","SP"), ("revenue",5823421.50), ("orders",32145)]
dict    = {"state":"SP", "revenue":5823421.50, "orders":32145}
```

## Endpoint Decorators

```python
@app.get("/kpis")
def get_kpis():
    ...
```

`@app.get("/kpis")` is a decorator — it tells FastAPI:
"when someone sends a GET request to the URL `/kpis`, run this function."

GET is an HTTP method meaning "retrieve data." Other methods include POST
(create data), PUT (update data), DELETE (remove data). For a read-only
analytics API, all endpoints use GET.

---

# PART 5 — ALL 9 ENDPOINTS EXPLAINED

## GET /health
**Purpose:** Confirms the API is alive.
**Returns:** `{"status": "ok", "message": "..."}`
**Used by:** Monitoring tools, deployment health checks, Render.
**No database query** — just returns a static message instantly.

## GET /kpis
**Purpose:** The six headline business metrics for the KPI cards.
**Returns:** One JSON object with six numbers.
**SQL:** Aggregates mart_sales for delivered orders only.

Metrics returned:
- `total_revenue` — SUM of payment_value
- `total_orders` — COUNT of order_id
- `total_customers` — COUNT DISTINCT customer_unique_id
- `avg_order_value` — AVG of payment_value
- `avg_fulfilment_days` — AVG of fulfilment_days
- `pct_on_time` — percentage where delivered_on_time = true

## GET /revenue/monthly
**Purpose:** Monthly revenue time series for the trend chart.
**Returns:** Array of objects, one per month, ordered chronologically.
**SQL:** Groups mart_sales by year_month, aggregates revenue and orders.

## GET /rfm/segments
**Purpose:** Customer count and revenue per RFM segment.
**Returns:** Array of segment objects ordered by total_revenue descending.
**SQL:** Groups mart_rfm by customer_segment, aggregates key metrics.

## GET /rfm/distribution
**Purpose:** How many customers have each RFM combined score (3-15).
**Returns:** Array of 13 objects (one per possible score value).
**SQL:** Groups mart_rfm by rfm_score, counts customers per score.

## GET /cohort
**Purpose:** Full cohort retention matrix for the heatmap.
**Returns:** Array of 188 objects (one per cohort-month combination).
**SQL:** Reads mart_cohort ordered by cohort_label and month number.

## GET /geo
**Purpose:** Revenue and delivery metrics per Brazilian state.
**Returns:** Array of 27 state objects ordered by total_revenue.
**SQL:** Reads mart_geo directly — already aggregated at state grain.

## GET /products
**Purpose:** Category performance with revenue and review scores.
**Returns:** Array of ~70 category objects ordered by total_revenue.
**SQL:** Reads mart_products directly.

## GET /forecast
**Purpose:** Prophet revenue forecast with confidence intervals.
**Returns:** Array of date-revenue objects for historical fit + future months.
**SQL:** Reads mart_forecast ordered by forecast_date.

## GET /payments
**Purpose:** Order volume and revenue by payment method.
**Returns:** Array of payment type objects ordered by order_count.
**SQL:** Groups mart_sales by payment_type for delivered orders.

---

# PART 6 — THE AUTO-GENERATED DOCS PAGE

Visiting `http://localhost:8000/docs` opens the Swagger UI — an interactive
API documentation website that FastAPI generates automatically from your code.

**What you can do on the docs page:**
- See every endpoint listed with its URL and description
- Click any endpoint to expand it
- Click "Try it out" then "Execute" to call the endpoint live
- See the actual JSON response in the browser
- See the expected response format

**Why this matters for your portfolio:**
When your API is deployed to Render, the docs page will be publicly accessible.
You can share the URL with recruiters or interviewers and they can explore your
API live without needing any technical setup. This is a significant portfolio asset.

There is also an alternative docs page at `/redoc` which has a different visual
style — cleaner for reading, less interactive.

---

# PART 7 — HOW THE DASHBOARD WILL USE THE API

Your Plotly Dash dashboard (Week 7) will call these endpoints like this:

```python
import requests

# Call the KPIs endpoint
response = requests.get("http://localhost:8000/kpis")
kpis = response.json()

# Now kpis is a Python dictionary
total_revenue = kpis["total_revenue"]   # 15422461.77
total_orders  = kpis["total_orders"]    # 96478
```

The dashboard does not write any SQL. It does not connect to Supabase directly.
It just calls the API endpoints and uses the data to render charts.

This clean separation means:
- The dashboard can be changed without touching the database
- The database can be changed without touching the dashboard
- The API can be tested independently of both

---

# PART 8 — RUNNING THE API

**Start the server:**
```cmd
uvicorn api.main:app --reload
```

**Test health check:**
```
http://localhost:8000/health
```

**View interactive docs:**
```
http://localhost:8000/docs
```

**Stop the server:**
Press `Ctrl+C` in the terminal

**Note:** Every time you open a new terminal you need to set the DB_PASSWORD
environment variable before running dbt commands:
```cmd
set DB_PASSWORD=your_password
```
The API reads DATABASE_URL from .env directly so it does not need this.

---

*Documentation covers Week 6. Last updated after FastAPI completion.*
