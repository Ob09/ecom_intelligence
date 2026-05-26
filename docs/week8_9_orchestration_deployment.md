# Weeks 8 & 9 — Pipeline Orchestration and Deployment
## Complete Documentation — Everything Explained Simply

---

# WEEK 8 — PIPELINE ORCHESTRATION

## What is Pipeline Orchestration?

A data pipeline is a sequence of steps that must run in a specific order.
In this project the pipeline is:

```
Step 1: Rebuild all dbt models (transform raw data)
Step 2: Run all dbt tests (validate the transformations)
Step 3: Run Great Expectations (validate business logic)
Step 4: Run Prophet forecast (update revenue predictions)
Step 5: Done — dashboard now shows fresh data
```

If any step fails, all subsequent steps must stop. You cannot run dbt tests if dbt run failed. You cannot forecast from data that failed validation.

Pipeline orchestration means automating this sequence, enforcing the correct order, handling failures gracefully, and providing visibility into what ran and when.

---

## Part 1 — Apache Airflow (Local Development Tool)

### What is Airflow?

Apache Airflow is the industry-standard pipeline orchestration tool used at companies like Airbnb (where it was invented), Netflix, Twitter, and thousands of others.

It lets you define pipelines as Python code using a concept called a DAG.

### What is a DAG?

DAG stands for Directed Acyclic Graph. This sounds complex but it is just a flowchart with rules:

- **Directed** — tasks flow in one direction (A → B → C, never C → B → A)
- **Acyclic** — no cycles (A → B → A would be a cycle and is not allowed)
- **Graph** — a collection of nodes (tasks) connected by edges (dependencies)

Your pipeline DAG looks like this:

```
[dbt_run] → [dbt_test] → [great_expectations] → [prophet_forecast] → [done]
```

Each box is a Task. The arrows are Dependencies. Task 2 only starts when Task 1 succeeds.

### The Airflow DAG File Explained

The DAG lives at `airflow/dags/ecommerce_pipeline.py`.

**Importing the tools:**
```python
from airflow import DAG
from airflow.operators.bash import BashOperator
```
`DAG` — the class that defines your pipeline
`BashOperator` — a task that runs a shell command (like typing in a terminal)

**Default arguments:**
```python
default_args = {
    "owner": "ecom-bi",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}
```
These settings apply to every task. `retries: 1` means if a task fails, Airflow tries it once more after 5 minutes before giving up.

**Creating the DAG:**
```python
with DAG(
    dag_id="ecommerce_bi_pipeline",
    schedule_interval="0 6 * * *",
    start_date=datetime(2024, 1, 1),
    catchup=False,
) as dag:
```
`dag_id` — unique name for this pipeline
`schedule_interval` — cron expression: run at 6am every day
`catchup=False` — do not run for every missed day if the pipeline was down

**A task:**
```python
dbt_run = BashOperator(
    task_id="dbt_run",
    bash_command="cd dbt_project/olist_bi && dbt run",
)
```
`task_id` — unique name for this task
`bash_command` — the shell command to run

**Task dependencies:**
```python
dbt_run >> dbt_test >> great_expectations >> prophet_forecast >> pipeline_complete
```
The `>>` operator means "then run". This single line defines the entire execution order.

### Why We Did Not Run Airflow Locally

Airflow was designed for Linux servers. Running it on Windows requires either:
- WSL (Windows Subsystem for Linux) — adds significant complexity
- Docker — another tool to learn and configure
- Fighting persistent path and SQLite issues

For this portfolio project, Airflow demonstrates that you understand professional pipeline orchestration concepts and can write DAG code. The actual automated scheduling is handled by GitHub Actions.

In a real job on a Linux server or in Docker, this DAG would run perfectly.

---

## Part 2 — GitHub Actions (Production Scheduler)

### What is GitHub Actions?

GitHub Actions is a free cloud automation service built into GitHub. It runs your code automatically on GitHub's servers in response to events — like a push to your repository, or a scheduled time.

### How It Works — Step by Step

1. You push code to GitHub
2. GitHub reads `.github/workflows/pipeline.yml`
3. At 6am UTC, GitHub spins up a fresh Ubuntu Linux machine
4. That machine runs every step in your workflow file
5. When done, the machine shuts down — you pay nothing
6. Your Supabase database has been updated with fresh data

### The Workflow File Explained

The workflow lives at `.github/workflows/pipeline.yml`.

