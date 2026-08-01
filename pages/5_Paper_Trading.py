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
from services.paper_trading_analytics import calculate_paper_trading_analytics
from services.paper_portfolio_exposure import calculate_portfolio_exposure
from services.paper_portfolio_rebalance import calculate_rebalance_plan
from services.paper_rebalance_execution import execute_rebalance_batch
from services.paper_rebalance_execution import validate_rebalance_batch
from services.paper_rebalance_audit import get_rebalance_batch
from services.paper_rebalance_audit import get_rebalance_batches
from services.paper_rebalance_audit import get_rebalance_batch_items
from services.paper_rebalance_audit import json_loads
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



def format_profit_factor(value):
    """Format a profit-factor value for display."""

    if value is None:
        return "N/A"

    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return "N/A"

    if numeric_value == float("inf"):
        return "∞"

    return f"{numeric_value:.2f}"


def render_trading_analytics(account_id):
    """Render closed-trade analytics for a paper account."""

    st.subheader("Closed-Trade Analytics")

    analytics = calculate_paper_trading_analytics(
        account_id=account_id
    )

    closed_trades = int(analytics["closed_trades"])

    if closed_trades == 0:
        st.info(
            "No completed SELL trades are available for "
            "closed-trade analytics."
        )
        return

    metric1, metric2, metric3, metric4 = st.columns(4)

    metric1.metric(
        "Closed Trades",
        closed_trades,
        delta=(
            f'{analytics["winning_trades"]} wins / '
            f'{analytics["losing_trades"]} losses'
        ),
    )

    metric2.metric(
        "Win Rate",
        f'{float(analytics["win_rate_pct"]):.2f}%',
    )

    metric3.metric(
        "Net Realized P/L",
        format_currency(
            analytics["net_realized_profit_loss"]
        ),
    )

    metric4.metric(
        "Trade Expectancy",
        format_currency(
            analytics["trade_expectancy"]
        ),
        help=(
            "Average realized profit or loss per completed "
            "SELL trade."
        ),
    )

    detail1, detail2, detail3, detail4 = st.columns(4)

    detail1.metric(
        "Profit Factor",
        format_profit_factor(
            analytics["profit_factor"]
        ),
        help=(
            "Gross profit divided by absolute gross loss."
        ),
    )

    detail2.metric(
        "Average Gain",
        format_currency(
            analytics["average_gain"]
        ),
    )

    detail3.metric(
        "Average Loss",
        format_currency(
            analytics["average_loss"]
        ),
    )

    detail4.metric(
        "Break-Even Trades",
        int(analytics["breakeven_trades"]),
    )

    result1, result2, result3, result4 = st.columns(4)

    result1.metric(
        "Largest Winner",
        format_currency(
            analytics["largest_winner"]
        ),
    )

    result2.metric(
        "Largest Loser",
        format_currency(
            analytics["largest_loser"]
        ),
    )

    result3.metric(
        "Gross Profit",
        format_currency(
            analytics["gross_profit"]
        ),
    )

    result4.metric(
        "Gross Loss",
        format_currency(
            analytics["gross_loss"]
        ),
    )

    ticker_tab, closed_trade_tab = st.tabs(
        [
            "Performance by Ticker",
            "Closed-Trade History",
        ]
    )

    with ticker_tab:
        ticker_rows = analytics["by_ticker"]

        if not ticker_rows:
            st.info("No ticker-level analytics are available.")
        else:
            ticker_dataframe = pd.DataFrame(ticker_rows)

            ticker_dataframe = ticker_dataframe.rename(
                columns={
                    "ticker": "Ticker",
                    "closed_trades": "Closed Trades",
                    "winning_trades": "Wins",
                    "losing_trades": "Losses",
                    "breakeven_trades": "Break-Even",
                    "win_rate_pct": "Win Rate %",
                    "gross_profit": "Gross Profit",
                    "gross_loss": "Gross Loss",
                    "net_realized_profit_loss": "Net Realized P/L",
                    "trade_expectancy": "Expectancy",
                    "profit_factor": "Profit Factor",
                    "shares_sold": "Shares Sold",
                    "sell_value": "Sell Value",
                }
            )

            currency_columns = [
                "Gross Profit",
                "Gross Loss",
                "Net Realized P/L",
                "Expectancy",
                "Sell Value",
            ]

            for column in currency_columns:
                ticker_dataframe[column] = (
                    ticker_dataframe[column].map(
                        format_currency
                    )
                )

            ticker_dataframe["Win Rate %"] = (
                ticker_dataframe["Win Rate %"].map(
                    lambda value: f"{float(value):.2f}%"
                )
            )

            ticker_dataframe["Profit Factor"] = (
                ticker_dataframe["Profit Factor"].map(
                    format_profit_factor
                )
            )

            st.dataframe(
                ticker_dataframe,
                use_container_width=True,
                hide_index=True,
            )

    with closed_trade_tab:
        closed_trade_rows = analytics[
            "closed_trade_rows"
        ]

        if not closed_trade_rows:
            st.info("No completed SELL trades are available.")
        else:
            closed_trade_dataframe = pd.DataFrame(
                closed_trade_rows
            )

            closed_trade_dataframe = (
                closed_trade_dataframe.rename(
                    columns={
                        "trade_id": "Trade ID",
                        "order_id": "Order ID",
                        "executed_at": "Executed",
                        "ticker": "Ticker",
                        "side": "Side",
                        "quantity": "Quantity",
                        "execution_price": "Execution Price",
                        "gross_value": "Gross Value",
                        "realized_profit_loss": "Realized P/L",
                        "result": "Result",
                    }
                )
            )

            for column in [
                "Execution Price",
                "Gross Value",
                "Realized P/L",
            ]:
                closed_trade_dataframe[column] = (
                    closed_trade_dataframe[column].map(
                        format_currency
                    )
                )

            st.dataframe(
                closed_trade_dataframe,
                use_container_width=True,
                hide_index=True,
            )



