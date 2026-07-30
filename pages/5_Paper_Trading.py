from __future__ import annotations

import pandas as pd
import streamlit as st

from paper_trading.closed_trades_ledger import (
    add_closed_trade,
    build_closed_trades_dataframe,
    build_closed_trades_summary,
    calculate_realized_pnl_by_ticker,
)
from paper_trading.execution_engine import (
    build_execution_summary,
    execute_paper_order,
)
from paper_trading.models import (
    ClosedPaperTrade,
    OrderSide,
    OrderType,
    PaperPosition,
    PaperTradingAccount,
)
from paper_trading.order_preview import (
    build_buy_sell_order_preview,
    build_order_preview_dataframe,
    build_order_preview_summary,
)
from paper_trading.order_ticket import build_order_ticket
from paper_trading.positions_ledger import (
    apply_trade_to_positions,
    build_open_positions_dataframe,
    build_open_positions_summary,
    update_position_prices,
)
from paper_trading.trade_journal import (
    add_journal_entry,
    build_trade_journal_dataframe,
    build_trade_journal_summary,
    create_trade_journal_entry,
)


DEFAULT_ACCOUNT_ID = "paper-acct-1"


def initialize_session_state() -> None:
    """Initialize paper trading session state."""
    if "paper_account" not in st.session_state:
        st.session_state.paper_account = PaperTradingAccount(
            account_id=DEFAULT_ACCOUNT_ID,
            account_name="Paper Trading Account",
            starting_cash=10000.0,
            cash_balance=10000.0,
        )

    if "paper_positions" not in st.session_state:
        st.session_state.paper_positions = []

    if "closed_trades" not in st.session_state:
        st.session_state.closed_trades = []

    if "journal_entries" not in st.session_state:
        st.session_state.journal_entries = []

    if "last_order_preview" not in st.session_state:
        st.session_state.last_order_preview = None

    if "last_order_ticket" not in st.session_state:
        st.session_state.last_order_ticket = None

    if "last_execution_summary" not in st.session_state:
        st.session_state.last_execution_summary = None


def reset_paper_account(starting_cash: float) -> None:
    """Reset paper account and related ledgers."""
    st.session_state.paper_account = PaperTradingAccount(
        account_id=DEFAULT_ACCOUNT_ID,
        account_name="Paper Trading Account",
        starting_cash=starting_cash,
        cash_balance=starting_cash,
    )
    st.session_state.paper_positions = []
    st.session_state.closed_trades = []
    st.session_state.journal_entries = []
    st.session_state.last_order_preview = None
    st.session_state.last_order_ticket = None
    st.session_state.last_execution_summary = None


def get_position_quantity(ticker: str) -> float:
    """Get current paper position quantity for ticker."""
    clean_ticker = ticker.strip().upper()

    for position in st.session_state.paper_positions:
        if position.ticker == clean_ticker:
            return float(position.quantity)

    return 0.0


def get_current_position(ticker: str) -> PaperPosition | None:
    """Get current paper position object for ticker."""
    clean_ticker = ticker.strip().upper()

    for position in st.session_state.paper_positions:
        if position.ticker == clean_ticker:
            return position

    return None


def render_account_panel() -> None:
    """Render paper account summary."""
    account = st.session_state.paper_account
    positions_summary = build_open_positions_summary(st.session_state.paper_positions)
    closed_summary = build_closed_trades_summary(st.session_state.closed_trades)
    journal_summary = build_trade_journal_summary(st.session_state.journal_entries)

    st.subheader("Paper Trading Account")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Cash Balance", f"${account.cash_balance:,.2f}")
    col2.metric("Open Positions", positions_summary["position_count"])
    col3.metric("Closed Trades", closed_summary["closed_trade_count"])
    col4.metric("Journal Notes", journal_summary["journal_entry_count"])

    col5, col6, col7, col8 = st.columns(4)

    col5.metric("Open Market Value", f"${positions_summary['total_market_value']:,.2f}")
    col6.metric("Unrealized P/L", f"${positions_summary['total_unrealized_pnl']:,.2f}")
    col7.metric("Realized P/L", f"${closed_summary['total_realized_pnl']:,.2f}")
    col8.metric("Win Rate", f"{closed_summary['win_rate_pct']:.2f}%")


