from datetime import date

import pandas as pd
import streamlit as st

from database import get_database_status
from database import get_portfolio_positions
from database import get_portfolio_snapshots
from database import get_watchlist_cached_metrics


ATTENTION_PRIORITY = {
    "critical": 4,
    "high": 3,
    "medium": 2,
    "low": 1,
}


def sort_attention_items(items):
    return sorted(
        items,
        key=lambda item: ATTENTION_PRIORITY.get(
            item.get("priority", "low"),
            0,
        ),
        reverse=True,
    )


def build_dashboard_attention_items(
    watchlist_metrics,
    latest_snapshot,
):
    items = []

    unavailable_tickers = [
        row["Ticker"]
        for row in watchlist_metrics
        if row.get("Cache Status") != "Cached"
    ]

    if unavailable_tickers:
        items.append(
            {
                "severity": "warning",
                "priority": "high",
                "title": "Missing watchlist cache",
                "action": (
                    "Open Watchlist and review unsupported "
                    "or uncached symbols."
                ),
                "message": (
                    f"{len(unavailable_tickers)} saved ticker(s) "
                    "do not have cached market data."
                ),
                "details": unavailable_tickers,
            }
        )

    stale_tickers = []

    for row in watchlist_metrics:
        market_date = row.get("Latest Market Date")

        if not market_date:
            continue

        parsed_date = pd.to_datetime(
            market_date,
            errors="coerce",
        )

        if pd.isna(parsed_date):
            continue

        age_days = (
            date.today() - parsed_date.date()
        ).days

        if age_days > 7:
            stale_tickers.append(
                {
                    "ticker": row["Ticker"],
                    "age_days": age_days,
                }
            )

    if stale_tickers:
        items.append(
            {
                "severity": "warning",
                "priority": "medium",
                "title": "Stale watchlist market data",
                "action": (
                    "Review stale tickers before using them "
                    "for research decisions."
                ),
                "message": (
                    f"{len(stale_tickers)} cached ticker(s) "
                    "are more than 7 days old."
                ),
                "details": [
                    (
                        f"{item['ticker']} "
                        f"({item['age_days']} days)"
                    )
                    for item in stale_tickers
                ],
            }
        )

    if latest_snapshot is None:
        items.append(
            {
                "severity": "info",
                "priority": "low",
                "title": "Portfolio snapshot missing",
                "action": (
                    "Open Portfolio Summary and save a "
                    "portfolio snapshot."
                ),
                "message": (
                    "No saved portfolio snapshot is available."
                ),
                "details": [],
            }
        )

        return items

    snapshot_date = getattr(
        latest_snapshot,
        "snapshot_date",
        None,
    )

    if snapshot_date is not None:
        parsed_snapshot_date = pd.to_datetime(
            snapshot_date,
            errors="coerce",
        )

        if not pd.isna(parsed_snapshot_date):
            snapshot_age_days = (
                date.today()
                - parsed_snapshot_date.date()
            ).days

            if snapshot_age_days > 7:
                items.append(
                    {
                        "severity": "warning",
                        "priority": "low",
                        "title": "Portfolio snapshot stale",
                        "action": (
                            "Open Portfolio Summary and save "
                            "a fresh portfolio snapshot."
                        ),
                        "message": (
                            "The latest portfolio snapshot is "
                            f"{snapshot_age_days} days old."
                        ),
                        "details": [],
                    }
                )

    risk_level = str(
        getattr(
            latest_snapshot,
            "risk_level",
            "",
        )
        or ""
    ).strip()

    normalized_risk = risk_level.lower()

    if (
        "high" in normalized_risk
        or "elevated" in normalized_risk
    ):
        items.append(
            {
                "severity": "error",
                "priority": "critical",
                "title": "Portfolio risk requires attention",
                "action": (
                    "Open Portfolio Summary and review "
                    "concentration, allocation, and risk."
                ),
                "message": (
                    "Latest portfolio risk level: "
                    + risk_level
                ),
                "details": [],
            }
        )

    return sort_attention_items(items)


def render_attention_items(attention_items):
    st.subheader("Attention Required")

    if not attention_items:
        st.success(
            "No current data-health or portfolio-risk "
            "alerts require attention."
        )
        return

    for item in attention_items:
        severity = item["severity"]
        priority = item.get(
            "priority",
            "low",
        ).upper()

        message = (
            f"[{priority}] "
            + item["title"]
            + ": "
            + item["message"]
        )

        if severity == "error":
            st.error(message)
        elif severity == "warning":
            st.warning(message)
        else:
            st.info(message)

        action = item.get("action")

        if action:
            st.caption(
                "Recommended action: " + action
            )

        details = item.get("details") or []

        if details:
            with st.expander(
                f"View {item[title].lower()} details"
            ):
                for detail in details:
                    st.write("- " + str(detail))


def render_dashboard(selected_ticker):
    st.header("Dashboard")

    st.caption(
        "Command center for research, watchlist, portfolio, "
        "and data-health status."
    )

    watchlist_metrics = get_watchlist_cached_metrics()
    portfolio_positions = get_portfolio_positions()
    portfolio_snapshots = get_portfolio_snapshots(
        limit=1
    )

    watchlist_count = len(watchlist_metrics)

    cached_count = sum(
        1
        for row in watchlist_metrics
        if row.get("Cache Status") == "Cached"
    )

    unavailable_count = (
        watchlist_count - cached_count
    )

    portfolio_position_count = len(
        portfolio_positions
    )

    latest_snapshot = (
        portfolio_snapshots[0]
        if portfolio_snapshots
        else None
    )

    attention_items = (
        build_dashboard_attention_items(
            watchlist_metrics,
            latest_snapshot,
        )
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

    render_attention_items(
        attention_items
    )

    st.subheader("Portfolio Snapshot")

    pcol1, pcol2, pcol3, pcol4 = (
        st.columns(4)
    )

    if latest_snapshot is None:
        pcol1.metric(
            "Portfolio Value",
            "No snapshot",
        )
        pcol2.metric(
            "Gain / Loss",
            "No snapshot",
        )
        pcol3.metric(
            "Risk Score",
            "No snapshot",
        )
        pcol4.metric(
            "Risk Level",
            "No snapshot",
        )
    else:
        pcol1.metric(
            "Portfolio Value",
            (
                f"${latest_snapshot.total_current_value:,.2f}"
            ),
        )

        pcol2.metric(
            "Gain / Loss",
            (
                f"${latest_snapshot.total_gain_loss:,.2f}"
            ),
            (
                f"{latest_snapshot.total_gain_loss_pct:.2f}%"
            ),
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
        cached_count
        / watchlist_count
        * 100
        if watchlist_count
        else 0.0
    )

    dcol3.metric(
        "Watchlist Coverage",
        f"{coverage_pct:.1f}%",
    )

    st.subheader("System Status")

    st.info(
        "Database: "
        + get_database_status()
    )

    st.caption(
        "Dashboard metrics and alerts use stored database "
        "and cache data only. Opening this page does not "
        "trigger a market-data provider request."
    )