def render_portfolio_exposure(
    account,
    position_dataframe,
    risk_settings,
):
    """Render portfolio allocation and concentration analytics."""

    st.subheader("Portfolio Exposure and Risk")

    if position_dataframe.empty:
        position_rows = []
    else:
        position_rows = position_dataframe.to_dict(
            orient="records"
        )

    exposure_settings = {
        "max_position_value_pct": risk_settings.get(
            "max_position_value_pct",
            20.0,
        ),
        "warning_position_value_pct": risk_settings.get(
            "warn_position_value_pct",
            15.0,
        ),
        "minimum_cash_reserve_pct": risk_settings.get(
            "minimum_cash_reserve_pct",
            10.0,
        ),
    }

    exposure = calculate_portfolio_exposure(
        cash_balance=account.cash_balance,
        position_rows=position_rows,
        settings=exposure_settings,
    )

    metric1, metric2, metric3, metric4 = st.columns(4)

    metric1.metric(
        "Cash Allocation",
        f'{float(exposure["cash_allocation_pct"]):.2f}%',
        delta=format_currency(
            exposure["cash_balance"]
        ),
    )

    metric2.metric(
        "Invested Allocation",
        f'{float(exposure["invested_allocation_pct"]):.2f}%',
        delta=format_currency(
            exposure["invested_value"]
        ),
    )

    metric3.metric(
        "Position Count",
        int(exposure["position_count"]),
    )

    largest_ticker = (
        exposure["largest_position_ticker"]
        or "None"
    )

    metric4.metric(
        "Largest Position",
        largest_ticker,
        delta=(
            f'{float(exposure["largest_position_weight_pct"]):.2f}% '
            "of equity"
        ),
    )

    detail1, detail2, detail3, detail4 = st.columns(4)

    detail1.metric(
        "Diversification Score",
        f'{float(exposure["diversification_score"]):.2f}/100',
        help=(
            "Higher scores indicate a more evenly distributed "
            "portfolio. A one-position portfolio scores zero."
        ),
    )

    detail2.metric(
        "Concentration Index",
        f'{float(exposure["concentration_index"]):.4f}',
        help=(
            "Sum of squared invested-position weights. "
            "Lower values generally indicate broader diversification."
        ),
    )

    detail3.metric(
        "Largest Position Limit Used",
        (
            f'{float(exposure["largest_position_limit_utilization_pct"]):.2f}%'
        ),
        delta=(
            f'Limit: '
            f'{float(exposure["max_position_limit_pct"]):.2f}%'
        ),
    )

    detail4.metric(
        "Cash Reserve Coverage",
        f'{float(exposure["cash_reserve_utilization_pct"]):.2f}%',
        delta=(
            f'Minimum reserve: '
            f'{float(exposure["cash_reserve_limit_pct"]):.2f}%'
        ),
        help=(
            "A value of 100% means the portfolio exactly meets "
            "the configured minimum cash reserve."
        ),
    )

    st.caption(
        "Largest-position utilization compares the position's "
        "portfolio weight with the configured maximum-position limit."
    )

    warnings = exposure.get("warnings", [])

    if warnings:
        st.warning(
            "Portfolio risk controls require attention."
        )

        for warning in warnings:
            st.warning(str(warning))
    else:
        st.success(
            "Portfolio exposure is within the configured "
            "concentration and cash-reserve limits."
        )

    position_rows = exposure.get("positions", [])

    if not position_rows:
        st.info(
            "No open positions are available for exposure analysis."
        )
        return

    exposure_dataframe = pd.DataFrame(position_rows)

    exposure_dataframe = exposure_dataframe.rename(
        columns={
            "ticker": "Ticker",
            "quantity": "Shares",
            "average_cost": "Average Cost",
            "current_price": "Current Price",
            "cost_basis": "Cost Basis",
            "market_value": "Market Value",
            "unrealized_profit_loss": "Unrealized P/L",
            "portfolio_weight_pct": "Portfolio Weight %",
            "invested_weight_pct": "Invested Weight %",
            "unrealized_risk_contribution_pct": (
                "Unrealized Risk Contribution %"
            ),
            "position_limit_utilization_pct": (
                "Position Limit Used %"
            ),
            "concentration_status": "Risk Status",
        }
    )

    currency_columns = [
        "Average Cost",
        "Current Price",
        "Cost Basis",
        "Market Value",
        "Unrealized P/L",
    ]

    for column in currency_columns:
        exposure_dataframe[column] = (
            exposure_dataframe[column].map(
                format_currency
            )
        )

    percentage_columns = [
        "Portfolio Weight %",
        "Invested Weight %",
        "Unrealized Risk Contribution %",
        "Position Limit Used %",
    ]

    for column in percentage_columns:
        exposure_dataframe[column] = (
            exposure_dataframe[column].map(
                lambda value: f"{float(value):.2f}%"
            )
        )

    display_columns = [
        "Ticker",
        "Shares",
        "Market Value",
        "Portfolio Weight %",
        "Invested Weight %",
        "Unrealized P/L",
        "Unrealized Risk Contribution %",
        "Position Limit Used %",
        "Risk Status",
    ]

    st.dataframe(
        exposure_dataframe[display_columns],
        use_container_width=True,
        hide_index=True,
    )



