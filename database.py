import os
from datetime import UTC
from datetime import datetime

import streamlit as st
from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Date
from sqlalchemy import Float
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker


LOCAL_DATABASE_URL = "sqlite:///stocks.db"


def utc_now():
    """
    Return naive UTC for existing timestamp-without-timezone columns.

    utc_now() is deprecated in Python 3.14.
    """

    return datetime.now(UTC).replace(tzinfo=None)


def normalize_database_url(database_url):
    if database_url.startswith("postgres://"):
        return database_url.replace(
            "postgres://",
            "postgresql://",
            1
        )

    return database_url


def get_database_url():
    environment_url = os.getenv("DATABASE_URL")

    if environment_url:
        return normalize_database_url(environment_url)

    try:
        secrets_url = st.secrets.get("DATABASE_URL")
    except Exception:
        secrets_url = None

    if secrets_url:
        return normalize_database_url(secrets_url)

    return LOCAL_DATABASE_URL


def get_database_status():
    database_url = get_database_url()

    try:
        has_secret = "DATABASE_URL" in st.secrets
    except Exception:
        has_secret = False

    has_environment = os.getenv("DATABASE_URL") is not None

    if database_url.startswith("sqlite"):
        return (
            "SQLite local fallback | "
            + "Secret: "
            + str(has_secret)
            + " | Env: "
            + str(has_environment)
        )

    if database_url.startswith("postgresql"):
        return (
            "Cloud Postgres | "
            + "Secret: "
            + str(has_secret)
            + " | Env: "
            + str(has_environment)
        )

    return (
        "Unknown database | "
        + "Secret: "
        + str(has_secret)
        + " | Env: "
        + str(has_environment)
    )




def create_database_engine():
    database_url = get_database_url()

    if database_url.startswith("sqlite"):
        return create_engine(
            database_url,
            echo=False,
            connect_args={
                "check_same_thread": False
            }
        )

    return create_engine(
        database_url,
        echo=False,
        pool_pre_ping=True,
        pool_recycle=300
    )


engine = create_database_engine()

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False
)

Base = declarative_base()


class WatchlistStock(Base):
    __tablename__ = "watchlist_stocks"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=utc_now)


class PortfolioPosition(Base):
    __tablename__ = "portfolio_positions"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, unique=True, nullable=False, index=True)
    shares = Column(Float, nullable=False)
    buy_price = Column(Float, nullable=False)
    created_at = Column(DateTime, default=utc_now)




class PortfolioSnapshot(Base):
    """Historical portfolio value snapshot."""

    __tablename__ = "portfolio_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    snapshot_date = Column(DateTime, default=utc_now, index=True)
    total_cost_basis = Column(Float, nullable=False, default=0.0)
    total_current_value = Column(Float, nullable=False, default=0.0)
    total_gain_loss = Column(Float, nullable=False, default=0.0)
    total_gain_loss_pct = Column(Float, nullable=False, default=0.0)
    position_count = Column(Integer, nullable=False, default=0)
    risk_score = Column(Float, nullable=True)
    risk_level = Column(String, nullable=True)
    risk_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)

