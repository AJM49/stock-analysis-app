from __future__ import annotations

import pandas as pd
import streamlit as st

from portfolio_rebalancing.position_sizing import (
    build_position_sizing_summary,
    build_risk_budget_position_sizing_summary,
    calculate_position_sizing_table,
    calculate_risk_budget_position_sizing_table,
)

from portfolio_rebalancing.rebalancing_math import (
    build_allocation_drift_summary,
    build_dollar_trade_summary,
    build_rebalance_alert_summary,
    build_rebalance_summary,
    build_share_trade_summary,
    calculate_dollar_trade_recommendations,
    calculate_rebalance_alerts,
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


DEFAULT_SIZING_CANDIDATES = pd.DataFrame(
    {
        "ticker": ["AAPL", "MSFT", "NVDA"],
        "current_price": [200.0, 400.0, 1000.0],
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


def prepare_sizing_candidates(input_df: pd.DataFrame) -> pd.DataFrame:
    """Prepare editable candidate table for position sizing."""
    required_columns = {
        "ticker",
        "current_price",
    }

    missing_columns = required_columns - set(input_df.columns)

    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Candidate input missing required columns: {missing}")

    candidates = input_df.copy()
    candidates["ticker"] = candidates["ticker"].astype(str).str.strip().str.upper()
    candidates["current_price"] = pd.to_numeric(
        candidates["current_price"],
        errors="coerce",
    )

    if candidates["current_price"].isna().any():
        raise ValueError("Candidate current prices must be numeric.")

    return candidates[["ticker", "current_price"]]


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


def render_rebalance_alerts(
    positions: pd.DataFrame,
    high_drift_threshold_pct: float,
    moderate_drift_threshold_pct: float,
    trade_tolerance: float,
) -> None:
    """Render drift detection and rebalance alerts."""
    st.subheader("Drift Detection and Rebalance Alerts")

    alerts = calculate_rebalance_alerts(
        positions=positions,
        high_drift_threshold_pct=high_drift_threshold_pct,
        moderate_drift_threshold_pct=moderate_drift_threshold_pct,
        trade_tolerance=trade_tolerance,
    )

    alert_summary = build_rebalance_alert_summary(
        positions=positions,
        high_drift_threshold_pct=high_drift_threshold_pct,
        moderate_drift_threshold_pct=moderate_drift_threshold_pct,
        trade_tolerance=trade_tolerance,
    )

    if alert_summary["high_drift_count"] > 0:
        st.error(
            f"{alert_summary['high_drift_count']} high-drift position(s) detected."
        )
    elif alert_summary["moderate_drift_count"] > 0:
        st.warning(
            f"{alert_summary['moderate_drift_count']} moderate-drift position(s) detected."
        )
    else:
        st.success("All positions are within the selected drift range.")

    alert_col1, alert_col2, alert_col3, alert_col4 = st.columns(4)

    alert_col1.metric(
        "High Drift",
        alert_summary["high_drift_count"],
    )

    alert_col2.metric(
        "Moderate Drift",
        alert_summary["moderate_drift_count"],
    )

    alert_col3.metric(
        "Within Range",
        alert_summary["within_range_count"],
    )

    alert_col4.metric(
        "Max Drift",
        f"{alert_summary['max_absolute_drift_pct']:.2f}%",
    )

    display_df = alerts.copy()
    numeric_columns = display_df.select_dtypes(include="number").columns
    display_df[numeric_columns] = display_df[numeric_columns].round(2)

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
    )

    alerts_csv = display_df.to_csv(index=False)

    st.download_button(
        label="Download Rebalance Alerts CSV",
        data=alerts_csv,
        file_name="rebalance_alerts.csv",
        mime="text/csv",
        key="download_rebalance_alerts_csv",
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


def render_position_sizing_section(
    candidates: pd.DataFrame,
    portfolio_value: float,
    risk_per_trade_pct: float,
    stop_loss_pct: float,
    max_position_weight_pct: float,
    allow_fractional_shares: bool,
) -> None:
    """Render standard position sizing table and summary."""
    st.subheader("Position Sizing Rules")

    try:
        sizing_table = calculate_position_sizing_table(
            candidates=candidates,
            portfolio_value=portfolio_value,
            risk_per_trade_pct=risk_per_trade_pct,
            stop_loss_pct=stop_loss_pct,
            max_position_weight_pct=max_position_weight_pct,
            allow_fractional_shares=allow_fractional_shares,
        )

        sizing_summary = build_position_sizing_summary(sizing_table)
    except Exception as error:
        st.error(f"Position sizing failed: {error}")
        return

    sizing_col1, sizing_col2, sizing_col3, sizing_col4 = st.columns(4)

    sizing_col1.metric(
        "Candidates",
        sizing_summary["candidate_count"],
    )

    sizing_col2.metric(
        "Total Position Value",
        f"${sizing_summary['total_position_value']:,.2f}",
    )

    sizing_col3.metric(
        "Estimated Risk",
        f"${sizing_summary['total_estimated_dollar_risk']:,.2f}",
    )

    sizing_col4.metric(
        "Capped Positions",
        sizing_summary["capped_position_count"],
    )

    display_df = sizing_table.copy()
    numeric_columns = display_df.select_dtypes(include="number").columns
    display_df[numeric_columns] = display_df[numeric_columns].round(4)

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
    )

    sizing_csv = display_df.to_csv(index=False)

    st.download_button(
        label="Download Position Sizing CSV",
        data=sizing_csv,
        file_name="position_sizing_rules.csv",
        mime="text/csv",
        key="download_position_sizing_rules_csv",
    )


def render_risk_budget_position_sizing_section(
    candidates: pd.DataFrame,
    portfolio_value: float,
    total_risk_budget_pct: float,
    stop_loss_pct: float,
    max_position_weight_pct: float,
    allow_fractional_shares: bool,
) -> None:
    """Render shared risk-budget position sizing table and summary."""
    st.subheader("Risk-Budget Position Sizing")

    try:
        risk_budget_table = calculate_risk_budget_position_sizing_table(
            candidates=candidates,
            portfolio_value=portfolio_value,
            total_risk_budget_pct=total_risk_budget_pct,
            stop_loss_pct=stop_loss_pct,
            max_position_weight_pct=max_position_weight_pct,
            allow_fractional_shares=allow_fractional_shares,
        )

        risk_budget_summary = build_risk_budget_position_sizing_summary(
            risk_budget_table
        )
    except Exception as error:
        st.error(f"Risk-budget position sizing failed: {error}")
        return

    budget_col1, budget_col2, budget_col3, budget_col4 = st.columns(4)

    budget_col1.metric(
        "Total Risk Budget",
        f"{risk_budget_summary['total_allocated_risk_budget_pct']:.2f}%",
    )

    budget_col2.metric(
        "Risk Budget $",
        f"${risk_budget_summary['total_allocated_risk_budget_amount']:,.2f}",
    )

    budget_col3.metric(
        "Estimated Risk $",
        f"${risk_budget_summary['total_estimated_dollar_risk']:,.2f}",
    )

    budget_col4.metric(
        "Position Value",
        f"${risk_budget_summary['total_position_value']:,.2f}",
    )

    display_df = risk_budget_table.copy()
    numeric_columns = display_df.select_dtypes(include="number").columns
    display_df[numeric_columns] = display_df[numeric_columns].round(4)

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
    )

    risk_budget_csv = display_df.to_csv(index=False)

    st.download_button(
        label="Download Risk-Budget Position Sizing CSV",
        data=risk_budget_csv,
        file_name="risk_budget_position_sizing.csv",
        mime="text/csv",
        key="download_risk_budget_position_sizing_csv",
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


def build_rebalancing_export_report(
    positions: pd.DataFrame,
    candidates: pd.DataFrame,
    rebalance_threshold_pct: float,
    moderate_drift_threshold_pct: float,
    high_drift_threshold_pct: float,
    trade_tolerance: float,
    allow_fractional_shares: bool,
    portfolio_value: float,
    risk_per_trade_pct: float,
    total_risk_budget_pct: float,
    stop_loss_pct: float,
    max_position_weight_pct: float,
) -> str:
    """Build a downloadable plain-text rebalancing report."""
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

    alert_summary = build_rebalance_alert_summary(
        positions=positions,
        high_drift_threshold_pct=high_drift_threshold_pct,
        moderate_drift_threshold_pct=moderate_drift_threshold_pct,
        trade_tolerance=trade_tolerance,
    )

    target_vs_current = calculate_target_vs_current_allocations(
        positions=positions,
        rebalance_threshold_pct=rebalance_threshold_pct,
    )

    alerts = calculate_rebalance_alerts(
        positions=positions,
        high_drift_threshold_pct=high_drift_threshold_pct,
        moderate_drift_threshold_pct=moderate_drift_threshold_pct,
        trade_tolerance=trade_tolerance,
    )

    dollar_recommendations = calculate_dollar_trade_recommendations(
        positions=positions,
        trade_tolerance=trade_tolerance,
    )

    share_recommendations = calculate_share_trade_recommendations(
        positions=positions,
        trade_tolerance=trade_tolerance,
        allow_fractional_shares=allow_fractional_shares,
    )

    rebalance_plan = calculate_rebalance_plan(positions)

    position_sizing_table = calculate_position_sizing_table(
        candidates=candidates,
        portfolio_value=portfolio_value,
        risk_per_trade_pct=risk_per_trade_pct,
        stop_loss_pct=stop_loss_pct,
        max_position_weight_pct=max_position_weight_pct,
        allow_fractional_shares=allow_fractional_shares,
    )

    position_sizing_summary = build_position_sizing_summary(position_sizing_table)

    risk_budget_table = calculate_risk_budget_position_sizing_table(
        candidates=candidates,
        portfolio_value=portfolio_value,
        total_risk_budget_pct=total_risk_budget_pct,
        stop_loss_pct=stop_loss_pct,
        max_position_weight_pct=max_position_weight_pct,
        allow_fractional_shares=allow_fractional_shares,
    )

    risk_budget_summary = build_risk_budget_position_sizing_summary(
        risk_budget_table
    )

    report_sections = [
        "Portfolio Rebalancing Report",
        "=" * 30,
        "",
        "Sprint 71 — Portfolio Rebalancing and Position Sizing Foundation",
        "",
        "Executive Summary",
        "-" * 17,
        f"Portfolio value: ${rebalance_summary['total_portfolio_value']:,.2f}",
        f"Positions reviewed: {rebalance_summary['position_count']}",
        f"Positions needing rebalance: {drift_summary['positions_needing_rebalance']}",
        f"High drift positions: {alert_summary['high_drift_count']}",
        f"Moderate drift positions: {alert_summary['moderate_drift_count']}",
        f"Total buy amount: ${dollar_summary['total_buy_amount']:,.2f}",
        f"Total sell amount: ${dollar_summary['total_sell_amount']:,.2f}",
        f"Gross trade amount: ${dollar_summary['gross_trade_amount']:,.2f}",
        f"Total absolute shares traded: {share_summary['total_absolute_shares_traded']:,.4f}",
        "",
        "Input Settings",
        "-" * 14,
        f"Rebalance threshold: {rebalance_threshold_pct:.2f}%",
        f"Moderate drift threshold: {moderate_drift_threshold_pct:.2f}%",
        f"High drift threshold: {high_drift_threshold_pct:.2f}%",
        f"Trade tolerance: ${trade_tolerance:,.2f}",
        f"Fractional shares enabled: {allow_fractional_shares}",
        f"Position sizing portfolio value: ${portfolio_value:,.2f}",
        f"Risk per trade: {risk_per_trade_pct:.2f}%",
        f"Total risk budget: {total_risk_budget_pct:.2f}%",
        f"Stop-loss distance: {stop_loss_pct:.2f}%",
        f"Max position weight: {max_position_weight_pct:.2f}%",
        "",
        "Rebalance Alert Summary",
        "-" * 23,
        f"High drift count: {alert_summary['high_drift_count']}",
        f"Moderate drift count: {alert_summary['moderate_drift_count']}",
        f"Within range count: {alert_summary['within_range_count']}",
        f"Positions needing attention: {alert_summary['positions_needing_attention']}",
        f"Max absolute drift: {alert_summary['max_absolute_drift_pct']:.2f}%",
        f"Total absolute drift: {alert_summary['total_absolute_drift_pct']:.2f}%",
        "",
        "Dollar Trade Summary",
        "-" * 20,
        f"Buy recommendations: {dollar_summary['buy_recommendations']}",
        f"Sell recommendations: {dollar_summary['sell_recommendations']}",
        f"Hold recommendations: {dollar_summary['hold_recommendations']}",
        f"High-priority trades: {dollar_summary['high_priority_trades']}",
        f"Medium-priority trades: {dollar_summary['medium_priority_trades']}",
        f"Low-priority trades: {dollar_summary['low_priority_trades']}",
        f"Total buy amount: ${dollar_summary['total_buy_amount']:,.2f}",
        f"Total sell amount: ${dollar_summary['total_sell_amount']:,.2f}",
        f"Gross trade amount: ${dollar_summary['gross_trade_amount']:,.2f}",
        f"Net trade amount: ${dollar_summary['net_trade_amount']:,.2f}",
        "",
        "Share Trade Summary",
        "-" * 19,
        f"Buy trades: {share_summary['buy_trades']}",
        f"Sell trades: {share_summary['sell_trades']}",
        f"Hold trades: {share_summary['hold_trades']}",
        f"Total absolute shares traded: {share_summary['total_absolute_shares_traded']:,.4f}",
        f"Gross estimated trade value: ${share_summary['gross_estimated_trade_value']:,.2f}",
        f"Net estimated trade value: ${share_summary['net_estimated_trade_value']:,.2f}",
        f"Post-trade portfolio value: ${share_summary['post_trade_portfolio_value']:,.2f}",
        "",
        "Position Sizing Summary",
        "-" * 23,
        f"Candidate count: {position_sizing_summary['candidate_count']}",
        f"Total position value: ${position_sizing_summary['total_position_value']:,.2f}",
        f"Total estimated dollar risk: ${position_sizing_summary['total_estimated_dollar_risk']:,.2f}",
        f"Average position weight: {position_sizing_summary['average_position_weight_pct']:.2f}%",
        f"Max position weight: {position_sizing_summary['max_position_weight_pct']:.2f}%",
        f"Capped positions: {position_sizing_summary['capped_position_count']}",
        f"Risk-sized positions: {position_sizing_summary['risk_sized_position_count']}",
        "",
        "Risk-Budget Position Sizing Summary",
        "-" * 36,
        f"Candidate count: {risk_budget_summary['candidate_count']}",
        f"Total allocated risk budget: {risk_budget_summary['total_allocated_risk_budget_pct']:.2f}%",
        f"Total allocated risk budget amount: ${risk_budget_summary['total_allocated_risk_budget_amount']:,.2f}",
        f"Total estimated dollar risk: ${risk_budget_summary['total_estimated_dollar_risk']:,.2f}",
        f"Total position value: ${risk_budget_summary['total_position_value']:,.2f}",
        f"Average position weight: {risk_budget_summary['average_position_weight_pct']:.2f}%",
        f"Max position weight: {risk_budget_summary['max_position_weight_pct']:.2f}%",
        f"Capped positions: {risk_budget_summary['capped_position_count']}",
        f"Risk-sized positions: {risk_budget_summary['risk_sized_position_count']}",
        "",
        "Target vs Current Allocation",
        "-" * 28,
        target_vs_current.round(4).to_string(index=False),
        "",
        "Drift Detection and Rebalance Alerts",
        "-" * 38,
        alerts.round(4).to_string(index=False),
        "",
        "Dollar Trade Recommendations",
        "-" * 28,
        dollar_recommendations.round(4).to_string(index=False),
        "",
        "Share Trade Recommendations",
        "-" * 27,
        share_recommendations.round(4).to_string(index=False),
        "",
        "Full Rebalance Plan",
        "-" * 19,
        rebalance_plan.round(4).to_string(index=False),
        "",
        "Position Sizing Rules",
        "-" * 21,
        position_sizing_table.round(4).to_string(index=False),
        "",
        "Risk-Budget Position Sizing",
        "-" * 27,
        risk_budget_table.round(4).to_string(index=False),
        "",
        "Methodology Notes",
        "-" * 17,
        "This report compares current portfolio allocation against target allocation.",
        "Dollar trade recommendations estimate buy and sell amounts needed to move toward targets.",
        "Share trade recommendations convert dollar trades into estimated share quantities.",
        "Position sizing estimates trade size from risk per trade, stop-loss distance, and max position weight.",
        "Risk-budget position sizing spreads a total portfolio risk budget across multiple candidates.",
        "",
        "Important: This is a portfolio research and engineering tool. It is not financial advice.",
    ]

    return "\n".join(report_sections)


def render_rebalancing_export_report(
    positions: pd.DataFrame,
    candidates: pd.DataFrame,
    rebalance_threshold_pct: float,
    moderate_drift_threshold_pct: float,
    high_drift_threshold_pct: float,
    trade_tolerance: float,
    allow_fractional_shares: bool,
    portfolio_value: float,
    risk_per_trade_pct: float,
    total_risk_budget_pct: float,
    stop_loss_pct: float,
    max_position_weight_pct: float,
) -> None:
    """Render downloadable rebalancing report."""
    st.subheader("Rebalancing Export Report")

    try:
        report_text = build_rebalancing_export_report(
            positions=positions,
            candidates=candidates,
            rebalance_threshold_pct=rebalance_threshold_pct,
            moderate_drift_threshold_pct=moderate_drift_threshold_pct,
            high_drift_threshold_pct=high_drift_threshold_pct,
            trade_tolerance=trade_tolerance,
            allow_fractional_shares=allow_fractional_shares,
            portfolio_value=portfolio_value,
            risk_per_trade_pct=risk_per_trade_pct,
            total_risk_budget_pct=total_risk_budget_pct,
            stop_loss_pct=stop_loss_pct,
            max_position_weight_pct=max_position_weight_pct,
        )
    except Exception as error:
        st.error(f"Rebalancing export report failed: {error}")
        return

    st.download_button(
        label="Download Rebalancing Report TXT",
        data=report_text,
        file_name="portfolio_rebalancing_report.txt",
        mime="text/plain",
        key="download_rebalancing_report_txt",
    )

    with st.expander("Rebalancing Report Preview", expanded=False):
        st.text(report_text)


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

### Drift Alert Logic

The drift alert section flags positions that are too far away from their target allocation.

Current alert levels:

- **High Drift:** Position drift is at or above the high drift threshold.
- **Moderate Drift:** Position drift is at or above the moderate threshold.
- **Within Range:** Position is inside the selected drift thresholds.

This helps decide which positions need the most attention before placing rebalance trades.

### Dollar Trade Logic

If a position is below target, the engine recommends a **Buy** amount.

If a position is above target, the engine recommends a **Sell** amount.

If the trade amount is below the tolerance threshold, the engine marks it as **Hold**.

### Share Trade Logic

Dollar trades are converted into share quantities using the current price.

If fractional shares are enabled, the engine can recommend partial shares.

If fractional shares are disabled, the engine rounds down to whole shares.

### Position Sizing Logic

The Position Sizing section estimates how many shares to buy based on:

- Portfolio value
- Risk per trade
- Stop-loss distance
- Current price
- Maximum position weight

This helps translate risk rules into realistic trade sizes.

### Risk-Budget Position Sizing Logic

The Risk-Budget Position Sizing section spreads a total portfolio risk budget across multiple candidate trades.

Example:

- Total risk budget: 3%
- Three candidates
- Equal risk budget: 1% per candidate

This helps prevent the portfolio from taking too much total risk across several trades at once.

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

        moderate_drift_threshold_pct = st.number_input(
            "Moderate Drift Threshold %",
            min_value=0.5,
            max_value=50.0,
            value=5.0,
            step=0.5,
        )

        high_drift_threshold_pct = st.number_input(
            "High Drift Threshold %",
            min_value=1.0,
            max_value=75.0,
            value=10.0,
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

        st.subheader("Position Sizing Inputs")

        portfolio_value = st.number_input(
            "Portfolio Value $",
            min_value=100.0,
            max_value=100000000.0,
            value=10000.0,
            step=500.0,
        )

        risk_per_trade_pct = st.number_input(
            "Risk Per Trade %",
            min_value=0.1,
            max_value=25.0,
            value=1.0,
            step=0.1,
        )

        total_risk_budget_pct = st.number_input(
            "Total Risk Budget %",
            min_value=0.1,
            max_value=50.0,
            value=3.0,
            step=0.1,
        )

        stop_loss_pct = st.number_input(
            "Stop-Loss Distance %",
            min_value=0.1,
            max_value=90.0,
            value=5.0,
            step=0.5,
        )

        max_position_weight_pct = st.number_input(
            "Max Position Weight %",
            min_value=0.1,
            max_value=100.0,
            value=25.0,
            step=1.0,
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

    st.subheader("Position Sizing Candidates")

    editable_candidates = st.data_editor(
        DEFAULT_SIZING_CANDIDATES,
        num_rows="dynamic",
        use_container_width=True,
        key="position_sizing_candidate_editor",
    )

    if not run_rebalance:
        render_rebalancing_methodology()
        st.info("Edit positions and click Run Rebalance Analysis.")
        return

    try:
        positions = prepare_positions(editable_positions)
        candidates = prepare_sizing_candidates(editable_candidates)

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

    st.divider()

    render_rebalance_alerts(
        positions=positions,
        high_drift_threshold_pct=high_drift_threshold_pct,
        moderate_drift_threshold_pct=moderate_drift_threshold_pct,
        trade_tolerance=trade_tolerance,
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

    st.divider()

    render_position_sizing_section(
        candidates=candidates,
        portfolio_value=portfolio_value,
        risk_per_trade_pct=risk_per_trade_pct,
        stop_loss_pct=stop_loss_pct,
        max_position_weight_pct=max_position_weight_pct,
        allow_fractional_shares=allow_fractional_shares,
    )

    st.divider()

    render_risk_budget_position_sizing_section(
        candidates=candidates,
        portfolio_value=portfolio_value,
        total_risk_budget_pct=total_risk_budget_pct,
        stop_loss_pct=stop_loss_pct,
        max_position_weight_pct=max_position_weight_pct,
        allow_fractional_shares=allow_fractional_shares,
    )

    st.divider()

    render_rebalancing_export_report(
        positions=positions,
        candidates=candidates,
        rebalance_threshold_pct=rebalance_threshold_pct,
        moderate_drift_threshold_pct=moderate_drift_threshold_pct,
        high_drift_threshold_pct=high_drift_threshold_pct,
        trade_tolerance=trade_tolerance,
        allow_fractional_shares=allow_fractional_shares,
        portfolio_value=portfolio_value,
        risk_per_trade_pct=risk_per_trade_pct,
        total_risk_budget_pct=total_risk_budget_pct,
        stop_loss_pct=stop_loss_pct,
        max_position_weight_pct=max_position_weight_pct,
    )

    render_rebalance_plan(positions)
    render_rebalancing_methodology()


render_portfolio_rebalancing_page()
