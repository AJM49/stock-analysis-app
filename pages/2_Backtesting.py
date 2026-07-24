from __future__ import annotations

import pandas as pd
import streamlit as st
import yfinance as yf

from backtesting.engine import BacktestEngine
from strategies.moving_average import MovingAverageCrossoverStrategy


st.set_page_config(
    page_title="Backtesting",
    page_icon="📈",
    layout="wide",
)


def normalize_yfinance_history(history: pd.DataFrame) -> pd.DataFrame:
    """Normalize yfinance history into the standard backtesting schema."""
    if history.empty:
        return pd.DataFrame(
            columns=["Date", "Open", "High", "Low", "Close", "Volume"]
        )

    normalized = history.reset_index()

    if "Date" not in normalized.columns:
        if "Datetime" in normalized.columns:
            normalized = normalized.rename(columns={"Datetime": "Date"})

    required_columns = ["Date", "Open", "High", "Low", "Close", "Volume"]

    missing_columns = [
        column
        for column in required_columns
        if column not in normalized.columns
    ]

    if missing_columns:
        raise ValueError(f"Missing required market data columns: {missing_columns}")

    normalized = normalized[required_columns].copy()
    normalized["Date"] = pd.to_datetime(normalized["Date"])

    for column in ["Open", "High", "Low", "Close", "Volume"]:
        normalized[column] = pd.to_numeric(normalized[column], errors="coerce")

    normalized = normalized.dropna(subset=["Close"])
    normalized = normalized[normalized["Close"] > 0]

    return normalized


@st.cache_data(show_spinner=False)
def load_backtest_price_data(ticker: str, period: str) -> pd.DataFrame:
    """Load historical market data for backtesting."""
    stock = yf.Ticker(ticker)
    history = stock.history(period=period)

    return normalize_yfinance_history(history)


def render_metric_row(result: dict) -> None:
    """Render top-level backtest metrics."""
    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)

    metric_col1.metric(
        "Starting Cash",
        f"${result['starting_cash']:,.2f}",
    )

    metric_col2.metric(
        "Ending Value",
        f"${result['ending_value']:,.2f}",
    )

    metric_col3.metric(
        "Total Return",
        f"{result['total_return_pct']:.2f}%",
    )

    metric_col4.metric(
        "Max Drawdown",
        f"{result['max_drawdown_pct']:.2f}%",
    )

    trade_col1, trade_col2, trade_col3, trade_col4 = st.columns(4)

    trade_col1.metric(
        "Number of Trades",
        result["number_of_trades"],
    )

    trade_col2.metric(
        "Completed Trades",
        result["completed_trades"],
    )

    trade_col3.metric(
        "Win Rate",
        f"{result['win_rate_pct']:.2f}%",
    )

    trade_col4.metric(
        "Exposure",
        f"{result['exposure_pct']:.2f}%",
    )

    pnl_col1, pnl_col2, pnl_col3, pnl_col4 = st.columns(4)

    pnl_col1.metric(
        "Average Gain",
        f"${result['average_gain']:,.2f}",
    )

    pnl_col2.metric(
        "Average Loss",
        f"${result['average_loss']:,.2f}",
    )

    pnl_col3.metric(
        "Best Trade",
        f"${result['best_trade']:,.2f}",
    )

    pnl_col4.metric(
        "Worst Trade",
        f"${result['worst_trade']:,.2f}",
    )

    benchmark_col1, benchmark_col2, benchmark_col3, benchmark_col4 = st.columns(4)

    benchmark_col1.metric(
        "Benchmark Ending Value",
        f"${result['benchmark_ending_value']:,.2f}",
    )

    benchmark_col2.metric(
        "Benchmark Return",
        f"{result['benchmark_total_return_pct']:.2f}%",
    )

    benchmark_col3.metric(
        "Benchmark Drawdown",
        f"{result['benchmark_max_drawdown_pct']:.2f}%",
    )

    benchmark_col4.metric(
        "Strategy Excess Return",
        f"{result['strategy_excess_return_pct']:.2f}%",
    )

    st.caption(
        f"Strategy: {result['strategy_name']} | "
        f"Benchmark: {result['benchmark_name']}"
    )


