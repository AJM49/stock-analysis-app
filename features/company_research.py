import streamlit as st

from controllers.stock_controller import load_stock_dashboard_data
from core.app_logging import log_warning
from core.user_messages import get_user_safe_market_data_error
from indicators import add_technical_indicators
from market_data import calculate_price_change
from market_data import clear_market_data_cache
from market_data import load_stock_data
from market_data import validate_ticker
from ui_components import render_app_diagnostics_page
from ui_components import render_comparison_chart
from ui_components import render_company_profile
from ui_components import render_developer_status_panel
from ui_components import render_price_chart
from ui_components import render_risk_dashboard
from ui_components import render_selected_ticker_freshness
from ui_components import render_stock_header
from ui_components import render_technical_indicators


def render_company_research(
    ticker,
    comparison_ticker,
    period,
    show_company_overview,
):
    try:
        cache_only_mode = st.checkbox(
            "Use cached data only",
            value=True,
            help=(
                "Prevents Alpha Vantage API calls and "
                "only reads from Neon cache."
            ),
        )

        render_developer_status_panel(cache_only_mode)

        show_diagnostics_page = st.sidebar.checkbox(
            "Show Diagnostics Page",
            value=False,
            help=(
                "Display app health, runtime, cache, "
                "and database diagnostics."
            ),
        )

        if show_diagnostics_page:
            render_app_diagnostics_page(cache_only_mode)
            st.stop()

        refresh_market_data = st.button(
            "Refresh Market Data",
            help=(
                "Uses one Alpha Vantage API request "
                "and updates the Neon cache."
            ),
            disabled=cache_only_mode,
        )

        stock_result = load_stock_dashboard_data(
            ticker,
            period,
            force_refresh=refresh_market_data,
            cache_only=cache_only_mode,
        )

        info = stock_result.info
        history = stock_result.history
        error_message = stock_result.error_message

        if refresh_market_data and error_message is None:
            clear_market_data_cache()
            st.success(
                "Market data refreshed and saved to Neon."
            )

        if cache_only_mode:
            st.info("Data source: Neon cache only.")
        elif refresh_market_data:
            st.info("Data source: Alpha Vantage refresh.")
        else:
            st.info(
                "Data source: Neon cache when available."
            )

        render_selected_ticker_freshness(ticker)

        if error_message:
            safe_error_message = (
                get_user_safe_market_data_error(
                    error_message,
                    stock_result.is_quota_error,
                )
            )

            log_warning(
                "Market data load issue for "
                + ticker
                + ": "
                + error_message
            )

            if stock_result.is_quota_error:
                st.warning(safe_error_message)
                st.info(
                    "This ticker is not cached in Neon yet. "
                    "Try a ticker already saved in "
                    "market_data_cache, or refresh again "
                    "tomorrow when the API quota resets."
                )
                st.stop()

            st.error(safe_error_message)
            st.stop()

        if history is None or history.empty:
            st.error(
                "No price history is available for "
                + ticker
                + "."
            )
            st.stop()

        history, volatility = add_technical_indicators(
            history
        )

        current_price, price_change_pct = (
            calculate_price_change(history)
        )

        if current_price is None:
            st.error(
                "Not enough price data to analyze "
                + ticker
                + "."
            )
            st.stop()

        render_stock_header(
            info,
            ticker,
            current_price,
            price_change_pct,
            history,
            cache_only=cache_only_mode,
        )

        render_company_profile(
            info,
            show_company_overview,
        )

        render_technical_indicators(
            history,
            volatility,
        )

        if comparison_ticker:
            (
                comparison_is_valid,
                comparison_result,
            ) = validate_ticker(comparison_ticker)

            if not comparison_is_valid:
                st.warning(comparison_result)
            else:
                comparison_ticker = comparison_result

                (
                    comparison_info,
                    comparison_history,
                    comparison_error,
                ) = load_stock_data(
                    comparison_ticker,
                    period,
                )

                if comparison_error:
                    st.warning(comparison_error)

                elif (
                    comparison_history is None
                    or comparison_history.empty
                ):
                    st.warning(
                        "No comparison data is available for "
                        + comparison_ticker
                        + "."
                    )

                else:
                    render_comparison_chart(
                        history,
                        comparison_history,
                        ticker,
                        comparison_ticker,
                    )

        render_price_chart(history, ticker)
        render_risk_dashboard(history, ticker)

    except Exception as error:
        st.error(
            "Unexpected Company Research error: "
            + str(error)
        )

        with open(
            "app.log",
            "a",
            encoding="utf-8",
        ) as log_file:
            log_file.write(
                "Unexpected Company Research error: "
                + str(error)
                + "\n"
            )