def render_rebalance_execution_result(account_id):
    """Render the most recent rebalance execution result."""

    state_key = (
        f"last_rebalance_execution_{int(account_id)}"
    )

    result = st.session_state.get(state_key)

    if not result:
        return

    st.markdown("#### Last Rebalance Execution")

    if result.get("success"):
        st.success(result.get("message"))
    else:
        st.warning(result.get("message"))

    summary1, summary2, summary3 = st.columns(3)

    summary1.metric(
        "Filled",
        int(result.get("filled_count", 0)),
    )

    summary2.metric(
        "Failed",
        int(result.get("failed_count", 0)),
    )

    summary3.metric(
        "Not Executed",
        int(result.get("unexecuted_count", 0)),
    )

    audit_uid = result.get("audit_batch_uid")
    audit_status = result.get(
        "audit_status",
        "NOT_CREATED",
    )

    if audit_uid:
        st.caption(
            f"Audit batch: {audit_uid} | "
            f"Audit status: {audit_status}"
        )
    else:
        st.caption(
            f"Audit status: {audit_status}"
        )

    for audit_error in result.get(
        "audit_errors",
        [],
    ):
        st.error(
            "Audit trail warning: "
            + str(audit_error)
        )

    result_rows = []

    for row in result.get("results", []):
        result_rows.append(
            {
                "Ticker": row.get("ticker"),
                "Action": row.get("action"),
                "Quantity": row.get("quantity"),
                "Execution Price": row.get(
                    "execution_price"
                ),
                "Estimated Value": row.get(
                    "estimated_value"
                ),
                "Status": (
                    "FILLED"
                    if row.get("success")
                    else "FAILED"
                ),
                "Order ID": row.get("order_id"),
                "Trade ID": row.get("trade_id"),
                "Realized P/L": row.get(
                    "realized_profit_loss",
                    0.0,
                ),
                "Message": row.get("message"),
            }
        )

    if result_rows:
        result_dataframe = pd.DataFrame(result_rows)

        st.dataframe(
            result_dataframe,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Quantity": (
                    st.column_config.NumberColumn(
                        format="%.6f"
                    )
                ),
                "Execution Price": (
                    st.column_config.NumberColumn(
                        format="$%.2f"
                    )
                ),
                "Estimated Value": (
                    st.column_config.NumberColumn(
                        format="$%.2f"
                    )
                ),
                "Realized P/L": (
                    st.column_config.NumberColumn(
                        format="$%.2f"
                    )
                ),
            },
        )

    if st.button(
        "Clear Execution Result",
        key=f"clear_rebalance_result_{account_id}",
    ):
        st.session_state.pop(state_key, None)
        st.rerun()


def render_rebalance_execution_controls(
    account,
    actionable_rows,
    risk_settings,
    target_allocations,
    rebalance_settings,
):
    """Render guarded selection and execution controls."""

    confirmation_key = (
        f"rebalance_confirmation_{account.id}"
    )
    selection_version_key = (
        f"rebalance_selection_version_{account.id}"
    )
    reset_key = (
        f"reset_rebalance_widgets_{account.id}"
    )

    if selection_version_key not in st.session_state:
        st.session_state[selection_version_key] = 0

    # Widget-bound state must be reset before the widgets
    # are instantiated during this script run.
    if st.session_state.pop(reset_key, False):
        st.session_state[confirmation_key] = ""
        st.session_state[selection_version_key] += 1

    selection_key = (
        f"rebalance_execution_selection_{account.id}_"
        f"{st.session_state[selection_version_key]}"
    )

    st.markdown("#### Rebalance Execution")

    st.warning(
        "Executing selected rows creates real paper orders "
        "and changes paper-account cash and positions."
    )

    render_rebalance_execution_result(account.id)

    if actionable_rows.empty:
        st.info(
            "No actionable BUY or SELL recommendations "
            "are available."
        )
        return

    execution_dataframe = actionable_rows[
        [
            "Ticker",
            "Suggested Action",
            "Suggested Shares",
            "Current Price",
            "Suggested Value",
            "Alert Level",
        ]
    ].copy()

    execution_dataframe.insert(
        0,
        "Execute",
        False,
    )

    edited_execution = st.data_editor(
        execution_dataframe,
        use_container_width=True,
        hide_index=True,
        disabled=[
            "Ticker",
            "Suggested Action",
            "Suggested Shares",
            "Current Price",
            "Suggested Value",
            "Alert Level",
        ],
        column_config={
            "Execute": st.column_config.CheckboxColumn(
                "Execute",
                help=(
                    "Select this recommendation for the "
                    "execution batch."
                ),
                default=False,
            ),
            "Suggested Shares": (
                st.column_config.NumberColumn(
                    format="%.6f"
                )
            ),
            "Current Price": (
                st.column_config.NumberColumn(
                    format="$%.2f"
                )
            ),
            "Suggested Value": (
                st.column_config.NumberColumn(
                    format="$%.2f"
                )
            ),
        },
        key=selection_key,
    )

    selected_dataframe = edited_execution[
        edited_execution["Execute"] == True
    ].copy()

    selected_candidates = selected_dataframe[
        [
            "Ticker",
            "Suggested Action",
            "Suggested Shares",
            "Current Price",
        ]
    ].to_dict(orient="records")

    preview = validate_rebalance_batch(
        account_id=account.id,
        selected_candidates=selected_candidates,
    )

    estimated_net_cash_change = (
        float(preview["estimated_sell_value"])
        - float(preview["estimated_buy_value"])
    )

    preview1, preview2, preview3, preview4 = (
        st.columns(4)
    )

    preview1.metric(
        "Selected Orders",
        len(selected_candidates),
    )

    preview2.metric(
        "Estimated Buys",
        format_currency(
            preview["estimated_buy_value"]
        ),
    )

    preview3.metric(
        "Estimated Sells",
        format_currency(
            preview["estimated_sell_value"]
        ),
    )

    preview4.metric(
        "Estimated Cash Change",
        format_currency(
            estimated_net_cash_change
        ),
        delta=(
            "Cash increase"
            if estimated_net_cash_change > 0
            else (
                "Cash decrease"
                if estimated_net_cash_change < 0
                else "Cash neutral"
            )
        ),
    )

    if selected_candidates:
        if preview["rejected"]:
            st.error(
                "The selected batch contains rejected rows "
                "and cannot be executed."
            )

            for row in preview["rejected"]:
                st.error(
                    f'{row.get("ticker") or "Unknown"}: '
                    f'{row.get("error")}'
                )
        else:
            st.success(
                f'{preview["approved_count"]} selected '
                "recommendation(s) passed preview validation."
            )
    else:
        st.info(
            "Select at least one recommendation to prepare "
            "an execution batch."
        )

    confirmation_phrase = "EXECUTE REBALANCE"

    confirmation = st.text_input(
        f'Type "{confirmation_phrase}" to confirm',
        value="",
        key=confirmation_key,
        disabled=not selected_candidates,
    )

    stop_on_failure = st.toggle(
        "Stop batch after first failed order",
        value=True,
        key=f"rebalance_stop_on_failure_{account.id}",
        help=(
            "Recommended. Previously filled orders are not "
            "automatically reversed if a later order fails."
        ),
    )

    execute_disabled = (
        not selected_candidates
        or bool(preview["rejected"])
        or confirmation.strip().upper()
        != confirmation_phrase
    )

    execute_clicked = st.button(
        "Execute Selected Rebalance Orders",
        type="primary",
        use_container_width=True,
        disabled=execute_disabled,
        key=f"execute_rebalance_batch_{account.id}",
    )

    if not execute_clicked:
        return

    # Validate again immediately before placing orders.
    final_preview = validate_rebalance_batch(
        account_id=account.id,
        selected_candidates=selected_candidates,
    )

    if not final_preview["valid"]:
        st.error(
            "Execution blocked because the selected batch "
            "failed final validation."
        )

        for row in final_preview["rejected"]:
            st.error(
                f'{row.get("ticker") or "Unknown"}: '
                f'{row.get("error")}'
            )

        return

    with st.spinner(
        "Executing selected paper rebalance orders..."
    ):
        execution_result = execute_rebalance_batch(
            account_id=account.id,
            selected_candidates=selected_candidates,
            risk_settings=risk_settings,
            stop_on_failure=stop_on_failure,
            target_allocations=target_allocations,
            rebalance_settings=rebalance_settings,
            cash_balance=float(account.cash_balance),
        )

    state_key = (
        f"last_rebalance_execution_{int(account.id)}"
    )

    st.session_state[state_key] = execution_result

    # Defer widget-bound state resets until the next
    # script run, before the widgets are instantiated.
    st.session_state[reset_key] = True

    st.rerun()


