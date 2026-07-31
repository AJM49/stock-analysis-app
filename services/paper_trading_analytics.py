"""Closed-trade analytics for paper-trading accounts."""

from collections import defaultdict
from math import isfinite

from database import PaperTrade
from database import get_database_session


MONEY_PRECISION = 2
PERCENT_PRECISION = 2
FLOAT_TOLERANCE = 1e-9


def safe_float(value, default=0.0):
    """Convert a value to a finite float."""

    try:
        number = float(value)
    except (TypeError, ValueError):
        return float(default)

    if not isfinite(number):
        return float(default)

    return number


def classify_trade_result(realized_profit_loss):
    """Classify a realized trade as WIN, LOSS, or BREAKEVEN."""

    realized_value = safe_float(realized_profit_loss)

    if realized_value > FLOAT_TOLERANCE:
        return "WIN"

    if realized_value < -FLOAT_TOLERANCE:
        return "LOSS"

    return "BREAKEVEN"


def get_closed_paper_trades(account_id, limit=None):
    """
    Return completed SELL trades chronologically.

    Realized profit or loss is generated when shares are sold, so
    BUY executions are excluded from closed-trade analytics.
    """

    session = get_database_session()

    try:
        query = (
            session.query(PaperTrade)
            .filter(
                PaperTrade.account_id == int(account_id),
                PaperTrade.side == "SELL",
            )
            .order_by(
                PaperTrade.executed_at.asc(),
                PaperTrade.id.asc(),
            )
        )

        if limit is not None:
            clean_limit = max(int(limit), 1)
            query = query.limit(clean_limit)

        return query.all()

    finally:
        session.close()


def build_empty_analytics():
    """Return an analytics result for an account with no closed trades."""

    return {
        "closed_trades": 0,
        "winning_trades": 0,
        "losing_trades": 0,
        "breakeven_trades": 0,
        "win_rate_pct": 0.0,
        "loss_rate_pct": 0.0,
        "average_gain": 0.0,
        "average_loss": 0.0,
        "gross_profit": 0.0,
        "gross_loss": 0.0,
        "profit_factor": None,
        "trade_expectancy": 0.0,
        "largest_winner": 0.0,
        "largest_loser": 0.0,
        "net_realized_profit_loss": 0.0,
        "total_sell_value": 0.0,
        "total_shares_sold": 0.0,
        "by_ticker": [],
        "closed_trade_rows": [],
    }


def calculate_profit_factor(gross_profit, gross_loss):
    """
    Calculate gross profit divided by absolute gross loss.

    Returns:
    - None when there are no gains and no losses.
    - infinity when gains exist but no losses exist.
    - a finite ratio otherwise.
    """

    clean_profit = safe_float(gross_profit)
    clean_loss = abs(safe_float(gross_loss))

    if clean_loss <= FLOAT_TOLERANCE:
        if clean_profit > FLOAT_TOLERANCE:
            return float("inf")

        return None

    return round(
        clean_profit / clean_loss,
        PERCENT_PRECISION,
    )


def summarize_ticker_performance(trades):
    """Aggregate closed-trade results by ticker."""

    ticker_data = defaultdict(
        lambda: {
            "closed_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "breakeven_trades": 0,
            "gross_profit": 0.0,
            "gross_loss": 0.0,
            "net_realized_profit_loss": 0.0,
            "shares_sold": 0.0,
            "sell_value": 0.0,
        }
    )

    for trade in trades:
        ticker = str(trade.ticker or "UNKNOWN").upper()
        realized_value = safe_float(
            trade.realized_profit_loss
        )
        result = classify_trade_result(realized_value)

        row = ticker_data[ticker]
        row["closed_trades"] += 1
        row["shares_sold"] += safe_float(trade.quantity)
        row["sell_value"] += safe_float(trade.gross_value)
        row["net_realized_profit_loss"] += realized_value

        if result == "WIN":
            row["winning_trades"] += 1
            row["gross_profit"] += realized_value
        elif result == "LOSS":
            row["losing_trades"] += 1
            row["gross_loss"] += realized_value
        else:
            row["breakeven_trades"] += 1

    results = []

    for ticker, values in ticker_data.items():
        closed_trades = values["closed_trades"]
        winning_trades = values["winning_trades"]

        if closed_trades:
            win_rate_pct = (
                winning_trades / closed_trades * 100
            )
            expectancy = (
                values["net_realized_profit_loss"]
                / closed_trades
            )
        else:
            win_rate_pct = 0.0
            expectancy = 0.0

        results.append(
            {
                "ticker": ticker,
                "closed_trades": closed_trades,
                "winning_trades": winning_trades,
                "losing_trades": values["losing_trades"],
                "breakeven_trades": (
                    values["breakeven_trades"]
                ),
                "win_rate_pct": round(
                    win_rate_pct,
                    PERCENT_PRECISION,
                ),
                "gross_profit": round(
                    values["gross_profit"],
                    MONEY_PRECISION,
                ),
                "gross_loss": round(
                    values["gross_loss"],
                    MONEY_PRECISION,
                ),
                "net_realized_profit_loss": round(
                    values["net_realized_profit_loss"],
                    MONEY_PRECISION,
                ),
                "trade_expectancy": round(
                    expectancy,
                    MONEY_PRECISION,
                ),
                "profit_factor": calculate_profit_factor(
                    gross_profit=values["gross_profit"],
                    gross_loss=values["gross_loss"],
                ),
                "shares_sold": round(
                    values["shares_sold"],
                    6,
                ),
                "sell_value": round(
                    values["sell_value"],
                    MONEY_PRECISION,
                ),
            }
        )

    return sorted(
        results,
        key=lambda row: (
            row["net_realized_profit_loss"],
            row["ticker"],
        ),
        reverse=True,
    )


