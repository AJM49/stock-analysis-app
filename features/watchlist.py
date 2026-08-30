from datetime import date

import pandas as pd
import streamlit as st

from database import get_watchlist_cached_metrics
from market_data import validate_ticker
from services.watchlist_signal_service import build_watchlist_research_signals
from services.watchlist_health_service import (
    build_watchlist_data_health,
    build_watchlist_research_reliability,
)
from ui_components import render_watchlist_sidebar
from services.watchlist_research_service import build_watchlist_research_queue


RESEARCH_PRIORITY = {
    "Needs Attention": 0,
    "Stale": 1,
    "Ready": 2,
}


def classify_watchlist_research_status(
    row,
    today=None,
):
    current_date = today or date.today()

    cache_status = str(
        row.get("Cache Status", "")
    ).strip()

    market_date_value = row.get(
        "Latest Market Date"
    )

    if cache_status != "Cached":
        return "Needs Attention", None

    market_timestamp = pd.to_datetime(
        market_date_value,
        errors="coerce",
    )

    if pd.isna(market_timestamp):
        return "Needs Attention", None

    market_date = market_timestamp.date()
    age_days = (
        current_date - market_date
    ).days

    if age_days > 7:
        return "Stale", age_days

    return "Ready", age_days


def rank_watchlist_research_queue(
    metrics_df,
    today=None,
):
    if metrics_df is None or metrics_df.empty:
        return pd.DataFrame()

    ranked_df = metrics_df.copy()

    classifications = ranked_df.apply(
        lambda row: classify_watchlist_research_status(
            row,
            today=today,
        ),
        axis=1,
    )

    ranked_df["Research Status"] = [
        result[0]
        for result in classifications
    ]

    ranked_df["Market Age Days"] = [
        result[1]
        for result in classifications
    ]

    ranked_df["Research Priority"] = (
        ranked_df["Research Status"].map(
            RESEARCH_PRIORITY
        )
    )

    ranked_df = ranked_df.sort_values(
        by=[
            "Research Priority",
            "Market Age Days",
            "Ticker",
        ],
        ascending=[
            True,
            False,
            True,
        ],
        na_position="first",
    ).reset_index(drop=True)

    return ranked_df


def render_watchlist_feature():
    st.header("Watchlist")

    st.sidebar.subheader("Watchlist Controls")

    watchlist_ticker = st.sidebar.text_input(
        "Watchlist Ticker",
        value=st.session_state.get(
            "watchlist_ticker",
            st.session_state.get("selected_ticker", "AAPL"),
        ),
        placeholder="Example: NOW",
        key="watchlist_ticker_input",
    ).upper().strip()

    is_valid, validation_result = validate_ticker(
        watchlist_ticker
    )

    if is_valid:
        watchlist_ticker = validation_result
        st.session_state["watchlist_ticker"] = (
            watchlist_ticker
        )

        render_watchlist_sidebar(
            watchlist_ticker
        )
    else:
        st.sidebar.warning(validation_result)

    st.subheader("Cached Watchlist Metrics")

    metric_rows = get_watchlist_cached_metrics()

    if not metric_rows:
        st.info(
            "No saved watchlist tickers yet. "
            "Add a ticker from the sidebar."
        )
        return

    signal_rows = build_watchlist_research_signals(
        metric_rows
    )

    research_rows = build_watchlist_research_queue(
        signal_rows
    )

    metrics_df = pd.DataFrame(
        research_rows
    )

    watchlist_health = build_watchlist_data_health(
        signal_rows
    )

    st.subheader("Watchlist Data Health")

    health_col1, health_col2 = st.columns(2)

    health_col1.metric(
        "Cache Coverage",
        f"{watchlist_health['coverage_pct']:.1f}%",
    )

    health_col2.metric(
        "Data Quality",
        watchlist_health["quality_status"],
    )

    watchlist_reliability = (
        build_watchlist_research_reliability(
            watchlist_health
        )
    )

    st.subheader("Research Reliability")

    reliability_col1, reliability_col2 = st.columns(2)

    reliability_col1.metric(
        "Decision Reliability",
        watchlist_reliability["status"],
    )

    reliability_col2.metric(
        "Quality Score",
        f"{watchlist_reliability['quality_score']:.1f}",
    )

    st.caption(
        f"Price coverage: "
        f"{watchlist_reliability['coverage_pct']:.1f}% | "
        f"Fresh prices: "
        f"{watchlist_reliability['freshness_pct']:.1f}%"
    )

    reliability_severity = watchlist_reliability[
        "severity"
    ]
    reliability_message = watchlist_reliability[
        "message"
    ]

    if reliability_severity == "success":
        st.success(reliability_message)
    elif reliability_severity == "warning":
        st.warning(reliability_message)
    elif reliability_severity == "error":
        st.error(reliability_message)
    else:
        st.info(reliability_message)

    cached_count = int(
        watchlist_health.get(
            "cached_count",
            watchlist_health.get(
                "available_count",
                0,
            ),
        )
    )

    unavailable_count = watchlist_health[
        "missing_count"
    ]

    review_now_count = int(
        (
            metrics_df["Research Status"]
            == "Review Now"
        ).sum()
    )

    needs_data_count = int(
        (
            metrics_df["Research Status"]
            == "Needs Data"
        ).sum()
    )

    high_priority_count = int(
        (
            metrics_df["Research Priority"]
            >= 3
        ).sum()
    )

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric(
        "Saved Tickers",
        len(metrics_df),
    )

    col2.metric(
        "Cached",
        cached_count,
    )

    col3.metric(
        "Review Now",
        review_now_count,
    )

    col4.metric(
        "Needs Data",
        needs_data_count,
    )

    col5.metric(
        "High Priority",
        high_priority_count,
    )

    display_df = metrics_df.drop(
        columns=["Research Priority"],
        errors="ignore",
    )

    st.caption(
        "Research queue priority: Needs Data → Review Now → "
        "Monitor → Stable. Higher-priority research items "
        "appear first."
    )

    st.dataframe(
        display_df,
        width="stretch",
        hide_index=True,
        column_config={
            "Ticker": st.column_config.TextColumn(
                "Ticker"
            ),
            "Latest Close": st.column_config.NumberColumn(
                "Latest Close",
                format="$%.2f",
            ),
            "Daily Change %": st.column_config.NumberColumn(
                "Daily Change %",
                format="%.2f%%",
            ),
            "Latest Market Date": (
                st.column_config.TextColumn(
                    "Latest Market Date"
                )
            ),
            "Cached Rows": st.column_config.NumberColumn(
                "Cached Rows",
                format="%d",
            ),
            "Cache Status": st.column_config.TextColumn(
                "Cache Status"
            ),
            "Research Status": st.column_config.TextColumn(
                "Research Status"
            ),
            "Research Reason": st.column_config.TextColumn(
                "Research Reason"
            ),
            "Market Age Days": st.column_config.NumberColumn(
                "Age (Days)",
                format="%d",
            ),
            "Data Freshness": st.column_config.TextColumn(
                "Data Freshness"
            ),
            "Move Signal": st.column_config.TextColumn(
                "Move Signal"
            ),
            "Research Priority": st.column_config.TextColumn(
                "Research Priority"
            ),
        },
    )

    if unavailable_count:
        st.info(
            f"{unavailable_count} saved ticker(s) do not "
            "currently have cached market data. "
            "Watchlist rendering never triggers a provider request."
        )