def render_portfolio_rebalancing(
    account,
    position_dataframe,
    risk_settings,
):
    """Render editable target allocations and rebalance guidance."""

    st.subheader("Portfolio Rebalancing and Drift Detection")

    st.caption(
        "Recommendations are informational only. "
        "This section does not submit paper orders."
    )

    if position_dataframe.empty:
        st.info(
            "No open positions are available for "
            "rebalancing analysis."
        )
        return

    source_dataframe = position_dataframe.copy()

    required_columns = {
        "Ticker",
        "Shares",
        "Current Price",
        "Market Value",
    }

    missing_columns = required_columns.difference(
        source_dataframe.columns
    )

    if missing_columns:
        st.error(
            "Rebalance analysis cannot run because the "
            "position data is missing: "
            + ", ".join(sorted(missing_columns))
        )
        return

    source_dataframe = source_dataframe[
        source_dataframe["Shares"].astype(float) > 0
    ].copy()

    source_dataframe = source_dataframe[
        source_dataframe["Current Price"].astype(float) > 0
    ].copy()

    if source_dataframe.empty:
        st.info(
            "No positions have valid quantities and prices."
        )
        return

    cash_balance = float(account.cash_balance)

    invested_value = float(
        source_dataframe["Market Value"]
        .astype(float)
        .sum()
    )

    account_equity = cash_balance + invested_value

    if account_equity <= 0:
        st.error(
            "Account equity must be greater than zero "
            "to calculate portfolio drift."
        )
        return

    source_dataframe["Current Weight %"] = (
        source_dataframe["Market Value"].astype(float)
        / account_equity
        * 100.0
    )

    source_dataframe = source_dataframe.sort_values(
        by=["Current Weight %", "Ticker"],
        ascending=[False, True],
    ).reset_index(drop=True)

    target_state_key = (
        f"paper_rebalance_targets_{int(account.id)}"
    )

    current_tickers = (
        source_dataframe["Ticker"]
        .astype(str)
        .str.upper()
        .str.strip()
        .tolist()
    )

    if target_state_key not in st.session_state:
        default_invested_target_pct = min(
            40.0,
            max(
                0.0,
                100.0
                - float(
                    risk_settings.get(
                        "minimum_cash_reserve_pct",
                        10.0,
                    )
                ),
            ),
        )

        equal_target = (
            default_invested_target_pct
            / len(current_tickers)
            if current_tickers
            else 0.0
        )

        st.session_state[target_state_key] = {
            ticker: equal_target
            for ticker in current_tickers
        }
    else:
        existing_targets = dict(
            st.session_state[target_state_key]
        )

        for ticker in current_tickers:
            existing_targets.setdefault(ticker, 0.0)

        existing_targets = {
            ticker: float(existing_targets.get(ticker, 0.0))
            for ticker in current_tickers
        }

        st.session_state[target_state_key] = (
            existing_targets
        )

    control1, control2, control3, control4 = (
        st.columns(4)
    )

    drift_warning_pct = control1.number_input(
        "Drift Warning %",
        min_value=0.0,
        max_value=100.0,
        value=2.0,
        step=0.5,
        format="%.2f",
        key=f"rebalance_warning_{account.id}",
        help=(
            "Positions crossing this absolute drift "
            "threshold are marked WATCH."
        ),
    )

    drift_rebalance_pct = control2.number_input(
        "Rebalance Threshold %",
        min_value=float(drift_warning_pct),
        max_value=100.0,
        value=max(5.0, float(drift_warning_pct)),
        step=0.5,
        format="%.2f",
        key=f"rebalance_threshold_{account.id}",
        help=(
            "Positions crossing this absolute drift "
            "threshold receive a rebalance recommendation."
        ),
    )

    minimum_cash_reserve_pct = control3.number_input(
        "Minimum Cash Reserve %",
        min_value=0.0,
        max_value=100.0,
        value=float(
            risk_settings.get(
                "minimum_cash_reserve_pct",
                10.0,
            )
        ),
        step=0.5,
        format="%.2f",
        key=f"rebalance_cash_reserve_{account.id}",
    )

    allow_fractional_shares = control4.toggle(
        "Allow Fractional Shares",
        value=True,
        key=f"rebalance_fractional_{account.id}",
    )

    target_editor = pd.DataFrame(
        {
            "Ticker": current_tickers,
            "Current Weight %": [
                round(float(value), 2)
                for value in source_dataframe[
                    "Current Weight %"
                ].tolist()
            ],
            "Target Weight %": [
                round(
                    float(
                        st.session_state[
                            target_state_key
                        ].get(ticker, 0.0)
                    ),
                    2,
                )
                for ticker in current_tickers
            ],
        }
    )

    st.markdown("#### Target Allocations")

    edited_targets = st.data_editor(
        target_editor,
        use_container_width=True,
        hide_index=True,
        disabled=[
            "Ticker",
            "Current Weight %",
        ],
        column_config={
            "Ticker": st.column_config.TextColumn(
                "Ticker",
            ),
            "Current Weight %": (
                st.column_config.NumberColumn(
                    "Current Weight %",
                    format="%.2f%%",
                )
            ),
            "Target Weight %": (
                st.column_config.NumberColumn(
                    "Target Weight %",
                    min_value=0.0,
                    max_value=100.0,
                    step=0.25,
                    format="%.2f%%",
                    required=True,
                )
            ),
        },
        key=f"rebalance_target_editor_{account.id}",
    )

    target_allocations = {}

    for row in edited_targets.to_dict(
        orient="records"
    ):
        ticker = str(row["Ticker"]).strip().upper()

        try:
            target_weight = float(
                row["Target Weight %"]
            )
        except (TypeError, ValueError):
            target_weight = 0.0

        target_allocations[ticker] = max(
            target_weight,
            0.0,
        )

    st.session_state[target_state_key] = dict(
        target_allocations
    )

    target_total_pct = sum(
        target_allocations.values()
    )

    target_cash_pct = 100.0 - target_total_pct

    summary1, summary2, summary3 = st.columns(3)

    summary1.metric(
        "Target Invested",
        f"{target_total_pct:.2f}%",
    )

    summary2.metric(
        "Target Cash",
        f"{target_cash_pct:.2f}%",
    )

    summary3.metric(
        "Current Cash",
        f"{cash_balance / account_equity * 100.0:.2f}%",
    )

    if target_total_pct > 100.0:
        st.error(
            "Target position weights total "
            f"{target_total_pct:.2f}%. "
            "The total cannot exceed 100%."
        )
        return

    if target_cash_pct < minimum_cash_reserve_pct:
        st.warning(
            f"Target cash is {target_cash_pct:.2f}%, "
            f"below the configured minimum reserve of "
            f"{minimum_cash_reserve_pct:.2f}%."
        )

    position_rows = []

    for row in source_dataframe.to_dict(
        orient="records"
    ):
        position_rows.append(
            {
                "ticker": row["Ticker"],
                "quantity": float(row["Shares"]),
                "current_price": float(
                    row["Current Price"]
                ),
                "market_value": float(
                    row["Market Value"]
                ),
            }
        )

    try:
        plan = calculate_rebalance_plan(
            account_equity=account_equity,
            cash_balance=cash_balance,
            position_rows=position_rows,
            target_allocations=target_allocations,
            settings={
                "drift_warning_pct": (
                    drift_warning_pct
                ),
                "drift_rebalance_pct": (
                    drift_rebalance_pct
                ),
                "minimum_cash_reserve_pct": (
                    minimum_cash_reserve_pct
                ),
                "allow_fractional_shares": (
                    allow_fractional_shares
                ),
            },
        )
    except ValueError as error:
        st.error(str(error))
        return

    status = plan["overall_status"]

    if status == "REBALANCE REQUIRED":
        st.error(
            "Portfolio status: REBALANCE REQUIRED"
        )
    elif status == "WATCH":
        st.warning("Portfolio status: WATCH")
    else:
        st.success("Portfolio status: ON TARGET")

    metric1, metric2, metric3, metric4 = st.columns(4)

    metric1.metric(
        "Total Absolute Drift",
        f'{float(plan["total_absolute_drift_pct"]):.2f}%',
    )

    metric2.metric(
        "Raw Buy Value",
        format_currency(plan["raw_buy_value"]),
    )

    metric3.metric(
        "Raw Sell Value",
        format_currency(plan["raw_sell_value"]),
    )

    metric4.metric(
        "Available Buying Cash",
        format_currency(
            plan["available_buying_cash"]
        ),
        delta=(
            f'Minimum reserve: '
            f'{float(plan["minimum_cash_reserve_pct"]):.2f}%'
        ),
    )

    alerts = plan.get("alerts", [])

    if alerts:
        with st.expander(
            "Rebalance Alerts",
            expanded=True,
        ):
            for alert in alerts:
                st.warning(str(alert))
    else:
        st.info(
            "No positions currently cross the configured "
            "drift thresholds."
        )

    recommendation_rows = []

    for row in plan.get("rows", []):
        recommendation_rows.append(
            {
                "Ticker": row["ticker"],
                "Current Weight %": (
                    row["current_weight_pct"]
                ),
                "Target Weight %": (
                    row["target_weight_pct"]
                ),
                "Drift %": row["drift_pct"],
                "Absolute Drift %": (
                    row["absolute_drift_pct"]
                ),
                "Allocation Status": (
                    row["allocation_status"]
                ),
                "Alert Level": row["alert_level"],
                "Suggested Action": (
                    row["suggested_action"]
                ),
                "Suggested Shares": (
                    row[
                        "suggested_share_adjustment"
                    ]
                ),
                "Suggested Value": (
                    row[
                        "suggested_adjustment_value"
                    ]
                ),
                "Current Price": (
                    row["current_price"]
                ),
                "Current Value": (
                    row["current_value"]
                ),
                "Target Value": row["target_value"],
                "Note": (
                    row["recommendation_note"]
                ),
            }
        )

    recommendation_dataframe = pd.DataFrame(
        recommendation_rows
    )

    if recommendation_dataframe.empty:
        st.info(
            "No rebalance recommendations are available."
        )
        return

    st.markdown("#### Rebalance Recommendations")

    st.dataframe(
        recommendation_dataframe,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Current Weight %": (
                st.column_config.NumberColumn(
                    format="%.2f%%"
                )
            ),
            "Target Weight %": (
                st.column_config.NumberColumn(
                    format="%.2f%%"
                )
            ),
            "Drift %": (
                st.column_config.NumberColumn(
                    format="%+.2f%%"
                )
            ),
            "Absolute Drift %": (
                st.column_config.NumberColumn(
                    format="%.2f%%"
                )
            ),
            "Suggested Shares": (
                st.column_config.NumberColumn(
                    format="%.6f"
                )
            ),
            "Suggested Value": (
                st.column_config.NumberColumn(
                    format="$%.2f"
                )
            ),
            "Current Price": (
                st.column_config.NumberColumn(
                    format="$%.2f"
                )
            ),
            "Current Value": (
                st.column_config.NumberColumn(
                    format="$%.2f"
                )
            ),
            "Target Value": (
                st.column_config.NumberColumn(
                    format="$%.2f"
                )
            ),
        },
    )

    actionable_rows = recommendation_dataframe[
        recommendation_dataframe[
            "Suggested Action"
        ].isin(["BUY", "SELL"])
    ]

    st.caption(
        f"{len(actionable_rows)} actionable recommendation(s). "
        "ON TARGET positions remain HOLD."
    )

    render_rebalance_execution_controls(
        account=account,
        actionable_rows=actionable_rows,
        risk_settings=risk_settings,
        target_allocations=target_allocations,
        rebalance_settings={
            "drift_warning_pct": float(
                drift_warning_pct
            ),
            "drift_rebalance_pct": float(
                drift_rebalance_pct
            ),
            "minimum_cash_reserve_pct": float(
                minimum_cash_reserve_pct
            ),
            "allow_fractional_shares": bool(
                allow_fractional_shares
            ),
            "target_cash_pct": float(
                target_cash_pct
            ),
        },
    )



