# ingestion/load_olist.py

import os
import pandas as pd
from sqlalchemy import create_engine
from dotenv import dotenv_values

# ── 1. LOAD CREDENTIALS ──────────────────────────────────────────────────────
config = dotenv_values(".env")
DATABASE_URL = config.get("DATABASE_URL")
engine = create_engine(DATABASE_URL)

# ── 2. DEFINE FILES ───────────────────────────────────────────────────────────
files = {
    "olist_orders_dataset.csv":              "raw_orders",
    "olist_customers_dataset.csv":           "raw_customers",
    "olist_products_dataset.csv":            "raw_products",
    "olist_sellers_dataset.csv":             "raw_sellers",
    "olist_order_payments_dataset.csv":      "raw_payments",
    "olist_order_reviews_dataset.csv":       "raw_reviews",
    "olist_order_items_dataset.csv":         "raw_order_items",
    "olist_geolocation_dataset.csv":         "raw_geolocation",
    "product_category_name_translation.csv": "raw_category_translation",
}

RAW_DATA_PATH = "data/raw"

# ── 3. CHUNK SIZE ─────────────────────────────────────────────────────────────
# How many rows to send to the database at a time
# 10,000 is safe for the Session pooler connection limit
CHUNK_SIZE = 10000

# ── 4. LOAD EACH FILE ─────────────────────────────────────────────────────────
print("Starting data ingestion...\n")

for filename, table_name in files.items():

    filepath = os.path.join(RAW_DATA_PATH, filename)

    if not os.path.exists(filepath):
        print(f"⚠️  File not found, skipping: {filename}")
        continue

    print(f"Loading {filename}...")

    df = pd.read_csv(filepath)
    total_rows = len(df)

    # Split the DataFrame into chunks and load each chunk separately
    # This prevents connection timeouts on large files
    for i in range(0, total_rows, CHUNK_SIZE):

        # df[i:i+CHUNK_SIZE] slices the DataFrame
        # from row i to row i+CHUNK_SIZE
        chunk = df[i:i + CHUNK_SIZE]

        # First chunk replaces the table
        # Subsequent chunks append to it
        if i == 0:
            chunk.to_sql(
                name=table_name,
                con=engine,
                if_exists="replace",
                index=False,
                method="multi"
            )
        else:
            chunk.to_sql(
                name=table_name,
                con=engine,
                if_exists="append",
                index=False,
                method="multi"
            )

        # Show progress
        loaded = min(i + CHUNK_SIZE, total_rows)
        print(f"  {loaded:,} / {total_rows:,} rows loaded...")

    print(f"✅ {table_name}: {total_rows:,} rows loaded\n")

print("🎉 All files loaded successfully into Supabase!")