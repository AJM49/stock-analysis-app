import os
from datetime import datetime

import streamlit as st
from sqlalchemy import Column
from sqlalchemy import DateTime
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