def build_rebalance_batch_dataframe(batches):
    """Convert rebalance audit batches to a display dataframe."""

    rows = []

    for batch in batches:
        rows.append(
            {
                "Batch ID": batch.id,
                "Batch UID": batch.batch_uid,
                "Created": batch.created_at,
                "Started": batch.started_at,
                "Completed": batch.completed_at,
                "Status": batch.status,
                "Selected": batch.selected_count,
                "Filled": batch.filled_count,
                "Failed": batch.failed_count,
                "Not Executed": batch.unexecuted_count,
                "Estimated Buys": (
                    batch.estimated_buy_value
                ),
                "Estimated Sells": (
                    batch.estimated_sell_value
                ),
                "Stop on Failure": (
                    batch.stop_on_failure
                ),
                "Message": batch.result_message,
            }
        )

    return pd.DataFrame(rows)


def build_rebalance_item_dataframe(items):
    """Convert rebalance audit items to a display dataframe."""

    rows = []

    for item in items:
        rows.append(
            {
                "Sequence": item.sequence_number,
                "Ticker": item.ticker,
                "Action": item.action,
                "Requested Quantity": (
                    item.requested_quantity
                ),
                "Requested Price": (
                    item.requested_price
                ),
                "Estimated Value": (
                    item.estimated_value
                ),
                "Status": item.status,
                "Order ID": item.order_id,
                "Trade ID": item.trade_id,
                "Owned Before": (
                    item.owned_quantity_before
                ),
                "Quantity After": (
                    item.quantity_after
                ),
                "Cash After": (
                    item.cash_balance_after
                ),
                "Realized P/L": (
                    item.realized_profit_loss
                ),
                "Executed": item.executed_at,
                "Message": item.result_message,
            }
        )

    return pd.DataFrame(rows)


