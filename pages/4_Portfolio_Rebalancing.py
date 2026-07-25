from __future__ import annotations

import pandas as pd
import streamlit as st

from portfolio_rebalancing.rebalancing_math import (
    build_allocation_drift_summary,
    build_dollar_trade_summary,
    build_rebalance_summary,
    build_share_trade_summary,
    calculate_dollar_trade_recommendations,
    calculate_rebalance_plan,
    calculate_share_trade_recommendations,
    calculate_target_vs_current_allocations,
)


DEFAULT_POSITIONS = pd.DataFrame(
    {
        "ticker": ["AAPL", "MSFT", "NVDA"],
        "shares": [10.0, 8.0, 2.0],
        "current_price": [200.0, 400.0, 1000.0],
        "target_weight_pct": [40.0, 35.0, 25.0],
    }
)


def prepare_positions(input_df: pd.DataFrame) -> pd.DataFrame:
    """Prepare editable Streamlit input for rebalancing engine."""
    required_columns = {
        "ticker",
        "shares",
        "current_price",
        "target_weight_pct",
    }

    missing_columns = required_columns - set(input_df.columns)

    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Input missing required columns: {missing}")

    positions = input_df.copy()

    positions["ticker"] = positions["ticker"].astype(str).str.strip().str.upper()
    positions["shares"] = pd.to_numeric(positions["shares"], errors="coerce")
    positions["current_price"] = pd.to_numeric(
        positions["current_price"],
        errors="coerce",
    )
    positions["target_weight_pct"] = pd.to_numeric(
        positions["target_weight_pct"],
        errors="coerce",
    )

    if positions[["shares", "current_price", "target_weight_pct"]].isna().any().any():
        raise ValueError("Shares, current price, and target weights must be numeric.")

    positions["target_weight"] = positions["target_weight_pct"] / 100

    return positions[
        [
            "ticker",
            "shares",
            "current_price",
            "target_weight",
        ]
    ]


def render_summary_metrics(
    rebalance_summary: dict,
    drift_summary: dict,
    dollar_summary: dict,
    share_summary: dict,
) -> None:
    """Render high-level summary metrics."""
    st.subheader("Rebalancing Summary")

    summary_col1, summary_col2, summary_col3, summary_col4 = st.columns(4)

    summary_col1.metric(
        "Portfolio Value",
        f"${rebalance_summary['total_portfolio_value']:,.2f}",
    )

    summary_col2.metric(
        "Needs Rebalance",
        drift_summary["positions_needing_rebalance"],
    )

    summary_col3.metric(
        "Total Buy Amount",
        f"${dollar_summary['total_buy_amount']:,.2f}",
    )

    summary_col4.metric(
        "Total Sell Amount",
        f"${dollar_summary['total_sell_amount']:,.2f}",
    )

    trade_col1, trade_col2, trade_col3, trade_col4 = st.columns(4)

    trade_col1.metric(
        "Buy Trades",
        dollar_summary["buy_recommendations"],
    )

    trade_col2.metric(
        "Sell Trades",
        dollar_summary["sell_recommendations"],
    )

    trade_col3.metric(
        "Gross Trade Amount",
        f"${dollar_summary['gross_trade_amount']:,.2f}",
    )

    trade_col4.metric(
        "Shares Traded",
        f"{share_summary['total_absolute_shares_traded']:,.4f}",
    )


def render_target_vs_current(positions: pd.DataFrame, threshold_pct: float) -> None:
    """Render target-vs-current allocation table."""
    st.subheader("Target vs Current Allocation")

    allocation_view = calculate_target_vs_current_allocations(
        positions=positions,
        rebalance_threshold_pct=threshold_pct,
    )

    display_df = allocation_view.copy()
    numeric_columns = display_df.select_dtypes(include="number").columns
    display_df[numeric_columns] = display_df[numeric_columns].round(4)

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
    )

    chart_df = display_df[
        [
            "ticker",
            "current_weight_pct",
            "target_weight_pct",
        ]
    ].set_index("ticker")

    st.bar_chart(chart_df)

    csv_data = display_df.to_csv(index=False)

    st.download_button(
        label="Download Target vs Current CSV",
        data=csv_data,
        file_name="target_vs_current_allocation.csv",
        mime="text/csv",
        key="download_target_vs_current_csv",
    )


def render_dollar_trade_recommendations(
    positions: pd.DataFrame,
    trade_tolerance: float,
) -> None:
    """Render dollar trade recommendations."""
    st.subheader("Dollar Trade Recommendations")

    recommendations = calculate_dollar_trade_recommendations(
        positions=positions,
        trade_tolerance=trade_tolerance,
    )

    display_df = recommendations.copy()
    numeric_columns = display_df.select_dtypes(include="number").columns
    display_df[numeric_columns] = display_df[numeric_columns].round(2)

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
    )

    dollar_csv = display_df.to_csv(index=False)

    st.download_button(
        label="Download Dollar Trade Recommendations CSV",
        data=dollar_csv,
        file_name="dollar_trade_recommendations.csv",
        mime="text/csv",
        key="download_dollar_trade_recommendations_csv",
    )