class PaperAccount(Base):
    """Simulated brokerage account used for paper trading."""

    __tablename__ = "paper_accounts"

    id = Column(Integer, primary_key=True, index=True)
    account_name = Column(
        String,
        nullable=False,
        default="Default Paper Account",
    )
    starting_cash = Column(
        Float,
        nullable=False,
        default=100000.0,
    )
    cash_balance = Column(
        Float,
        nullable=False,
        default=100000.0,
    )
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
    )
    created_at = Column(
        DateTime,
        default=utc_now,
        nullable=False,
    )
    updated_at = Column(
        DateTime,
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class PaperPosition(Base):
    """Open simulated position held by a paper account."""

    __tablename__ = "paper_positions"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(
        Integer,
        nullable=False,
        index=True,
    )
    ticker = Column(
        String,
        nullable=False,
        index=True,
    )
    quantity = Column(
        Float,
        nullable=False,
        default=0.0,
    )
    average_cost = Column(
        Float,
        nullable=False,
        default=0.0,
    )
    realized_profit_loss = Column(
        Float,
        nullable=False,
        default=0.0,
    )
    created_at = Column(
        DateTime,
        default=utc_now,
        nullable=False,
    )
    updated_at = Column(
        DateTime,
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class PaperOrder(Base):
    """Submitted simulated order and its execution status."""

    __tablename__ = "paper_orders"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(
        Integer,
        nullable=False,
        index=True,
    )
    ticker = Column(
        String,
        nullable=False,
        index=True,
    )
    side = Column(
        String,
        nullable=False,
    )
    order_type = Column(
        String,
        nullable=False,
        default="MARKET",
    )
    quantity = Column(
        Float,
        nullable=False,
    )
    requested_price = Column(
        Float,
        nullable=True,
    )
    executed_price = Column(
        Float,
        nullable=True,
    )
    order_value = Column(
        Float,
        nullable=True,
    )
    status = Column(
        String,
        nullable=False,
        default="PENDING",
    )
    rejection_reason = Column(
        Text,
        nullable=True,
    )
    submitted_at = Column(
        DateTime,
        default=utc_now,
        nullable=False,
    )
    executed_at = Column(
        DateTime,
        nullable=True,
    )


class PaperTrade(Base):
    """Completed simulated trade created from a filled order."""

    __tablename__ = "paper_trades"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(
        Integer,
        nullable=False,
        index=True,
    )
    order_id = Column(
        Integer,
        nullable=False,
        index=True,
    )
    ticker = Column(
        String,
        nullable=False,
        index=True,
    )
    side = Column(
        String,
        nullable=False,
    )
    quantity = Column(
        Float,
        nullable=False,
    )
    execution_price = Column(
        Float,
        nullable=False,
    )
    gross_value = Column(
        Float,
        nullable=False,
    )
    realized_profit_loss = Column(
        Float,
        nullable=False,
        default=0.0,
    )
    executed_at = Column(
        DateTime,
        default=utc_now,
        nullable=False,
    )

class PaperEquitySnapshot(Base):
    """Historical paper-account equity and drawdown snapshot."""

    __tablename__ = "paper_equity_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(
        Integer,
        nullable=False,
        index=True,
    )
    snapshot_time = Column(
        DateTime,
        default=utc_now,
        nullable=False,
        index=True,
    )
    cash_balance = Column(
        Float,
        nullable=False,
        default=0.0,
    )
    market_value = Column(
        Float,
        nullable=False,
        default=0.0,
    )
    account_equity = Column(
        Float,
        nullable=False,
        default=0.0,
    )
    total_profit_loss = Column(
        Float,
        nullable=False,
        default=0.0,
    )
    total_return_pct = Column(
        Float,
        nullable=False,
        default=0.0,
    )
    peak_equity = Column(
        Float,
        nullable=False,
        default=0.0,
    )
    drawdown_value = Column(
        Float,
        nullable=False,
        default=0.0,
    )
    drawdown_pct = Column(
        Float,
        nullable=False,
        default=0.0,
    )
    created_at = Column(
        DateTime,
        default=utc_now,
        nullable=False,
    )

class PaperRebalanceBatch(Base):
    """Persistent audit record for one rebalance execution batch."""

    __tablename__ = "paper_rebalance_batches"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )
    batch_uid = Column(
        String,
        unique=True,
        nullable=False,
        index=True,
    )
    account_id = Column(
        Integer,
        nullable=False,
        index=True,
    )
    status = Column(
        String,
        nullable=False,
        default="PENDING",
        index=True,
    )
    selected_count = Column(
        Integer,
        nullable=False,
        default=0,
    )
    filled_count = Column(
        Integer,
        nullable=False,
        default=0,
    )
    failed_count = Column(
        Integer,
        nullable=False,
        default=0,
    )
    unexecuted_count = Column(
        Integer,
        nullable=False,
        default=0,
    )
    stop_on_failure = Column(
        Boolean,
        nullable=False,
        default=True,
    )
    estimated_buy_value = Column(
        Float,
        nullable=False,
        default=0.0,
    )
    estimated_sell_value = Column(
        Float,
        nullable=False,
        default=0.0,
    )
    target_allocations_json = Column(
        Text,
        nullable=True,
    )
    risk_settings_json = Column(
        Text,
        nullable=True,
    )
    rebalance_settings_json = Column(
        Text,
        nullable=True,
    )
    pre_portfolio_json = Column(
        Text,
        nullable=True,
    )
    post_portfolio_json = Column(
        Text,
        nullable=True,
    )
    result_message = Column(
        Text,
        nullable=True,
    )
    created_at = Column(
        DateTime,
        default=utc_now,
        nullable=False,
        index=True,
    )
    started_at = Column(
        DateTime,
        nullable=True,
    )
    completed_at = Column(
        DateTime,
        nullable=True,
    )