def render_account_controls() -> None:
    """Render account reset controls."""
    with st.sidebar:
        st.header("Paper Account")

        starting_cash = st.number_input(
            "Starting Cash $",
            min_value=100.0,
            max_value=100000000.0,
            value=float(st.session_state.paper_account.starting_cash),
            step=500.0,
        )

        if st.button("Reset Paper Account"):
            reset_paper_account(starting_cash=starting_cash)
            st.success("Paper account reset.")


def render_order_ticket_controls() -> dict[str, object]:
    """Render order ticket controls and return inputs."""
    st.subheader("Simulated Order Ticket")

    col1, col2, col3 = st.columns(3)

    ticker = col1.text_input(
        "Ticker",
        value="AAPL",
        key="paper_order_ticker",
    ).strip().upper()

    side_label = col2.selectbox(
        "Side",
        options=["Buy", "Sell"],
        index=0,
    )

    order_type_label = col3.selectbox(
        "Order Type",
        options=["Market", "Limit"],
        index=0,
    )

    order_col1, order_col2, order_col3 = st.columns(3)

    quantity = order_col1.number_input(
        "Quantity",
        min_value=0.0001,
        max_value=1000000.0,
        value=1.0,
        step=1.0,
    )

    estimated_price = order_col2.number_input(
        "Estimated Market Price $",
        min_value=0.01,
        max_value=1000000.0,
        value=200.0,
        step=1.0,
    )

    limit_price = None

    if order_type_label == "Limit":
        limit_price = order_col3.number_input(
            "Limit Price $",
            min_value=0.01,
            max_value=1000000.0,
            value=estimated_price,
            step=1.0,
        )
    else:
        order_col3.metric("Limit Price", "N/A")

    risk_col1, risk_col2, risk_col3 = st.columns(3)

    commission_rate_pct = risk_col1.number_input(
        "Commission Rate %",
        min_value=0.0,
        max_value=10.0,
        value=0.0,
        step=0.01,
    )

    minimum_commission = risk_col2.number_input(
        "Minimum Commission $",
        min_value=0.0,
        max_value=1000.0,
        value=0.0,
        step=1.0,
    )

    max_exposure_pct = risk_col3.number_input(
        "Max Exposure %",
        min_value=0.1,
        max_value=100.0,
        value=25.0,
        step=1.0,
    )

    return {
        "ticker": ticker,
        "side": OrderSide.BUY if side_label == "Buy" else OrderSide.SELL,
        "quantity": quantity,
        "order_type": OrderType.MARKET if order_type_label == "Market" else OrderType.LIMIT,
        "estimated_price": estimated_price,
        "limit_price": limit_price,
        "commission_rate_pct": commission_rate_pct,
        "minimum_commission": minimum_commission,
        "max_exposure_pct": max_exposure_pct,
    }


