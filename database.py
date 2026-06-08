from datetime import datetime

from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Float
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker


DATABASE_URL = "sqlite:///stocks.db"

engine = create_engine(DATABASE_URL, echo=False)

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


def get_watchlist():
    session = SessionLocal()

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

    session = SessionLocal()

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

    session = SessionLocal()

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
    session = SessionLocal()

    try:
        positions = (
            session.query(PortfolioPosition)
            .order_by(PortfolioPosition.ticker.asc())
            .all()
        )
        return positions
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

    session = SessionLocal()

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

    session = SessionLocal()

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

    finally:
        session.close()