def render_backtesting_page() -> None:
    """Render the Streamlit backtesting page."""
    st.title("Backtesting Lab")
    st.caption("Sprint 68 — Backtesting Engine Foundation")

    st.markdown(
        """
Use this page to test a moving-average crossover strategy against historical market data.

The Streamlit page displays the results. The calculation engine lives in the `backtesting/`
and `strategies/` modules.
"""
    )

    with st.sidebar:
        st.header("Backtest Settings")

        ticker = st.text_input(
            "Ticker",
            value="AAPL",
            key="backtest_ticker_input",
        ).strip().upper()

        period = st.selectbox(
            "Historical Period",
            options=["6mo", "1y", "2y", "5y"],
            index=1,
            key="backtest_period_select",
        )

        starting_cash = st.number_input(
            "Starting Cash",
            min_value=100.0,
            max_value=1_000_000.0,
            value=10_000.0,
            step=500.0,
            key="backtest_starting_cash_input",
        )

        short_window = st.number_input(
            "Short Moving Average Window",
            min_value=2,
            max_value=100,
            value=20,
            step=1,
            key="backtest_short_window_input",
        )

        long_window = st.number_input(
            "Long Moving Average Window",
            min_value=5,
            max_value=300,
            value=50,
            step=1,
            key="backtest_long_window_input",
        )

        trade_size_pct = st.slider(
            "Trade Size",
            min_value=0.10,
            max_value=1.00,
            value=1.00,
            step=0.05,
            format="%.2f",
            key="backtest_trade_size_slider",
        )

        run_backtest = st.button(
            "Run Backtest",
            type="primary",
            key="run_backtest_button",
        )

    if not ticker:
        st.warning("Enter a ticker symbol to run a backtest.")
        return

    if short_window >= long_window:
        st.error("Short moving average window must be less than long moving average window.")
        return

    if not run_backtest:
        st.info("Set your parameters in the sidebar, then click Run Backtest.")
        return

    try:
        with st.spinner("Loading market data and running backtest..."):
            price_data = load_backtest_price_data(ticker=ticker, period=period)

            if price_data.empty:
                st.error("No market data returned for this ticker and period.")
                return

            strategy = MovingAverageCrossoverStrategy(
                short_window=int(short_window),
                long_window=int(long_window),
            )

            engine = BacktestEngine(
                strategy=strategy,
                ticker=ticker,
                starting_cash=float(starting_cash),
                trade_size_pct=float(trade_size_pct),
            )

            result = engine.run(price_data)

    except Exception as error:
        st.error(f"Backtest failed: {error}")
        return

    st.subheader(f"{ticker} Backtest Results")
    render_metric_row(result)

    equity_curve = result["equity_curve"]
    benchmark_equity_curve = result["benchmark_equity_curve"]
    trades = result["trades"]
    completed_trade_details = result["completed_trade_details"]
    signals = result["signals"]

    st.subheader("Strategy vs Benchmark Equity Curve")

    if not equity_curve.empty and not benchmark_equity_curve.empty:
        strategy_chart = equity_curve[["Date", "total_value"]].copy()
        strategy_chart = strategy_chart.rename(
            columns={"total_value": "Strategy Value"}
        )

        benchmark_chart = benchmark_equity_curve[
            ["Date", "benchmark_total_value"]
        ].copy()
        benchmark_chart = benchmark_chart.rename(
            columns={"benchmark_total_value": "Buy-and-Hold Value"}
        )

        chart_data = strategy_chart.merge(
            benchmark_chart,
            on="Date",
            how="inner",
        ).set_index("Date")

        st.line_chart(chart_data)
    elif not equity_curve.empty:
        chart_data = equity_curve.set_index("Date")[["total_value"]]
        st.line_chart(chart_data)
    else:
        st.info("No equity curve data available.")

    st.subheader("Strategy Signals")

    signal_columns = [
        column
        for column in ["Date", "Close", "short_ma", "long_ma", "signal"]
        if column in signals.columns
    ]

    st.dataframe(
        signals[signal_columns].tail(100),
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Trade Log")

    if trades.empty:
        st.info("No trades were generated for this period and strategy configuration.")
    else:
        st.dataframe(
            trades,
            use_container_width=True,
            hide_index=True,
        )

    st.subheader("Completed Trade PnL")

    if completed_trade_details.empty:
        st.info("No completed buy/sell trade pairs available yet.")
    else:
        st.dataframe(
            completed_trade_details,
            use_container_width=True,
            hide_index=True,
        )

    with st.expander("Backtesting Methodology", expanded=False):
        st.markdown(
            """
### Strategy Logic

The current strategy is a moving-average crossover.

- Buy signal: short moving average crosses above long moving average.
- Sell signal: short moving average crosses below long moving average.

### Engine Logic

The backtesting engine:

1. Validates standardized price data.
2. Generates strategy signals.
3. Simulates long-only buy/sell trades.
4. Tracks cash, shares, position value, and total portfolio value.
5. Builds an equity curve.
6. Returns basic metrics.

### Benchmark Logic

The benchmark uses a simple buy-and-hold approach:

1. Invest all starting cash at the first available close price.
2. Hold the same number of shares through the full historical period.
3. Compare ending value, total return, and drawdown against the strategy.

### Current Limitations

This first version does not yet include:

- Transaction costs
- Slippage
- Taxes
- Dividends
- Short selling
- Stop losses
- Multi-asset portfolios
- Broker execution

Those should be added in later Sprint 68 features.
"""
        )


render_backtesting_page()
