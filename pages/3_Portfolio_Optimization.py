from __future__ import annotations

import pandas as pd
import streamlit as st
import yfinance as yf

from portfolio_optimization.comparison import (
    build_allocation_comparison_table,
    compare_portfolio_optimizers,
)


DEFAULT_TICKERS = "AAPL, MSFT, NVDA"


def clean_ticker_list(raw_tickers: str) -> list[str]:
    """Clean comma-separated ticker input."""
    tickers = [
        ticker.strip().upper()
        for ticker in raw_tickers.split(",")
        if ticker.strip()
    ]

    unique_tickers = list(dict.fromkeys(tickers))

    return unique_tickers


@st.cache_data(show_spinner=False)
def load_multi_asset_price_data(
    tickers: tuple[str, ...],
    period: str,
) -> pd.DataFrame:
    """Load adjusted close price data for multiple tickers."""
    if len(tickers) < 2:
        raise ValueError("Enter at least two tickers.")

    price_frames = []

    for ticker in tickers:
        history = yf.Ticker(ticker).history(period=period)

        if history.empty or "Close" not in history.columns:
            continue

        close_prices = history[["Close"]].rename(columns={"Close": ticker})
        price_frames.append(close_prices)

    if not price_frames:
        raise ValueError("No price data was returned for the selected tickers.")

    price_data = pd.concat(price_frames, axis=1).sort_index()
    price_data = price_data.ffill().dropna(how="all")
    price_data = price_data.dropna(axis=1, how="all")

    if price_data.shape[1] < 2:
        raise ValueError("At least two valid tickers are required for optimization.")

    return price_data


def render_optimizer_summary(comparison: dict) -> None:
    """Render optimizer summary metrics and table."""
    st.subheader("Optimization Summary")

    summary = comparison["summary"].copy()

    metric_col1, metric_col2, metric_col3 = st.columns(3)

    metric_col1.metric(
        "Best Return Optimizer",
        comparison["best_return_optimizer"],
    )

    metric_col2.metric(
        "Lowest Volatility Optimizer",
        comparison["lowest_volatility_optimizer"],
    )

    metric_col3.metric(
        "Best Sharpe Optimizer",
        comparison["best_sharpe_optimizer"],
    )

    display_summary = summary[
        [
            "optimizer_name",
            "portfolio_return_pct",
            "portfolio_volatility_pct",
            "sharpe_ratio",
            "asset_count",
        ]
    ].copy()

    display_summary["portfolio_return_pct"] = display_summary[
        "portfolio_return_pct"
    ].round(2)
    display_summary["portfolio_volatility_pct"] = display_summary[
        "portfolio_volatility_pct"
    ].round(2)
    display_summary["sharpe_ratio"] = display_summary["sharpe_ratio"].round(2)

    st.dataframe(
        display_summary,
        use_container_width=True,
        hide_index=True,
    )

    summary_csv = display_summary.to_csv(index=False)

    st.download_button(
        label="Download Optimizer Summary CSV",
        data=summary_csv,
        file_name="portfolio_optimizer_summary.csv",
        mime="text/csv",
        key="download_optimizer_summary_csv",
    )


def render_allocation_comparison(comparison: dict) -> None:
    """Render optimizer allocation comparison."""
    st.subheader("Allocation Comparison")

    allocation_table = build_allocation_comparison_table(comparison)

    display_allocations = allocation_table.copy()

    optimizer_columns = [
        column
        for column in display_allocations.columns
        if column != "ticker"
    ]

    for column in optimizer_columns:
        display_allocations[column] = display_allocations[column].round(2)

    st.dataframe(
        display_allocations,
        use_container_width=True,
        hide_index=True,
    )

    chart_data = display_allocations.set_index("ticker")
    st.bar_chart(chart_data)

    allocation_csv = display_allocations.to_csv(index=False)

    st.download_button(
        label="Download Allocation Comparison CSV",
        data=allocation_csv,
        file_name="portfolio_allocation_comparison.csv",
        mime="text/csv",
        key="download_allocation_comparison_csv",
    )


