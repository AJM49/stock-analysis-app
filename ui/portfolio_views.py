from __future__ import annotations

import pandas as pd
import streamlit as st
import plotly.express as px
from services.portfolio_analytics_service import build_portfolio_risk_flags, build_sector_exposure_dataframe, build_position_weight_dataframe
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

    st.divider()

    with st.expander("Portfolio Overview", expanded=True):
        render_portfolio_help_text("Portfolio Overview")
        render_best_worst_performer_summary(portfolio_df)
        render_unrealized_gain_loss_summary(portfolio_df)

    with st.expander("Risk Intelligence", expanded=True):
        render_portfolio_help_text("Risk Intelligence")
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
