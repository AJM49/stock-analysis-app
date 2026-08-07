import streamlit as st

from database import get_database_status
from database import get_portfolio_positions
from database import get_portfolio_snapshots
from database import get_watchlist_cached_metrics


def render_dashboard(selected_ticker):
    st.header("Dashboard")
    st.caption(
        "Command center for research, watchlist, portfolio, "
        "and data-health status."
    )

    watchlist_metrics = get_watchlist_cached_metrics()
    portfolio_positions = get_portfolio_positions()
    portfolio_snapshots = get_portfolio_snapshots(limit=1)

    watchlist_count = len(watchlist_metrics)

    cached_count = sum(
        1
        for row in watchlist_metrics
        if row.get("Cache Status") == "Cached"
    )

    unavailable_count = watchlist_count - cached_count

    portfolio_position_count = len(portfolio_positions)

    latest_snapshot = (
        portfolio_snapshots[0]
        if portfolio_snapshots
        else None
    )

    st.subheader("Research Overview")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Research Ticker",
        selected_ticker or "None",
    )

    col2.metric(
        "Watchlist",
        watchlist_count,
    )

    col3.metric(
        "Cached Watchlist",
        cached_count,
    )

    col4.metric(
        "Portfolio Positions",
        portfolio_position_count,
    )

    st.subheader("Portfolio Snapshot")

    pcol1, pcol2, pcol3, pcol4 = st.columns(4)

    if latest_snapshot is None:
        pcol1.metric("Portfolio Value", "No snapshot")
        pcol2.metric("Gain / Loss", "No snapshot")
        pcol3.metric("Risk Score", "No snapshot")
        pcol4.metric("Risk Level", "No snapshot")

        st.info(
            "Save a Portfolio Snapshot from Portfolio Summary "
            "to populate portfolio dashboard metrics."
        )
    else:
        pcol1.metric(
            "Portfolio Value",
            f"${latest_snapshot.total_current_value:,.2f}",
        )

        pcol2.metric(
            "Gain / Loss",
            f"${latest_snapshot.total_gain_loss:,.2f}",
            f"{latest_snapshot.total_gain_loss_pct:.2f}%",
        )

        risk_score = getattr(
            latest_snapshot,
            "risk_score",
            None,
        )

        risk_level = getattr(
            latest_snapshot,
            "risk_level",
            None,
        )

        pcol3.metric(
            "Risk Score",
            (
                f"{risk_score:.0f}"
                if risk_score is not None
                else "No data"
            ),
        )

        pcol4.metric(
            "Risk Level",
            risk_level or "No data",
        )

    st.subheader("Data Health")

    dcol1, dcol2, dcol3 = st.columns(3)

    dcol1.metric(
        "Cached",
        cached_count,
    )

    dcol2.metric(
        "Unavailable",
        unavailable_count,
    )

    coverage_pct = (
        cached_count / watchlist_count * 100
        if watchlist_count
        else 0.0
    )

    dcol3.metric(
        "Watchlist Coverage",
        f"{coverage_pct:.1f}%",
    )

    if unavailable_count:
        st.warning(
            f"{unavailable_count} watchlist ticker(s) currently "
            "lack cached market data."
        )
    elif watchlist_count:
        st.success(
            "All saved watchlist tickers currently have cached "
            "market data."
        )
    else:
        st.info(
            "Add tickers to the Watchlist to begin tracking "
            "market-data coverage."
        )

    st.subheader("System Status")

    st.info(
        "Database: " + get_database_status()
    )

    st.caption(
        "Dashboard metrics use stored database and cache data only. "
        "Opening this page does not trigger a market-data provider request."
    )
