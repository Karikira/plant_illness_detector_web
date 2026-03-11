"""Utility for obtaining a raw psycopg2 connection to the Supabase
PostgreSQL database.  This module is optional – the Supabase Python client
(`supabase`) is usually more convenient, but you can drop down to this
helper if you need to execute raw SQL.

Environment variables `DB_HOST`, `DB_USER`, `DB_PASSWORD` (and optionally
`DB_NAME`/`DB_PORT`) are expected.
"""

import os
import psycopg2


def get_db():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "your-supabase-host"),
        database=os.getenv("DB_NAME", "postgres"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
        port=os.getenv("DB_PORT", "5432"),
    )
