import pandas as pd
import streamlit as st

from database import get_watchlist_cached_metrics
from market_data import validate_ticker
from ui_components import render_watchlist_sidebar


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

    metrics_df = pd.DataFrame(metric_rows)

    cached_count = int(
        (metrics_df["Cache Status"] == "Cached").sum()
    )

    unavailable_count = int(
        (metrics_df["Cache Status"] != "Cached").sum()
    )

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Saved Tickers",
        len(metrics_df),
    )

    col2.metric(
        "Cached",
        cached_count,
    )

    col3.metric(
        "Unavailable",
        unavailable_count,
    )

    st.dataframe(
        metrics_df,
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
        },
    )

    if unavailable_count:
        st.info(
            f"{unavailable_count} saved ticker(s) do not "
            "currently have cached market data. "
            "Watchlist rendering never triggers a provider request."
        )
