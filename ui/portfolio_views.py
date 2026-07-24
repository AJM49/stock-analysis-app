from __future__ import annotations
from database import save_portfolio_scenario, get_portfolio_scenarios, delete_portfolio_scenario

import pandas as pd
import streamlit as st

REPORT_SPRINT_VERSION = "Sprint 64"
REPORT_FEATURE_LABEL = "Portfolio Reporting and Decision Support"
import plotly.express as px
from services.portfolio_analytics_service import build_portfolio_risk_flags, build_sector_exposure_dataframe, build_position_weight_dataframe, calculate_portfolio_risk_score
from portfolio import calculate_target_price
from portfolio import calculate_stop_loss
from portfolio import calculate_risk_reward

def make_arrow_safe(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Return dataframe copy that is safe for Streamlit Arrow rendering."""
    if dataframe is None:
        return pd.DataFrame()

    safe_df = dataframe.copy()

    for column in safe_df.columns:
        if safe_df[column].dtype == "object":
            safe_df[column] = safe_df[column].astype(str)

    return safe_df


def format_portfolio_dataframe(portfolio_df: pd.DataFrame) -> pd.DataFrame:
    """Format portfolio dataframe for display."""
    if portfolio_df is None or portfolio_df.empty:
        return pd.DataFrame()

    display_df = portfolio_df.copy()

    currency_columns = [
        "Buy Price",
        "Cost Basis",
        "Current Price",
        "Current Value",
        "Gain/Loss",
    ]

    percent_columns = [
        "Gain/Loss %",
        "Allocation %",
        "Volatility %",
    ]

    for column in currency_columns:
        if column in display_df.columns:
            display_df[column] = display_df[column].map(
                lambda value: f"${float(value):,.2f}"
            )

    for column in percent_columns:
        if column in display_df.columns:
            display_df[column] = display_df[column].map(
                lambda value: f"{float(value):.2f}%"
            )

    return display_df


def render_portfolio_dashboard(portfolio_df):
    """Render the full portfolio analytics dashboard."""
    st.subheader("Portfolio Analytics")

    if portfolio_df is None or portfolio_df.empty:
        st.info(
            "No portfolio positions found. Add a ticker, share count, and "
            "buy price from the sidebar to activate portfolio analytics."
        )
        st.caption(
            "After positions are added, this dashboard will show allocation, "
            "gain/loss, concentration risk, sector exposure, and export tools."
        )
        return

    total_cost_basis = float(portfolio_df["Cost Basis"].sum())
    total_current_value = float(portfolio_df["Current Value"].sum())
    total_gain_loss = float(portfolio_df["Gain/Loss"].sum())

    if total_cost_basis > 0:
        total_gain_loss_pct = (total_gain_loss / total_cost_basis) * 100
    else:
        total_gain_loss_pct = 0.0

    summary_col1, summary_col2, summary_col3 = st.columns(3)

    summary_col1.metric(
        "Total Current Value",
        f"${total_current_value:,.2f}",
    )

    summary_col2.metric(
        "Total Cost Basis",
        f"${total_cost_basis:,.2f}",
    )

    summary_col3.metric(
        "Total Gain/Loss",
        f"${total_gain_loss:,.2f}",
        f"{total_gain_loss_pct:.2f}%",
    )

    render_portfolio_risk_alert_banner(portfolio_df)
    render_portfolio_executive_summary(portfolio_df)

    with st.expander("Portfolio What-If Scenario Planner", expanded=False):
        render_portfolio_what_if_scenario(portfolio_df)

    st.divider()

    with st.expander("Portfolio Overview", expanded=True):
        render_portfolio_help_text("Portfolio Overview")
        render_best_worst_performer_summary(portfolio_df)
        render_unrealized_gain_loss_summary(portfolio_df)

    with st.expander("Risk Intelligence", expanded=True):
        render_portfolio_help_text("Risk Intelligence")
        render_portfolio_risk_score(portfolio_df)
        render_portfolio_risk_recommendations(portfolio_df)
        render_portfolio_concentration_score(portfolio_df)
        render_sector_concentration_warning(portfolio_df)
        render_missing_price_warning(portfolio_df)
        render_portfolio_risk_flags(portfolio_df)

    with st.expander("Allocation and Exposure", expanded=True):
        render_portfolio_help_text("Allocation and Exposure")
        render_portfolio_allocation_chart(portfolio_df)
        render_position_weight_summary(portfolio_df)
        render_sector_exposure_summary(portfolio_df)

    with st.expander("Portfolio Export", expanded=False):
        render_portfolio_help_text("Portfolio Export")
        render_portfolio_export(portfolio_df)

    with st.expander("Portfolio Table", expanded=False):
        render_portfolio_help_text("Portfolio Table")
        render_portfolio_table(portfolio_df)


def render_missing_price_warning(portfolio_df: pd.DataFrame) -> None:
    """Warn when portfolio positions are missing current price data."""
    if portfolio_df is None or portfolio_df.empty:
        return

    if "Price Status" not in portfolio_df.columns:
        return

    missing_price_df = portfolio_df[
        portfolio_df["Price Status"] == "Missing"
    ]

    if missing_price_df.empty:
        return

    missing_tickers = ", ".join(
        missing_price_df["Ticker"].astype(str).tolist()
    )

    st.warning(
        "Missing current price data for: "
        + missing_tickers
        + ". These positions may show $0 current value until price data is refreshed."
    )



def render_unrealized_gain_loss_summary(portfolio_df: pd.DataFrame) -> None:
    """Render unrealized gain/loss portfolio summary."""
    st.subheader("Unrealized Gain/Loss")

    if portfolio_df is None or portfolio_df.empty:
        st.info("No unrealized gain/loss data available yet.")
        return

    required_columns = [
        "Ticker",
        "Cost Basis",
        "Current Value",
        "Gain/Loss",
        "Gain/Loss %",
    ]

    missing_columns = [
        column for column in required_columns
        if column not in portfolio_df.columns
    ]

    if missing_columns:
        st.info(
            "Portfolio gain/loss data is missing required columns: "
            + ", ".join(missing_columns)
        )
        return

    total_cost_basis = float(portfolio_df["Cost Basis"].sum())
    total_current_value = float(portfolio_df["Current Value"].sum())
    total_gain_loss = float(portfolio_df["Gain/Loss"].sum())

    if total_cost_basis > 0:
        portfolio_return_pct = (total_gain_loss / total_cost_basis) * 100
    else:
        portfolio_return_pct = 0.0

    winning_positions = portfolio_df[portfolio_df["Gain/Loss"] > 0]
    losing_positions = portfolio_df[portfolio_df["Gain/Loss"] < 0]

    best_dollar_position = portfolio_df.sort_values(
        by="Gain/Loss",
        ascending=False,
    ).iloc[0]

    worst_dollar_position = portfolio_df.sort_values(
        by="Gain/Loss",
        ascending=True,
    ).iloc[0]

    gain_col1, gain_col2, gain_col3, gain_col4 = st.columns(4)

    gain_col1.metric(
        "Unrealized Gain/Loss",
        f"${total_gain_loss:,.2f}",
        f"{portfolio_return_pct:.2f}%",
    )

    gain_col2.metric(
        "Current Value",
        f"${total_current_value:,.2f}",
    )

    gain_col3.metric(
        "Winning Positions",
        str(len(winning_positions)),
    )

    gain_col4.metric(
        "Losing Positions",
        str(len(losing_positions)),
    )

    perf_col1, perf_col2 = st.columns(2)

    best_gain_loss = float(best_dollar_position["Gain/Loss"])
    worst_gain_loss = float(worst_dollar_position["Gain/Loss"])

    perf_col1.metric(
        "Best Dollar Performer",
        str(best_dollar_position["Ticker"]),
        f"${best_gain_loss:,.2f}",
    )

    perf_col2.metric(
        "Worst Dollar Performer",
        str(worst_dollar_position["Ticker"]),
        f"${worst_gain_loss:,.2f}",
    )

    performance_df = portfolio_df[
        [
            "Ticker",
            "Cost Basis",
            "Current Value",
            "Gain/Loss",
            "Gain/Loss %",
        ]
    ].copy()

    performance_df = performance_df.sort_values(
        by="Gain/Loss",
        ascending=False,
    )

    formatted_df = performance_df.copy()

    formatted_df["Cost Basis"] = formatted_df["Cost Basis"].map(
        lambda value: f"${value:,.2f}"
    )
    formatted_df["Current Value"] = formatted_df["Current Value"].map(
        lambda value: f"${value:,.2f}"
    )
    formatted_df["Gain/Loss"] = formatted_df["Gain/Loss"].map(
        lambda value: f"${value:,.2f}"
    )
    formatted_df["Gain/Loss %"] = formatted_df["Gain/Loss %"].map(
        lambda value: f"{value:.2f}%"
    )

    st.dataframe(formatted_df, use_container_width=True)


def get_position_weight_status(allocation_pct: float) -> tuple[str, str]:
    """Return position weight label and risk note."""
    if allocation_pct >= 50:
        return (
            "Concentrated risk",
            "This position is more than half of the portfolio.",
        )

    if allocation_pct >= 25:
        return (
            "Heavy position",
            "This position has meaningful concentration risk.",
        )

    if allocation_pct >= 10:
        return (
            "Moderate position",
            "This position is within a normal active range.",
        )

    return (
        "Small position",
        "This position has limited portfolio impact.",
    )


def render_position_weight_summary(portfolio_df: pd.DataFrame) -> None:
    """Render portfolio position weight by ticker."""
    st.subheader("Position Weight by Ticker")

    try:
        weight_df = build_position_weight_dataframe(portfolio_df)
    except ValueError as error:
        st.info(str(error))
        return

    if weight_df.empty:
        st.info("No position weight data available yet.")
        return

    display_df = weight_df.copy()

    display_df["Current Value"] = display_df["Current Value"].map(
        lambda value: f"${value:,.2f}"
    )

    display_df["Allocation %"] = display_df["Allocation %"].map(
        lambda value: f"{value:.2f}%"
    )

    st.dataframe(display_df, use_container_width=True)

    largest_position = weight_df.iloc[0]
    largest_allocation = float(largest_position["Allocation %"])
    largest_ticker = str(largest_position["Ticker"])

    if largest_allocation >= 50:
        st.warning(
            "Concentration risk detected: "
            + largest_ticker
            + " is more than 50% of the portfolio."
        )
    elif largest_allocation >= 25:
        st.info(
            "Largest position watch: "
            + largest_ticker
            + " is above 25% of the portfolio."
        )
    else:
        st.success("No major single-position concentration risk detected.")

def render_sector_exposure_summary(portfolio_df: pd.DataFrame) -> None:
    """Render portfolio sector exposure summary."""
    st.subheader("Sector Exposure")

    try:
        sector_df = build_sector_exposure_dataframe(portfolio_df)
    except ValueError as error:
        st.info(str(error))
        return

    if sector_df.empty:
        st.info("No sector exposure data available yet.")
        return

    fig = px.pie(
        sector_df,
        names="Sector",
        values="Current Value",
        title="Exposure by Sector",
        hole=0.35,
    )

    st.plotly_chart(fig, use_container_width=True)

    display_df = sector_df.copy()

    display_df["Current Value"] = display_df["Current Value"].map(
        lambda value: f"${value:,.2f}"
    )

    display_df["Exposure %"] = display_df["Exposure %"].map(
        lambda value: f"{value:.2f}%"
    )

    st.dataframe(display_df, use_container_width=True)

    largest_sector = sector_df.iloc[0]
    largest_sector_name = str(largest_sector["Sector"])
    largest_exposure = float(largest_sector["Exposure %"])

    if largest_exposure >= 50:
        st.warning(
            "Sector concentration risk detected: "
            + largest_sector_name
            + " is more than 50% of the portfolio."
        )
    elif largest_exposure >= 35:
        st.info(
            "Sector exposure watch: "
            + largest_sector_name
            + " is above 35% of the portfolio."
        )
    else:
        st.success("No major sector concentration risk detected.")

def render_risk_dashboard(portfolio_df, largest_position=None):
    st.subheader("Portfolio Risk Dashboard")

    if portfolio_df is None or portfolio_df.empty:
        st.info("Add portfolio positions to view risk analytics.")
        return

    required_columns = [
        "Ticker",
        "Current Value",
        "Allocation %",
        "Volatility %",
    ]

    for column in required_columns:
        if column not in portfolio_df.columns:
            portfolio_df[column] = 0

    total_value = portfolio_df["Current Value"].sum()

    if total_value > 0:
        portfolio_df["Allocation %"] = (
            portfolio_df["Current Value"] / total_value
        ) * 100
    else:
        portfolio_df["Allocation %"] = 0

    max_allocation = portfolio_df["Allocation %"].max()
    average_volatility = portfolio_df["Volatility %"].mean()

    if largest_position is None:
        largest_position = portfolio_df.sort_values(
            by="Allocation %",
            ascending=False
        ).iloc[0]

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Largest Allocation",
        f"{max_allocation:.2f}%"
    )

    col2.metric(
        "Average Volatility",
        f"{average_volatility:.2f}%"
    )

    col3.metric(
        "Risk Level",
        "High" if max_allocation > 50 else "Moderate"
    )

    if max_allocation > 50:
        st.warning(
            "Portfolio concentration risk is high. "
            "One position is more than 50% of portfolio value."
        )
    else:
        st.success("Portfolio concentration risk is within a moderate range.")

def render_stop_loss_calculator(portfolio_df):
    st.subheader("Stop-Loss and Target Calculator")

    calculator_col1, calculator_col2, calculator_col3 = st.columns(3)

    calculator_ticker = calculator_col1.selectbox(
        "Select Position",
        options=portfolio_df["Ticker"].tolist(),
        key="risk_calculator_ticker"
    )

    stop_loss_pct = calculator_col2.number_input(
        "Stop-Loss %",
        min_value=1.0,
        max_value=90.0,
        value=10.0,
        step=1.0,
        key="stop_loss_pct_input"
    )

    target_gain_pct = calculator_col3.number_input(
        "Target Gain %",
        min_value=1.0,
        max_value=500.0,
        value=20.0,
        step=1.0,
        key="target_gain_pct_input"
    )

    selected_row = portfolio_df[
        portfolio_df["Ticker"] == calculator_ticker
    ].iloc[0]

    current_price = selected_row["Current Price"]

    stop_price = calculate_stop_loss(current_price, stop_loss_pct)
    target_price = calculate_target_price(current_price, target_gain_pct)

    risk_reward_ratio = calculate_risk_reward(
        current_price,
        stop_price,
        target_price
    )

    calc_col1, calc_col2, calc_col3, calc_col4 = st.columns(4)

    calc_col1.metric("Current Price", f"${current_price:,.2f}")
    calc_col2.metric("Stop-Loss Price", f"${stop_price:,.2f}")
    calc_col3.metric("Target Price", f"${target_price:,.2f}")
    calc_col4.metric("Risk/Reward Ratio", f"{risk_reward_ratio:.2f}")

    if risk_reward_ratio >= 2:
        st.success("Risk/reward profile is favorable.")
    elif risk_reward_ratio >= 1:
        st.info("Risk/reward profile is balanced.")
    else:
        st.warning("Risk/reward profile is weak.")

def render_portfolio_allocation_chart(portfolio_df: pd.DataFrame) -> None:
    """Render portfolio allocation chart by ticker."""
    st.subheader("Portfolio Allocation")

    if portfolio_df is None or portfolio_df.empty:
        st.info("No portfolio allocation data available yet.")
        return

    required_columns = ["Ticker", "Current Value", "Allocation %"]

    for column in required_columns:
        if column not in portfolio_df.columns:
            st.info("Portfolio allocation data is missing required columns.")
            return

    allocation_df = portfolio_df[
        [
            "Ticker",
            "Current Value",
            "Allocation %",
        ]
    ].copy()

    allocation_df = allocation_df[allocation_df["Current Value"] > 0]

    if allocation_df.empty:
        st.info("No positive portfolio value available for allocation chart.")
        return

    fig = px.pie(
        allocation_df,
        names="Ticker",
        values="Current Value",
        title="Allocation by Current Value",
        hole=0.35,
    )

    st.plotly_chart(fig, use_container_width=True)

    display_df = allocation_df.copy()

    display_df["Current Value"] = display_df["Current Value"].map(
        lambda value: f"${value:,.2f}"
    )

    display_df["Allocation %"] = display_df["Allocation %"].map(
        lambda value: f"{value:.2f}%"
    )

    st.dataframe(display_df, use_container_width=True)

def render_portfolio_risk_flags(portfolio_df: pd.DataFrame) -> None:
    """Render portfolio-level risk flags."""
    st.subheader("Portfolio Risk Flags")

    if portfolio_df is None or portfolio_df.empty:
        st.info("No portfolio data available for risk flags.")
        return

    sector_df = pd.DataFrame()

    try:
        sector_df = build_sector_exposure_dataframe(portfolio_df)
    except Exception as error:
        st.warning(f"Sector risk check unavailable: {error}")

    try:
        risk_flags = build_portfolio_risk_flags(
            portfolio_df=portfolio_df,
            sector_df=sector_df,
        )
    except Exception as error:
        st.warning(f"Portfolio risk flags unavailable: {error}")
        return

    if not risk_flags:
        st.success("No major portfolio risk flags detected.")
        return

    risk_flags_df = pd.DataFrame(risk_flags)

    st.dataframe(
        make_arrow_safe(risk_flags_df),
        use_container_width=True,
        hide_index=True,
    )



def render_portfolio_export(portfolio_df: pd.DataFrame) -> None:
    """Render portfolio CSV export button."""
    if portfolio_df is None or portfolio_df.empty:
        return

    export_df = portfolio_df.copy()

    csv_data = export_df.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="Download Portfolio Summary CSV",
        data=csv_data,
        file_name="portfolio_summary.csv",
        mime="text/csv",
        use_container_width=True,
    )



def render_portfolio_table(portfolio_df):
    if portfolio_df.empty:
        st.info("No portfolio positions saved yet.")
        return

    formatted_portfolio_df = format_portfolio_dataframe(portfolio_df)

    st.dataframe(
        make_arrow_safe(formatted_portfolio_df),
        use_container_width=True
    )
    sort_option = st.selectbox(
        "Sort Portfolio By",
        options=[
            "Ticker",
            "Current Value",
            "Gain/Loss",
            "Gain/Loss %",
            "Allocation %",
            "Volatility %"
        ],
        index=1,
        key="portfolio_sort_option"
    )

    sort_direction = st.radio(
        "Sort Direction",
        options=[
            "Descending",
            "Ascending"
        ],
        horizontal=True,
        key="portfolio_sort_direction"
    )

    ascending_sort = sort_direction == "Ascending"

    sorted_portfolio_df = portfolio_df.sort_values(
        by=sort_option,
        ascending=ascending_sort
    )


    st.dataframe(formatted_portfolio_df),

    portfolio_csv = portfolio_df.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="Download Portfolio CSV",
        data=portfolio_csv,
        file_name="portfolio_risk_dashboard.csv",
        mime="text/csv",
        key="download_portfolio_csv"
    )



def render_portfolio_snapshot_history(snapshots) -> None:
    """Render saved portfolio snapshot history."""
    st.subheader("Portfolio Snapshot History")

    if not snapshots:
        st.info("No portfolio snapshots saved yet.")
        return

    snapshot_rows = []

    for snapshot in snapshots:
        snapshot_rows.append(
            {
                "Snapshot Date": snapshot.snapshot_date,
                "Total Cost Basis": snapshot.total_cost_basis,
                "Total Current Value": snapshot.total_current_value,
                "Total Gain/Loss": snapshot.total_gain_loss,
                "Total Gain/Loss %": snapshot.total_gain_loss_pct,
                "Position Count": snapshot.position_count,
                "Risk Score": getattr(snapshot, "risk_score", None),
                "Risk Level": getattr(snapshot, "risk_level", None),
                "Risk Notes": getattr(snapshot, "risk_notes", None),
            }
        )

    snapshot_df = pd.DataFrame(snapshot_rows)

    if not snapshot_df.empty:
        snapshot_df["Snapshot Date"] = pd.to_datetime(
            snapshot_df["Snapshot Date"]
        ).dt.strftime("%Y-%m-%d %H:%M")

        currency_columns = [
            "Total Cost Basis",
            "Total Current Value",
            "Total Gain/Loss",
        ]

        for column in currency_columns:
            snapshot_df[column] = snapshot_df[column].map(
                lambda value: f"${float(value):,.2f}"
            )

        snapshot_df["Total Gain/Loss %"] = snapshot_df[
            "Total Gain/Loss %"
        ].map(
            lambda value: f"{float(value):.2f}%"
        )

    st.dataframe(
        make_arrow_safe(snapshot_df),
        use_container_width=True,
        hide_index=True,
    )


def render_portfolio_value_history_chart(snapshots) -> None:
    """Render portfolio value history chart from saved snapshots."""
    st.subheader("Portfolio Value History")

    if not snapshots:
        st.info("No portfolio snapshots available for charting.")
        return

    snapshot_rows = []

    for snapshot in snapshots:
        snapshot_rows.append(
            {
                "Snapshot Date": snapshot.snapshot_date,
                "Total Current Value": snapshot.total_current_value,
            }
        )

    snapshot_df = pd.DataFrame(snapshot_rows)

    if snapshot_df.empty:
        st.info("No portfolio snapshot values available for charting.")
        return

    snapshot_df["Snapshot Date"] = pd.to_datetime(
        snapshot_df["Snapshot Date"]
    )

    snapshot_df = snapshot_df.sort_values(
        by="Snapshot Date",
        ascending=True,
    )

    st.line_chart(
        data=snapshot_df,
        x="Snapshot Date",
        y="Total Current Value",
        use_container_width=True,
    )


def render_portfolio_gain_loss_history_chart(snapshots) -> None:
    """Render portfolio gain/loss history chart from saved snapshots."""
    st.subheader("Portfolio Gain/Loss History")

    if not snapshots:
        st.info("No portfolio snapshots available for gain/loss charting.")
        return

    snapshot_rows = []

    for snapshot in snapshots:
        snapshot_rows.append(
            {
                "Snapshot Date": snapshot.snapshot_date,
                "Total Gain/Loss": snapshot.total_gain_loss,
            }
        )

    snapshot_df = pd.DataFrame(snapshot_rows)

    if snapshot_df.empty:
        st.info("No portfolio gain/loss values available for charting.")
        return

    snapshot_df["Snapshot Date"] = pd.to_datetime(
        snapshot_df["Snapshot Date"]
    )

    snapshot_df = snapshot_df.sort_values(
        by="Snapshot Date",
        ascending=True,
    )

    st.line_chart(
        data=snapshot_df,
        x="Snapshot Date",
        y="Total Gain/Loss",
        use_container_width=True,
    )



def render_portfolio_snapshot_export(snapshots) -> None:
    """Render CSV export for saved portfolio snapshot history."""
    st.subheader("Export Portfolio Snapshot History")

    if not snapshots:
        st.info(
        "No portfolio snapshot history is available to export yet."
    )
        return

    snapshot_rows = []

    for snapshot in snapshots:
        snapshot_rows.append(
            {
                "Snapshot Date": snapshot.snapshot_date,
                "Total Cost Basis": snapshot.total_cost_basis,
                "Total Current Value": snapshot.total_current_value,
                "Total Gain/Loss": snapshot.total_gain_loss,
                "Total Gain/Loss %": snapshot.total_gain_loss_pct,
                "Position Count": snapshot.position_count,
            }
        )

    snapshot_df = pd.DataFrame(snapshot_rows)

    if snapshot_df.empty:
        st.info("No portfolio snapshot rows available to export.")
        return

    snapshot_df["Snapshot Date"] = pd.to_datetime(
        snapshot_df["Snapshot Date"]
    ).dt.strftime("%Y-%m-%d %H:%M:%S")

    csv_data = snapshot_df.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="Download Portfolio Snapshot History CSV",
        data=csv_data,
        file_name="portfolio_snapshot_history.csv",
        mime="text/csv",
        use_container_width=True,
    )


def render_best_worst_performer_summary(portfolio_df: pd.DataFrame) -> None:
    """Render best and worst portfolio performer summary cards."""
    st.subheader("Best/Worst Performer Summary")

    if portfolio_df is None or portfolio_df.empty:
        st.info("No portfolio data available for performer summary.")
        return

    required_columns = [
        "Ticker",
        "Gain/Loss",
        "Gain/Loss %",
        "Current Value",
    ]

    missing_columns = [
        column for column in required_columns
        if column not in portfolio_df.columns
    ]

    if missing_columns:
        st.warning(
            "Performer summary unavailable. Missing columns: "
            + ", ".join(missing_columns)
        )
        return

    best_pct = portfolio_df.sort_values(
        by="Gain/Loss %",
        ascending=False,
    ).iloc[0]

    worst_pct = portfolio_df.sort_values(
        by="Gain/Loss %",
        ascending=True,
    ).iloc[0]

    largest_gain = portfolio_df.sort_values(
        by="Gain/Loss",
        ascending=False,
    ).iloc[0]

    largest_loss = portfolio_df.sort_values(
        by="Gain/Loss",
        ascending=True,
    ).iloc[0]

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Best Performer",
        str(best_pct["Ticker"]),
        f"{float(best_pct['Gain/Loss %']):.2f}%",
    )

    col2.metric(
        "Worst Performer",
        str(worst_pct["Ticker"]),
        f"{float(worst_pct['Gain/Loss %']):.2f}%",
    )

    col3.metric(
        "Largest Gain",
        str(largest_gain["Ticker"]),
        f"${float(largest_gain['Gain/Loss']):,.2f}",
    )

    col4.metric(
        "Largest Loss",
        str(largest_loss["Ticker"]),
        f"${float(largest_loss['Gain/Loss']):,.2f}",
    )


def render_portfolio_concentration_score(portfolio_df: pd.DataFrame) -> None:
    """Render portfolio concentration score based on largest allocation."""
    st.subheader("Portfolio Concentration Score")

    if portfolio_df is None or portfolio_df.empty:
        st.info("No portfolio data available for concentration score.")
        return

    required_columns = [
        "Ticker",
        "Allocation %",
    ]

    missing_columns = [
        column for column in required_columns
        if column not in portfolio_df.columns
    ]

    if missing_columns:
        st.warning(
            "Concentration score unavailable. Missing columns: "
            + ", ".join(missing_columns)
        )
        return

    largest_position = portfolio_df.sort_values(
        by="Allocation %",
        ascending=False,
    ).iloc[0]

    ticker = str(largest_position["Ticker"])
    allocation_pct = float(largest_position["Allocation %"])

    if allocation_pct >= 50:
        concentration_level = "High"
        concentration_note = (
            "The portfolio is highly concentrated in one position."
        )
    elif allocation_pct >= 25:
        concentration_level = "Medium"
        concentration_note = (
            "The portfolio has meaningful single-position concentration."
        )
    else:
        concentration_level = "Low"
        concentration_note = (
            "The portfolio is reasonably diversified by position weight."
        )

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Concentration Level",
        concentration_level,
    )

    col2.metric(
        "Largest Position",
        ticker,
    )

    col3.metric(
        "Largest Allocation",
        f"{allocation_pct:.2f}%",
    )

    st.caption(concentration_note)


def render_sector_concentration_warning(portfolio_df: pd.DataFrame) -> None:
    """Render warning when portfolio sector exposure is concentrated."""
    st.subheader("Sector Concentration Warning")

    if portfolio_df is None or portfolio_df.empty:
        st.info("No portfolio data available for sector concentration check.")
        return

    try:
        sector_df = build_sector_exposure_dataframe(portfolio_df)
    except Exception as error:
        st.warning(f"Sector concentration check unavailable: {error}")
        return

    if sector_df is None or sector_df.empty:
        st.info("No sector exposure data available.")
        return

    required_columns = [
        "Sector",
        "Exposure %",
    ]

    missing_columns = [
        column for column in required_columns
        if column not in sector_df.columns
    ]

    if missing_columns:
        st.warning(
            "Sector concentration warning unavailable. Missing columns: "
            + ", ".join(missing_columns)
        )
        return

    largest_sector = sector_df.sort_values(
        by="Exposure %",
        ascending=False,
    ).iloc[0]

    sector = str(largest_sector["Sector"])
    exposure_pct = float(largest_sector["Exposure %"])

    if exposure_pct >= 50:
        st.error(
            f"High sector concentration: {sector} is {exposure_pct:.2f}% "
            "of the portfolio."
        )
    elif exposure_pct >= 35:
        st.warning(
            f"Medium sector concentration: {sector} is {exposure_pct:.2f}% "
            "of the portfolio."
        )
    else:
        st.success(
            f"No major sector concentration detected. Largest sector: "
            f"{sector} at {exposure_pct:.2f}%."
        )


def render_portfolio_performance_summary_cards(snapshots) -> None:
    """Render summary cards for portfolio snapshot history."""
    st.subheader("Portfolio Performance Summary")

    if not snapshots:
        st.info(
        "No portfolio snapshots saved yet. Add positions, then use "
        "'Save Portfolio Snapshot' in the sidebar to start tracking history."
    )
        return

    snapshot_rows = []

    for snapshot in snapshots:
        snapshot_rows.append(
            {
                "Snapshot Date": snapshot.snapshot_date,
                "Total Current Value": snapshot.total_current_value,
                "Total Gain/Loss": snapshot.total_gain_loss,
                "Total Gain/Loss %": snapshot.total_gain_loss_pct,
                "Position Count": snapshot.position_count,
            }
        )

    snapshot_df = pd.DataFrame(snapshot_rows)

    if snapshot_df.empty:
        st.info("No portfolio snapshot rows available.")
        return

    snapshot_df["Snapshot Date"] = pd.to_datetime(
        snapshot_df["Snapshot Date"]
    )

    snapshot_df = snapshot_df.sort_values(
        by="Snapshot Date",
        ascending=True,
    )

    latest_snapshot = snapshot_df.iloc[-1]
    best_value_snapshot = snapshot_df.sort_values(
        by="Total Current Value",
        ascending=False,
    ).iloc[0]

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Latest Snapshot Value",
        f"${float(latest_snapshot['Total Current Value']):,.2f}",
    )

    col2.metric(
        "Latest Gain/Loss",
        f"${float(latest_snapshot['Total Gain/Loss']):,.2f}",
        f"{float(latest_snapshot['Total Gain/Loss %']):.2f}%",
    )

    col3.metric(
        "Snapshot Count",
        f"{len(snapshot_df)}",
    )

    col4.metric(
        "Best Saved Value",
        f"${float(best_value_snapshot['Total Current Value']):,.2f}",
    )


def render_portfolio_help_text(section_name: str) -> None:
    """Render short help text for portfolio dashboard sections."""
    help_text = {
        "Portfolio Overview": (
            "Shows the strongest and weakest positions plus total unrealized "
            "gain or loss."
        ),
        "Risk Intelligence": (
            "Highlights concentration, missing price data, negative return "
            "risk, and sector exposure risk."
        ),
        "Allocation and Exposure": (
            "Shows how portfolio value is distributed across positions and "
            "sectors."
        ),
        "Portfolio Export": (
            "Download the current portfolio analytics view as a CSV file."
        ),
        "Portfolio Table": (
            "Review the full position-level portfolio data used by the "
            "dashboard."
        ),
    }

    message = help_text.get(section_name)

    if message:
        st.caption(message)


def render_portfolio_risk_alert_banner(portfolio_df: pd.DataFrame) -> None:
    """Render a top-level portfolio risk alert banner."""
    if portfolio_df is None or portfolio_df.empty:
        return

    alerts = []

    if "Allocation %" in portfolio_df.columns and "Ticker" in portfolio_df.columns:
        largest_position = portfolio_df.sort_values(
            by="Allocation %",
            ascending=False,
        ).iloc[0]

        largest_ticker = str(largest_position["Ticker"])
        largest_allocation = float(largest_position["Allocation %"])

        if largest_allocation >= 50:
            alerts.append(
                {
                    "level": "high",
                    "message": (
                        f"High position concentration: {largest_ticker} is "
                        f"{largest_allocation:.2f}% of the portfolio."
                    ),
                }
            )
        elif largest_allocation >= 25:
            alerts.append(
                {
                    "level": "medium",
                    "message": (
                        f"Medium position concentration: {largest_ticker} is "
                        f"{largest_allocation:.2f}% of the portfolio."
                    ),
                }
            )

    try:
        sector_df = build_sector_exposure_dataframe(portfolio_df)
    except Exception:
        sector_df = pd.DataFrame()

    if sector_df is not None and not sector_df.empty:
        if "Sector" in sector_df.columns and "Exposure %" in sector_df.columns:
            largest_sector = sector_df.sort_values(
                by="Exposure %",
                ascending=False,
            ).iloc[0]

            sector = str(largest_sector["Sector"])
            exposure_pct = float(largest_sector["Exposure %"])

            if exposure_pct >= 50:
                alerts.append(
                    {
                        "level": "high",
                        "message": (
                            f"High sector concentration: {sector} is "
                            f"{exposure_pct:.2f}% of the portfolio."
                        ),
                    }
                )
            elif exposure_pct >= 35:
                alerts.append(
                    {
                        "level": "medium",
                        "message": (
                            f"Medium sector concentration: {sector} is "
                            f"{exposure_pct:.2f}% of the portfolio."
                        ),
                    }
                )

    if "Price Status" in portfolio_df.columns:
        missing_price_count = int(
            (portfolio_df["Price Status"] == "Missing").sum()
        )

        if missing_price_count > 0:
            alerts.append(
                {
                    "level": "medium",
                    "message": (
                        f"{missing_price_count} portfolio position(s) have "
                        "missing price data."
                    ),
                }
            )

    if "Gain/Loss" in portfolio_df.columns:
        total_gain_loss = float(portfolio_df["Gain/Loss"].sum())

        if total_gain_loss < 0:
            alerts.append(
                {
                    "level": "medium",
                    "message": (
                        f"Portfolio is currently negative by "
                        f"${total_gain_loss:,.2f}."
                    ),
                }
            )

    if not alerts:
        st.success("Portfolio risk alert: no major risk triggers detected.")
        return

    high_alerts = [
        alert["message"]
        for alert in alerts
        if alert["level"] == "high"
    ]

    medium_alerts = [
        alert["message"]
        for alert in alerts
        if alert["level"] == "medium"
    ]

    if high_alerts:
        st.error("Portfolio risk alert: " + high_alerts[0])
    elif medium_alerts:
        st.warning("Portfolio risk alert: " + medium_alerts[0])

    with st.expander("View all portfolio risk alerts", expanded=False):
        for alert in alerts:
            if alert["level"] == "high":
                st.error(alert["message"])
            else:
                st.warning(alert["message"])


def render_portfolio_risk_score(portfolio_df: pd.DataFrame) -> None:
    """Render a portfolio risk severity score."""
    if portfolio_df is None or portfolio_df.empty:
        return

    score = 0
    reasons = []

    if "Allocation %" in portfolio_df.columns and "Ticker" in portfolio_df.columns:
        largest_position = portfolio_df.sort_values(
            by="Allocation %",
            ascending=False,
        ).iloc[0]

        largest_ticker = str(largest_position["Ticker"])
        largest_allocation = float(largest_position["Allocation %"])

        if largest_allocation >= 50:
            score += 35
            reasons.append(
                f"{largest_ticker} is highly concentrated at {largest_allocation:.2f}%."
            )
        elif largest_allocation >= 25:
            score += 20
            reasons.append(
                f"{largest_ticker} is moderately concentrated at {largest_allocation:.2f}%."
            )

    try:
        sector_df = build_sector_exposure_dataframe(portfolio_df)
    except Exception:
        sector_df = pd.DataFrame()

    if sector_df is not None and not sector_df.empty:
        if "Sector" in sector_df.columns and "Exposure %" in sector_df.columns:
            largest_sector = sector_df.sort_values(
                by="Exposure %",
                ascending=False,
            ).iloc[0]

            sector = str(largest_sector["Sector"])
            exposure_pct = float(largest_sector["Exposure %"])

            if exposure_pct >= 50:
                score += 30
                reasons.append(
                    f"{sector} sector exposure is high at {exposure_pct:.2f}%."
                )
            elif exposure_pct >= 35:
                score += 15
                reasons.append(
                    f"{sector} sector exposure is elevated at {exposure_pct:.2f}%."
                )

    if "Price Status" in portfolio_df.columns:
        missing_price_count = int(
            (portfolio_df["Price Status"] == "Missing").sum()
        )

        if missing_price_count > 0:
            score += min(20, missing_price_count * 5)
            reasons.append(
                f"{missing_price_count} position(s) have missing price data."
            )

    if "Gain/Loss" in portfolio_df.columns:
        total_gain_loss = float(portfolio_df["Gain/Loss"].sum())

        if total_gain_loss < 0:
            score += 15
            reasons.append(
                f"Portfolio unrealized gain/loss is negative by ${total_gain_loss:,.2f}."
            )

    score = min(score, 100)

    if score >= 75:
        risk_level = "High Risk"
    elif score >= 50:
        risk_level = "Elevated Risk"
    elif score >= 25:
        risk_level = "Moderate Risk"
    else:
        risk_level = "Low Risk"

    st.subheader("Portfolio Risk Score")

    col1, col2 = st.columns(2)

    col1.metric("Risk Score", f"{score}/100")
    col2.metric("Risk Level", risk_level)

    if reasons:
        with st.expander("Risk score drivers", expanded=False):
            for reason in reasons:
                st.warning(reason)
    else:
        st.success("No major risk score drivers detected.")


def render_portfolio_risk_recommendations(portfolio_df: pd.DataFrame) -> None:
    """Render action recommendations based on portfolio risk conditions."""
    if portfolio_df is None or portfolio_df.empty:
        return

    recommendations = []

    if "Allocation %" in portfolio_df.columns and "Ticker" in portfolio_df.columns:
        largest_position = portfolio_df.sort_values(
            by="Allocation %",
            ascending=False,
        ).iloc[0]

        ticker = str(largest_position["Ticker"])
        allocation_pct = float(largest_position["Allocation %"])

        if allocation_pct >= 50:
            recommendations.append(
                f"Review concentration risk in {ticker}. It represents "
                f"{allocation_pct:.2f}% of the portfolio. Consider reducing "
                "position size or adding other holdings."
            )
        elif allocation_pct >= 25:
            recommendations.append(
                f"Monitor {ticker}. It represents {allocation_pct:.2f}% of "
                "the portfolio and may become a concentration risk."
            )

    try:
        sector_df = build_sector_exposure_dataframe(portfolio_df)
    except Exception:
        sector_df = pd.DataFrame()

    if sector_df is not None and not sector_df.empty:
        if "Sector" in sector_df.columns and "Exposure %" in sector_df.columns:
            largest_sector = sector_df.sort_values(
                by="Exposure %",
                ascending=False,
            ).iloc[0]

            sector = str(largest_sector["Sector"])
            exposure_pct = float(largest_sector["Exposure %"])

            if exposure_pct >= 50:
                recommendations.append(
                    f"Review sector exposure. {sector} represents "
                    f"{exposure_pct:.2f}% of the portfolio. Consider adding "
                    "holdings from other sectors."
                )
            elif exposure_pct >= 35:
                recommendations.append(
                    f"Monitor {sector} exposure. It represents "
                    f"{exposure_pct:.2f}% of the portfolio."
                )

    if "Price Status" in portfolio_df.columns:
        missing_price_count = int(
            (portfolio_df["Price Status"] == "Missing").sum()
        )

        if missing_price_count > 0:
            recommendations.append(
                f"Fix missing price data for {missing_price_count} position(s). "
                "Use the sidebar refresh control or verify ticker symbols."
            )

    if "Gain/Loss" in portfolio_df.columns:
        total_gain_loss = float(portfolio_df["Gain/Loss"].sum())

        if total_gain_loss < 0:
            recommendations.append(
                "Review losing positions. Compare current losses against your "
                "original investment thesis before adding more capital."
            )

    st.subheader("Risk Action Recommendations")

    if not recommendations:
        st.success(
            "No urgent risk actions detected. Continue monitoring the portfolio "
            "and saving snapshots over time."
        )
        return

    for recommendation in recommendations:
        st.info(recommendation)


def render_portfolio_risk_score_history_chart(snapshots) -> None:
    """Render portfolio risk score history chart."""
    st.subheader("Portfolio Risk Score History")

    if not snapshots:
        st.info(
            "No risk score history available yet. Save portfolio snapshots "
            "after risk scoring is enabled."
        )
        return

    snapshot_rows = []

    for snapshot in snapshots:
        risk_score = getattr(snapshot, "risk_score", None)

        if risk_score is None:
            continue

        snapshot_rows.append(
            {
                "Snapshot Date": snapshot.snapshot_date,
                "Risk Score": float(risk_score),
                "Risk Level": getattr(snapshot, "risk_level", None),
            }
        )

    risk_df = pd.DataFrame(snapshot_rows)

    if risk_df.empty:
        st.info(
            "Portfolio Risk Score History is active, but no saved snapshots "
            "currently contain risk scores. Save a new portfolio snapshot to "
            "start risk score history tracking."
        )
        return

    risk_df["Snapshot Date"] = pd.to_datetime(risk_df["Snapshot Date"])

    risk_df = risk_df.sort_values(
        by="Snapshot Date",
        ascending=True,
    )

    st.line_chart(
        risk_df,
        x="Snapshot Date",
        y="Risk Score",
    )

    latest_risk = risk_df.iloc[-1]
    latest_level = latest_risk.get("Risk Level")

    st.caption(
        f"Latest saved risk score: {latest_risk['Risk Score']:.0f}/100"
        + (f" — {latest_level}" if latest_level else "")
    )



def render_portfolio_executive_summary(portfolio_df: pd.DataFrame) -> None:
    """Render a plain-English executive summary for the portfolio."""
    st.subheader("Portfolio Executive Summary")

    if portfolio_df is None or portfolio_df.empty:
        st.info(
            "No portfolio positions found. Add positions from the sidebar to "
            "generate an executive summary."
        )
        return

    total_cost_basis = float(portfolio_df["Cost Basis"].sum())
    total_current_value = float(portfolio_df["Current Value"].sum())
    total_gain_loss = float(portfolio_df["Gain/Loss"].sum())

    if total_cost_basis > 0:
        total_gain_loss_pct = (total_gain_loss / total_cost_basis) * 100
    else:
        total_gain_loss_pct = 0.0

    risk_score, risk_level, risk_notes = calculate_portfolio_risk_score(
        portfolio_df
    )

    main_risk_driver = risk_notes[0] if risk_notes else "No major risk triggers detected."

    if risk_score >= 75:
        recommended_action = (
            "Review concentration and risk exposure before adding more capital."
        )
    elif risk_score >= 50:
        recommended_action = (
            "Monitor high-impact positions and consider gradual diversification."
        )
    elif risk_score >= 25:
        recommended_action = (
            "Continue monitoring risk drivers and save snapshots regularly."
        )
    else:
        recommended_action = (
            "Portfolio risk appears low. Continue tracking performance over time."
        )

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Portfolio Value",
        f"${total_current_value:,.2f}",
    )

    col2.metric(
        "Total Gain/Loss",
        f"${total_gain_loss:,.2f}",
        f"{total_gain_loss_pct:.2f}%",
    )

    col3.metric(
        "Current Risk Level",
        risk_level,
        f"{risk_score}/100",
    )

    st.markdown(
        f"""
        **Summary:** Portfolio current value is **\\${total_current_value:,.2f}** with
        total unrealized gain/loss of **\\${total_gain_loss:,.2f}**
        (**{total_gain_loss_pct:.2f}%**).

        **Main risk driver:** {main_risk_driver}

        **Recommended next action:** {recommended_action}
        """
    )


def render_latest_snapshot_status_panel(
    portfolio_df: pd.DataFrame,
    snapshots,
) -> None:
    """Render status comparing current portfolio state to latest snapshot."""
    st.subheader("Latest Snapshot Status")

    if portfolio_df is None or portfolio_df.empty:
        st.info("No portfolio positions available for snapshot status.")
        return

    if not snapshots:
        st.info(
            "No portfolio snapshots saved yet. Use Save Portfolio Snapshot "
            "in the sidebar to record the current portfolio state."
        )
        return

    current_cost_basis = float(portfolio_df["Cost Basis"].sum())
    current_value = float(portfolio_df["Current Value"].sum())
    current_gain_loss = float(portfolio_df["Gain/Loss"].sum())

    if current_cost_basis > 0:
        current_gain_loss_pct = (current_gain_loss / current_cost_basis) * 100
    else:
        current_gain_loss_pct = 0.0

    current_risk_score, current_risk_level, _ = calculate_portfolio_risk_score(
        portfolio_df
    )

    latest_snapshot = sorted(
        snapshots,
        key=lambda snapshot: snapshot.snapshot_date,
        reverse=True,
    )[0]

    latest_value = float(latest_snapshot.total_current_value)
    latest_gain_loss = float(latest_snapshot.total_gain_loss)
    latest_risk_score = getattr(latest_snapshot, "risk_score", None)
    latest_risk_level = getattr(latest_snapshot, "risk_level", None) or "No Data"

    value_delta = current_value - latest_value
    gain_loss_delta = current_gain_loss - latest_gain_loss

    if latest_risk_score is None:
        risk_delta_text = "No saved risk score"
    else:
        risk_delta = current_risk_score - float(latest_risk_score)
        risk_delta_text = f"{risk_delta:+.0f} points"

    value_is_close = abs(value_delta) < 0.01
    gain_loss_is_close = abs(gain_loss_delta) < 0.01

    if latest_risk_score is None:
        risk_is_close = False
    else:
        risk_is_close = abs(current_risk_score - float(latest_risk_score)) < 0.01

    if value_is_close and gain_loss_is_close and risk_is_close:
        status_message = "Current portfolio appears to match the latest saved snapshot."
        status_type = "success"
    else:
        status_message = (
            "Current portfolio may differ from the latest saved snapshot. "
            "Save a new snapshot if you want to record the current state."
        )
        status_type = "warning"

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Latest Snapshot Value",
        f"${latest_value:,.2f}",
        f"{value_delta:+,.2f} current delta",
    )

    col2.metric(
        "Latest Snapshot Gain/Loss",
        f"${latest_gain_loss:,.2f}",
        f"{gain_loss_delta:+,.2f} current delta",
    )

    col3.metric(
        "Latest Snapshot Risk",
        latest_risk_level,
        risk_delta_text,
    )

    st.caption(
        f"Latest snapshot date: {latest_snapshot.snapshot_date.strftime('%Y-%m-%d %H:%M:%S')}"
    )

    st.caption(
        f"Current value: ${current_value:,.2f} | "
        f"Current gain/loss: ${current_gain_loss:,.2f} "
        f"({current_gain_loss_pct:.2f}%) | "
        f"Current risk: {current_risk_level} ({current_risk_score}/100)"
    )

    if status_type == "success":
        st.success(status_message)
    else:
        st.warning(status_message)

    decision_summary = build_snapshot_decision_summary(
        value_delta=value_delta,
        gain_loss_delta=gain_loss_delta,
        current_risk_score=current_risk_score,
        latest_risk_score=latest_risk_score,
    )

    st.subheader("Snapshot Decision Summary")
    st.info(decision_summary)


def build_snapshot_decision_summary(
    value_delta: float,
    gain_loss_delta: float,
    current_risk_score: int,
    latest_risk_score,
) -> str:
    """Build plain-English decision summary for latest snapshot comparison."""
    value_changed = abs(value_delta) >= 0.01
    gain_loss_changed = abs(gain_loss_delta) >= 0.01

    if latest_risk_score is None:
        risk_changed = True
        risk_message = (
            "The latest snapshot does not have a saved risk score, so the "
            "current risk score should be saved for better tracking."
        )
    else:
        risk_delta = current_risk_score - float(latest_risk_score)

        if risk_delta > 0:
            risk_changed = True
            risk_message = (
                f"Risk score increased by {risk_delta:.0f} point(s) since "
                "the latest snapshot."
            )
        elif risk_delta < 0:
            risk_changed = True
            risk_message = (
                f"Risk score decreased by {abs(risk_delta):.0f} point(s) since "
                "the latest snapshot."
            )
        else:
            risk_changed = False
            risk_message = "Risk score is unchanged since the latest snapshot."

    if value_delta > 0:
        value_message = f"Portfolio value increased by ${value_delta:,.2f}."
    elif value_delta < 0:
        value_message = f"Portfolio value decreased by ${abs(value_delta):,.2f}."
    else:
        value_message = "Portfolio value is unchanged."

    if gain_loss_delta > 0:
        gain_loss_message = (
            f"Unrealized gain/loss improved by ${gain_loss_delta:,.2f}."
        )
    elif gain_loss_delta < 0:
        gain_loss_message = (
            f"Unrealized gain/loss declined by ${abs(gain_loss_delta):,.2f}."
        )
    else:
        gain_loss_message = "Unrealized gain/loss is unchanged."

    if value_changed or gain_loss_changed or risk_changed:
        action_message = (
            "Recommended action: save a new snapshot to record the current "
            "portfolio state."
        )
    else:
        action_message = (
            "Recommended action: no new snapshot is needed unless you want "
            "another timestamped record."
        )

    return (
        f"{value_message} {gain_loss_message} {risk_message} "
        f"{action_message}"
    )


def render_portfolio_report_summary(
    portfolio_df: pd.DataFrame,
    snapshots,
) -> None:
    """Render a copy-ready plain-English portfolio report summary."""
    st.subheader("Portfolio Report Summary")

    if portfolio_df is None or portfolio_df.empty:
        st.info(
            "No portfolio positions available. Add positions from the sidebar "
            "to generate a report summary."
        )
        return

    total_cost_basis = float(portfolio_df["Cost Basis"].sum())
    total_current_value = float(portfolio_df["Current Value"].sum())
    total_gain_loss = float(portfolio_df["Gain/Loss"].sum())

    if total_cost_basis > 0:
        total_gain_loss_pct = (total_gain_loss / total_cost_basis) * 100
    else:
        total_gain_loss_pct = 0.0

    risk_score, risk_level, risk_notes = calculate_portfolio_risk_score(
        portfolio_df
    )

    main_risk_driver = (
        risk_notes[0]
        if risk_notes
        else "No major risk triggers detected."
    )

    if risk_score >= 75:
        recommended_action = (
            "Review concentration and risk exposure before adding more capital."
        )
    elif risk_score >= 50:
        recommended_action = (
            "Monitor high-impact positions and consider gradual diversification."
        )
    elif risk_score >= 25:
        recommended_action = (
            "Continue monitoring risk drivers and save snapshots regularly."
        )
    else:
        recommended_action = (
            "Portfolio risk appears low. Continue tracking performance over time."
        )

    if snapshots:
        latest_snapshot = sorted(
            snapshots,
            key=lambda snapshot: snapshot.snapshot_date,
            reverse=True,
        )[0]

        latest_snapshot_text = (
            f"Latest saved snapshot was recorded on "
            f"{latest_snapshot.snapshot_date.strftime('%Y-%m-%d %H:%M:%S')}."
        )
    else:
        latest_snapshot_text = (
            "No saved portfolio snapshot exists yet."
        )

    report_generated_at = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
    report_filename_timestamp = pd.Timestamp.now().strftime("%Y-%m-%d_%H%M")

    report_summary = f"""Portfolio Report Summary

Report generated at: {report_generated_at}
Sprint version: {REPORT_SPRINT_VERSION}
Report type: TXT portfolio report summary

Portfolio value: ${total_current_value:,.2f}
Total unrealized gain/loss: ${total_gain_loss:,.2f} ({total_gain_loss_pct:.2f}%)
Current risk level: {risk_level} ({risk_score}/100)
Main risk driver: {main_risk_driver}
Recommended next action: {recommended_action}
Latest snapshot status: {latest_snapshot_text}
"""

    st.text_area(
        "Copy-ready portfolio report",
        value=report_summary,
        height=220,
        key="copy_ready_portfolio_report_summary",
    )

    st.download_button(
        label="Download Portfolio Report Summary TXT",
        data=report_summary.encode("utf-8"),
        file_name=f"portfolio_report_summary_{report_filename_timestamp}.txt",
        mime="text/plain",
        key="download_portfolio_report_summary_txt",
    )

    latest_snapshot_date = ""
    latest_snapshot_value = ""
    latest_snapshot_risk_score = ""
    latest_snapshot_risk_level = ""

    if snapshots:
        latest_snapshot_date = latest_snapshot.snapshot_date.strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        latest_snapshot_value = float(latest_snapshot.total_current_value)
        latest_snapshot_risk_score = getattr(latest_snapshot, "risk_score", "")
        latest_snapshot_risk_level = getattr(latest_snapshot, "risk_level", "")

    report_export_df = pd.DataFrame(
        [
            {
                "Report Generated At": report_generated_at,
                "Sprint Version": REPORT_SPRINT_VERSION,
                "Report Feature": REPORT_FEATURE_LABEL,
                "Report Type": "CSV portfolio report summary",
                "Portfolio Value": total_current_value,
                "Total Cost Basis": total_cost_basis,
                "Total Gain/Loss": total_gain_loss,
                "Total Gain/Loss %": total_gain_loss_pct,
                "Risk Score": risk_score,
                "Risk Level": risk_level,
                "Main Risk Driver": main_risk_driver,
                "Recommended Action": recommended_action,
                "Latest Snapshot Date": latest_snapshot_date,
                "Latest Snapshot Value": latest_snapshot_value,
                "Latest Snapshot Risk Score": latest_snapshot_risk_score,
                "Latest Snapshot Risk Level": latest_snapshot_risk_level,
            }
        ]
    )

    report_csv_data = report_export_df.to_csv(index=False).encode("utf-8-sig")

    st.download_button(
        label="Download Portfolio Report Summary CSV",
        data=report_csv_data,
        file_name=f"portfolio_report_summary_{report_filename_timestamp}.csv",
        mime="text/csv",
        key="download_portfolio_report_summary_csv",
    )

    st.caption(
        "The TXT file is best for notes or written updates. The CSV file is "
        "best for Excel, Google Sheets, dashboards, and structured reporting."
    )


def render_portfolio_what_if_scenario(portfolio_df: pd.DataFrame) -> None:
    """Render portfolio what-if scenario planner without changing saved data."""
    st.subheader("Portfolio What-If Scenario Planner")

    if portfolio_df is None or portfolio_df.empty:
        st.info(
            "No portfolio positions available. Add positions before running "
            "what-if scenarios."
        )
        return

    required_columns = [
        "Ticker",
        "Shares",
        "Buy Price",
        "Current Price",
        "Cost Basis",
        "Current Value",
        "Gain/Loss",
        "Allocation %",
    ]

    missing_columns = [
        column for column in required_columns
        if column not in portfolio_df.columns
    ]

    if missing_columns:
        st.warning(
            "What-if scenario planner unavailable. Missing columns: "
            + ", ".join(missing_columns)
        )
        return

    if st.button(
        "Reset Scenario Inputs",
        key="reset_portfolio_scenario_inputs_button",
    ):
        reset_portfolio_scenario_inputs()

    if "pending_scenario_action" in st.session_state:
        st.session_state["scenario_action_select"] = st.session_state.pop(
            "pending_scenario_action"
        )

    if "pending_scenario_price" in st.session_state:
        st.session_state["scenario_price_input"] = st.session_state.pop(
            "pending_scenario_price"
        )

    scenario_ticker = st.selectbox(
        "Scenario ticker",
        options=portfolio_df["Ticker"].astype(str).tolist(),
        key="scenario_ticker_select",
    )

    scenario_action = st.selectbox(
        "Scenario action",
        options=[
            "Add shares",
            "Reduce shares",
            "Change price",
        ],
        key="scenario_action_select",
    )

    selected_position = portfolio_df[
        portfolio_df["Ticker"].astype(str) == scenario_ticker
    ].iloc[0]

    current_shares = float(selected_position["Shares"])
    current_price = float(selected_position["Current Price"])
    buy_price = float(selected_position["Buy Price"])

    st.caption("Scenario Price Presets")

    preset_col1, preset_col2, preset_col3, preset_col4 = st.columns(4)

    if preset_col1.button("Price -10%", key="scenario_price_minus_10"):
        apply_scenario_price_preset(current_price, -0.10)

    if preset_col2.button("Price +10%", key="scenario_price_plus_10"):
        apply_scenario_price_preset(current_price, 0.10)

    if preset_col3.button("Price -25%", key="scenario_price_minus_25"):
        apply_scenario_price_preset(current_price, -0.25)

    if preset_col4.button("Price +25%", key="scenario_price_plus_25"):
        apply_scenario_price_preset(current_price, 0.25)

    scenario_shares_delta = 0.0
    scenario_price = current_price

    if scenario_action == "Add shares":
        scenario_shares_delta = st.number_input(
            "Shares to add",
            min_value=0.0,
            value=1.0,
            step=1.0,
            key="scenario_add_shares_input",
        )
    elif scenario_action == "Reduce shares":
        scenario_shares_delta = -st.number_input(
            "Shares to reduce",
            min_value=0.0,
            max_value=current_shares,
            value=min(1.0, current_shares),
            step=1.0,
            key="scenario_reduce_shares_input",
        )
    else:
        scenario_price = st.number_input(
            "Scenario current price",
            min_value=0.0,
            value=current_price,
            step=1.0,
            key="scenario_price_input",
        )

    scenario_df = portfolio_df.copy()

    ticker_mask = scenario_df["Ticker"].astype(str) == scenario_ticker

    scenario_df.loc[ticker_mask, "Shares"] = (
        scenario_df.loc[ticker_mask, "Shares"].astype(float)
        + scenario_shares_delta
    )

    scenario_df.loc[ticker_mask, "Shares"] = scenario_df.loc[
        ticker_mask,
        "Shares",
    ].clip(lower=0)

    scenario_df.loc[ticker_mask, "Current Price"] = scenario_price

    scenario_df.loc[ticker_mask, "Cost Basis"] = (
        scenario_df.loc[ticker_mask, "Shares"].astype(float) * buy_price
    )

    scenario_df.loc[ticker_mask, "Current Value"] = (
        scenario_df.loc[ticker_mask, "Shares"].astype(float) * scenario_price
    )

    scenario_df.loc[ticker_mask, "Gain/Loss"] = (
        scenario_df.loc[ticker_mask, "Current Value"].astype(float)
        - scenario_df.loc[ticker_mask, "Cost Basis"].astype(float)
    )

    total_scenario_value = float(scenario_df["Current Value"].sum())

    if total_scenario_value > 0:
        scenario_df["Allocation %"] = (
            scenario_df["Current Value"].astype(float) / total_scenario_value
        ) * 100
    else:
        scenario_df["Allocation %"] = 0.0

    current_total_value = float(portfolio_df["Current Value"].sum())
    current_total_gain_loss = float(portfolio_df["Gain/Loss"].sum())

    scenario_total_value = float(scenario_df["Current Value"].sum())
    scenario_total_gain_loss = float(scenario_df["Gain/Loss"].sum())

    current_risk_score, current_risk_level, _ = calculate_portfolio_risk_score(
        portfolio_df
    )

    scenario_risk_score, scenario_risk_level, scenario_risk_notes = (
        calculate_portfolio_risk_score(scenario_df)
    )

    value_delta = scenario_total_value - current_total_value
    gain_loss_delta = scenario_total_gain_loss - current_total_gain_loss
    risk_delta = scenario_risk_score - current_risk_score

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Scenario Portfolio Value",
        f"${scenario_total_value:,.2f}",
        f"{value_delta:+,.2f}",
    )

    col2.metric(
        "Scenario Gain/Loss",
        f"${scenario_total_gain_loss:,.2f}",
        f"{gain_loss_delta:+,.2f}",
    )

    col3.metric(
        "Scenario Risk Level",
        scenario_risk_level,
        f"{risk_delta:+.0f} points",
    )

    scenario_comparison_summary, scenario_decision = (
        build_scenario_comparison_summary(
            value_delta=value_delta,
            gain_loss_delta=gain_loss_delta,
            risk_delta=risk_delta,
        )
    )

    st.subheader("Scenario Comparison Summary")
    st.info(scenario_comparison_summary)
    st.caption(f"Scenario decision label: {scenario_decision}")

    current_selected_position = portfolio_df[
        portfolio_df["Ticker"].astype(str) == scenario_ticker
    ].iloc[0]

    scenario_selected_position = scenario_df[
        scenario_df["Ticker"].astype(str) == scenario_ticker
    ].iloc[0]

    comparison_rows = [
        {
            "Metric": "Portfolio Value",
            "Current": current_total_value,
            "Scenario": scenario_total_value,
            "Change": value_delta,
        },
        {
            "Metric": "Total Gain/Loss",
            "Current": current_total_gain_loss,
            "Scenario": scenario_total_gain_loss,
            "Change": gain_loss_delta,
        },
        {
            "Metric": "Risk Score",
            "Current": current_risk_score,
            "Scenario": scenario_risk_score,
            "Change": risk_delta,
        },
        {
            "Metric": "Risk Level",
            "Current": current_risk_level,
            "Scenario": scenario_risk_level,
            "Change": scenario_decision,
        },
        {
            "Metric": f"{scenario_ticker} Shares",
            "Current": float(current_selected_position["Shares"]),
            "Scenario": float(scenario_selected_position["Shares"]),
            "Change": (
                float(scenario_selected_position["Shares"])
                - float(current_selected_position["Shares"])
            ),
        },
        {
            "Metric": f"{scenario_ticker} Current Price",
            "Current": float(current_selected_position["Current Price"]),
            "Scenario": float(scenario_selected_position["Current Price"]),
            "Change": (
                float(scenario_selected_position["Current Price"])
                - float(current_selected_position["Current Price"])
            ),
        },
        {
            "Metric": f"{scenario_ticker} Current Value",
            "Current": float(current_selected_position["Current Value"]),
            "Scenario": float(scenario_selected_position["Current Value"]),
            "Change": (
                float(scenario_selected_position["Current Value"])
                - float(current_selected_position["Current Value"])
            ),
        },
        {
            "Metric": f"{scenario_ticker} Allocation %",
            "Current": float(current_selected_position["Allocation %"]),
            "Scenario": float(scenario_selected_position["Allocation %"]),
            "Change": (
                float(scenario_selected_position["Allocation %"])
                - float(current_selected_position["Allocation %"])
            ),
        },
    ]

    scenario_comparison_df = pd.DataFrame(comparison_rows)

    st.subheader("Scenario Baseline Comparison")
    st.dataframe(
        scenario_comparison_df,
        use_container_width=True,
        hide_index=True,
    )

    scenario_threshold_warnings = build_scenario_risk_threshold_warnings(
        scenario_df=scenario_df,
        current_risk_score=current_risk_score,
        scenario_risk_score=scenario_risk_score,
        scenario_risk_level=scenario_risk_level,
    )

    st.subheader("Scenario Risk Threshold Warning")

    if scenario_threshold_warnings:
        for warning in scenario_threshold_warnings:
            st.error(warning)
    else:
        st.success("No major scenario risk thresholds were triggered.")

    scenario_user_notes = st.session_state.get(
        "scenario_user_notes_text_area",
        "",
    )

    scenario_generated_at = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
    scenario_filename_timestamp = pd.Timestamp.now().strftime("%Y-%m-%d_%H%M")

    save_col1, save_col2 = st.columns(2)

    if save_col1.button(
        "Save Scenario to Session History",
        key="save_scenario_to_history_button",
    ):
        save_scenario_to_session_history(
            scenario_generated_at=scenario_generated_at,
            scenario_ticker=scenario_ticker,
            scenario_action=scenario_action,
            scenario_total_value=scenario_total_value,
            value_delta=value_delta,
            scenario_total_gain_loss=scenario_total_gain_loss,
            gain_loss_delta=gain_loss_delta,
            scenario_risk_score=scenario_risk_score,
            scenario_risk_level=scenario_risk_level,
            scenario_decision=scenario_decision,
            scenario_user_notes=scenario_user_notes,
        )
        st.success("Scenario saved to this session's history.")

    if save_col2.button(
        "Save Scenario to Database",
        key="save_scenario_to_database_button",
    ):
        saved_to_database = save_portfolio_scenario(
            ticker=scenario_ticker,
            action=scenario_action,
            scenario_portfolio_value=scenario_total_value,
            value_delta=value_delta,
            scenario_gain_loss=scenario_total_gain_loss,
            gain_loss_delta=gain_loss_delta,
            scenario_risk_score=scenario_risk_score,
            scenario_risk_level=scenario_risk_level,
            scenario_decision=scenario_decision,
            scenario_notes=(
                scenario_user_notes.strip()
                if scenario_user_notes.strip()
                else "No user notes entered."
            ),
        )

        if saved_to_database:
            st.success("Scenario saved to database.")
        else:
            st.error("Scenario could not be saved to database.")

    render_scenario_session_history()

    with st.expander("Database Scenario History", expanded=False):
        render_database_scenario_history()

    with st.expander("Scenario risk drivers", expanded=False):
        for note in scenario_risk_notes:
            st.info(note)

    with st.expander("Scenario position table", expanded=False):
        st.dataframe(
            scenario_df,
            use_container_width=True,
            hide_index=True,
        )

    scenario_generated_at = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
    scenario_filename_timestamp = pd.Timestamp.now().strftime("%Y-%m-%d_%H%M")

    scenario_summary = f"""Portfolio What-If Scenario Summary

Scenario generated at: {scenario_generated_at}
Scenario ticker: {scenario_ticker}
Scenario action: {scenario_action}

Current portfolio value: ${current_total_value:,.2f}
Scenario portfolio value: ${scenario_total_value:,.2f}
Value change: ${value_delta:,.2f}

Current gain/loss: ${current_total_gain_loss:,.2f}
Scenario gain/loss: ${scenario_total_gain_loss:,.2f}
Gain/loss change: ${gain_loss_delta:,.2f}

Current risk level: {current_risk_level} ({current_risk_score}/100)
Scenario risk level: {scenario_risk_level} ({scenario_risk_score}/100)
Risk score change: {risk_delta:+.0f} point(s)
Scenario decision: {scenario_decision}
Scenario comparison summary: {scenario_comparison_summary}

Scenario threshold warnings:
{chr(10).join(f"- {warning}" for warning in scenario_threshold_warnings) if scenario_threshold_warnings else "- No major scenario risk thresholds were triggered."}

Scenario risk drivers:
{chr(10).join(f"- {note}" for note in scenario_risk_notes)}
"""

    scenario_export_df = scenario_df.copy()
    scenario_export_df.insert(0, "Scenario Generated At", scenario_generated_at)
    scenario_export_df.insert(1, "Scenario Ticker", scenario_ticker)
    scenario_export_df.insert(2, "Scenario Action", scenario_action)
    scenario_export_df.insert(3, "Scenario Risk Score", scenario_risk_score)
    scenario_export_df.insert(4, "Scenario Risk Level", scenario_risk_level)
    scenario_export_df.insert(5, "Scenario Decision", scenario_decision)
    scenario_export_df.insert(6, "Scenario Comparison Summary", scenario_comparison_summary)
    scenario_export_df.insert(
        7,
        "Scenario Threshold Warnings",
        "; ".join(scenario_threshold_warnings)
        if scenario_threshold_warnings
        else "No major scenario risk thresholds were triggered.",
    )

    scenario_csv_data = scenario_export_df.to_csv(index=False).encode("utf-8-sig")

    st.download_button(
        label="Download Scenario Summary TXT",
        data=scenario_summary.encode("utf-8"),
        file_name=f"portfolio_scenario_summary_{scenario_filename_timestamp}.txt",
        mime="text/plain",
        key="download_scenario_summary_txt",
    )

    st.download_button(
        label="Download Scenario Data CSV",
        data=scenario_csv_data,
        file_name=f"portfolio_scenario_data_{scenario_filename_timestamp}.csv",
        mime="text/csv",
        key="download_scenario_data_csv",
    )

    scenario_comparison_csv = scenario_comparison_df.to_csv(
        index=False
    ).encode("utf-8-sig")

    st.download_button(
        label="Download Scenario Comparison CSV",
        data=scenario_comparison_csv,
        file_name=f"portfolio_scenario_comparison_{scenario_filename_timestamp}.csv",
        mime="text/csv",
        key="download_scenario_comparison_csv",
    )

    st.caption(
        "This scenario is temporary and does not change saved portfolio "
        "positions or snapshots. TXT is best for notes. CSV is best for "
        "Excel, Google Sheets, and scenario comparison."
    )


def build_scenario_comparison_summary(
    value_delta: float,
    gain_loss_delta: float,
    risk_delta: int | float,
) -> tuple[str, str]:
    """Build plain-English scenario comparison summary and decision label."""
    if value_delta > 0:
        value_message = f"This scenario increases portfolio value by ${value_delta:,.2f}."
    elif value_delta < 0:
        value_message = f"This scenario decreases portfolio value by ${abs(value_delta):,.2f}."
    else:
        value_message = "This scenario leaves portfolio value unchanged."

    if gain_loss_delta > 0:
        gain_loss_message = (
            f"This scenario improves unrealized gain/loss by ${gain_loss_delta:,.2f}."
        )
    elif gain_loss_delta < 0:
        gain_loss_message = (
            f"This scenario weakens unrealized gain/loss by ${abs(gain_loss_delta):,.2f}."
        )
    else:
        gain_loss_message = "This scenario leaves unrealized gain/loss unchanged."

    if risk_delta > 0:
        risk_message = f"This scenario raises risk score by {risk_delta:.0f} point(s)."
    elif risk_delta < 0:
        risk_message = f"This scenario reduces risk score by {abs(risk_delta):.0f} point(s)."
    else:
        risk_message = "This scenario leaves risk score unchanged."

    if risk_delta >= 15:
        decision = "Risky scenario"
        decision_message = (
            "Decision: risky scenario. Review concentration, sector exposure, "
            "or missing price data before acting."
        )
    elif value_delta > 0 and gain_loss_delta >= 0 and risk_delta <= 0:
        decision = "Favorable scenario"
        decision_message = (
            "Decision: favorable scenario. Value improves without increasing "
            "the risk score."
        )
    elif value_delta < 0 and gain_loss_delta < 0:
        decision = "Unfavorable scenario"
        decision_message = (
            "Decision: unfavorable scenario. Value and gain/loss both decline."
        )
    else:
        decision = "Neutral scenario"
        decision_message = (
            "Decision: neutral scenario. Review the trade-off between value, "
            "gain/loss, and risk before acting."
        )

    summary = (
        f"{value_message} {gain_loss_message} {risk_message} "
        f"{decision_message}"
    )

    return summary, decision


def build_scenario_risk_threshold_warnings(
    scenario_df: pd.DataFrame,
    current_risk_score: int | float,
    scenario_risk_score: int | float,
    scenario_risk_level: str,
) -> list[str]:
    """Build threshold warnings for risky what-if scenarios."""
    warnings = []

    risk_delta = float(scenario_risk_score) - float(current_risk_score)

    if risk_delta >= 15:
        warnings.append(
            f"Risk score increases by {risk_delta:.0f} point(s), which is a major risk jump."
        )

    if scenario_risk_level == "High Risk":
        warnings.append(
            "Scenario risk level becomes High Risk."
        )

    if "Allocation %" in scenario_df.columns and "Ticker" in scenario_df.columns:
        largest_position = scenario_df.sort_values(
            by="Allocation %",
            ascending=False,
        ).iloc[0]

        ticker = str(largest_position["Ticker"])
        allocation_pct = float(largest_position["Allocation %"])

        if allocation_pct >= 50:
            warnings.append(
                f"Largest position warning: {ticker} becomes {allocation_pct:.2f}% of the portfolio."
            )

    try:
        sector_df = build_sector_exposure_dataframe(scenario_df)
    except Exception:
        sector_df = pd.DataFrame()

    if sector_df is not None and not sector_df.empty:
        if "Sector" in sector_df.columns and "Exposure %" in sector_df.columns:
            largest_sector = sector_df.sort_values(
                by="Exposure %",
                ascending=False,
            ).iloc[0]

            sector = str(largest_sector["Sector"])
            exposure_pct = float(largest_sector["Exposure %"])

            if exposure_pct >= 50:
                warnings.append(
                    f"Sector exposure warning: {sector} becomes {exposure_pct:.2f}% of the portfolio."
                )

    if "Price Status" in scenario_df.columns:
        missing_price_count = int(
            (scenario_df["Price Status"] == "Missing").sum()
        )

        if missing_price_count > 0:
            warnings.append(
                f"{missing_price_count} scenario position(s) have missing price data."
            )

    return warnings


def reset_portfolio_scenario_inputs() -> None:
    """Reset what-if scenario planner widget state."""
    scenario_keys = [
        "scenario_ticker_select",
        "scenario_action_select",
        "scenario_add_shares_input",
        "scenario_reduce_shares_input",
        "scenario_price_input",
        "pending_scenario_action",
        "pending_scenario_price",
    ]

    for key in scenario_keys:
        if key in st.session_state:
            del st.session_state[key]

    st.rerun()


def apply_scenario_price_preset(current_price: float, percent_change: float) -> None:
    """Store a pending scenario price preset and rerun safely."""
    scenario_price = current_price * (1 + percent_change)

    if scenario_price < 0:
        scenario_price = 0.0

    st.session_state["pending_scenario_action"] = "Change price"
    st.session_state["pending_scenario_price"] = float(scenario_price)

    st.rerun()


def save_scenario_to_session_history(
    scenario_generated_at: str,
    scenario_ticker: str,
    scenario_action: str,
    scenario_total_value: float,
    value_delta: float,
    scenario_total_gain_loss: float,
    gain_loss_delta: float,
    scenario_risk_score: int | float,
    scenario_risk_level: str,
    scenario_decision: str,
    scenario_user_notes: str,
) -> None:
    """Save a what-if scenario record to session-state history."""
    if "portfolio_scenario_history" not in st.session_state:
        st.session_state["portfolio_scenario_history"] = []

    st.session_state["portfolio_scenario_history"].append(
        {
            "Scenario Generated At": scenario_generated_at,
            "Ticker": scenario_ticker,
            "Action": scenario_action,
            "Scenario Portfolio Value": float(scenario_total_value),
            "Value Delta": float(value_delta),
            "Scenario Gain/Loss": float(scenario_total_gain_loss),
            "Gain/Loss Delta": float(gain_loss_delta),
            "Scenario Risk Score": float(scenario_risk_score),
            "Scenario Risk Level": scenario_risk_level,
            "Scenario Decision": scenario_decision,
            "Scenario Notes": (
                scenario_user_notes.strip()
                if scenario_user_notes.strip()
                else "No user notes entered."
            ),
        }
    )


def render_scenario_session_history() -> None:
    """Render saved what-if scenarios from session-state history."""
    scenario_history = st.session_state.get("portfolio_scenario_history", [])

    st.subheader("Scenario History")

    if not scenario_history:
        st.info("No scenarios saved in this session yet.")
        return

    scenario_history_df = pd.DataFrame(scenario_history)

    risk_options = ["All Risk Levels"] + sorted(
        scenario_history_df["Scenario Risk Level"].dropna().astype(str).unique().tolist()
    )

    decision_options = ["All Decisions"] + sorted(
        scenario_history_df["Scenario Decision"].dropna().astype(str).unique().tolist()
    )

    filter_col1, filter_col2 = st.columns(2)

    selected_risk_filter = filter_col1.selectbox(
        "Scenario history risk filter",
        options=risk_options,
        index=0,
        key="scenario_history_risk_filter",
    )

    selected_decision_filter = filter_col2.selectbox(
        "Scenario history decision filter",
        options=decision_options,
        index=0,
        key="scenario_history_decision_filter",
    )

    filtered_history_df = scenario_history_df.copy()

    if selected_risk_filter != "All Risk Levels":
        filtered_history_df = filtered_history_df[
            filtered_history_df["Scenario Risk Level"].astype(str) == selected_risk_filter
        ]

    if selected_decision_filter != "All Decisions":
        filtered_history_df = filtered_history_df[
            filtered_history_df["Scenario Decision"].astype(str) == selected_decision_filter
        ]

    st.caption(
        f"Showing {len(filtered_history_df)} of {len(scenario_history_df)} saved scenario(s)."
    )

    if filtered_history_df.empty:
        st.warning("No saved scenarios match the selected filters.")
    else:
        summary_col1, summary_col2, summary_col3 = st.columns(3)

        scenario_count = len(filtered_history_df)
        average_risk_score = filtered_history_df["Scenario Risk Score"].mean()
        total_value_delta = filtered_history_df["Value Delta"].sum()

        summary_col1.metric("Saved Scenarios", scenario_count)
        summary_col2.metric("Average Risk Score", f"{average_risk_score:.0f}/100")
        summary_col3.metric("Total Value Delta", f"${total_value_delta:,.2f}")

        best_scenario = filtered_history_df.sort_values(
            by="Value Delta",
            ascending=False,
        ).iloc[0]

        worst_scenario = filtered_history_df.sort_values(
            by="Value Delta",
            ascending=True,
        ).iloc[0]

        st.markdown("**Best saved scenario by value delta:**")
        st.info(
            f"{best_scenario['Ticker']} | {best_scenario['Action']} | "
            f"Value Delta: ${float(best_scenario['Value Delta']):,.2f} | "
            f"Risk: {best_scenario['Scenario Risk Level']} "
            f"({float(best_scenario['Scenario Risk Score']):.0f}/100)"
        )

        st.markdown("**Worst saved scenario by value delta:**")
        st.warning(
            f"{worst_scenario['Ticker']} | {worst_scenario['Action']} | "
            f"Value Delta: ${float(worst_scenario['Value Delta']):,.2f} | "
            f"Risk: {worst_scenario['Scenario Risk Level']} "
            f"({float(worst_scenario['Scenario Risk Score']):.0f}/100)"
        )

        st.dataframe(
            filtered_history_df,
            use_container_width=True,
            hide_index=True,
        )

        scenario_history_timestamp = pd.Timestamp.now().strftime("%Y-%m-%d_%H%M")

        st.download_button(
            label="Download Filtered Scenario History CSV",
            data=filtered_history_df.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"portfolio_filtered_scenario_history_{scenario_history_timestamp}.csv",
            mime="text/csv",
            key="download_filtered_scenario_history_csv",
        )

    if st.button(
        "Clear Scenario History",
        key="clear_portfolio_scenario_history_button",
    ):
        st.session_state["portfolio_scenario_history"] = []
        st.rerun()


def render_database_scenario_history(limit: int = 100) -> None:
    """Render saved what-if scenarios from the database."""
    st.subheader("Saved Scenario Database History")

    scenarios = get_portfolio_scenarios(limit=limit)

    if not scenarios:
        st.info("No database-saved scenarios yet.")
        return

    scenario_rows = []

    for scenario in scenarios:
        scenario_rows.append(
            {
                "ID": scenario.id,
                "Scenario Date": scenario.scenario_date,
                "Ticker": scenario.ticker,
                "Action": scenario.action,
                "Scenario Portfolio Value": scenario.scenario_portfolio_value,
                "Value Delta": scenario.value_delta,
                "Scenario Gain/Loss": scenario.scenario_gain_loss,
                "Gain/Loss Delta": scenario.gain_loss_delta,
                "Scenario Risk Score": scenario.scenario_risk_score,
                "Scenario Risk Level": scenario.scenario_risk_level,
                "Scenario Decision": scenario.scenario_decision,
                "Scenario Notes": scenario.scenario_notes,
            }
        )

    scenario_db_df = pd.DataFrame(scenario_rows)

    st.dataframe(
        scenario_db_df,
        use_container_width=True,
        hide_index=True,
    )

    scenario_db_timestamp = pd.Timestamp.now().strftime("%Y-%m-%d_%H%M")

    st.download_button(
        label="Download Database Scenario History CSV",
        data=scenario_db_df.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"portfolio_database_scenario_history_{scenario_db_timestamp}.csv",
        mime="text/csv",
        key="download_database_scenario_history_csv",
    )

    scenario_ids = scenario_db_df["ID"].tolist()

    selected_scenario_id = st.selectbox(
        "Delete saved database scenario",
        options=scenario_ids,
        key="delete_database_scenario_selectbox",
    )

    if st.button(
        "Delete Selected Database Scenario",
        key="delete_database_scenario_button",
    ):
        deleted = delete_portfolio_scenario(int(selected_scenario_id))

        if deleted:
            st.success("Selected database scenario deleted.")
            st.rerun()
        else:
            st.error("Selected database scenario could not be deleted.")