class PaperRebalanceItem(Base):
    """One recommendation and execution result within a batch."""

    __tablename__ = "paper_rebalance_items"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )
    batch_id = Column(
        Integer,
        nullable=False,
        index=True,
    )
    account_id = Column(
        Integer,
        nullable=False,
        index=True,
    )
    sequence_number = Column(
        Integer,
        nullable=False,
    )
    ticker = Column(
        String,
        nullable=False,
        index=True,
    )
    action = Column(
        String,
        nullable=False,
    )
    requested_quantity = Column(
        Float,
        nullable=False,
        default=0.0,
    )
    requested_price = Column(
        Float,
        nullable=False,
        default=0.0,
    )
    estimated_value = Column(
        Float,
        nullable=False,
        default=0.0,
    )
    status = Column(
        String,
        nullable=False,
        default="PENDING",
        index=True,
    )
    order_id = Column(
        Integer,
        nullable=True,
        index=True,
    )
    trade_id = Column(
        Integer,
        nullable=True,
        index=True,
    )
    owned_quantity_before = Column(
        Float,
        nullable=True,
    )
    quantity_after = Column(
        Float,
        nullable=True,
    )
    cash_balance_after = Column(
        Float,
        nullable=True,
    )
    realized_profit_loss = Column(
        Float,
        nullable=False,
        default=0.0,
    )
    result_message = Column(
        Text,
        nullable=True,
    )
    created_at = Column(
        DateTime,
        default=utc_now,
        nullable=False,
    )
    executed_at = Column(
        DateTime,
        nullable=True,
    )


class MarketDataCache(Base):
    __tablename__ = "market_data_cache"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, nullable=False, index=True)
    price_date = Column(Date, nullable=False, index=True)
    open_price = Column(Float)
    high_price = Column(Float)
    low_price = Column(Float)
    close_price = Column(Float)
    volume = Column(Integer)
    fetched_at = Column(DateTime, default=utc_now)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)



def init_database():
    Base.metadata.create_all(bind=engine)


def get_database_session():
    return SessionLocal()


def get_watchlist():
    session = get_database_session()

    try:
        stocks = (
            session.query(WatchlistStock)
            .order_by(WatchlistStock.ticker.asc())
            .all()
        )
        return stocks

    finally:
        session.close()


def add_to_watchlist(ticker):
    clean_ticker = ticker.upper().strip()

    if not clean_ticker:
        return False, "Ticker cannot be empty."

    session = get_database_session()

    try:
        existing_stock = (
            session.query(WatchlistStock)
            .filter(WatchlistStock.ticker == clean_ticker)
            .first()
        )

        if existing_stock:
            message = clean_ticker + " is already in your watchlist."
            return False, message

        stock = WatchlistStock(ticker=clean_ticker)

        session.add(stock)
        session.commit()

        message = clean_ticker + " added to watchlist."
        return True, message

    except Exception as error:
        session.rollback()
        return False, "Database error: " + str(error)

    finally:
        session.close()


def remove_from_watchlist(ticker):
    clean_ticker = ticker.upper().strip()

    session = get_database_session()

    try:
        stock = (
            session.query(WatchlistStock)
            .filter(WatchlistStock.ticker == clean_ticker)
            .first()
        )

        if not stock:
            message = clean_ticker + " was not found."
            return False, message

        session.delete(stock)
        session.commit()

        message = clean_ticker + " removed from watchlist."
        return True, message

    except Exception as error:
        session.rollback()
        return False, "Database error: " + str(error)

    finally:
        session.close()


