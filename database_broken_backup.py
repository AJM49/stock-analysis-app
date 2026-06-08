cat > database.py <<'PY'
from datetime import datetime

from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker


DATABASE_URL = "sqlite:///stocks.db"

engine = create_engine(
    DATABASE_URL,
    echo=False
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False
)

Base = declarative_base()


class WatchlistStock(Base):
    __tablename__ = "watchlist_stocks"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    ticker = Column(
        String,
        unique=True,
        nullable=False,
        index=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )


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
            return False, f"{clean_ticker} is already in your watchlist."

        stock = WatchlistStock(ticker=clean_ticker)

        session.add(stock)
        session.commit()

        return True, f"{clean_ticker} added to watchlist."

    except Exception as error:
        session.rollback()
        return False, f"Database error: {error}"

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
            return False, f"{clean_ticker} was not found in your 
watchlist."

        session.delete(stock)
        session.commit()

        return True, f"{clean_ticker} removed from watchlist."

    except Exception as error:
        session.rollback()
        return False, f"Database error: {error}"

    finally:
        session.close()
PY
