"""Streamlit paper-trading dashboard."""

import pandas as pd
import streamlit as st

from database import get_active_paper_account
from database import get_or_create_paper_account
from database import get_paper_orders
from database import get_paper_positions
from database import get_paper_trades
from database import init_database
from database import get_database_session
from market_data import get_current_price
from services.paper_trading_service import execute_market_order
from services.paper_trading_risk import DEFAULT_RISK_SETTINGS
from services.paper_trading_risk import evaluate_pre_trade_risk
from services.paper_trading_performance import get_paper_equity_snapshots
from services.paper_trading_performance import reset_paper_account
from services.paper_trading_performance import save_equity_snapshot


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



def render_risk_settings():
    """Render configurable paper-trading risk controls."""

    st.sidebar.divider()
    st.sidebar.header("Paper Trading Risk Controls")

    with st.sidebar.expander("Risk Settings", expanded=False):
        max_order_value_pct = st.number_input(
            "Maximum Order Value %",
            min_value=0.1,
            max_value=100.0,
            value=float(
                DEFAULT_RISK_SETTINGS["max_order_value_pct"]
            ),
            step=0.5,
            format="%.2f",
            key="risk_max_order_value_pct",
        )

        max_position_value_pct = st.number_input(
            "Maximum Position Value %",
            min_value=0.1,
            max_value=100.0,
            value=float(
                DEFAULT_RISK_SETTINGS[
                    "max_position_value_pct"
                ]
            ),
            step=0.5,
            format="%.2f",
            key="risk_max_position_value_pct",
        )

        minimum_cash_reserve_pct = st.number_input(
            "Minimum Cash Reserve %",
            min_value=0.0,
            max_value=100.0,
            value=float(
                DEFAULT_RISK_SETTINGS[
                    "minimum_cash_reserve_pct"
                ]
            ),
            step=0.5,
            format="%.2f",
            key="risk_minimum_cash_reserve_pct",
        )

        max_share_quantity = st.number_input(
            "Maximum Shares Per Order",
            min_value=0.000001,
            max_value=1000000.0,
            value=float(
                DEFAULT_RISK_SETTINGS["max_share_quantity"]
            ),
            step=1.0,
            format="%.6f",
            key="risk_max_share_quantity",
        )

        duplicate_order_window_seconds = st.number_input(
            "Duplicate Protection Window",
            min_value=0,
            max_value=3600,
            value=int(
                DEFAULT_RISK_SETTINGS[
                    "duplicate_order_window_seconds"
                ]
            ),
            step=1,
            key="risk_duplicate_window",
        )

        warn_order_value_pct = st.number_input(
            "Order Warning Threshold %",
            min_value=0.0,
            max_value=100.0,
            value=float(
                DEFAULT_RISK_SETTINGS[
                    "warn_order_value_pct"
                ]
            ),
            step=0.5,
            format="%.2f",
            key="risk_warn_order_value_pct",
        )

        warn_position_value_pct = st.number_input(
            "Position Warning Threshold %",
            min_value=0.0,
            max_value=100.0,
            value=float(
                DEFAULT_RISK_SETTINGS[
                    "warn_position_value_pct"
                ]
            ),
            step=0.5,
            format="%.2f",
            key="risk_warn_position_value_pct",
        )

    return {
        "max_order_value_pct": max_order_value_pct,
        "max_position_value_pct": max_position_value_pct,
        "minimum_cash_reserve_pct": minimum_cash_reserve_pct,
        "max_share_quantity": max_share_quantity,
        "duplicate_order_window_seconds": int(
            duplicate_order_window_seconds
        ),
        "warn_order_value_pct": warn_order_value_pct,
        "warn_position_value_pct": warn_position_value_pct,
    }


def render_risk_result(risk_result):
    """Render a paper-order risk evaluation."""

    level = risk_result.get("level", "PASS")
    message = risk_result.get(
        "message",
        "Risk check completed.",
    )

    if level == "BLOCK":
        st.error(message)
    elif level == "WARNING":
        st.warning(message)
    else:
        st.success(message)

    for violation in risk_result.get("violations", []):
        st.error("BLOCK: " + str(violation))

    for warning in risk_result.get("warnings", []):
        st.warning("WARNING: " + str(warning))

    metrics = risk_result.get("metrics", {})

    if not metrics:
        return

    metric1, metric2, metric3 = st.columns(3)

    metric1.metric(
        "Order Value",
        format_currency(metrics.get("order_value", 0.0)),
        delta=(
            f'{float(metrics.get("order_value_pct", 0.0)):.2f}% '
            "of starting cash"
        ),
    )

    metric2.metric(
        "Projected Position",
        format_currency(
            metrics.get("projected_position_value", 0.0)
        ),
        delta=(
            f'{float(metrics.get("projected_position_pct", 0.0)):.2f}% '
            "of starting cash"
        ),
    )

    metric3.metric(
        "Projected Cash",
        format_currency(metrics.get("projected_cash", 0.0)),
        delta=(
            f'{float(metrics.get("projected_cash_reserve_pct", 0.0)):.2f}% '
            "reserve"
        ),
    )


