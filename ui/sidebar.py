from __future__ import annotations

import streamlit as st

from database import add_portfolio_position
from database import add_to_watchlist
from database import get_portfolio_positions
from database import get_watchlist
from market_data import validate_ticker
from database import delete_portfolio_position

def render_watchlist_sidebar(ticker):
    st.sidebar.divider()
    st.sidebar.header("Saved Watchlist")

    if st.sidebar.button(
        "Save Primary Ticker",
        key="save_primary_ticker"
    ):
        success, message = add_to_watchlist(ticker)

        if success:
            st.sidebar.success(message)
        else:
            st.sidebar.warning(message)

    watchlist_items = get_watchlist()

    if watchlist_items:
        saved_tickers = [stock.ticker for stock in watchlist_items]

        selected_watchlist_ticker = st.sidebar.selectbox(
            "Saved Tickers",
            options=saved_tickers,
            key="saved_tickers_select"
        )

        if st.sidebar.button(
            "Remove Selected Ticker",
            key="remove_selected_ticker"
        ):
            success, message = remove_from_watchlist(
                selected_watchlist_ticker
            )

            if success:
                st.sidebar.success(message)
                st.rerun()
            else:
                st.sidebar.warning(message)
    else:
        st.sidebar.info("No saved tickers yet.")

def render_portfolio_sidebar():
    st.sidebar.divider()
    st.sidebar.header("Portfolio Tracker")

    with st.sidebar.form("add_portfolio_position_form"):
        portfolio_ticker = st.text_input(
            "Portfolio Ticker",
            value="",
            placeholder="Example: AAPL, MSFT, NVDA",
            key="portfolio_ticker_input"
        ).upper().strip()

        portfolio_shares = st.number_input(
            "Shares",
            min_value=0.0,
            step=1.0,
            key="portfolio_shares_input"
        )

        portfolio_buy_price = st.number_input(
            "Buy Price",
            min_value=0.0,
            step=1.0,
            key="portfolio_buy_price_input"
        )

        auto_add_to_watchlist = st.checkbox(
            "Also add to watchlist",
            value=True,
            key="auto_add_portfolio_to_watchlist"
        )

        submitted = st.form_submit_button("Add Portfolio Position")

        if submitted:
            is_valid, validation_result = validate_ticker(portfolio_ticker)

            if not is_valid:
                st.sidebar.error(validation_result)
            else:
                success, message = add_portfolio_position(
                    validation_result,
                    portfolio_shares,
                    portfolio_buy_price
                )

                if success:
                    if auto_add_to_watchlist:
                        add_to_watchlist(validation_result)

                    st.sidebar.success(message)
                    st.rerun()
                else:
                    st.sidebar.warning(message)

    portfolio_positions = get_portfolio_positions()

    if portfolio_positions:
        portfolio_tickers = [
            position.ticker for position in portfolio_positions
        ]

        selected_portfolio_ticker = st.sidebar.selectbox(
            "Portfolio Positions",
            options=portfolio_tickers,
            key="portfolio_positions_select"
        )

        if st.sidebar.button(
            "Remove Selected Position",
            key="remove_selected_position"
        ):
            success, message = remove_portfolio_position(
                selected_portfolio_ticker
            )

            if success:
                st.sidebar.success(message)
                st.rerun()
            else:
                st.sidebar.warning(message)
    else:
        st.sidebar.info("Add a portfolio position from the sidebar.")


    st.sidebar.divider()
    st.sidebar.subheader("Delete Portfolio Position")

    saved_positions = get_portfolio_positions()

    if not saved_positions:
        st.sidebar.info("No saved portfolio positions to delete.")
    else:
        position_options = {
            (
                f"{position.ticker} | "
                f"{position.shares} shares | "
                f"${position.buy_price:,.2f}"
            ): position.id
            for position in saved_positions
        }

        selected_position = st.sidebar.selectbox(
            "Select position to delete",
            options=list(position_options.keys()),
            key="delete_portfolio_position_select",
        )

        confirm_delete = st.sidebar.checkbox(
            "Confirm delete",
            key="confirm_delete_portfolio_position",
        )

        if st.sidebar.button(
            "Delete Selected Position",
            key="delete_portfolio_position_button",
        ):
            if not confirm_delete:
                st.sidebar.warning("Check confirm delete before deleting.")
            else:
                deleted = delete_portfolio_position(
                    position_options[selected_position]
                )

                if deleted:
                    st.sidebar.success("Portfolio position deleted.")
                    st.rerun()
                else:
                    st.sidebar.error("Portfolio position was not found.")

