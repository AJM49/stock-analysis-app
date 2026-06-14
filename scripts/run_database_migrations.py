from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import text


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database import engine


MIGRATIONS = [
    """
    CREATE TABLE IF NOT EXISTS market_data_cache (
        id SERIAL PRIMARY KEY,
        ticker VARCHAR NOT NULL,
        price_date DATE NOT NULL,
        open_price FLOAT,
        high_price FLOAT,
        low_price FLOAT,
        close_price FLOAT,
        volume INTEGER,
        fetched_at TIMESTAMP,
        created_at TIMESTAMP,
        updated_at TIMESTAMP
    )
    """,
    """
    ALTER TABLE market_data_cache
    ADD COLUMN IF NOT EXISTS fetched_at TIMESTAMP
    """,
    """
    ALTER TABLE market_data_cache
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMP
    """,
    """
    ALTER TABLE market_data_cache
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP
    """,
    """
    ALTER TABLE market_data_cache
    ADD COLUMN IF NOT EXISTS price_date DATE
    """,
    """
    ALTER TABLE market_data_cache
    ADD COLUMN IF NOT EXISTS open_price FLOAT
    """,
    """
    ALTER TABLE market_data_cache
    ADD COLUMN IF NOT EXISTS high_price FLOAT
    """,
    """
    ALTER TABLE market_data_cache
    ADD COLUMN IF NOT EXISTS low_price FLOAT
    """,
    """
    ALTER TABLE market_data_cache
    ADD COLUMN IF NOT EXISTS close_price FLOAT
    """,
    """
    ALTER TABLE market_data_cache
    ADD COLUMN IF NOT EXISTS volume INTEGER
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_market_data_cache_ticker
    ON market_data_cache (ticker)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_market_data_cache_price_date
    ON market_data_cache (price_date)
    """,
]


def run_migrations():
    with engine.begin() as connection:
        for migration in MIGRATIONS:
            connection.execute(text(migration))

    print("Database migrations completed.")


if __name__ == "__main__":
    run_migrations()