def calculate_paper_trading_analytics(account_id):
    """Calculate closed-trade analytics for a paper account."""

    trades = get_closed_paper_trades(account_id)

    if not trades:
        return build_empty_analytics()

    realized_results = []
    winning_results = []
    losing_results = []
    breakeven_results = []
    closed_trade_rows = []

    total_sell_value = 0.0
    total_shares_sold = 0.0

    for trade in trades:
        realized_value = safe_float(
            trade.realized_profit_loss
        )
        result = classify_trade_result(realized_value)

        realized_results.append(realized_value)
        total_sell_value += safe_float(trade.gross_value)
        total_shares_sold += safe_float(trade.quantity)

        if result == "WIN":
            winning_results.append(realized_value)
        elif result == "LOSS":
            losing_results.append(realized_value)
        else:
            breakeven_results.append(realized_value)

        closed_trade_rows.append(
            {
                "trade_id": trade.id,
                "order_id": trade.order_id,
                "executed_at": trade.executed_at,
                "ticker": trade.ticker,
                "side": trade.side,
                "quantity": round(
                    safe_float(trade.quantity),
                    6,
                ),
                "execution_price": round(
                    safe_float(trade.execution_price),
                    MONEY_PRECISION,
                ),
                "gross_value": round(
                    safe_float(trade.gross_value),
                    MONEY_PRECISION,
                ),
                "realized_profit_loss": round(
                    realized_value,
                    MONEY_PRECISION,
                ),
                "result": result,
            }
        )

    closed_trades = len(realized_results)
    winning_trades = len(winning_results)
    losing_trades = len(losing_results)
    breakeven_trades = len(breakeven_results)

    gross_profit = sum(winning_results)
    gross_loss = sum(losing_results)
    net_realized_profit_loss = sum(realized_results)

    win_rate_pct = (
        winning_trades / closed_trades * 100
        if closed_trades
        else 0.0
    )

    loss_rate_pct = (
        losing_trades / closed_trades * 100
        if closed_trades
        else 0.0
    )

    average_gain = (
        gross_profit / winning_trades
        if winning_trades
        else 0.0
    )

    average_loss = (
        gross_loss / losing_trades
        if losing_trades
        else 0.0
    )

    trade_expectancy = (
        net_realized_profit_loss / closed_trades
        if closed_trades
        else 0.0
    )

    largest_winner = (
        max(winning_results)
        if winning_results
        else 0.0
    )

    largest_loser = (
        min(losing_results)
        if losing_results
        else 0.0
    )

    return {
        "closed_trades": closed_trades,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "breakeven_trades": breakeven_trades,
        "win_rate_pct": round(
            win_rate_pct,
            PERCENT_PRECISION,
        ),
        "loss_rate_pct": round(
            loss_rate_pct,
            PERCENT_PRECISION,
        ),
        "average_gain": round(
            average_gain,
            MONEY_PRECISION,
        ),
        "average_loss": round(
            average_loss,
            MONEY_PRECISION,
        ),
        "gross_profit": round(
            gross_profit,
            MONEY_PRECISION,
        ),
        "gross_loss": round(
            gross_loss,
            MONEY_PRECISION,
        ),
        "profit_factor": calculate_profit_factor(
            gross_profit=gross_profit,
            gross_loss=gross_loss,
        ),
        "trade_expectancy": round(
            trade_expectancy,
            MONEY_PRECISION,
        ),
        "largest_winner": round(
            largest_winner,
            MONEY_PRECISION,
        ),
        "largest_loser": round(
            largest_loser,
            MONEY_PRECISION,
        ),
        "net_realized_profit_loss": round(
            net_realized_profit_loss,
            MONEY_PRECISION,
        ),
        "total_sell_value": round(
            total_sell_value,
            MONEY_PRECISION,
        ),
        "total_shares_sold": round(
            total_shares_sold,
            6,
        ),
        "by_ticker": summarize_ticker_performance(
            trades
        ),
        "closed_trade_rows": closed_trade_rows,
    }