def render_share_trade_recommendations(
    positions: pd.DataFrame,
    trade_tolerance: float,
    allow_fractional_shares: bool,
) -> None:
    """Render share trade recommendations."""
    st.subheader("Share Trade Recommendations")

    recommendations = calculate_share_trade_recommendations(
        positions=positions,
        trade_tolerance=trade_tolerance,
        allow_fractional_shares=allow_fractional_shares,
    )

    display_df = recommendations.copy()
    numeric_columns = display_df.select_dtypes(include="number").columns
    display_df[numeric_columns] = display_df[numeric_columns].round(4)

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
    )

    share_csv = display_df.to_csv(index=False)

    st.download_button(
        label="Download Share Trade Recommendations CSV",
        data=share_csv,
        file_name="share_trade_recommendations.csv",
        mime="text/csv",
        key="download_share_trade_recommendations_csv",
    )


def render_rebalance_plan(positions: pd.DataFrame) -> None:
    """Render full rebalance plan."""
    st.subheader("Full Rebalance Plan")

    plan = calculate_rebalance_plan(positions)

    display_df = plan.copy()
    numeric_columns = display_df.select_dtypes(include="number").columns
    display_df[numeric_columns] = display_df[numeric_columns].round(4)

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
    )

    plan_csv = display_df.to_csv(index=False)

    st.download_button(
        label="Download Full Rebalance Plan CSV",
        data=plan_csv,
        file_name="full_rebalance_plan.csv",
        mime="text/csv",
        key="download_full_rebalance_plan_csv",
    )


def render_rebalancing_methodology() -> None:
    """Render methodology notes."""
    with st.expander("Portfolio Rebalancing Methodology", expanded=False):
        st.markdown(
            """
### Rebalancing Logic

This page compares your current portfolio allocation against your target allocation.

The engine calculates:

- Current market value
- Current allocation percentage
- Target allocation percentage
- Allocation drift
- Dollar trade recommendation
- Share trade recommendation
- Post-trade allocation estimate

### Dollar Trade Logic

If a position is below target, the engine recommends a **Buy** amount.

If a position is above target, the engine recommends a **Sell** amount.

If the trade amount is below the tolerance threshold, the engine marks it as **Hold**.

### Share Trade Logic

Dollar trades are converted into share quantities using the current price.

If fractional shares are enabled, the engine can recommend partial shares.

If fractional shares are disabled, the engine rounds down to whole shares.

### Project Use

This is a portfolio research and engineering tool. It is not financial advice.
"""
        )


def render_portfolio_rebalancing_page() -> None:
    """Render Portfolio Rebalancing page."""
    st.set_page_config(
        page_title="Portfolio Rebalancing",
        layout="wide",
    )

    st.title("Portfolio Rebalancing")
    st.caption("Sprint 71: Portfolio Rebalancing and Position Sizing Foundation")

    with st.sidebar:
        st.header("Rebalancing Inputs")

        rebalance_threshold_pct = st.number_input(
            "Rebalance Threshold %",
            min_value=0.5,
            max_value=50.0,
            value=5.0,
            step=0.5,
        )

        trade_tolerance = st.number_input(
            "Trade Tolerance $",
            min_value=0.0,
            max_value=10000.0,
            value=1.0,
            step=1.0,
        )

        allow_fractional_shares = st.checkbox(
            "Allow Fractional Shares",
            value=True,
        )

        run_rebalance = st.button("Run Rebalance Analysis")

    st.markdown(
        """
Edit the table below with your current holdings, current prices, and target allocation percentages.
"""
    )

    editable_positions = st.data_editor(
        DEFAULT_POSITIONS,
        num_rows="dynamic",
        use_container_width=True,
        key="portfolio_rebalancing_editor",
    )

    if not run_rebalance:
        render_rebalancing_methodology()
        st.info("Edit positions and click Run Rebalance Analysis.")
        return

    try:
        positions = prepare_positions(editable_positions)

        rebalance_summary = build_rebalance_summary(positions)
        drift_summary = build_allocation_drift_summary(
            positions=positions,
            rebalance_threshold_pct=rebalance_threshold_pct,
        )
        dollar_summary = build_dollar_trade_summary(
            positions=positions,
            trade_tolerance=trade_tolerance,
        )
        share_summary = build_share_trade_summary(
            positions=positions,
            trade_tolerance=trade_tolerance,
            allow_fractional_shares=allow_fractional_shares,
        )

    except Exception as error:
        st.error(f"Rebalance analysis failed: {error}")
        return

    render_summary_metrics(
        rebalance_summary=rebalance_summary,
        drift_summary=drift_summary,
        dollar_summary=dollar_summary,
        share_summary=share_summary,
    )

    render_target_vs_current(
        positions=positions,
        threshold_pct=rebalance_threshold_pct,
    )

    render_dollar_trade_recommendations(
        positions=positions,
        trade_tolerance=trade_tolerance,
    )

    render_share_trade_recommendations(
        positions=positions,
        trade_tolerance=trade_tolerance,
        allow_fractional_shares=allow_fractional_shares,
    )

    render_rebalance_plan(positions)
    render_rebalancing_methodology()


render_portfolio_rebalancing_page()