**The trigger section:**
```yaml
on:
  schedule:
    - cron: "0 6 * * *"
  workflow_dispatch:
```
`schedule` — runs automatically every day at 6am UTC
`workflow_dispatch` — adds a "Run workflow" button in GitHub UI for manual triggers

**Understanding cron expressions:**
```
0  6  *  *  *
│  │  │  │  │
│  │  │  │  └─ day of week (* = every day)
│  │  │  └──── month (* = every month)
│  │  └─────── day of month (* = every day)
│  └────────── hour (6 = 6am)
└───────────── minute (0 = on the hour)
```

**The job section:**
```yaml
jobs:
  run_pipeline:
    runs-on: ubuntu-latest
```
`ubuntu-latest` — GitHub spins up a fresh Ubuntu Linux machine

**Each step:**
```yaml
steps:
  - name: Checkout repository
    uses: actions/checkout@v4
```
`name` — human-readable label shown in the GitHub Actions logs
`uses` — a pre-built action (like a function someone else wrote)
`actions/checkout@v4` — clones your GitHub repo onto the runner machine

**Installing Python:**
```yaml
  - name: Set up Python 3.11
    uses: actions/setup-python@v4
    with:
      python-version: "3.11"
```
Installs Python 3.11 on the Ubuntu machine.

**Installing dependencies:**
```yaml
  - name: Install dependencies
    run: pip install -r requirements.txt
```
`run` — runs a shell command directly (unlike `uses` which calls a pre-built action)
Installs all your Python packages from requirements.txt.

**Creating credentials securely:**
```yaml
  - name: Configure dbt profile
    run: |
      mkdir -p ~/.dbt
      cat > ~/.dbt/profiles.yml << EOF
      olist_bi:
        outputs:
          dev:
            pass: ${{ secrets.DB_PASSWORD }}
      EOF
```
`${{ secrets.DB_PASSWORD }}` — injects the encrypted GitHub Secret value
The `<<EOF` syntax is a heredoc — writes multiple lines to a file
The actual password value is never visible in any log

**Running dbt:**
```yaml
  - name: Run dbt models
    working-directory: dbt_project/olist_bi
    run: dbt run --profiles-dir ~/.dbt
```
`working-directory` — changes into this folder before running the command
Exactly the same command you run locally, just on a cloud machine

### GitHub Secrets

Secrets are encrypted credentials stored in your GitHub repository settings. They are:
- Encrypted at rest — stored in encrypted form, unreadable
- Injected at runtime — only decrypted inside a running Actions workflow
- Never logged — GitHub automatically masks secret values in logs
- Safe in public repos — nobody browsing your code can see them

The four secrets we added:
- `DATABASE_URL` — full Supabase connection string
- `DB_HOST` — the database server address
- `DB_USER` — the database username
- `DB_PASSWORD` — the database password

### Why GitHub Actions is Better Than Airflow for This Project

| Airflow | GitHub Actions |
|---|---|
| Requires a server to run on | Runs on GitHub's free cloud |
| Complex to set up on Windows | Works from a YAML file |
| Needs memory and compute | Completely free for public repos |
| Hard to share | Anyone can see the workflow file |
| Great for complex enterprise pipelines | Perfect for portfolio projects |

---

# WEEK 9 — DEPLOYMENT ON RENDER

## What is Deployment?

Deployment means taking code that runs on your local machine and moving it to a server on the internet so anyone can access it from anywhere, at any time, without your laptop being involved.

Before deployment:
- Dashboard only works when your laptop is on and running the script
- Only you can see it at `http://localhost:8050`

After deployment:
- Dashboard runs 24/7 on Render's servers
- Anyone in the world can visit the public URL
- Your laptop can be completely off

## What is Render?

Render is a cloud hosting platform that runs web applications. The free tier gives you:
- Two Web Services (we used both — one for FastAPI, one for Dash)
- Automatic deployment from GitHub — push code, Render redeploys automatically
- HTTPS by default — your URLs start with `https://` secured automatically
- 750 hours of runtime per month — enough for 24/7 operation

**The one limitation of the free tier:**
Services spin down after 15 minutes of inactivity. The first request after sleeping takes 30-50 seconds to wake the server up. After that, everything is fast. Paid tiers stay awake permanently.

## How Render Connects to GitHub

