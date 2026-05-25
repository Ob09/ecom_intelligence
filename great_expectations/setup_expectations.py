# ============================================================
# Great Expectations — Setup and Validation Script
# PURPOSE: Connect to Supabase and validate mart tables
# RUN FROM: project root (e_com_analyser)
# ============================================================

import great_expectations as gx
from dotenv import load_dotenv
import os

# Load database credentials from .env file
load_dotenv()
DB_URL = os.getenv("DATABASE_URL")

if not DB_URL:
    raise ValueError(
        "DATABASE_URL not found in .env file. "
        "Make sure your .env has: DATABASE_URL=postgresql://..."
    )

print("Connecting to database...")

# Create a Great Expectations Data Context
# This reads from the gx/ folder we initialised
context = gx.get_context()

# ── ADD DATASOURCE ─────────────────────────────────────────────
# A datasource tells GE where your data lives.
# We connect to Supabase PostgreSQL using SQLAlchemy.
datasource = context.sources.add_or_update_sql(
    name="supabase_postgres",
    connection_string=DB_URL,
)

print("Datasource connected successfully.")

# ── ADD DATA ASSETS ────────────────────────────────────────────
# A data asset is a specific table GE can validate.
# We add all 5 mart tables as assets.

tables = [
    ("public_marts", "mart_sales"),
    ("public_marts", "mart_rfm"),
    ("public_marts", "mart_cohort"),
    ("public_marts", "mart_geo"),
    ("public_marts", "mart_products"),
]

for schema, table in tables:
    try:
        datasource.add_table_asset(
            name=f"{schema}.{table}",
            schema_name=schema,
            table_name=table,
        )
        print(f"  Added asset: {schema}.{table}")
    except Exception as e:
        print(f"  Asset {schema}.{table} already exists or error: {e}")

print("\nSetup complete. Run validate_expectations.py next.")