def get_portfolio_positions():
    session = get_database_session()

    try:
        positions = (
            session.query(PortfolioPosition)
            .order_by(PortfolioPosition.ticker.asc())
            .all()
        )

        if positions is None:
            return []

        return positions

    except Exception:
        return []

    finally:
        session.close()


def is_valid_ticker_value(ticker) -> bool:
    """Return True when ticker input is structurally valid."""
    if ticker is None:
        return False

    clean_ticker = str(ticker).strip().upper()

    if not clean_ticker:
        return False

    if len(clean_ticker) > 10:
        return False

    allowed_characters = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ.-")

    return all(character in allowed_characters for character in clean_ticker)

def add_portfolio_position(ticker, shares, buy_price):
    clean_ticker = ticker.upper().strip()

    if not clean_ticker:
        return False, "Ticker cannot be empty."

    if shares <= 0:
        return False, "Shares must be greater than zero."

    if buy_price <= 0:
        return False, "Buy price must be greater than zero."

    session = get_database_session()

    try:
        existing_position = (
            session.query(PortfolioPosition)
            .filter(PortfolioPosition.ticker == clean_ticker)
            .first()
        )

        if existing_position:
            message = clean_ticker + " is already in your portfolio."
            return False, message

        position = PortfolioPosition(
            ticker=clean_ticker,
            shares=shares,
            buy_price=buy_price
        )

        session.add(position)
        session.commit()

        message = clean_ticker + " added to portfolio."
        return True, message

    except Exception as error:
        session.rollback()
        return False, "Database error: " + str(error)

    finally:
        session.close()


def remove_portfolio_position(ticker):
    clean_ticker = ticker.upper().strip()

    session = get_database_session()

    try:
        position = (
            session.query(PortfolioPosition)
            .filter(PortfolioPosition.ticker == clean_ticker)
            .first()
        )

        if not position:
            message = clean_ticker + " was not found."
            return False, message

        session.delete(position)
        session.commit()

        message = clean_ticker + " removed from portfolio."
        return True, message

    except Exception as error:
        session.rollback()
        return False, "Database error: " + str(error)
def get_cached_market_data(ticker):
    clean_ticker = ticker.upper().strip()

    session = get_database_session()

    try:
        rows = (
            session.query(MarketDataCache)
            .filter(MarketDataCache.ticker == clean_ticker)
            .order_by(MarketDataCache.price_date.asc())
            .all()
        )

        if rows is None:
            return []

        return rows

    except Exception:
        return []

def save_market_data_cache(ticker, market_dataframe):
    clean_ticker = ticker.upper().strip()

    if market_dataframe is None or market_dataframe.empty:
        return False, "No market data to cache."

    session = get_database_session()

    try:
        existing_rows = (
            session.query(MarketDataCache)
            .filter(MarketDataCache.ticker == clean_ticker)
            .all()
        )

        for row in existing_rows:
            session.delete(row)

        for _, row in market_dataframe.iterrows():
            cached_row = MarketDataCache(
                ticker=clean_ticker,
                price_date=row["Date"],
                open_price=row.get("Open"),
                high_price=row.get("High"),
                low_price=row.get("Low"),
                close_price=row.get("Close"),
                volume=row.get("Volume"),
                fetched_at=utc_now()
            )

            session.add(cached_row)

        session.commit()

        return True, clean_ticker + " market data cached."

    except Exception as error:
        session.rollback()
        return False, "Database cache error: " + str(error)

    finally:
        session.close()


def clear_market_data_cache_for_ticker(ticker):
    clean_ticker = ticker.upper().strip()

    session = get_database_session()

    try:
        rows = (
            session.query(MarketDataCache)
            .filter(MarketDataCache.ticker == clean_ticker)
            .all()
        )

        for row in rows:
            session.delete(row)

        session.commit()

        return True, clean_ticker + " market cache cleared."

    except Exception as error:
        session.rollback()
        return False, "Database cache error: " + str(error)

    finally:
        session.close()