When you connected your GitHub repository to Render, you gave Render permission to read your code. Every time you push a commit to your `main` branch, Render automatically:
1. Detects the new commit
2. Clones your repository onto a Render server
3. Runs your build command (`pip install -r requirements.txt`)
4. Starts your application with the start command
5. Makes it available at your public URL

This means deploying an update is as simple as `git push`.

## Service 1 — FastAPI on Render

**What it does:** Serves all your analytics data as JSON through 9 REST API endpoints

**Build command:**
```
pip install -r requirements.txt
```
Installs all Python packages on Render's server.

**Start command:**
```
uvicorn api.main:app --host 0.0.0.0 --port $PORT
```
`uvicorn` — the web server that runs FastAPI
`api.main:app` — load the `app` object from `api/main.py`
`--host 0.0.0.0` — listen on all network interfaces (required for Render)
`--port $PORT` — Render assigns a random port number and passes it as $PORT

**Environment variable:**
```
DATABASE_URL = postgresql://...
```
The database connection string, stored securely in Render's environment variables. Never in the code.

**Live URL:** `https://ecom-bi-api.onrender.com`

## Service 2 — Plotly Dash on Render

**What it does:** Serves the interactive dashboard at a public URL

**Build command:**
```
pip install -r requirements.txt
```

**Start command:**
```
gunicorn dashboard.app:server --bind 0.0.0.0:$PORT
```
`gunicorn` — a production-grade Python web server (more robust than running Python directly)
`dashboard.app:server` — load the `server` object from `dashboard/app.py`
`--bind 0.0.0.0:$PORT` — listen on Render's assigned port

Why `server` not `app`? Gunicorn needs a WSGI server object, not the Dash app object.
That is why we added `server = app.server` to `app.py` — it exposes the underlying
Flask server that gunicorn can use.

**Environment variable:**
```
API_URL = https://ecom-bi-api.onrender.com
```
Tells the dashboard where to find the API. Locally this is `http://localhost:8000`.
On Render this is the live API URL. We used `os.getenv("API_URL", "http://localhost:8000")`
in the code so it works in both environments without changing anything.

**Live URL:** `https://ecom-bi-dashboard.onrender.com`

## The Python Version Fix

Render by default uses the latest Python version available. When we first deployed,
it used Python 3.14 which was too new — pandas 2.1.4 had not been updated to support it yet.

The fix was a `.python-version` file in the project root:
```
3.11.0
```
This single file tells Render exactly which Python version to use. Problem solved.

## The Complete Deployment Flow

```
You push code to GitHub
        ↓
Render detects new commit
        ↓
Render clones your repository
        ↓
Render runs: pip install -r requirements.txt
        ↓
Render starts: gunicorn dashboard.app:server
        ↓
Dashboard is live at public URL
        ↓
Dashboard calls: https://ecom-bi-api.onrender.com/kpis
        ↓
FastAPI runs SQL against Supabase
        ↓
Returns JSON to dashboard
        ↓
Dashboard renders charts
        ↓
User sees live data
```

Your laptop is not involved in any step of this flow.

## What Happens Every Day at 6am

```
GitHub Actions wakes up
        ↓
Spins up Ubuntu machine
        ↓
Clones your repository
        ↓
Installs dependencies
        ↓
Runs: dbt run (rebuilds all mart tables)
        ↓
Runs: dbt test (validates 27 checks)
        ↓
Runs: Great Expectations (validates business logic)
        ↓
Runs: Prophet forecast (updates mart_forecast)
        ↓
Machine shuts down
        ↓
Supabase now has fresh data
        ↓
Dashboard reads fresh data from API
        ↓
Users see updated numbers
```

Total cost to you: R$0. Total involvement required: none.

---

## Summary of All Deployment Decisions

| Decision | Choice | Reason |
|---|---|---|
| Database hosting | Supabase free tier | PostgreSQL in EU West Ireland, session pooler for IPv4 |
| API hosting | Render free tier | Automatic GitHub deploy, zero config |
| Dashboard hosting | Render free tier | Same as API, both on same platform |
| Python version | 3.11.0 | Stable, compatible with all our dependencies |
| Production server | Gunicorn | Industry standard for Python web apps |
| Scheduling | GitHub Actions | Free, cloud-native, no server required |
| Orchestration code | Airflow DAG | Industry standard, demonstrates knowledge |
| Credentials | Environment variables + GitHub Secrets | Never in code, encrypted at rest |

---

*Documentation covers Weeks 8 and 9. Last updated after successful deployment.*