def render_order_preview(order_inputs: dict[str, object]) -> None:
    """Render order preview section."""
    account = st.session_state.paper_account
    ticker = str(order_inputs["ticker"])
    current_quantity = get_position_quantity(ticker)

    portfolio_value = (
        account.cash_balance
        + build_open_positions_summary(st.session_state.paper_positions)["total_market_value"]
    )

    if st.button("Preview Order"):
        try:
            preview = build_buy_sell_order_preview(
                account_id=account.account_id,
                ticker=ticker,
                side=order_inputs["side"],
                quantity=float(order_inputs["quantity"]),
                order_type=order_inputs["order_type"],
                estimated_price=float(order_inputs["estimated_price"]),
                cash_balance=float(account.cash_balance),
                portfolio_value=float(portfolio_value),
                current_position_quantity=float(current_quantity),
                limit_price=order_inputs["limit_price"],
                commission_rate_pct=float(order_inputs["commission_rate_pct"]),
                minimum_commission=float(order_inputs["minimum_commission"]),
                max_exposure_pct=float(order_inputs["max_exposure_pct"]),
            )

            ticket = build_order_ticket(
                account_id=account.account_id,
                ticker=ticker,
                side=order_inputs["side"],
                quantity=float(order_inputs["quantity"]),
                order_type=order_inputs["order_type"],
                estimated_price=float(order_inputs["estimated_price"]),
                limit_price=order_inputs["limit_price"],
                cash_balance=float(account.cash_balance),
                current_position_quantity=float(current_quantity),
                commission_rate_pct=float(order_inputs["commission_rate_pct"]),
                minimum_commission=float(order_inputs["minimum_commission"]),
            )

            st.session_state.last_order_preview = preview
            st.session_state.last_order_ticket = ticket

        except Exception as error:
            st.error(f"Order preview failed: {error}")

    preview = st.session_state.last_order_preview

    if preview is None:
        st.info("Build an order ticket and click Preview Order.")
        return

    st.subheader("Buy/Sell Order Preview")

    if preview["preview_status"] == "Accepted":
        st.success(preview["preview_reason"])
    elif preview["preview_status"] == "Warning":
        st.warning(preview["preview_reason"])
    else:
        st.error(preview["preview_reason"])

    preview_df = build_order_preview_dataframe([preview])
    preview_display = preview_df.copy()
    numeric_columns = preview_display.select_dtypes(include="number").columns
    preview_display[numeric_columns] = preview_display[numeric_columns].round(4)

    st.dataframe(
        preview_display,
        use_container_width=True,
        hide_index=True,
    )

    preview_summary = build_order_preview_summary([preview])

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Status", preview["preview_status"])
    col2.metric("Order Value", f"${preview_summary['total_estimated_order_value']:,.2f}")
    col3.metric("Cash Impact", f"${preview_summary['total_estimated_cash_impact']:,.2f}")
    col4.metric("Exposure After", f"{preview_summary['max_exposure_pct_after_order']:.2f}%")

    csv_data = preview_display.to_csv(index=False)

    st.download_button(
        label="Download Order Preview CSV",
        data=csv_data,
        file_name="paper_order_preview.csv",
        mime="text/csv",
        key="download_order_preview_csv",
    )


def render_trade_execution() -> None:
    """Render execution controls and output."""
    st.subheader("Paper Trade Execution")

    ticket = st.session_state.last_order_ticket

    if ticket is None:
        st.info("Preview an order before execution.")
        return

    market_price = st.number_input(
        "Execution Market Price $",
        min_value=0.01,
        max_value=1000000.0,
        value=float(ticket["order_price"]),
        step=1.0,
    )

    if st.button("Execute Paper Trade"):
        try:
            account = st.session_state.paper_account
            order = ticket["order"]
            current_position = get_current_position(order.ticker)

            result = execute_paper_order(
                order=order,
                account=account,
                market_price=float(market_price),
                current_position=current_position,
                commission=float(ticket["estimated_commission"]),
            )

            st.session_state.paper_account = result["updated_account"]

            if result["trade"] is not None:
                updated_positions, closed_trade = apply_trade_to_positions(
                    positions=st.session_state.paper_positions,
                    trade=result["trade"],
                )
                st.session_state.paper_positions = updated_positions

                if closed_trade is not None:
                    st.session_state.closed_trades = add_closed_trade(
                        st.session_state.closed_trades,
                        closed_trade,
                    )

            st.session_state.last_execution_summary = build_execution_summary(result)

        except Exception as error:
            st.error(f"Paper trade execution failed: {error}")

    if st.session_state.last_execution_summary is None:
        return

    summary = st.session_state.last_execution_summary

    if summary["execution_status"] == "Filled":
        st.success(summary["execution_reason"])
    elif summary["execution_status"] == "Not Filled":
        st.warning(summary["execution_reason"])
    else:
        st.error(summary["execution_reason"])

    summary_df = pd.DataFrame([summary])
    numeric_columns = summary_df.select_dtypes(include="number").columns
    summary_df[numeric_columns] = summary_df[numeric_columns].round(4)

    st.dataframe(
        summary_df,
        use_container_width=True,
        hide_index=True,
    )

    st.download_button(
        label="Download Execution Summary CSV",
        data=summary_df.to_csv(index=False),
        file_name="paper_execution_summary.csv",
        mime="text/csv",
        key="download_execution_summary_csv",
    )