def get_market_data_cache_summary():
    session = get_database_session()

    try:
        rows = session.query(MarketDataCache).all()

        if not rows:
            return []

        summary = {}

        for row in rows:
            ticker = row.ticker

            if ticker not in summary:
                summary[ticker] = {
                    "ticker": ticker,
                    "row_count": 0,
                    "oldest_date": row.price_date,
                    "newest_date": row.price_date,
                    "last_fetched": row.fetched_at,
                }

            summary[ticker]["row_count"] += 1

            if row.price_date < summary[ticker]["oldest_date"]:
                summary[ticker]["oldest_date"] = row.price_date

            if row.price_date > summary[ticker]["newest_date"]:
                summary[ticker]["newest_date"] = row.price_date

            current_last_fetched = summary[ticker]["last_fetched"]

            if current_last_fetched is None:
                summary[ticker]["last_fetched"] = row.fetched_at
            elif row.fetched_at and row.fetched_at > current_last_fetched:
                summary[ticker]["last_fetched"] = row.fetched_at

        return list(summary.values())

    except Exception:
        return []

    finally:
        session.close()


def delete_portfolio_position(position_id):
    session = get_database_session()

    if session is None:
        return False, "Database session unavailable."

    try:
        position = (
            session.query(PortfolioPosition)
            .filter(PortfolioPosition.id == position_id)
            .first()
        )

        if position is None:
            return False, "Portfolio position not found."

        ticker = position.ticker
        session.delete(position)
        session.commit()

        return True, "Deleted portfolio position for " + ticker + "."

    except Exception as error:
        session.rollback()
        return False, "Failed to delete portfolio position: " + str(error)

    finally:
        session.close()


def get_market_data_freshness_for_ticker(ticker):
    session = get_database_session()

    if session is None:
        return {
            "ticker": ticker,
            "has_cache": False,
            "newest_date": None,
            "is_fresh": False,
            "message": "Database session unavailable.",
        }

    try:
        clean_ticker = str(ticker).strip().upper()

        newest_date = (
            session.query(MarketDataCache.price_date)
            .filter(MarketDataCache.ticker == clean_ticker)
            .order_by(MarketDataCache.price_date.desc())
            .first()
        )

        if newest_date is None:
            return {
                "ticker": clean_ticker,
                "has_cache": False,
                "newest_date": None,
                "is_fresh": False,
                "message": clean_ticker + " is not cached.",
            }

        newest_value = newest_date[0]

        age_days = (utc_now().date() - newest_value).days
        is_fresh = age_days <= 5

        return {
            "ticker": clean_ticker,
            "has_cache": True,
            "newest_date": newest_value,
            "is_fresh": is_fresh,
            "age_days": age_days,
            "message": "Fresh" if is_fresh else "Stale",
        }

    except Exception as error:
        return {
            "ticker": ticker,
            "has_cache": False,
            "newest_date": None,
            "is_fresh": False,
            "message": "Freshness check failed: " + str(error),
        }

    finally:
        session.close()





def update_portfolio_position(position_id: int, ticker, shares, buy_price) -> bool:
    """Update a portfolio position by database id."""
    session = SessionLocal()

    try:
        position = (
            session.query(PortfolioPosition)
            .filter(PortfolioPosition.id == position_id)
            .first()
        )

        if position is None:
            return False

        clean_ticker = str(ticker).strip().upper()

        if not is_valid_ticker_value(clean_ticker):
            return False

        if float(shares) <= 0:
            return False

        if float(buy_price) <= 0:
            return False

        position.ticker = clean_ticker
        position.shares = float(shares)
        position.buy_price = float(buy_price)

        session.commit()
        return True

    except Exception:
        session.rollback()
        raise

    finally:
        session.close()


def save_portfolio_snapshot(
    total_cost_basis: float,
    total_current_value: float,
    total_gain_loss: float,
    total_gain_loss_pct: float,
    position_count: int,
    risk_score: float | None = None,
    risk_level: str | None = None,
    risk_notes: str | None = None,
) -> bool:
    """Save a portfolio performance snapshot."""
    session = SessionLocal()

    try:
        snapshot = PortfolioSnapshot(
            total_cost_basis=float(total_cost_basis),
            total_current_value=float(total_current_value),
            total_gain_loss=float(total_gain_loss),
            total_gain_loss_pct=float(total_gain_loss_pct),
            position_count=int(position_count),
            risk_score=risk_score,
            risk_level=risk_level,
            risk_notes=risk_notes,
        )

        session.add(snapshot)
        session.commit()
        return True

    except Exception:
        session.rollback()
        raise

    finally:
        session.close()


