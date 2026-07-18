import os
from datetime import datetime

import streamlit as st
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Date
from sqlalchemy import Float
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker


LOCAL_DATABASE_URL = "sqlite:///stocks.db"


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
    created_at = Column(DateTime, default=datetime.utcnow)


class PortfolioPosition(Base):
    __tablename__ = "portfolio_positions"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, unique=True, nullable=False, index=True)
    shares = Column(Float, nullable=False)
    buy_price = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)




class PortfolioSnapshot(Base):
    """Historical portfolio value snapshot."""

    __tablename__ = "portfolio_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    snapshot_date = Column(DateTime, default=datetime.utcnow, index=True)
    total_cost_basis = Column(Float, nullable=False, default=0.0)
    total_current_value = Column(Float, nullable=False, default=0.0)
    total_gain_loss = Column(Float, nullable=False, default=0.0)
    total_gain_loss_pct = Column(Float, nullable=False, default=0.0)
    position_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

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
    fetched_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)



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
                fetched_at=datetime.utcnow()
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

        age_days = (datetime.utcnow().date() - newest_value).days
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