def build_portfolio_comparison(
    pre_portfolio,
    post_portfolio,
):
    """Compare pre- and post-rebalance position quantities."""

    pre_portfolio = pre_portfolio or {}
    post_portfolio = post_portfolio or {}

    pre_positions = {
        str(row.get("ticker", "")).upper(): row
        for row in pre_portfolio.get("positions", [])
        if row.get("ticker")
    }

    post_positions = {
        str(row.get("ticker", "")).upper(): row
        for row in post_portfolio.get("positions", [])
        if row.get("ticker")
    }

    tickers = sorted(
        set(pre_positions) | set(post_positions)
    )

    rows = []

    for ticker in tickers:
        pre_row = pre_positions.get(ticker, {})
        post_row = post_positions.get(ticker, {})

        quantity_before = float(
            pre_row.get("quantity", 0.0) or 0.0
        )
        quantity_after = float(
            post_row.get("quantity", 0.0) or 0.0
        )

        average_cost_before = float(
            pre_row.get("average_cost", 0.0) or 0.0
        )
        average_cost_after = float(
            post_row.get("average_cost", 0.0) or 0.0
        )

        realized_before = float(
            pre_row.get(
                "realized_profit_loss",
                0.0,
            )
            or 0.0
        )
        realized_after = float(
            post_row.get(
                "realized_profit_loss",
                0.0,
            )
            or 0.0
        )

        rows.append(
            {
                "Ticker": ticker,
                "Quantity Before": quantity_before,
                "Quantity After": quantity_after,
                "Quantity Change": (
                    quantity_after - quantity_before
                ),
                "Average Cost Before": (
                    average_cost_before
                ),
                "Average Cost After": (
                    average_cost_after
                ),
                "Realized P/L Before": (
                    realized_before
                ),
                "Realized P/L After": (
                    realized_after
                ),
                "Realized P/L Change": (
                    realized_after - realized_before
                ),
            }
        )

    return pd.DataFrame(rows)