def get_portfolio_snapshots(limit: int = 100):
    """Return recent portfolio snapshots."""
    session = SessionLocal()

    try:
        return (
            session.query(PortfolioSnapshot)
            .order_by(PortfolioSnapshot.snapshot_date.desc())
            .limit(limit)
            .all()
        )

    finally:
        session.close()


def delete_portfolio_snapshot(snapshot_id: int) -> bool:
    """Delete a portfolio snapshot by database id."""
    session = SessionLocal()

    try:
        snapshot = (
            session.query(PortfolioSnapshot)
            .filter(PortfolioSnapshot.id == snapshot_id)
            .first()
        )

        if snapshot is None:
            return False

        session.delete(snapshot)
        session.commit()
        return True

    except Exception:
        session.rollback()
        raise

    finally:
        session.close()


def ensure_portfolio_snapshot_risk_columns() -> None:
    """Ensure portfolio snapshot risk columns exist for existing databases."""
    engine_name = engine.dialect.name

    with engine.begin() as connection:
        if engine_name == "sqlite":
            existing_columns = {
                row[1]
                for row in connection.exec_driver_sql(
                    "PRAGMA table_info(portfolio_snapshots)"
                ).fetchall()
            }

            if "risk_score" not in existing_columns:
                connection.exec_driver_sql(
                    "ALTER TABLE portfolio_snapshots ADD COLUMN risk_score FLOAT"
                )

            if "risk_level" not in existing_columns:
                connection.exec_driver_sql(
                    "ALTER TABLE portfolio_snapshots ADD COLUMN risk_level VARCHAR"
                )

            if "risk_notes" not in existing_columns:
                connection.exec_driver_sql(
                    "ALTER TABLE portfolio_snapshots ADD COLUMN risk_notes TEXT"
                )

        else:
            connection.exec_driver_sql(
                """
                ALTER TABLE portfolio_snapshots
                ADD COLUMN IF NOT EXISTS risk_score DOUBLE PRECISION
                """
            )
            connection.exec_driver_sql(
                """
                ALTER TABLE portfolio_snapshots
                ADD COLUMN IF NOT EXISTS risk_level VARCHAR
                """
            )
            connection.exec_driver_sql(
                """
                ALTER TABLE portfolio_snapshots
                ADD COLUMN IF NOT EXISTS risk_notes TEXT
                """
            )

ensure_portfolio_snapshot_risk_columns()


class PortfolioScenario(Base):
    """Saved what-if scenario history."""

    __tablename__ = "portfolio_scenarios"

    id = Column(Integer, primary_key=True, index=True)
    scenario_date = Column(DateTime, default=utc_now, nullable=False)
    ticker = Column(String, nullable=False)
    action = Column(String, nullable=False)
    scenario_portfolio_value = Column(Float, nullable=False)
    value_delta = Column(Float, nullable=False)
    scenario_gain_loss = Column(Float, nullable=False)
    gain_loss_delta = Column(Float, nullable=False)
    scenario_risk_score = Column(Float, nullable=True)
    scenario_risk_level = Column(String, nullable=True)
    scenario_decision = Column(String, nullable=True)
    scenario_notes = Column(Text, nullable=True)


