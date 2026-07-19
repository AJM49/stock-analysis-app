from __future__ import annotations

import streamlit as st

from database import add_portfolio_position
from database import add_to_watchlist
from database import get_portfolio_positions
from database import get_watchlist
from market_data import validate_ticker
from database import delete_portfolio_position
from database import update_portfolio_position
from services.market_data_service import get_stock_data
from database import save_portfolio_snapshot
from database import delete_portfolio_snapshot
from database import get_portfolio_snapshots
from services.portfolio_analytics_service import calculate_portfolio_risk_score

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
                    st.sidebar.error(message)

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

    st.sidebar.divider()

    st.sidebar.divider()
    st.sidebar.subheader("Refresh Portfolio Prices")

    refresh_result = st.session_state.pop("portfolio_refresh_result", None)

    if refresh_result:
        refreshed_count = refresh_result.get("refreshed_count", 0)
        failed_tickers = refresh_result.get("failed_tickers", [])

        if refreshed_count > 0:
            st.sidebar.success(
                f"Refreshed price data for {refreshed_count} ticker(s)."
            )

        if failed_tickers:
            st.sidebar.warning(
                "Could not refresh: " + ", ".join(failed_tickers)
            )

        if refreshed_count == 0 and not failed_tickers:
            st.sidebar.info("No portfolio tickers were refreshed.")

    refresh_positions = get_portfolio_positions()

    if not refresh_positions:
        st.sidebar.info("No saved portfolio positions to refresh.")
    else:
        if st.sidebar.button(
            "Refresh Saved Ticker Prices",
            key="refresh_portfolio_prices_button",
        ):
            refreshed_count = 0
            failed_tickers = []

            for position in refresh_positions:
                ticker = str(position.ticker).strip().upper()

                try:
                    get_stock_data(ticker, cache_only=False)
                    refreshed_count += 1
                except Exception:
                    failed_tickers.append(ticker)

            st.session_state["portfolio_refresh_result"] = {
                "refreshed_count": refreshed_count,
                "failed_tickers": failed_tickers,
            }

            st.rerun()

    st.sidebar.subheader("Edit Portfolio Position")

    editable_positions = get_portfolio_positions()

    if not editable_positions:
        st.sidebar.info("No saved portfolio positions to edit.")
    else:
        edit_options = {
            (
                f"{position.ticker} | "
                f"{position.shares} shares | "
                f"${position.buy_price:,.2f}"
            ): position
            for position in editable_positions
        }

        selected_edit_position_label = st.sidebar.selectbox(
            "Select position to edit",
            options=list(edit_options.keys()),
            key="edit_portfolio_position_select",
        )

        selected_edit_position = edit_options[selected_edit_position_label]

        edited_ticker = st.sidebar.text_input(
            "Edit ticker",
            value=selected_edit_position.ticker,
            key="edit_portfolio_ticker",
        )

        edited_shares = st.sidebar.number_input(
            "Edit shares",
            min_value=0.0,
            value=float(selected_edit_position.shares),
            step=1.0,
            key="edit_portfolio_shares",
        )

        edited_buy_price = st.sidebar.number_input(
            "Edit buy price",
            min_value=0.0,
            value=float(selected_edit_position.buy_price),
            step=1.0,
            key="edit_portfolio_buy_price",
        )

        if st.sidebar.button(
            "Update Selected Position",
            key="update_portfolio_position_button",
        ):
            updated = update_portfolio_position(
                position_id=selected_edit_position.id,
                ticker=edited_ticker,
                shares=edited_shares,
                buy_price=edited_buy_price,
            )

            if updated:
                st.sidebar.success("Portfolio position updated.")
                st.rerun()
            else:
                st.sidebar.error("Portfolio position was not updated.")

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



def render_save_portfolio_snapshot_control(portfolio_df) -> None:
    """Render sidebar control for saving portfolio performance snapshots."""
    st.sidebar.divider()
    st.sidebar.subheader("Portfolio Snapshot")

    if st.session_state.pop("portfolio_snapshot_saved", False):
        st.sidebar.success("Portfolio snapshot saved.")

    if portfolio_df is None or portfolio_df.empty:
        st.sidebar.info("Add portfolio positions before saving a snapshot.")
        return

    if st.sidebar.button(
        "Save Portfolio Snapshot",
        key="save_portfolio_snapshot_button",
    ):
        total_cost_basis = float(portfolio_df["Cost Basis"].sum())
        total_current_value = float(portfolio_df["Current Value"].sum())
        total_gain_loss = float(portfolio_df["Gain/Loss"].sum())

        if total_cost_basis > 0:
            total_gain_loss_pct = (total_gain_loss / total_cost_basis) * 100
        else:
            total_gain_loss_pct = 0.0

        position_count = int(len(portfolio_df))

        risk_score, risk_level, risk_notes = calculate_portfolio_risk_score(
            portfolio_df
        )

        saved = save_portfolio_snapshot(
            total_cost_basis=total_cost_basis,
            total_current_value=total_current_value,
            total_gain_loss=total_gain_loss,
            total_gain_loss_pct=total_gain_loss_pct,
            position_count=position_count,
            risk_score=risk_score,
            risk_level=risk_level,
            risk_notes="; ".join(risk_notes),
        )

        if saved:
            st.session_state["portfolio_snapshot_saved"] = True
            st.rerun()

        st.sidebar.error("Portfolio snapshot could not be saved.")

def render_portfolio_snapshot_cleanup_control() -> None:
    """Render sidebar control to delete saved portfolio snapshots."""
    st.sidebar.divider()
    st.sidebar.subheader("Portfolio Snapshot Cleanup")

    snapshots = get_portfolio_snapshots(limit=10000)

    if not snapshots:
        st.sidebar.info("No portfolio snapshots to delete.")
        return

    snapshot_options = {
        (
            f"{snapshot.snapshot_date.strftime('%Y-%m-%d %H:%M')} | "
            f"${snapshot.total_current_value:,.2f} | "
            f"{snapshot.position_count} positions"
        ): snapshot.id
        for snapshot in snapshots
    }

    selected_snapshot = st.sidebar.selectbox(
        "Select snapshot to delete",
        options=list(snapshot_options.keys()),
        key="delete_portfolio_snapshot_select",
    )

    confirm_delete_snapshot = st.sidebar.checkbox(
        "Confirm snapshot delete",
        key="confirm_delete_portfolio_snapshot",
    )

    if st.sidebar.button(
        "Delete Selected Snapshot",
        key="delete_portfolio_snapshot_button",
    ):
        if not confirm_delete_snapshot:
            st.sidebar.warning("Check confirm snapshot delete before deleting.")
            return

        deleted = delete_portfolio_snapshot(
            snapshot_options[selected_snapshot]
        )

        if deleted:
            st.session_state["portfolio_snapshot_deleted"] = True
            st.rerun()
        else:
            st.sidebar.error("Portfolio snapshot was not found.")
