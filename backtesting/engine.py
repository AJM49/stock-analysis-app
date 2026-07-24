from __future__ import annotations

from dataclasses import asdict
from typing import Any

import pandas as pd

from backtesting.metrics import calculate_max_drawdown, calculate_total_return
from backtesting.trade import Trade
from strategies.base_strategy import BaseStrategy


class BacktestEngine:
    """Basic long-only backtesting engine."""

    def __init__(
        self,
        strategy: BaseStrategy,
        ticker: str,
        starting_cash: float = 10_000.0,
        trade_size_pct: float = 1.0,
    ):
        if starting_cash <= 0:
            raise ValueError("starting_cash must be greater than 0")

        if not 0 < trade_size_pct <= 1:
            raise ValueError("trade_size_pct must be greater than 0 and less than or equal to 1")

        self.strategy = strategy
        self.ticker = ticker.upper()
        self.starting_cash = float(starting_cash)
        self.trade_size_pct = float(trade_size_pct)

    def run(self, price_data: pd.DataFrame) -> dict[str, Any]:
        """Run a backtest against standardized historical price data."""
        self._validate_price_data(price_data)

        signals = self.strategy.generate_signals(price_data)

        cash = self.starting_cash
        shares = 0.0
        trades: list[Trade] = []
        equity_rows: list[dict[str, Any]] = []

        for _, row in signals.iterrows():
            date = row["Date"]
            close_price = float(row["Close"])
            signal = int(row["signal"])

            if signal == 1 and cash > 0:
                cash_to_use = cash * self.trade_size_pct
                shares_to_buy = cash_to_use / close_price

                shares += shares_to_buy
                cash -= cash_to_use

                trades.append(
                    Trade(
                        date=date,
                        ticker=self.ticker,
                        action="BUY",
                        shares=shares_to_buy,
                        price=close_price,
                        cash_after_trade=cash,
                        position_after_trade=shares,
                    )
                )

            elif signal == -1 and shares > 0:
                cash_from_sale = shares * close_price
                shares_sold = shares

                cash += cash_from_sale
                shares = 0.0

                trades.append(
                    Trade(
                        date=date,
                        ticker=self.ticker,
                        action="SELL",
                        shares=shares_sold,
                        price=close_price,
                        cash_after_trade=cash,
                        position_after_trade=shares,
                    )
                )

            position_value = shares * close_price
            total_value = cash + position_value

            equity_rows.append(
                {
                    "Date": date,
                    "Close": close_price,
                    "cash": cash,
                    "shares": shares,
                    "position_value": position_value,
                    "total_value": total_value,
                    "signal": signal,
                }
            )

        equity_curve = pd.DataFrame(equity_rows)
        trades_df = pd.DataFrame([asdict(trade) for trade in trades])

        ending_value = (
            float(equity_curve["total_value"].iloc[-1])
            if not equity_curve.empty
            else self.starting_cash
        )

        total_return = calculate_total_return(
            starting_value=self.starting_cash,
            ending_value=ending_value,
        )

        max_drawdown = calculate_max_drawdown(equity_curve["total_value"])

        result = {
            "ticker": self.ticker,
            "strategy_name": self.strategy.name,
            "starting_cash": self.starting_cash,
            "ending_value": ending_value,
            "total_return_pct": total_return,
            "max_drawdown_pct": max_drawdown,
            "number_of_trades": len(trades_df),
            "equity_curve": equity_curve,
            "trades": trades_df,
            "signals": signals,
        }

        return result

    @staticmethod
    def _validate_price_data(price_data: pd.DataFrame) -> None:
        """Validate standardized price input."""
        required_columns = {"Date", "Open", "High", "Low", "Close", "Volume"}
        missing_columns = required_columns - set(price_data.columns)

        if missing_columns:
            raise ValueError(f"Missing required columns: {sorted(missing_columns)}")

        if price_data.empty:
            raise ValueError("price_data cannot be empty")

        if price_data["Close"].isna().any():
            raise ValueError("price_data Close column cannot contain missing values")

        if (price_data["Close"] <= 0).any():
            raise ValueError("price_data Close column must contain positive prices")
