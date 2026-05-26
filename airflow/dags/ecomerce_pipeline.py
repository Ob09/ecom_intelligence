# ============================================================
# airflow/dags/ecommerce_pipeline.py
# PURPOSE: Orchestrates the full e-commerce BI pipeline
# SCHEDULE: Daily at 6am UTC
# TASKS: dbt run → dbt test → Great Expectations → Prophet
# ============================================================

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

# ── DEFAULT ARGUMENTS ──────────────────────────────────────────
# These settings apply to every task in the DAG unless overridden.
default_args = {
    "owner": "ecom-bi",

    # If the pipeline fails, retry once after 5 minutes
    "retries": 1,
    "retry_delay": timedelta(minutes=5),

    # Send an email on failure (configure SMTP in airflow.cfg)
    "email_on_failure": False,
    "email_on_retry": False,
}

# ── PROJECT PATHS ──────────────────────────────────────────────
PROJECT_ROOT = "/opt/airflow/project"  # adjust for your environment
DBT_PROJECT  = f"{PROJECT_ROOT}/dbt_project/olist_bi"

# ── DAG DEFINITION ─────────────────────────────────────────────
# schedule_interval="0 6 * * *" means: run at 6:00am every day
# This is a cron expression: minute=0, hour=6, day=*, month=*, weekday=*
with DAG(
    dag_id="ecommerce_bi_pipeline",
    description="Daily e-commerce BI pipeline: dbt → tests → quality → forecast",
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    schedule_interval="0 6 * * *",  # daily at 6am UTC
    catchup=False,  # don't run for every missed day if pipeline was down
    tags=["ecommerce", "bi", "dbt", "prophet"],
) as dag:

    # ── TASK 1: RUN DBT MODELS ─────────────────────────────────
    # Rebuilds all 13 dbt models in dependency order:
    # staging → intermediate → marts
    # BashOperator runs a shell command as a task
    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=f"cd {DBT_PROJECT} && dbt run --profiles-dir ~/.dbt",
        doc_md="""
        Runs all dbt models in dependency order.
        Rebuilds staging views, intermediate view, and all 5 mart tables.
        Fails if any model has a compilation or database error.
        """,
    )

    # ── TASK 2: RUN DBT TESTS ──────────────────────────────────
    # Runs all 27 data quality tests defined in schema.yml
    # and the singular test assert_no_negative_payments.sql
    # This task only runs if dbt_run succeeded (dependency defined below)
    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=f"cd {DBT_PROJECT} && dbt test --profiles-dir ~/.dbt",
        doc_md="""
        Runs all 27 dbt tests against the mart tables.
        Tests: unique keys, not-null constraints, accepted values,
        RFM scores 1-5, no negative payments.
        Fails if any test finds data quality issues.
        """,
    )

    # ── TASK 3: GREAT EXPECTATIONS VALIDATION ─────────────────
    # Runs business logic checks against all 5 mart tables:
    # row count minimums, value ranges, business rule validation
    great_expectations = BashOperator(
        task_id="great_expectations_validation",
        bash_command=(
            f"cd {PROJECT_ROOT} && "
            "python great_expectations/validate_expectations.py"
        ),
        doc_md="""
        Runs Great Expectations validation suite against all mart tables.
        Checks: row counts, value ranges, business logic rules.
        Fails if any expectation is violated.
        Stops pipeline before bad data reaches the dashboard.
        """,
    )

    # ── TASK 4: PROPHET FORECAST ───────────────────────────────
    # Reruns the Prophet forecasting model on the latest data
    # and saves updated forecast to mart_forecast in Supabase
    prophet_forecast = BashOperator(
        task_id="prophet_forecast",
        bash_command=(
            f"cd {PROJECT_ROOT} && "
            "python analytics/forecast.py"
        ),
        doc_md="""
        Runs Prophet revenue forecasting model.
        Reads updated monthly revenue from mart_sales.
        Generates 2-month forward forecast with confidence intervals.
        Saves results to public_marts.mart_forecast in Supabase.
        Dashboard forecast tab reads from this table.
        """,
    )

    # ── TASK 5: PIPELINE COMPLETE ──────────────────────────────
    # Simple success marker — confirms full pipeline ran cleanly
    pipeline_complete = BashOperator(
        task_id="pipeline_complete",
        bash_command=(
            f"echo 'Pipeline complete at $(date). "
            f"All tasks succeeded.'"
        ),
        doc_md="""
        Final task — confirms all previous tasks completed successfully.
        In production: trigger dashboard cache refresh or send
        success notification to Slack/email.
        """,
    )

    # ── TASK DEPENDENCIES ──────────────────────────────────────
    # The >> operator defines the execution order.
    # Each task only starts when the previous one succeeds.
    # If any task fails, all subsequent tasks are skipped.
    #
    # Flow: dbt_run → dbt_test → great_expectations
    #                                     → prophet_forecast
    #                                              → pipeline_complete
    (
        dbt_run
        >> dbt_test
        >> great_expectations
        >> prophet_forecast
        >> pipeline_complete
    )