def render_order_ticket(account, risk_settings):
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
            risk_settings=risk_settings,
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



def render_account_management(account):
    """Render guarded paper-account reset controls."""

    st.sidebar.header("Paper Account Controls")

    starting_cash = st.sidebar.number_input(
        "Reset Starting Cash",
        min_value=1000.0,
        max_value=10000000.0,
        value=float(account.starting_cash),
        step=1000.0,
        format="%.2f",
        key="paper_reset_starting_cash",
    )

    confirmation = st.sidebar.text_input(
        'Type "RESET" to confirm',
        value="",
        key="paper_reset_confirmation",
    )

    reset_clicked = st.sidebar.button(
        "Reset Paper Account",
        use_container_width=True,
        key="reset_paper_account_button",
    )

    if not reset_clicked:
        return

    if confirmation.strip().upper() != "RESET":
        st.sidebar.error('Type "RESET" before resetting.')
        return

    success, message = reset_paper_account(
        account_id=account.id,
        starting_cash=starting_cash,
    )

    if success:
        st.session_state.pop("last_paper_order", None)
        st.sidebar.success(message)
        st.rerun()

    st.sidebar.error(message)


def render_snapshot_control(account, totals):
    """Save the current paper-account equity state."""

    st.subheader("Performance Snapshot")

    info_column, button_column = st.columns([2, 1])

    info_column.info(
        "Save the current account state to build equity and "
        "drawdown history."
    )

    save_clicked = button_column.button(
        "Save Equity Snapshot",
        type="primary",
        use_container_width=True,
        key="save_paper_equity_snapshot",
    )

    if not save_clicked:
        return

    success, message, _ = save_equity_snapshot(
        account_id=account.id,
        cash_balance=account.cash_balance,
        market_value=totals["market_value"],
        starting_cash=account.starting_cash,
    )

    if success:
        st.success(message)
        st.rerun()

    st.error(message)


def render_performance_history(account_id):
    """Render paper-account equity and drawdown history."""

    st.subheader("Paper Trading Performance")

    snapshots = get_paper_equity_snapshots(
        account_id=account_id,
        limit=500,
    )

    if not snapshots:
        st.info(
            "No equity snapshots saved. "
            "Save a snapshot to start performance tracking."
        )
        return

    rows = []

    for snapshot in snapshots:
        rows.append(
            {
                "Snapshot Time": snapshot.snapshot_time,
                "Account Equity": snapshot.account_equity,
                "Peak Equity": snapshot.peak_equity,
                "Return %": snapshot.total_return_pct,
                "Drawdown": snapshot.drawdown_value,
                "Drawdown %": snapshot.drawdown_pct,
                "Cash Balance": snapshot.cash_balance,
                "Market Value": snapshot.market_value,
                "Total P/L": snapshot.total_profit_loss,
            }
        )

    history_dataframe = pd.DataFrame(rows)
    history_dataframe["Snapshot Time"] = pd.to_datetime(
        history_dataframe["Snapshot Time"],
        errors="coerce",
    )
    history_dataframe = history_dataframe.dropna(
        subset=["Snapshot Time"]
    ).sort_values("Snapshot Time")

    if history_dataframe.empty:
        st.info("No valid equity snapshot records were found.")
        return

    latest = history_dataframe.iloc[-1]

    metric1, metric2, metric3, metric4 = st.columns(4)

    metric1.metric(
        "Latest Equity",
        format_currency(latest["Account Equity"]),
    )
    metric2.metric(
        "Peak Equity",
        format_currency(latest["Peak Equity"]),
    )
    metric3.metric(
        "Drawdown",
        format_currency(latest["Drawdown"]),
        delta=f'{float(latest["Drawdown %"]):.2f}%',
    )
    metric4.metric(
        "Return",
        f'{float(latest["Return %"]):.2f}%',
    )

    equity_chart = history_dataframe[
        [
            "Snapshot Time",
            "Account Equity",
            "Peak Equity",
        ]
    ].set_index("Snapshot Time")

    st.line_chart(
        equity_chart,
        use_container_width=True,
    )

    drawdown_chart = history_dataframe[
        [
            "Snapshot Time",
            "Drawdown %",
        ]
    ].set_index("Snapshot Time")

    st.line_chart(
        drawdown_chart,
        use_container_width=True,
    )

    with st.expander(
        "View Equity Snapshot History",
        expanded=False,
    ):
        st.dataframe(
            history_dataframe,
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

    render_account_management(account)
    risk_settings = render_risk_settings()

    position_dataframe, totals = load_position_dashboard(
        account.id
    )

    render_account_summary(
        account=account,
        totals=totals,
    )

    render_snapshot_control(
        account=account,
        totals=totals,
    )

    render_performance_history(account.id)

    st.divider()

    order_column, position_column = st.columns(
        [1, 2],
        gap="large",
    )

    with order_column:
        render_order_ticket(
            account=account,
            risk_settings=risk_settings,
        )

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