def render_open_positions_ledger() -> None:
    """Render open positions ledger."""
    st.subheader("Open Positions Ledger")

    positions = st.session_state.paper_positions

    if not positions:
        st.info("No open paper positions yet.")
        return

    price_updates = {}

    with st.expander("Update Current Prices", expanded=False):
        for position in positions:
            price_updates[position.ticker] = st.number_input(
                f"{position.ticker} Current Price $",
                min_value=0.01,
                max_value=1000000.0,
                value=float(position.current_price or position.average_cost),
                step=1.0,
                key=f"price_update_{position.ticker}",
            )

        if st.button("Apply Price Updates"):
            try:
                st.session_state.paper_positions = update_position_prices(
                    positions=positions,
                    price_lookup=price_updates,
                )
                st.success("Position prices updated.")
            except Exception as error:
                st.error(f"Price update failed: {error}")

    positions_df = build_open_positions_dataframe(st.session_state.paper_positions)
    positions_display = positions_df.copy()
    numeric_columns = positions_display.select_dtypes(include="number").columns
    positions_display[numeric_columns] = positions_display[numeric_columns].round(4)

    summary = build_open_positions_summary(st.session_state.paper_positions)

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Positions", summary["position_count"])
    col2.metric("Market Value", f"${summary['total_market_value']:,.2f}")
    col3.metric("Unrealized P/L", f"${summary['total_unrealized_pnl']:,.2f}")
    col4.metric("Unrealized P/L %", f"{summary['total_unrealized_pnl_pct']:.2f}%")

    st.dataframe(
        positions_display,
        use_container_width=True,
        hide_index=True,
    )

    st.download_button(
        label="Download Open Positions CSV",
        data=positions_display.to_csv(index=False),
        file_name="paper_open_positions.csv",
        mime="text/csv",
        key="download_open_positions_csv",
    )


def render_closed_trades_ledger() -> None:
    """Render closed trades ledger."""
    st.subheader("Closed Trades Ledger")

    closed_trades = st.session_state.closed_trades

    if not closed_trades:
        st.info("No closed paper trades yet.")
        return

    closed_df = build_closed_trades_dataframe(closed_trades)
    closed_display = closed_df.copy()
    numeric_columns = closed_display.select_dtypes(include="number").columns
    closed_display[numeric_columns] = closed_display[numeric_columns].round(4)

    summary = build_closed_trades_summary(closed_trades)

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Closed Trades", summary["closed_trade_count"])
    col2.metric("Win Rate", f"{summary['win_rate_pct']:.2f}%")
    col3.metric("Realized P/L", f"${summary['total_realized_pnl']:,.2f}")
    col4.metric("Avg Realized P/L", f"${summary['average_realized_pnl']:,.2f}")

    st.dataframe(
        closed_display,
        use_container_width=True,
        hide_index=True,
    )

    ticker_df = calculate_realized_pnl_by_ticker(closed_trades)
    ticker_display = ticker_df.copy()
    numeric_columns = ticker_display.select_dtypes(include="number").columns
    ticker_display[numeric_columns] = ticker_display[numeric_columns].round(4)

    with st.expander("Realized P/L by Ticker", expanded=False):
        st.dataframe(
            ticker_display,
            use_container_width=True,
            hide_index=True,
        )

    st.download_button(
        label="Download Closed Trades CSV",
        data=closed_display.to_csv(index=False),
        file_name="paper_closed_trades.csv",
        mime="text/csv",
        key="download_closed_trades_csv",
    )