def save_portfolio_scenario(
    ticker: str,
    action: str,
    scenario_portfolio_value: float,
    value_delta: float,
    scenario_gain_loss: float,
    gain_loss_delta: float,
    scenario_risk_score: float | None,
    scenario_risk_level: str | None,
    scenario_decision: str | None,
    scenario_notes: str | None,
) -> bool:
    """Save a what-if scenario to the database."""
    session = SessionLocal()

    try:
        scenario = PortfolioScenario(
            ticker=str(ticker).upper(),
            action=str(action),
            scenario_portfolio_value=float(scenario_portfolio_value),
            value_delta=float(value_delta),
            scenario_gain_loss=float(scenario_gain_loss),
            gain_loss_delta=float(gain_loss_delta),
            scenario_risk_score=(
                float(scenario_risk_score)
                if scenario_risk_score is not None
                else None
            ),
            scenario_risk_level=scenario_risk_level,
            scenario_decision=scenario_decision,
            scenario_notes=scenario_notes,
        )

        session.add(scenario)
        session.commit()
        return True

    except Exception:
        session.rollback()
        return False

    finally:
        session.close()


def get_portfolio_scenarios(limit: int = 100) -> list[PortfolioScenario]:
    """Return saved what-if scenarios from newest to oldest."""
    session = SessionLocal()

    try:
        return (
            session.query(PortfolioScenario)
            .order_by(PortfolioScenario.scenario_date.desc())
            .limit(limit)
            .all()
        )

    finally:
        session.close()


def delete_portfolio_scenario(scenario_id: int) -> bool:
    """Delete one saved what-if scenario."""
    session = SessionLocal()

    try:
        scenario = (
            session.query(PortfolioScenario)
            .filter(PortfolioScenario.id == scenario_id)
            .first()
        )

        if scenario is None:
            return False

        session.delete(scenario)
        session.commit()
        return True

    except Exception:
        session.rollback()
        return False

    finally:
        session.close()


def ensure_portfolio_scenario_table() -> bool:
    """Ensure the portfolio_scenarios table exists."""
    try:
        Base.metadata.create_all(bind=engine)
        return True
    except Exception:
        return False


def get_portfolio_scenario_count() -> int:
    """Return the number of saved portfolio scenarios."""
    session = SessionLocal()

    try:
        return int(session.query(PortfolioScenario).count())
    except Exception:
        return 0
    finally:
        session.close()


def delete_duplicate_portfolio_scenarios() -> tuple[int, str]:
    """
    Delete duplicate portfolio scenario records.

    A duplicate is defined as same:
    ticker, action, scenario_portfolio_value, value_delta,
    scenario_gain_loss, gain_loss_delta, scenario_risk_score,
    scenario_risk_level, scenario_decision, scenario_notes.
    """
    session = SessionLocal()

    try:
        scenarios = (
            session.query(PortfolioScenario)
            .order_by(PortfolioScenario.scenario_date.asc())
            .all()
        )

        seen = set()
        duplicate_ids = []

        for scenario in scenarios:
            scenario_key = (
                str(scenario.ticker),
                str(scenario.action),
                round(float(scenario.scenario_portfolio_value or 0), 4),
                round(float(scenario.value_delta or 0), 4),
                round(float(scenario.scenario_gain_loss or 0), 4),
                round(float(scenario.gain_loss_delta or 0), 4),
                round(float(scenario.scenario_risk_score or 0), 4),
                str(scenario.scenario_risk_level),
                str(scenario.scenario_decision),
                str(scenario.scenario_notes),
            )

            if scenario_key in seen:
                duplicate_ids.append(scenario.id)
            else:
                seen.add(scenario_key)

        if not duplicate_ids:
            return 0, "No duplicate portfolio scenarios found."

        deleted_count = (
            session.query(PortfolioScenario)
            .filter(PortfolioScenario.id.in_(duplicate_ids))
            .delete(synchronize_session=False)
        )

        session.commit()

        return int(deleted_count), f"Deleted {int(deleted_count)} duplicate scenario record(s)."

    except Exception as error:
        session.rollback()
        return 0, f"Duplicate cleanup failed: {error}"

    finally:
        session.close()


def get_portfolio_scenario_database_health() -> dict:
    """Return basic health information for the portfolio scenario database."""
    table_ready = ensure_portfolio_scenario_table()
    scenario_count = get_portfolio_scenario_count() if table_ready else 0

    return {
        "table_ready": table_ready,
        "scenario_count": scenario_count,
    }


def get_watchlist_count() -> int:
    """Return saved watchlist count."""
    session = SessionLocal()

    try:
        return int(session.query(WatchlistStock).count())
    except Exception:
        return 0
    finally:
        session.close()


