from __future__ import annotations

import pandas as pd
import streamlit as st
import plotly.express as px

def render_portfolio_dashboard(portfolio_df):
    st.subheader("Portfolio Analytics")

    if portfolio_df.empty:
        st.info("Add a portfolio position from the sidebar.")
        return

    total_cost_basis = portfolio_df["Cost Basis"].sum()
    total_current_value = portfolio_df["Current Value"].sum()
    total_gain_loss = portfolio_df["Gain/Loss"].sum()

    if total_cost_basis > 0:
        total_gain_loss_pct = (
            total_gain_loss / total_cost_basis
        ) * 100
    else:
        total_gain_loss_pct = 0.0

    best_position = portfolio_df.sort_values(
        by="Gain/Loss %",
        ascending=False
    ).iloc[0]

    worst_position = portfolio_df.sort_values(
        by="Gain/Loss %",
        ascending=True
    ).iloc[0]

    largest_position = portfolio_df.sort_values(
        by="Allocation %",
        ascending=False
    ).iloc[0]

    summary_col1, summary_col2, summary_col3 = st.columns(3)

    summary_col1.metric(
        "Total Current Value",
        f"${total_current_value:,.2f}"
    )

    summary_col2.metric(
        "Total Cost Basis",
        f"${total_cost_basis:,.2f}"
    )

    summary_col3.metric(
        "Total Gain/Loss",
        f"${total_gain_loss:,.2f}",
        f"{total_gain_loss_pct:.2f}%"
    )

    insight_col1, insight_col2, insight_col3 = st.columns(3)

    insight_col1.metric(
        "Best Performer",
        best_position["Ticker"],
        f"{best_position['Gain/Loss %']:.2f}%"
    )

    insight_col2.metric(
        "Worst Performer",
        worst_position["Ticker"],
        f"{worst_position['Gain/Loss %']:.2f}%"
    )

    insight_col3.metric(
        "Largest Allocation",
        largest_position["Ticker"],
        f"{largest_position['Allocation %']:.2f}%"
    )

    render_portfolio_allocation_chart(portfolio_df)
    render_risk_dashboard(portfolio_df, largest_position)
    render_portfolio_table(portfolio_df)

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

