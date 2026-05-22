import os
from dotenv import load_dotenv, dotenv_values
from sqlalchemy import create_engine, text

# dotenv_values reads the .env file and returns a dictionary
# This is more reliable than load_dotenv on Windows
config = dotenv_values(".env")

# Get just the URL value from the dictionary
DATABASE_URL = config.get("DATABASE_URL")

print(f"Connecting with URL: {DATABASE_URL[:50]}...")  # shows first 50 chars only

try:
    engine = create_engine(DATABASE_URL)

    with engine.connect() as connection:
        result = connection.execute(text("SELECT version()"))
        version = result.fetchone()[0]
        print("✅ Connection successful!")
        print(f"PostgreSQL version: {version}")

except Exception as e:
    print(f"❌ Connection failed: {e}")