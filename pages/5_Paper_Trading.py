"""Streamlit paper-trading dashboard."""

import pandas as pd
import streamlit as st

from database import get_active_paper_account
from database import get_or_create_paper_account
from database import get_paper_orders
from database import get_paper_positions
from database import get_paper_trades
from database import init_database
from market_data import get_current_price
from services.paper_trading_service import execute_market_order


PAGE_TITLE = "Paper Trading"
DEFAULT_STARTING_CASH = 100000.0


st.set_page_config(
    page_title=PAGE_TITLE,
    layout="wide",
)

init_database()


def format_currency(value):
    """Format a number as U.S. currency."""

    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return "$0.00"


def load_position_dashboard(account_id):
    """Build position rows and account market-value totals."""

    positions = get_paper_positions(account_id)
    rows = []

    total_market_value = 0.0
    total_cost_basis = 0.0
    total_unrealized_profit_loss = 0.0
    total_realized_profit_loss = 0.0

    for position in positions:
        quantity = float(position.quantity)
        average_cost = float(position.average_cost)
        current_price = get_current_price(position.ticker)

        if current_price is None:
            current_price = average_cost
            price_status = "Fallback: average cost"
        else:
            current_price = float(current_price)
            price_status = "Current market price"

        cost_basis = quantity * average_cost
        market_value = quantity * current_price
        unrealized_profit_loss = market_value - cost_basis

        if cost_basis == 0:
            unrealized_profit_loss_pct = 0.0
        else:
            unrealized_profit_loss_pct = (
                unrealized_profit_loss / cost_basis
            ) * 100

        realized_profit_loss = float(
            position.realized_profit_loss or 0.0
        )

        total_market_value += market_value
        total_cost_basis += cost_basis
        total_unrealized_profit_loss += unrealized_profit_loss
        total_realized_profit_loss += realized_profit_loss

        rows.append(
            {
                "Ticker": position.ticker,
                "Shares": quantity,
                "Average Cost": average_cost,
                "Current Price": current_price,
                "Cost Basis": cost_basis,
                "Market Value": market_value,
                "Unrealized P/L": unrealized_profit_loss,
                "Unrealized P/L %": unrealized_profit_loss_pct,
                "Realized P/L": realized_profit_loss,
                "Price Source": price_status,
            }
        )

    dataframe = pd.DataFrame(rows)

    totals = {
        "market_value": total_market_value,
        "cost_basis": total_cost_basis,
        "unrealized_profit_loss": total_unrealized_profit_loss,
        "realized_profit_loss": total_realized_profit_loss,
    }

    return dataframe, totals


def render_account_summary(account, totals):
    """Render paper-account summary metrics."""

    cash_balance = float(account.cash_balance)
    market_value = float(totals["market_value"])
    account_equity = cash_balance + market_value
    total_profit_loss = (
        account_equity - float(account.starting_cash)
    )

    if float(account.starting_cash) == 0:
        total_return_pct = 0.0
    else:
        total_return_pct = (
            total_profit_loss / float(account.starting_cash)
        ) * 100

    st.subheader("Account Summary")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Cash Balance",
        format_currency(cash_balance),
    )
    col2.metric(
        "Open Positions",
        format_currency(market_value),
    )
    col3.metric(
        "Account Equity",
        format_currency(account_equity),
    )
    col4.metric(
        "Total Return",
        format_currency(total_profit_loss),
        delta=f"{total_return_pct:.2f}%",
    )

    detail_col1, detail_col2, detail_col3 = st.columns(3)

    detail_col1.metric(
        "Starting Cash",
        format_currency(account.starting_cash),
    )
    detail_col2.metric(
        "Unrealized P/L",
        format_currency(totals["unrealized_profit_loss"]),
    )
    detail_col3.metric(
        "Realized P/L",
        format_currency(totals["realized_profit_loss"]),
    )


