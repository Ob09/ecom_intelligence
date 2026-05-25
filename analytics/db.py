# ============================================================
# analytics/db.py
# PURPOSE: Shared database connection for all analytics scripts
# All analytics scripts import get_engine() from here
# ============================================================
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os

# Load credentials from .env file
load_dotenv()

def get_engine():
    """
    Creates and returns a SQLAlchemy engine connected to Supabase.
    Call this function at the top of any analytics script that
    needs to read from the database.
    """
    db_url = os.getenv("DATABASE_URL")

    if not db_url:
        raise ValueError(
            "DATABASE_URL not found in .env file. "
            "Check your .env has the correct connection string."
        )

    # create_engine creates a connection pool to the database.
    # pool_pre_ping=True checks the connection is alive before
    # each use — prevents errors from idle connection timeouts.
    engine = create_engine(db_url, pool_pre_ping=True)
    return engine