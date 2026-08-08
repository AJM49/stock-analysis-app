from __future__ import annotations

from database import get_portfolio_positions
from portfolio import build_portfolio_dataframe
from services.market_data_service import get_stock_data


REFRESHABLE_PRICE_STATES = {
    "Missing",
    "Stale",
}


def refresh_portfolio_prices():
    """Refresh only portfolio positions with stale or missing cached prices."""

    positions = get_portfolio_positions()

    result = {
        "position_count": len(positions),
        "attempted_count": 0,
        "refreshed_count": 0,
        "skipped_fresh_count": 0,
        "attempted_tickers": [],
        "refreshed_tickers": [],
        "skipped_fresh_tickers": [],
        "failed_tickers": [],
    }

    if not positions:
        return result

    portfolio_df = build_portfolio_dataframe(
        positions
    )

    if portfolio_df.empty:
        return result

    for _, row in portfolio_df.iterrows():
        ticker = str(
            row["Ticker"]
        ).strip().upper()

        freshness = str(
            row.get(
                "Price Freshness",
                "Missing",
            )
        )

        if freshness not in REFRESHABLE_PRICE_STATES:
            result[
                "skipped_fresh_count"
            ] += 1

            result[
                "skipped_fresh_tickers"
            ].append(ticker)

            continue

        result["attempted_count"] += 1
        result[
            "attempted_tickers"
        ].append(ticker)

        try:
            history, error_message = get_stock_data(
                ticker,
                force_refresh=True,
                cache_only=False,
            )

            if (
                error_message is not None
                or history is None
                or history.empty
            ):
                result[
                    "failed_tickers"
                ].append(ticker)

                continue

            result["refreshed_count"] += 1
            result[
                "refreshed_tickers"
            ].append(ticker)

        except Exception:
            result[
                "failed_tickers"
            ].append(ticker)

    return result
