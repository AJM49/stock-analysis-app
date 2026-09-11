from datetime import date
from datetime import datetime

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


WATCHLIST_PRIORITY_ORDER = {
    "High": 0,
    "Medium": 1,
    "Low": 2,
}


def classify_watchlist_priority(row, today=None):
    if today is None:
        today = date.today()

    cache_status = str(
        row.get("Cache Status", "")
    ).strip()

    if cache_status != "Cached":
        return "High"

    market_date = row.get(
        "Latest Market Date"
    )

    if market_date:
        try:
            parsed_date = pd.to_datetime(
                market_date
            ).date()

            age_days = (
                today - parsed_date
            ).days

            if age_days > 7:
                return "High"
        except (TypeError, ValueError):
            return "High"

    daily_change = row.get(
        "Daily Change %",
        0.0,
    )

    try:
        daily_change = float(
            daily_change or 0.0
        )
    except (TypeError, ValueError):
        daily_change = 0.0

    if abs(daily_change) >= 3.0:
        return "Medium"

    return "Low"


def build_prioritized_watchlist(
    metric_rows,
    high_priority_only=False,
    today=None,
):
    if not metric_rows:
        return pd.DataFrame()

    metrics_df = pd.DataFrame(
        metric_rows
    ).copy()

    metrics_df["Research Priority"] = (
        metrics_df.apply(
            lambda row: classify_watchlist_priority(
                row,
                today=today,
            ),
            axis=1,
        )
    )

    metrics_df["_Priority Rank"] = (
        metrics_df[
            "Research Priority"
        ].map(
            WATCHLIST_PRIORITY_ORDER
        )
    )

    if high_priority_only:
        metrics_df = metrics_df[
            metrics_df[
                "Research Priority"
            ] == "High"
        ]

    metrics_df = (
        metrics_df.sort_values(
            by=[
                "_Priority Rank",
                "Ticker",
            ],
            ascending=[
                True,
                True,
            ],
            kind="stable",
        )
        .drop(
            columns=[
                "_Priority Rank",
            ]
        )
        .reset_index(
            drop=True
        )
    )

    return metrics_df


def build_watchlist_priority_row(metric_row, today=None):
    today = today or date.today()

    ticker = str(
        metric_row.get("Ticker", "")
    ).strip().upper()

    cache_status = str(
        metric_row.get(
            "Cache Status",
            "Unavailable",
        )
    )

    cached_rows = int(
        metric_row.get("Cached Rows", 0) or 0
    )

    daily_change = metric_row.get(
        "Daily Change %"
    )

    latest_market_date = metric_row.get(
        "Latest Market Date"
    )

    score = 0
    reasons = []

    if cache_status != "Cached":
        score += 100
        reasons.append(
            "Missing cache (+100)"
        )
    else:
        age_days = None

        if latest_market_date:
            if isinstance(
                latest_market_date,
                str,
            ):
                market_date = (
                    datetime.strptime(
                        latest_market_date,
                        "%Y-%m-%d",
                    ).date()
                )
            elif isinstance(
                latest_market_date,
                datetime,
            ):
                market_date = (
                    latest_market_date.date()
                )
            else:
                market_date = (
                    latest_market_date
                )

            age_days = (
                today - market_date
            ).days

        if (
            age_days is not None
            and age_days > 7
        ):
            score += 40
            reasons.append(
                f"Stale data: {age_days} days old (+40)"
            )

        if daily_change is not None:
            move = abs(
                float(daily_change)
            )

            if move >= 5.0:
                score += 25
                reasons.append(
                    f"Large move: {float(daily_change):+.2f}% (+25)"
                )
            elif move >= 3.0:
                score += 15
                reasons.append(
                    f"Notable move: {float(daily_change):+.2f}% (+15)"
                )

        if cached_rows < 20:
            score += 15
            reasons.append(
                f"Research gap: only {cached_rows} cached observations (+15)"
            )

    if not reasons:
        reasons.append(
            "No elevated priority signals"
        )

    return {
        **metric_row,
        "Priority Score": score,
        "Priority Reasons": reasons,
        "Why Ranked Here": "; ".join(
            reasons
        ),
    }


def build_ranked_watchlist(
    metric_rows,
    today=None,
):
    ranked_rows = [
        build_watchlist_priority_row(
            row,
            today=today,
        )
        for row in metric_rows
    ]

    return sorted(
        ranked_rows,
        key=lambda row: (
            -row["Priority Score"],
            row["Ticker"],
        ),
    )


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
            == "High"
        ).sum()
    )

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric(
        "Visible Tickers",
        len(metrics_df),
        f"{len(all_metrics_df)} saved",
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

    display_df = metrics_df.copy()

    st.caption(
        "Research queue priority: Needs Data → Review Now → "
        "Monitor → Stable. Higher-priority research items "
        "appear first."
    )

    if high_priority_only:
        st.caption(
            f"Showing {len(metrics_df)} high-priority "
            f"ticker(s) from {len(all_metrics_df)} saved."
        )

    st.dataframe(
        display_df,
        width="stretch",
        hide_index=True,
        column_config={
            "Ticker": st.column_config.TextColumn(
                "Ticker"
            ),
            "Priority Score": st.column_config.NumberColumn(
                "Score",
                format="%d",
            ),
            "Why Ranked Here": st.column_config.TextColumn(
                "Why Ranked Here"
            ),
            "Research Priority": st.column_config.TextColumn(
                "Priority"
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