def render_json_settings_table(title, values):
    """Render a dictionary as a two-column table."""

    st.markdown(f"##### {title}")

    if not isinstance(values, dict) or not values:
        st.info(f"No {title.lower()} were stored.")
        return

    rows = []

    for key, value in sorted(values.items()):
        rows.append(
            {
                "Setting": str(key),
                "Value": value,
            }
        )

    st.dataframe(
        pd.DataFrame(rows),
        use_container_width=True,
        hide_index=True,
    )


def render_rebalance_history(account_id):
    """Render persistent rebalance batch history and drill-down."""

    st.subheader("Rebalance Audit History")

    all_batches = get_rebalance_batches(
        account_id=account_id,
        limit=500,
    )

    if not all_batches:
        st.info(
            "No persisted rebalance audit batches "
            "are available."
        )
        return

    filter1, filter2, filter3 = st.columns(3)

    available_statuses = sorted(
        {
            str(batch.status)
            for batch in all_batches
            if batch.status
        }
    )

    selected_statuses = filter1.multiselect(
        "Batch Status",
        options=available_statuses,
        default=available_statuses,
        key=f"rebalance_history_status_{account_id}",
    )

    minimum_filled = filter2.number_input(
        "Minimum Filled Orders",
        min_value=0,
        max_value=100000,
        value=0,
        step=1,
        key=f"rebalance_history_min_filled_{account_id}",
    )

    history_limit = filter3.selectbox(
        "Recent Batch Limit",
        options=[10, 25, 50, 100, 250, 500],
        index=2,
        key=f"rebalance_history_limit_{account_id}",
    )

    filtered_batches = [
        batch
        for batch in all_batches
        if (
            (
                not selected_statuses
                or batch.status in selected_statuses
            )
            and int(batch.filled_count or 0)
            >= int(minimum_filled)
        )
    ][:int(history_limit)]

    if not filtered_batches:
        st.warning(
            "No rebalance batches match the "
            "selected filters."
        )
        return

    batch_dataframe = (
        build_rebalance_batch_dataframe(
            filtered_batches
        )
    )

    summary1, summary2, summary3, summary4 = (
        st.columns(4)
    )

    summary1.metric(
        "Visible Batches",
        len(filtered_batches),
    )

    summary2.metric(
        "Filled Orders",
        int(
            batch_dataframe["Filled"]
            .fillna(0)
            .sum()
        ),
    )

    summary3.metric(
        "Failed Orders",
        int(
            batch_dataframe["Failed"]
            .fillna(0)
            .sum()
        ),
    )

    summary4.metric(
        "Estimated Turnover",
        format_currency(
            batch_dataframe[
                "Estimated Buys"
            ].fillna(0).sum()
            + batch_dataframe[
                "Estimated Sells"
            ].fillna(0).sum()
        ),
    )

    st.dataframe(
        batch_dataframe,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Estimated Buys": (
                st.column_config.NumberColumn(
                    format="$%.2f"
                )
            ),
            "Estimated Sells": (
                st.column_config.NumberColumn(
                    format="$%.2f"
                )
            ),
        },
    )

    batch_csv = batch_dataframe.to_csv(
        index=False
    ).encode("utf-8")

    st.download_button(
        "Download Batch History CSV",
        data=batch_csv,
        file_name=(
            f"rebalance_batch_history_"
            f"account_{account_id}.csv"
        ),
        mime="text/csv",
        key=f"download_rebalance_batches_{account_id}",
    )

    batch_options = {
        (
            f"{batch.batch_uid} | "
            f"{batch.status} | "
            f"{batch.created_at}"
        ): batch.id
        for batch in filtered_batches
    }

    selected_label = st.selectbox(
        "Select Batch for Drill-Down",
        options=list(batch_options.keys()),
        key=f"rebalance_history_batch_{account_id}",
    )

    selected_batch_id = batch_options[
        selected_label
    ]

    batch = get_rebalance_batch(
        batch_id=selected_batch_id,
        account_id=account_id,
    )

    if batch is None:
        st.error(
            "The selected rebalance batch "
            "could not be loaded."
        )
        return

    st.markdown("#### Batch Detail")

    detail1, detail2, detail3, detail4 = (
        st.columns(4)
    )

    detail1.metric(
        "Status",
        batch.status,
    )

    detail2.metric(
        "Filled",
        int(batch.filled_count or 0),
    )

    detail3.metric(
        "Failed",
        int(batch.failed_count or 0),
    )

    detail4.metric(
        "Not Executed",
        int(batch.unexecuted_count or 0),
    )

    st.caption(
        f"Batch UID: {batch.batch_uid} | "
        f"Created: {batch.created_at} | "
        f"Completed: {batch.completed_at or 'Not completed'}"
    )

    if batch.result_message:
        st.info(batch.result_message)

    target_allocations = json_loads(
        batch.target_allocations_json,
        default={},
    )

    risk_settings = json_loads(
        batch.risk_settings_json,
        default={},
    )

    rebalance_settings = json_loads(
        batch.rebalance_settings_json,
        default={},
    )

    settings_tab1, settings_tab2, settings_tab3 = (
        st.tabs(
            [
                "Target Allocations",
                "Risk Settings",
                "Rebalance Settings",
            ]
        )
    )

    with settings_tab1:
        if target_allocations:
            allocation_rows = [
                {
                    "Ticker": ticker,
                    "Target Weight %": value,
                }
                for ticker, value in sorted(
                    target_allocations.items()
                )
            ]

            st.dataframe(
                pd.DataFrame(allocation_rows),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Target Weight %": (
                        st.column_config.NumberColumn(
                            format="%.2f%%"
                        )
                    )
                },
            )
        else:
            st.info(
                "No target allocations were stored."
            )

    with settings_tab2:
        render_json_settings_table(
            "Risk Settings",
            risk_settings,
        )

    with settings_tab3:
        render_json_settings_table(
            "Rebalance Settings",
            rebalance_settings,
        )

    items = get_rebalance_batch_items(
        batch_id=batch.id
    )

    st.markdown("#### Batch Orders and Trades")

    item_dataframe = (
        build_rebalance_item_dataframe(items)
    )

    if item_dataframe.empty:
        st.info(
            "No item records were stored for this batch."
        )
    else:
        st.dataframe(
            item_dataframe,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Requested Quantity": (
                    st.column_config.NumberColumn(
                        format="%.6f"
                    )
                ),
                "Requested Price": (
                    st.column_config.NumberColumn(
                        format="$%.2f"
                    )
                ),
                "Estimated Value": (
                    st.column_config.NumberColumn(
                        format="$%.2f"
                    )
                ),
                "Owned Before": (
                    st.column_config.NumberColumn(
                        format="%.6f"
                    )
                ),
                "Quantity After": (
                    st.column_config.NumberColumn(
                        format="%.6f"
                    )
                ),
                "Cash After": (
                    st.column_config.NumberColumn(
                        format="$%.2f"
                    )
                ),
                "Realized P/L": (
                    st.column_config.NumberColumn(
                        format="$%.2f"
                    )
                ),
            },
        )

        item_csv = item_dataframe.to_csv(
            index=False
        ).encode("utf-8")

        st.download_button(
            "Download Selected Batch Items CSV",
            data=item_csv,
            file_name=(
                f"{batch.batch_uid}_items.csv"
            ),
            mime="text/csv",
            key=(
                f"download_rebalance_items_"
                f"{batch.id}"
            ),
        )

    pre_portfolio = json_loads(
        batch.pre_portfolio_json,
        default={},
    )

    post_portfolio = json_loads(
        batch.post_portfolio_json,
        default={},
    )

    st.markdown("#### Pre/Post Portfolio Comparison")

    cash_before = pre_portfolio.get(
        "cash_balance"
    )
    cash_after = post_portfolio.get(
        "cash_balance"
    )

    cash1, cash2, cash3 = st.columns(3)

    cash1.metric(
        "Cash Before",
        (
            format_currency(cash_before)
            if cash_before is not None
            else "Not stored"
        ),
    )

    cash2.metric(
        "Cash After",
        (
            format_currency(cash_after)
            if cash_after is not None
            else "Not stored"
        ),
    )

    if (
        cash_before is not None
        and cash_after is not None
    ):
        cash_change = (
            float(cash_after)
            - float(cash_before)
        )

        cash3.metric(
            "Cash Change",
            format_currency(cash_change),
        )
    else:
        cash3.metric(
            "Cash Change",
            "Unavailable",
        )

    comparison_dataframe = (
        build_portfolio_comparison(
            pre_portfolio=pre_portfolio,
            post_portfolio=post_portfolio,
        )
    )

    if comparison_dataframe.empty:
        st.info(
            "No pre/post position comparison "
            "is available."
        )
    else:
        changed_only = st.toggle(
            "Show Changed Positions Only",
            value=True,
            key=(
                f"rebalance_changed_only_"
                f"{batch.id}"
            ),
        )

        display_comparison = (
            comparison_dataframe.copy()
        )

        if changed_only:
            display_comparison = (
                display_comparison[
                    display_comparison[
                        "Quantity Change"
                    ].abs() > 1e-9
                ]
            )

        if display_comparison.empty:
            st.info(
                "No position quantities changed "
                "in this batch."
            )
        else:
            st.dataframe(
                display_comparison,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Quantity Before": (
                        st.column_config.NumberColumn(
                            format="%.6f"
                        )
                    ),
                    "Quantity After": (
                        st.column_config.NumberColumn(
                            format="%.6f"
                        )
                    ),
                    "Quantity Change": (
                        st.column_config.NumberColumn(
                            format="%+.6f"
                        )
                    ),
                    "Average Cost Before": (
                        st.column_config.NumberColumn(
                            format="$%.2f"
                        )
                    ),
                    "Average Cost After": (
                        st.column_config.NumberColumn(
                            format="$%.2f"
                        )
                    ),
                    "Realized P/L Before": (
                        st.column_config.NumberColumn(
                            format="$%.2f"
                        )
                    ),
                    "Realized P/L After": (
                        st.column_config.NumberColumn(
                            format="$%.2f"
                        )
                    ),
                    "Realized P/L Change": (
                        st.column_config.NumberColumn(
                            format="$%.2f"
                        )
                    ),
                },
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

    render_trading_analytics(account.id)

    st.divider()

    render_portfolio_exposure(
        account=account,
        position_dataframe=position_dataframe,
        risk_settings=risk_settings,
    )

    st.divider()

    render_portfolio_rebalancing(
        account=account,
        position_dataframe=position_dataframe,
        risk_settings=risk_settings,
    )

    st.divider()

    render_rebalance_history(
        account_id=account.id,
    )

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