def render_trade_journal() -> None:
    """Render trade journal notes."""
    st.subheader("Trade Journal Notes")

    with st.expander("Add Journal Note", expanded=True):
        col1, col2, col3 = st.columns(3)

        ticker = col1.text_input(
            "Journal Ticker",
            value="AAPL",
            key="journal_ticker",
        ).strip().upper()

        review_label = col2.selectbox(
            "Review Label",
            options=[
                "Plan",
                "Good Trade",
                "Bad Trade",
                "Mistake",
                "Lesson",
                "Follow Up",
            ],
        )

        linked_trade_id = col3.text_input(
            "Linked Trade ID",
            value="",
            key="journal_linked_trade_id",
        ).strip() or None

        tags_raw = st.text_input(
            "Tags comma-separated",
            value="plan, risk",
            key="journal_tags",
        )

        note = st.text_area(
            "Journal Note",
            value="Write the reasoning, setup, risk, result, or lesson here.",
            key="journal_note",
        )

        if st.button("Add Journal Note"):
            try:
                tags = [tag.strip() for tag in tags_raw.split(",") if tag.strip()]
                entry = create_trade_journal_entry(
                    account_id=st.session_state.paper_account.account_id,
                    ticker=ticker,
                    note=note,
                    linked_trade_id=linked_trade_id,
                    review_label=review_label,
                    tags=tags,
                )
                st.session_state.journal_entries = add_journal_entry(
                    st.session_state.journal_entries,
                    entry,
                )
                st.success("Journal note added.")
            except Exception as error:
                st.error(f"Journal note failed: {error}")

    journal_entries = st.session_state.journal_entries

    if not journal_entries:
        st.info("No journal notes yet.")
        return

    journal_df = build_trade_journal_dataframe(journal_entries)
    summary = build_trade_journal_summary(journal_entries)

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Journal Notes", summary["journal_entry_count"])
    col2.metric("Unique Tickers", summary["unique_ticker_count"])
    col3.metric("Linked Notes", summary["linked_trade_note_count"])
    col4.metric("Most Common Ticker", summary["most_common_ticker"] or "N/A")

    st.dataframe(
        journal_df,
        use_container_width=True,
        hide_index=True,
    )

    st.download_button(
        label="Download Trade Journal CSV",
        data=journal_df.to_csv(index=False),
        file_name="paper_trade_journal.csv",
        mime="text/csv",
        key="download_trade_journal_csv",
    )


def render_methodology() -> None:
    """Render paper trading methodology."""
    with st.expander("Paper Trading Methodology", expanded=False):
        st.markdown(
            """
### Paper Trading Workflow

This page simulates a trading workflow without placing real trades.

The workflow is:

1. Set up a paper account.
2. Build a simulated buy or sell order ticket.
3. Preview cash impact and portfolio exposure.
4. Execute the paper trade.
5. Track open positions.
6. Track closed trades.
7. Add trade journal notes.

### Execution Logic

Market orders fill at the selected execution market price.

Limit buy orders fill when the market price is at or below the limit price.

Limit sell orders fill when the market price is at or above the limit price.

### Ledger Logic

Open positions track quantity, average cost, market value, and unrealized P/L.

Closed trades track realized P/L, return percentage, and win/loss result.

Journal notes capture the reasoning, review label, tags, and linked trade ID.

### Project Use

This is a simulated trading and engineering tool. It is not financial advice and does not place real brokerage orders.
"""
        )


def render_paper_trading_page() -> None:
    """Render Paper Trading page."""
    st.set_page_config(
        page_title="Paper Trading",
        layout="wide",
    )

    initialize_session_state()

    st.title("Paper Trading")
    st.caption("Sprint 72: Paper Trading and Trade Journal Foundation")

    render_account_controls()
    render_account_panel()

    st.divider()
    order_inputs = render_order_ticket_controls()

    st.divider()
    render_order_preview(order_inputs)

    st.divider()
    render_trade_execution()

    st.divider()
    render_open_positions_ledger()

    st.divider()
    render_closed_trades_ledger()

    st.divider()
    render_trade_journal()

    st.divider()
    render_methodology()


render_paper_trading_page()