def render_order_ticket(account):
    """Render and process a simulated market-order form."""

    st.subheader("Market Order Ticket")

    with st.form(
        "paper_market_order_form",
        clear_on_submit=False,
    ):
        ticker_column, side_column = st.columns(2)

        ticker = ticker_column.text_input(
            "Ticker",
            value="AAPL",
            max_chars=15,
        ).upper().strip()

        side = side_column.selectbox(
            "Side",
            options=["BUY", "SELL"],
        )

        quantity_column, price_column = st.columns(2)

        quantity = quantity_column.number_input(
            "Share Quantity",
            min_value=0.000001,
            value=1.0,
            step=1.0,
            format="%.6f",
        )

        detected_price = None

        if ticker:
            detected_price = get_current_price(ticker)

        default_price = (
            float(detected_price)
            if detected_price is not None
            else 0.01
        )

        execution_price = price_column.number_input(
            "Execution Price",
            min_value=0.01,
            value=round(default_price, 2),
            step=0.01,
            format="%.2f",
            help=(
                "Defaults to the latest cached or provider market price. "
                "You may edit it for paper-trading simulations."
            ),
        )

        estimated_value = float(quantity) * float(execution_price)

        st.info(
            f"Estimated order value: "
            f"{format_currency(estimated_value)}"
        )

        submitted = st.form_submit_button(
            "Submit Paper Order",
            type="primary",
            use_container_width=True,
        )

    if submitted:
        result = execute_market_order(
            account_id=account.id,
            ticker=ticker,
            side=side,
            quantity=quantity,
            execution_price=execution_price,
        )

        if result["success"]:
            st.success(result["message"])
            st.session_state["last_paper_order"] = result
            st.rerun()
        else:
            st.error(result["message"])


def render_positions(position_dataframe):
    """Render currently open paper positions."""

    st.subheader("Open Positions")

    if position_dataframe.empty:
        st.info("No open paper positions.")
        return

    display_dataframe = position_dataframe.copy()

    currency_columns = [
        "Average Cost",
        "Current Price",
        "Cost Basis",
        "Market Value",
        "Unrealized P/L",
        "Realized P/L",
    ]

    for column in currency_columns:
        display_dataframe[column] = display_dataframe[column].map(
            format_currency
        )

    display_dataframe["Unrealized P/L %"] = (
        display_dataframe["Unrealized P/L %"]
        .map(lambda value: f"{float(value):.2f}%")
    )

    st.dataframe(
        display_dataframe,
        use_container_width=True,
        hide_index=True,
    )


def render_order_history(account_id):
    """Render submitted and rejected paper orders."""

    st.subheader("Order History")

    orders = get_paper_orders(
        account_id=account_id,
        limit=100,
    )

    if not orders:
        st.info("No paper orders have been submitted.")
        return

    rows = []

    for order in orders:
        rows.append(
            {
                "Order ID": order.id,
                "Submitted": order.submitted_at,
                "Ticker": order.ticker,
                "Side": order.side,
                "Type": order.order_type,
                "Quantity": order.quantity,
                "Requested Price": order.requested_price,
                "Executed Price": order.executed_price,
                "Order Value": order.order_value,
                "Status": order.status,
                "Rejection Reason": order.rejection_reason,
            }
        )

    dataframe = pd.DataFrame(rows)

    st.dataframe(
        dataframe,
        use_container_width=True,
        hide_index=True,
    )


def render_trade_history(account_id):
    """Render completed paper trades."""

    st.subheader("Trade History")

    trades = get_paper_trades(
        account_id=account_id,
        limit=100,
    )

    if not trades:
        st.info("No completed paper trades.")
        return

    rows = []

    for trade in trades:
        rows.append(
            {
                "Trade ID": trade.id,
                "Order ID": trade.order_id,
                "Executed": trade.executed_at,
                "Ticker": trade.ticker,
                "Side": trade.side,
                "Quantity": trade.quantity,
                "Execution Price": trade.execution_price,
                "Gross Value": trade.gross_value,
                "Realized P/L": trade.realized_profit_loss,
            }
        )

    dataframe = pd.DataFrame(rows)

    st.dataframe(
        dataframe,
        use_container_width=True,
        hide_index=True,
    )


def render_paper_trading_page():
    """Render the complete paper-trading dashboard."""

    st.title("Paper Trading Dashboard")
    st.caption(
        "Execute simulated market orders without risking real capital."
    )

    account = get_active_paper_account()

    if account is None:
        account = get_or_create_paper_account(
            starting_cash=DEFAULT_STARTING_CASH,
        )

    position_dataframe, totals = load_position_dashboard(
        account.id
    )

    render_account_summary(
        account=account,
        totals=totals,
    )

    st.divider()

    order_column, position_column = st.columns(
        [1, 2],
        gap="large",
    )

    with order_column:
        render_order_ticket(account)

    with position_column:
        render_positions(position_dataframe)

    st.divider()

    history_tab, trades_tab = st.tabs(
        [
            "Order History",
            "Completed Trades",
        ]
    )

    with history_tab:
        render_order_history(account.id)

    with trades_tab:
        render_trade_history(account.id)

    st.caption(
        "Paper-trading prices are simulations based on the latest "
        "available cached or provider market data."
    )


render_paper_trading_page()
