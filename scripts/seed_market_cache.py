import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from market_data import clean_ticker_symbol
from market_data import fetch_alpha_vantage_daily
from database import save_market_data_cache


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/seed_market_cache.py AAPL")
        raise SystemExit(1)

    ticker = clean_ticker_symbol(sys.argv[1])

    if not ticker:
        print("Ticker cannot be empty.")
        raise SystemExit(1)

    print(f"Fetching market data for {ticker}...")

    history, error = fetch_alpha_vantage_daily(ticker)

    if error:
        print(f"Error: {error}")
        raise SystemExit(1)

    if history.empty:
        print(f"No market data returned for {ticker}.")
        raise SystemExit(1)

    success, message = save_market_data_cache(ticker, history)

    if not success:
        print(f"Cache save failed: {message}")
        raise SystemExit(1)

    print(message)
    print(f"Rows cached: {len(history)}")


if __name__ == "__main__":
    main()