def get_portfolio_position_count() -> int:
    """Return saved portfolio position count."""
    session = SessionLocal()

    try:
        return int(session.query(PortfolioPosition).count())
    except Exception:
        return 0
    finally:
        session.close()


def get_portfolio_snapshot_count() -> int:
    """Return saved portfolio snapshot count."""
    session = SessionLocal()

    try:
        return int(session.query(PortfolioSnapshot).count())
    except Exception:
        return 0
    finally:
        session.close()

def get_active_paper_account():
    """Return the active paper account, if one exists."""

    session = get_database_session()

    try:
        return (
            session.query(PaperAccount)
            .filter(PaperAccount.is_active.is_(True))
            .order_by(PaperAccount.id.asc())
            .first()
        )
    finally:
        session.close()


def create_paper_account(
    account_name="Default Paper Account",
    starting_cash=100000.0,
):
    """Create a new active paper-trading account."""

    clean_name = str(account_name).strip()
    clean_starting_cash = float(starting_cash)

    if not clean_name:
        return False, "Account name cannot be empty.", None

    if clean_starting_cash <= 0:
        return False, "Starting cash must be greater than zero.", None

    session = get_database_session()


    try:
        existing_accounts = (
            session.query(PaperAccount)
            .filter(PaperAccount.is_active.is_(True))
            .all()
        )

        for account in existing_accounts:
            account.is_active = False

        paper_account = PaperAccount(
            account_name=clean_name,
            starting_cash=clean_starting_cash,
            cash_balance=clean_starting_cash,
            is_active=True,
        )

        session.add(paper_account)
        session.commit()
        session.refresh(paper_account)

        return (
            True,
            "Paper-trading account created.",
            paper_account,
        )

    except Exception as error:
        session.rollback()
        return (
            False,
            "Database error: " + str(error),
            None,
        )

    finally:
        session.close()


def get_or_create_paper_account(
    starting_cash=100000.0,
):
    """Return the active account or create the default 
account."""

    account = get_active_paper_account()

    if account:
        return account

    success, message, account = create_paper_account(
        account_name="Default Paper Account",
        starting_cash=starting_cash,
    )

    if not success:
        raise RuntimeError(message)

    return account


def get_paper_positions(account_id):
    """Return all open positions for a paper account."""

    session = get_database_session()

    try:
        return (
            session.query(PaperPosition)
            .filter(
                PaperPosition.account_id == int(account_id),
                PaperPosition.quantity > 0,
            )
            .order_by(PaperPosition.ticker.asc())
            .all()
        )
    finally:
        session.close()


def get_paper_orders(
    account_id,
    limit=100,
):
    """Return recent paper orders."""

    session = get_database_session()

    try:
        return (
            session.query(PaperOrder)
            .filter(PaperOrder.account_id == int(account_id))
            .order_by(PaperOrder.submitted_at.desc())
            .limit(int(limit))
            .all()
        )
    finally:
        session.close()


def get_paper_trades(
    account_id,
    limit=100,
):
    """Return recent completed paper trades."""

    session = get_database_session()

    try:
        return (
            session.query(PaperTrade)
            .filter(PaperTrade.account_id == int(account_id))
            .order_by(PaperTrade.executed_at.desc())
            .limit(int(limit))
            .all()
        )
    finally:
        session.close()


def get_app_database_health() -> dict:
    """Return app-level database health summary."""
    scenario_health = get_portfolio_scenario_database_health()

    try:
        Base.metadata.create_all(bind=engine)
        database_ready = True
    except Exception:
        database_ready = False

    return {
        "database_ready": database_ready,
        "scenario_table_ready": scenario_health.get("table_ready", False),
        "watchlist_count": get_watchlist_count() if database_ready else 0,
        "portfolio_position_count": (
            get_portfolio_position_count() if database_ready else 0
        ),
        "portfolio_snapshot_count": (
            get_portfolio_snapshot_count() if database_ready else 0
        ),
        "portfolio_scenario_count": (
            scenario_health.get("scenario_count", 0) if database_ready else 0
        ),
    }