def render_optimizer_details(comparison: dict) -> None:
    """Render detailed optimizer allocation tables."""
    st.subheader("Optimizer Details")

    for result in comparison["results"]:
        with st.expander(result["optimizer_name"], expanded=False):
            allocations = result["allocations"].copy()
            allocations["weight"] = allocations["weight"].round(4)
            allocations["weight_pct"] = allocations["weight_pct"].round(2)

            st.dataframe(
                allocations,
                use_container_width=True,
                hide_index=True,
            )

            detail_col1, detail_col2, detail_col3 = st.columns(3)

            detail_col1.metric(
                "Portfolio Return",
                f"{result['portfolio_return'] * 100:.2f}%",
            )

            detail_col2.metric(
                "Portfolio Volatility",
                f"{result['portfolio_volatility'] * 100:.2f}%",
            )

            detail_col3.metric(
                "Sharpe Ratio",
                f"{result['sharpe_ratio']:.2f}",
            )


def render_methodology() -> None:
    """Render methodology notes."""
    with st.expander("Portfolio Optimization Methodology", expanded=False):
        st.markdown(
            """
### Portfolio Optimization Logic

This page compares three allocation methods:

- **Equal Weight:** Splits capital evenly across selected tickers.
- **Minimum Volatility:** Searches random long-only portfolios and selects the allocation with the lowest volatility.
- **Maximum Sharpe:** Searches random long-only portfolios and selects the allocation with the highest Sharpe-style ratio.

### Current Constraints

- Long-only allocations
- No short selling
- Weights must sum to 100%
- Uses historical close prices from yfinance
- Uses annualized return and covariance estimates
- Uses random simulation search, not a formal convex optimizer

### Interpretation

The output is for project research and education. It is not financial advice.

Use this page to compare how different optimization goals change the portfolio allocation.
"""
        )


def render_portfolio_optimization_page() -> None:
    """Render portfolio optimization Streamlit page."""
    st.set_page_config(
        page_title="Portfolio Optimization",
        layout="wide",
    )

    st.title("Portfolio Optimization")
    st.caption("Sprint 70: Portfolio Optimization Foundation")

    with st.sidebar:
        st.header("Optimization Inputs")

        raw_tickers = st.text_input(
            "Tickers",
            value=DEFAULT_TICKERS,
            help="Enter at least two comma-separated tickers.",
        )

        period = st.selectbox(
            "Price History Period",
            options=["3mo", "6mo", "1y", "2y", "5y"],
            index=2,
        )

        simulation_count = st.slider(
            "Simulation Count",
            min_value=500,
            max_value=10000,
            value=5000,
            step=500,
        )

        risk_free_rate_pct = st.number_input(
            "Risk-Free Rate %",
            min_value=0.0,
            max_value=20.0,
            value=0.0,
            step=0.25,
        )

        run_optimization = st.button("Run Portfolio Optimization")

    tickers = clean_ticker_list(raw_tickers)

    st.markdown(
        """
Use this page to compare portfolio allocation methods across multiple assets.
"""
    )

    st.write("Selected tickers:", ", ".join(tickers) if tickers else "None")

    if not run_optimization:
        render_methodology()
        st.info("Enter tickers in the sidebar and click Run Portfolio Optimization.")
        return

    if len(tickers) < 2:
        st.error("Enter at least two tickers.")
        return

    try:
        with st.spinner("Loading price data and running optimizers..."):
            price_data = load_multi_asset_price_data(
                tickers=tuple(tickers),
                period=period,
            )

            comparison = compare_portfolio_optimizers(
                price_data=price_data,
                simulation_count=simulation_count,
                risk_free_rate=risk_free_rate_pct / 100,
                random_seed=42,
            )
    except Exception as error:
        st.error(f"Portfolio optimization failed: {error}")
        return

    st.subheader("Price Data Preview")
    st.dataframe(
        price_data.tail(),
        use_container_width=True,
    )

    st.line_chart(price_data)

    render_optimizer_summary(comparison)
    render_allocation_comparison(comparison)
    render_optimizer_details(comparison)
    render_methodology()


render_portfolio_optimization_page()
