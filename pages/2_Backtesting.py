from __future__ import annotations

import pandas as pd
import streamlit as st
import yfinance as yf

import posthog_analytics
from backtesting.engine import BacktestEngine
from strategies.buy_and_hold import BuyAndHoldStrategy
from backtesting.comparison import compare_strategies
from strategies.moving_average import MovingAverageCrossoverStrategy
from factors.technical import build_technical_factor_table
from risk.risk_metrics import calculate_drawdown_series
from risk.risk_metrics import calculate_rolling_volatility


st.set_page_config(
    page_title="Backtesting",
    page_icon="📈",
    layout="wide",
)


def normalize_yfinance_history(history: pd.DataFrame) -> pd.DataFrame:
    """Normalize yfinance history into the standard backtesting schema."""
    if history.empty:
        return pd.DataFrame(
            columns=["Date", "Open", "High", "Low", "Close", "Volume"]
        )

    normalized = history.reset_index()

    if "Date" not in normalized.columns:
        if "Datetime" in normalized.columns:
            normalized = normalized.rename(columns={"Datetime": "Date"})

    required_columns = ["Date", "Open", "High", "Low", "Close", "Volume"]

    missing_columns = [
        column
        for column in required_columns
        if column not in normalized.columns
    ]

    if missing_columns:
        raise ValueError(f"Missing required market data columns: {missing_columns}")

    normalized = normalized[required_columns].copy()
    normalized["Date"] = pd.to_datetime(normalized["Date"])

    for column in ["Open", "High", "Low", "Close", "Volume"]:
        normalized[column] = pd.to_numeric(normalized[column], errors="coerce")

    normalized = normalized.dropna(subset=["Close"])
    normalized = normalized[normalized["Close"] > 0]

    return normalized


@st.cache_data(show_spinner=False)
def load_backtest_price_data(ticker: str, period: str) -> pd.DataFrame:
    """Load historical market data for backtesting."""
    stock = yf.Ticker(ticker)
    history = stock.history(period=period)

    return normalize_yfinance_history(history)


def build_risk_alerts(result: dict) -> pd.DataFrame:
    """Build rule-based risk alerts from a backtest result."""
    alerts: list[dict[str, str]] = []

    annualized_volatility = float(result.get("annualized_volatility_pct", 0.0))
    sharpe_ratio = float(result.get("sharpe_ratio", 0.0))
    max_drawdown = abs(float(result.get("risk_max_drawdown_pct", 0.0)))
    value_at_risk = abs(float(result.get("value_at_risk_95_pct", 0.0)))
    total_return = float(result.get("total_return_pct", 0.0))
    strategy_excess_return = float(result.get("strategy_excess_return_pct", 0.0))

    if annualized_volatility > 30:
        alerts.append(
            {
                "Severity": "High",
                "Alert": "High volatility",
                "Metric": "Annualized Volatility",
                "Value": f"{annualized_volatility:.2f}%",
                "Action": "Review position sizing, reduce exposure, or test a lower-risk strategy.",
            }
        )
    elif annualized_volatility > 15:
        alerts.append(
            {
                "Severity": "Moderate",
                "Alert": "Moderate volatility",
                "Metric": "Annualized Volatility",
                "Value": f"{annualized_volatility:.2f}%",
                "Action": "Monitor volatility before scaling the strategy.",
            }
        )

    if sharpe_ratio < 0.5:
        alerts.append(
            {
                "Severity": "High",
                "Alert": "Weak risk-adjusted return",
                "Metric": "Sharpe Ratio",
                "Value": f"{sharpe_ratio:.2f}",
                "Action": "Improve signal quality or compare against simpler strategies.",
            }
        )
    elif sharpe_ratio < 1.0:
        alerts.append(
            {
                "Severity": "Moderate",
                "Alert": "Moderate risk-adjusted return",
                "Metric": "Sharpe Ratio",
                "Value": f"{sharpe_ratio:.2f}",
                "Action": "Review whether return is sufficient for the volatility taken.",
            }
        )

    if max_drawdown > 25:
        alerts.append(
            {
                "Severity": "High",
                "Alert": "Large drawdown",
                "Metric": "Risk Max Drawdown",
                "Value": f"{max_drawdown:.2f}%",
                "Action": "Add drawdown controls, stop rules, or allocation limits.",
            }
        )
    elif max_drawdown > 10:
        alerts.append(
            {
                "Severity": "Moderate",
                "Alert": "Moderate drawdown",
                "Metric": "Risk Max Drawdown",
                "Value": f"{max_drawdown:.2f}%",
                "Action": "Review worst drawdown periods before accepting the strategy.",
            }
        )

    if value_at_risk > 3:
        alerts.append(
            {
                "Severity": "High",
                "Alert": "High daily tail-risk estimate",
                "Metric": "Value at Risk 95%",
                "Value": f"{value_at_risk:.2f}%",
                "Action": "Review downside days and consider stricter risk limits.",
            }
        )
    elif value_at_risk > 1:
        alerts.append(
            {
                "Severity": "Moderate",
                "Alert": "Moderate daily tail-risk estimate",
                "Metric": "Value at Risk 95%",
                "Value": f"{value_at_risk:.2f}%",
                "Action": "Monitor downside risk against strategy goals.",
            }
        )

    if total_return < 0:
        alerts.append(
            {
                "Severity": "High",
                "Alert": "Negative strategy return",
                "Metric": "Total Return",
                "Value": f"{total_return:.2f}%",
                "Action": "Do not advance this strategy without redesign or parameter review.",
            }
        )

    if strategy_excess_return < 0:
        alerts.append(
            {
                "Severity": "Moderate",
                "Alert": "Strategy underperformed benchmark",
                "Metric": "Strategy Excess Return",
                "Value": f"{strategy_excess_return:.2f}%",
                "Action": "Compare against buy-and-hold before adding complexity.",
            }
        )

    if not alerts:
        alerts.append(
            {
                "Severity": "Low",
                "Alert": "No major risk alerts",
                "Metric": "Composite Review",
                "Value": "Pass",
                "Action": "Continue testing across more tickers and time periods.",
            }
        )

    return pd.DataFrame(alerts)


def classify_risk_level(result: dict) -> dict[str, str]:
    """Classify strategy risk using backtest risk metrics."""
    sharpe_ratio = float(result.get("sharpe_ratio", 0.0))
    annualized_volatility = float(result.get("annualized_volatility_pct", 0.0))
    max_drawdown = abs(float(result.get("risk_max_drawdown_pct", 0.0)))
    value_at_risk = abs(float(result.get("value_at_risk_95_pct", 0.0)))
    total_return = float(result.get("total_return_pct", 0.0))

    if sharpe_ratio >= 1.0:
        sharpe_rating = "Strong"
    elif sharpe_ratio >= 0.5:
        sharpe_rating = "Moderate"
    else:
        sharpe_rating = "Weak"

    if annualized_volatility <= 15:
        volatility_rating = "Low"
    elif annualized_volatility <= 30:
        volatility_rating = "Moderate"
    else:
        volatility_rating = "High"

    if max_drawdown <= 10:
        drawdown_rating = "Low"
    elif max_drawdown <= 25:
        drawdown_rating = "Moderate"
    else:
        drawdown_rating = "High"

    if value_at_risk <= 1:
        var_rating = "Low"
    elif value_at_risk <= 3:
        var_rating = "Moderate"
    else:
        var_rating = "High"

    risk_points = 0

    if sharpe_rating == "Weak":
        risk_points += 2
    elif sharpe_rating == "Moderate":
        risk_points += 1

    if volatility_rating == "High":
        risk_points += 2
    elif volatility_rating == "Moderate":
        risk_points += 1

    if drawdown_rating == "High":
        risk_points += 2
    elif drawdown_rating == "Moderate":
        risk_points += 1

    if var_rating == "High":
        risk_points += 2
    elif var_rating == "Moderate":
        risk_points += 1

    if total_return < 0:
        risk_points += 2

    if risk_points <= 2:
        overall_rating = "Stable"
    elif risk_points <= 5:
        overall_rating = "Moderate Risk"
    else:
        overall_rating = "High Risk"

    if overall_rating == "Stable":
        interpretation = (
            "The strategy has a relatively controlled risk profile based on the current backtest."
        )
    elif overall_rating == "Moderate Risk":
        interpretation = (
            "The strategy shows usable results but has risk areas that should be reviewed before scaling."
        )
    else:
        interpretation = (
            "The strategy shows elevated risk and should be improved before optimization, paper trading, or live execution."
        )

    return {
        "overall_rating": overall_rating,
        "sharpe_rating": sharpe_rating,
        "volatility_rating": volatility_rating,
        "drawdown_rating": drawdown_rating,
        "var_rating": var_rating,
        "interpretation": interpretation,
    }


def build_risk_dashboard_dataframe(result: dict) -> pd.DataFrame:
    """Build risk dashboard summary table."""
    ratings = classify_risk_level(result)

    rows = [
        {
            "Area": "Overall",
            "Rating": ratings["overall_rating"],
            "Metric": "Composite risk review",
            "Value": ratings["overall_rating"],
        },
        {
            "Area": "Return quality",
            "Rating": ratings["sharpe_rating"],
            "Metric": "Sharpe Ratio",
            "Value": round(float(result.get("sharpe_ratio", 0.0)), 2),
        },
        {
            "Area": "Volatility",
            "Rating": ratings["volatility_rating"],
            "Metric": "Annualized Volatility",
            "Value": f"{float(result.get('annualized_volatility_pct', 0.0)):.2f}%",
        },
        {
            "Area": "Drawdown",
            "Rating": ratings["drawdown_rating"],
            "Metric": "Risk Max Drawdown",
            "Value": f"{float(result.get('risk_max_drawdown_pct', 0.0)):.2f}%",
        },
        {
            "Area": "Tail risk",
            "Rating": ratings["var_rating"],
            "Metric": "Value at Risk 95%",
            "Value": f"{float(result.get('value_at_risk_95_pct', 0.0)):.2f}%",
        },
    ]

    return pd.DataFrame(rows)


def build_risk_report_text(result: dict) -> str:
    """Build downloadable risk report text from a backtest result."""
    lines = [
        "Stock Analysis App — Backtest Risk Report",
        "",
        "Backtest Summary",
        f"Ticker: {result['ticker']}",
        f"Strategy: {result['strategy_name']}",
        f"Benchmark: {result['benchmark_name']}",
        f"Starting Cash: ${result['starting_cash']:,.2f}",
        f"Ending Value: ${result['ending_value']:,.2f}",
        f"Total Return: {result['total_return_pct']:.2f}%",
        f"Benchmark Return: {result['benchmark_total_return_pct']:.2f}%",
        f"Strategy Excess Return: {result['strategy_excess_return_pct']:.2f}%",
        "",
        "Risk Metrics",
        f"Annualized Return: {result['annualized_return_pct']:.2f}%",
        f"Annualized Volatility: {result['annualized_volatility_pct']:.2f}%",
        f"Sharpe Ratio: {result['sharpe_ratio']:.2f}",
        f"Sortino Ratio: {result['sortino_ratio']:.2f}",
        f"Risk Max Drawdown: {result['risk_max_drawdown_pct']:.2f}%",
        f"Drawdown Duration: {result['drawdown_duration']}",
        f"Value at Risk 95%: {result['value_at_risk_95_pct']:.2f}%",
        f"Conditional VaR 95%: {result['conditional_value_at_risk_95_pct']:.2f}%",
        f"Calmar Ratio: {result['calmar_ratio']:.2f}",
        "",
        "Trade Metrics",
        f"Number of Trades: {result['number_of_trades']}",
        f"Completed Trades: {result['completed_trades']}",
        f"Win Rate: {result['win_rate_pct']:.2f}%",
        f"Exposure: {result['exposure_pct']:.2f}%",
        f"Average Gain: ${result['average_gain']:,.2f}",
        f"Average Loss: ${result['average_loss']:,.2f}",
        f"Best Trade: ${result['best_trade']:,.2f}",
        f"Worst Trade: ${result['worst_trade']:,.2f}",
        "",
        "Disclaimer",
        "This report is for educational and portfolio purposes only. It is not financial advice.",
    ]

    return "\n".join(lines)


def build_risk_report_dataframe(result: dict) -> pd.DataFrame:
    """Build downloadable risk report table from a backtest result."""
    report_rows = [
        {"Category": "Backtest", "Metric": "Ticker", "Value": result["ticker"]},
        {"Category": "Backtest", "Metric": "Strategy", "Value": result["strategy_name"]},
        {"Category": "Backtest", "Metric": "Benchmark", "Value": result["benchmark_name"]},
        {"Category": "Backtest", "Metric": "Starting Cash", "Value": result["starting_cash"]},
        {"Category": "Backtest", "Metric": "Ending Value", "Value": result["ending_value"]},
        {"Category": "Backtest", "Metric": "Total Return %", "Value": result["total_return_pct"]},
        {"Category": "Backtest", "Metric": "Benchmark Return %", "Value": result["benchmark_total_return_pct"]},
        {"Category": "Backtest", "Metric": "Strategy Excess Return %", "Value": result["strategy_excess_return_pct"]},
        {"Category": "Risk", "Metric": "Annualized Return %", "Value": result["annualized_return_pct"]},
        {"Category": "Risk", "Metric": "Annualized Volatility %", "Value": result["annualized_volatility_pct"]},
        {"Category": "Risk", "Metric": "Sharpe Ratio", "Value": result["sharpe_ratio"]},
        {"Category": "Risk", "Metric": "Sortino Ratio", "Value": result["sortino_ratio"]},
        {"Category": "Risk", "Metric": "Risk Max Drawdown %", "Value": result["risk_max_drawdown_pct"]},
        {"Category": "Risk", "Metric": "Drawdown Duration", "Value": result["drawdown_duration"]},
        {"Category": "Risk", "Metric": "Value at Risk 95% %", "Value": result["value_at_risk_95_pct"]},
        {
            "Category": "Risk",
            "Metric": "Conditional VaR 95% %",
            "Value": result["conditional_value_at_risk_95_pct"],
        },
        {"Category": "Risk", "Metric": "Calmar Ratio", "Value": result["calmar_ratio"]},
        {"Category": "Trade", "Metric": "Number of Trades", "Value": result["number_of_trades"]},
        {"Category": "Trade", "Metric": "Completed Trades", "Value": result["completed_trades"]},
        {"Category": "Trade", "Metric": "Win Rate %", "Value": result["win_rate_pct"]},
        {"Category": "Trade", "Metric": "Exposure %", "Value": result["exposure_pct"]},
        {"Category": "Trade", "Metric": "Average Gain", "Value": result["average_gain"]},
        {"Category": "Trade", "Metric": "Average Loss", "Value": result["average_loss"]},
        {"Category": "Trade", "Metric": "Best Trade", "Value": result["best_trade"]},
        {"Category": "Trade", "Metric": "Worst Trade", "Value": result["worst_trade"]},
    ]

    return pd.DataFrame(report_rows)


def render_rolling_volatility_section(result: dict) -> None:
    """Render rolling volatility chart, table, and export."""
    st.subheader("Rolling Volatility Analysis")

    equity_curve = result["equity_curve"]

    if equity_curve.empty:
        st.info("No equity curve available for rolling volatility analysis.")
        return

    try:
        volatility_df = calculate_rolling_volatility(
            equity_curve=equity_curve,
            window=20,
        )
    except Exception as error:
        st.error(f"Rolling volatility calculation failed: {error}")
        return

    volatility_column = "rolling_volatility_20"

    st.markdown(
        """
Rolling volatility measures how unstable the strategy's returns are over a moving window. Higher volatility means the equity curve is moving more aggressively.
"""
    )

    chart_data = volatility_df[["Date", volatility_column]].copy()
    chart_data = chart_data.set_index("Date")

    st.line_chart(chart_data)

    latest_volatility = float(volatility_df[volatility_column].iloc[-1])
    average_volatility = float(volatility_df[volatility_column].mean())
    max_volatility = float(volatility_df[volatility_column].max())

    vol_col1, vol_col2, vol_col3 = st.columns(3)

    vol_col1.metric(
        "Latest Rolling Volatility",
        f"{latest_volatility:.2f}%",
    )

    vol_col2.metric(
        "Average Rolling Volatility",
        f"{average_volatility:.2f}%",
    )

    vol_col3.metric(
        "Max Rolling Volatility",
        f"{max_volatility:.2f}%",
    )

    with st.expander("Rolling Volatility Table", expanded=False):
        display_df = volatility_df.copy()
        display_df[volatility_column] = display_df[volatility_column].round(2)
        display_df["total_value"] = display_df["total_value"].round(2)

        st.dataframe(
            display_df.tail(100),
            use_container_width=True,
            hide_index=True,
        )

    volatility_csv = volatility_df.to_csv(index=False)

    st.download_button(
        label="Download Rolling Volatility CSV",
        data=volatility_csv,
        file_name=f"{str(result['ticker']).lower()}_rolling_volatility.csv",
        mime="text/csv",
        key="download_rolling_volatility_csv",
    )


def render_drawdown_section(result: dict) -> None:
    """Render drawdown chart, worst drawdown table, and export."""
    st.subheader("Drawdown Analysis")

    equity_curve = result["equity_curve"]

    if equity_curve.empty:
        st.info("No equity curve available for drawdown analysis.")
        return

    try:
        drawdown_series = calculate_drawdown_series(equity_curve)
    except Exception as error:
        st.error(f"Drawdown calculation failed: {error}")
        return

    drawdown_df = equity_curve[["Date", "total_value"]].copy()
    drawdown_df["drawdown_pct"] = drawdown_series.values
    drawdown_df["running_peak"] = drawdown_df["total_value"].cummax()

    st.markdown(
        """
Drawdown shows how far the strategy falls from its previous equity peak. It helps measure downside risk, not just total return.
"""
    )

    chart_data = drawdown_df[["Date", "drawdown_pct"]].copy()
    chart_data = chart_data.set_index("Date")

    st.line_chart(chart_data)

    worst_drawdowns = (
        drawdown_df.sort_values(
            by="drawdown_pct",
            ascending=True,
        )
        .head(10)
        .copy()
    )

    worst_drawdowns["drawdown_pct"] = worst_drawdowns["drawdown_pct"].round(2)
    worst_drawdowns["total_value"] = worst_drawdowns["total_value"].round(2)
    worst_drawdowns["running_peak"] = worst_drawdowns["running_peak"].round(2)

    with st.expander("Worst Drawdown Periods", expanded=False):
        st.dataframe(
            worst_drawdowns,
            use_container_width=True,
            hide_index=True,
        )

    drawdown_csv = drawdown_df.to_csv(index=False)

    st.download_button(
        label="Download Drawdown CSV",
        data=drawdown_csv,
        file_name=f"{str(result['ticker']).lower()}_drawdown.csv",
        mime="text/csv",
        key="download_drawdown_csv",
    )


def render_risk_report_export_section(result: dict) -> None:
    """Render risk report export controls."""
    st.subheader("Risk Report Export")

    report_text = build_risk_report_text(result)
    report_df = build_risk_report_dataframe(result)
    report_csv = report_df.to_csv(index=False)

    safe_ticker = str(result["ticker"]).lower()
    safe_strategy = (
        str(result["strategy_name"])
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )

    export_col1, export_col2 = st.columns(2)

    if export_col1.download_button(
        label="Download Risk Report TXT",
        data=report_text,
        file_name=f"{safe_ticker}_{safe_strategy}_risk_report.txt",
        mime="text/plain",
        key="download_risk_report_txt",
    ):
        posthog_analytics.capture("risk_report_downloaded", {
            "ticker": str(result["ticker"]),
            "strategy": str(result.get("strategy_name", "")),
            "format": "txt",
        })

    if export_col2.download_button(
        label="Download Risk Report CSV",
        data=report_csv,
        file_name=f"{safe_ticker}_{safe_strategy}_risk_report.csv",
        mime="text/csv",
        key="download_risk_report_csv",
    ):
        posthog_analytics.capture("risk_report_downloaded", {
            "ticker": str(result["ticker"]),
            "strategy": str(result.get("strategy_name", "")),
            "format": "csv",
        })

    with st.expander("Risk Report Preview", expanded=False):
        st.text(report_text)


def render_risk_alerts_section(result: dict) -> None:
    """Render risk alerts and threshold warnings."""
    st.subheader("Risk Alerts and Threshold Warnings")

    alerts_df = build_risk_alerts(result)

    high_alerts = alerts_df[alerts_df["Severity"] == "High"]
    moderate_alerts = alerts_df[alerts_df["Severity"] == "Moderate"]

    if not high_alerts.empty:
        st.error(
            f"{len(high_alerts)} high-severity risk alert(s) detected. Review before advancing this strategy."
        )
    elif not moderate_alerts.empty:
        st.warning(
            f"{len(moderate_alerts)} moderate-severity risk alert(s) detected. Review before scaling this strategy."
        )
    else:
        st.success("No major risk alerts detected for this backtest.")

    with st.expander("Risk Alert Details", expanded=True):
        st.dataframe(
            alerts_df,
            use_container_width=True,
            hide_index=True,
        )

        alerts_csv = alerts_df.to_csv(index=False)

        st.download_button(
            label="Download Risk Alerts CSV",
            data=alerts_csv,
            file_name=f"{str(result['ticker']).lower()}_risk_alerts.csv",
            mime="text/csv",
            key="download_risk_alerts_csv",
        )


def render_risk_dashboard_summary_section(result: dict) -> None:
    """Render high-level strategy risk dashboard summary."""
    st.subheader("Risk Dashboard Summary")

    ratings = classify_risk_level(result)
    dashboard_df = build_risk_dashboard_dataframe(result)

    dashboard_col1, dashboard_col2, dashboard_col3, dashboard_col4 = st.columns(4)

    dashboard_col1.metric(
        "Overall Risk",
        ratings["overall_rating"],
    )

    dashboard_col2.metric(
        "Sharpe Rating",
        ratings["sharpe_rating"],
    )

    dashboard_col3.metric(
        "Volatility Rating",
        ratings["volatility_rating"],
    )

    dashboard_col4.metric(
        "Drawdown Rating",
        ratings["drawdown_rating"],
    )

    if ratings["overall_rating"] == "Stable":
        st.success(ratings["interpretation"])
    elif ratings["overall_rating"] == "Moderate Risk":
        st.warning(ratings["interpretation"])
    else:
        st.error(ratings["interpretation"])

    with st.expander("Risk Dashboard Details", expanded=False):
        st.dataframe(
            dashboard_df,
            use_container_width=True,
            hide_index=True,
        )

        dashboard_csv = dashboard_df.to_csv(index=False)

        st.download_button(
            label="Download Risk Dashboard CSV",
            data=dashboard_csv,
            file_name=f"{str(result['ticker']).lower()}_risk_dashboard.csv",
            mime="text/csv",
            key="download_risk_dashboard_csv",
        )


def render_risk_metric_section(result: dict) -> None:
    """Render risk metrics returned by the backtesting engine."""
    st.subheader("Risk Analytics")

    st.markdown(
        """
These metrics are calculated by the reusable `risk/risk_metrics.py` module and returned by the backtesting engine.
"""
    )

    risk_col1, risk_col2, risk_col3 = st.columns(3)

    risk_col1.metric(
        "Annualized Return",
        f"{result['annualized_return_pct']:.2f}%",
    )

    risk_col2.metric(
        "Annualized Volatility",
        f"{result['annualized_volatility_pct']:.2f}%",
    )

    risk_col3.metric(
        "Sharpe Ratio",
        f"{result['sharpe_ratio']:.2f}",
    )

    risk_col4, risk_col5, risk_col6 = st.columns(3)

    risk_col4.metric(
        "Sortino Ratio",
        f"{result['sortino_ratio']:.2f}",
    )

    risk_col5.metric(
        "Risk Max Drawdown",
        f"{result['risk_max_drawdown_pct']:.2f}%",
    )

    risk_col6.metric(
        "Drawdown Duration",
        result["drawdown_duration"],
    )

    risk_col7, risk_col8, risk_col9 = st.columns(3)

    risk_col7.metric(
        "Value at Risk 95%",
        f"{result['value_at_risk_95_pct']:.2f}%",
    )

    risk_col8.metric(
        "Conditional VaR 95%",
        f"{result['conditional_value_at_risk_95_pct']:.2f}%",
    )

    risk_col9.metric(
        "Calmar Ratio",
        f"{result['calmar_ratio']:.2f}",
    )

    risk_summary_rows = [
        {
            "Metric": "Annualized Return",
            "Value": f"{result['annualized_return_pct']:.2f}%",
            "Meaning": "Estimated yearly return based on the backtest equity curve.",
        },
        {
            "Metric": "Annualized Volatility",
            "Value": f"{result['annualized_volatility_pct']:.2f}%",
            "Meaning": "Estimated yearly variability of daily returns.",
        },
        {
            "Metric": "Sharpe Ratio",
            "Value": f"{result['sharpe_ratio']:.2f}",
            "Meaning": "Return compared with total volatility.",
        },
        {
            "Metric": "Sortino Ratio",
            "Value": f"{result['sortino_ratio']:.2f}",
            "Meaning": "Return compared with downside volatility only.",
        },
        {
            "Metric": "Risk Max Drawdown",
            "Value": f"{result['risk_max_drawdown_pct']:.2f}%",
            "Meaning": "Worst peak-to-trough decline in the equity curve.",
        },
        {
            "Metric": "Drawdown Duration",
            "Value": result["drawdown_duration"],
            "Meaning": "Longest number of periods spent below a prior equity high.",
        },
        {
            "Metric": "Value at Risk 95%",
            "Value": f"{result['value_at_risk_95_pct']:.2f}%",
            "Meaning": "Historical estimate of a bad daily return threshold.",
        },
        {
            "Metric": "Conditional VaR 95%",
            "Value": f"{result['conditional_value_at_risk_95_pct']:.2f}%",
            "Meaning": "Average return during the worst tail-return days.",
        },
        {
            "Metric": "Calmar Ratio",
            "Value": f"{result['calmar_ratio']:.2f}",
            "Meaning": "Annualized return compared with absolute maximum drawdown.",
        },
    ]

    with st.expander("Risk Metric Definitions", expanded=False):
        st.dataframe(
            pd.DataFrame(risk_summary_rows),
            use_container_width=True,
            hide_index=True,
        )


def render_metric_row(result: dict) -> None:
    """Render top-level backtest metrics."""
    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)

    metric_col1.metric(
        "Starting Cash",
        f"${result['starting_cash']:,.2f}",
    )

    metric_col2.metric(
        "Ending Value",
        f"${result['ending_value']:,.2f}",
    )

    metric_col3.metric(
        "Total Return",
        f"{result['total_return_pct']:.2f}%",
    )

    metric_col4.metric(
        "Max Drawdown",
        f"{result['max_drawdown_pct']:.2f}%",
    )

    trade_col1, trade_col2, trade_col3, trade_col4 = st.columns(4)

    trade_col1.metric(
        "Number of Trades",
        result["number_of_trades"],
    )

    trade_col2.metric(
        "Completed Trades",
        result["completed_trades"],
    )

    trade_col3.metric(
        "Win Rate",
        f"{result['win_rate_pct']:.2f}%",
    )

    trade_col4.metric(
        "Exposure",
        f"{result['exposure_pct']:.2f}%",
    )

    pnl_col1, pnl_col2, pnl_col3, pnl_col4 = st.columns(4)

    pnl_col1.metric(
        "Average Gain",
        f"${result['average_gain']:,.2f}",
    )

    pnl_col2.metric(
        "Average Loss",
        f"${result['average_loss']:,.2f}",
    )

    pnl_col3.metric(
        "Best Trade",
        f"${result['best_trade']:,.2f}",
    )

    pnl_col4.metric(
        "Worst Trade",
        f"${result['worst_trade']:,.2f}",
    )

    benchmark_col1, benchmark_col2, benchmark_col3, benchmark_col4 = st.columns(4)

    benchmark_col1.metric(
        "Benchmark Ending Value",
        f"${result['benchmark_ending_value']:,.2f}",
    )

    benchmark_col2.metric(
        "Benchmark Return",
        f"{result['benchmark_total_return_pct']:.2f}%",
    )

    benchmark_col3.metric(
        "Benchmark Drawdown",
        f"{result['benchmark_max_drawdown_pct']:.2f}%",
    )

    benchmark_col4.metric(
        "Strategy Excess Return",
        f"{result['strategy_excess_return_pct']:.2f}%",
    )

    st.caption(
        f"Strategy: {result['strategy_name']} | "
        f"Benchmark: {result['benchmark_name']}"
    )


def render_strategy_comparison_section(
    price_data: pd.DataFrame,
    ticker: str,
    starting_cash: float,
    short_window: int,
    long_window: int,
    trade_size_pct: float,
) -> None:
    """Render side-by-side strategy comparison results."""
    st.subheader("Strategy Comparison")

    st.markdown(
        """
Compare the moving-average crossover strategy against a buy-and-hold strategy using the same ticker, period, and starting cash.
"""
    )

    try:
        comparison = compare_strategies(
            price_data=price_data,
            ticker=ticker,
            strategies=[
                MovingAverageCrossoverStrategy(
                    short_window=int(short_window),
                    long_window=int(long_window),
                ),
                BuyAndHoldStrategy(),
            ],
            starting_cash=float(starting_cash),
            trade_size_pct=float(trade_size_pct),
        )
    except Exception as error:
        st.error(f"Strategy comparison failed: {error}")
        return

    summary = comparison["summary"]

    if summary.empty:
        st.info("No strategy comparison results available.")
        return

    best_return_strategy = comparison["best_return_strategy"]
    lowest_drawdown_strategy = comparison["lowest_drawdown_strategy"]

    best_sharpe_strategy = comparison["best_sharpe_strategy"]
    best_calmar_strategy = comparison["best_calmar_strategy"]

    summary_col1, summary_col2, summary_col3, summary_col4 = st.columns(4)

    summary_col1.metric(
        "Best Return Strategy",
        best_return_strategy,
    )

    summary_col2.metric(
        "Lowest Drawdown Strategy",
        lowest_drawdown_strategy,
    )

    summary_col3.metric(
        "Best Sharpe Strategy",
        best_sharpe_strategy,
    )

    summary_col4.metric(
        "Best Calmar Strategy",
        best_calmar_strategy,
    )

    display_summary = summary.copy()

    numeric_columns = [
        "starting_cash",
        "ending_value",
        "total_return_pct",
        "max_drawdown_pct",
        "win_rate_pct",
        "exposure_pct",
        "annualized_return_pct",
        "annualized_volatility_pct",
        "sharpe_ratio",
        "sortino_ratio",
        "risk_max_drawdown_pct",
        "value_at_risk_95_pct",
        "conditional_value_at_risk_95_pct",
        "calmar_ratio",
    ]

    for column in numeric_columns:
        if column in display_summary.columns:
            display_summary[column] = display_summary[column].round(2)

    st.dataframe(
        display_summary,
        use_container_width=True,
        hide_index=True,
    )

    chart_frames = []

    for row in comparison["results"]:
        result = row["result"]
        equity_curve = result["equity_curve"]

        if equity_curve.empty:
            continue

        strategy_chart = equity_curve[["Date", "total_value"]].copy()
        strategy_chart = strategy_chart.rename(
            columns={"total_value": row["strategy_name"]}
        )

        chart_frames.append(strategy_chart)

    if chart_frames:
        chart_data = chart_frames[0]

        for next_frame in chart_frames[1:]:
            chart_data = chart_data.merge(
                next_frame,
                on="Date",
                how="inner",
            )

        chart_data = chart_data.set_index("Date")

        st.subheader("Strategy Equity Curve Comparison")
        st.line_chart(chart_data)
    else:
        st.info("No strategy equity curves available.")

    comparison_csv = display_summary.to_csv(index=False)

    st.download_button(
        label="Download Strategy Comparison CSV",
        data=comparison_csv,
        file_name="strategy_comparison.csv",
        mime="text/csv",
        key="download_strategy_comparison_csv",
    )



def render_technical_factor_section(price_data: pd.DataFrame) -> None:
    """Render technical factors generated from standardized price data."""
    try:
        factor_table = build_technical_factor_table(price_data)
    except Exception as error:
        st.error(f"Technical factor calculation failed: {error}")
        return

    st.subheader("Technical Factor Research")

    st.markdown(
        """
This section uses the reusable `factors/technical.py` module. These indicators can later feed strategy rules, strategy comparison, risk analytics, and machine learning features.
"""
    )

    latest_row = factor_table.iloc[-1]

    factor_col1, factor_col2, factor_col3, factor_col4 = st.columns(4)

    factor_col1.metric(
        "RSI 14",
        f"{latest_row.get('rsi_14', 0):.2f}",
    )

    factor_col2.metric(
        "Volatility 20",
        f"{latest_row.get('volatility_20', 0) * 100:.2f}%",
    )

    factor_col3.metric(
        "Momentum 20",
        f"{latest_row.get('momentum_20', 0) * 100:.2f}%",
    )

    factor_col4.metric(
        "Distance from MA 50",
        f"{latest_row.get('price_distance_from_ma_50', 0):.2f}%",
    )

    with st.expander("Moving Averages", expanded=False):
        moving_average_columns = [
            column
            for column in ["Date", "Close", "ma_20", "ma_50", "ma_200"]
            if column in factor_table.columns
        ]

        chart_data = factor_table[moving_average_columns].copy()

        if "Date" in chart_data.columns:
            chart_data = chart_data.set_index("Date")

        st.line_chart(chart_data)

    with st.expander("RSI, MACD, Momentum, and Volatility", expanded=False):
        indicator_columns = [
            column
            for column in [
                "Date",
                "rsi_14",
                "macd",
                "macd_signal",
                "macd_histogram",
                "momentum_20",
                "volatility_20",
            ]
            if column in factor_table.columns
        ]

        indicator_data = factor_table[indicator_columns].copy()

        if "Date" in indicator_data.columns:
            indicator_data = indicator_data.set_index("Date")

        st.line_chart(indicator_data)

    with st.expander("Technical Factor Table", expanded=False):
        display_columns = [
            column
            for column in [
                "Date",
                "Open",
                "High",
                "Low",
                "Close",
                "Volume",
                "daily_return",
                "cumulative_return",
                "ma_20",
                "ma_50",
                "ma_200",
                "volatility_20",
                "momentum_20",
                "rsi_14",
                "macd",
                "macd_signal",
                "macd_histogram",
                "volume_average_20",
                "price_distance_from_ma_50",
            ]
            if column in factor_table.columns
        ]

        st.dataframe(
            factor_table[display_columns].tail(100),
            use_container_width=True,
            hide_index=True,
        )

        factor_csv = factor_table[display_columns].to_csv(index=False)

        st.download_button(
            label="Download Technical Factors CSV",
            data=factor_csv,
            file_name="technical_factors.csv",
            mime="text/csv",
            key="download_technical_factors_csv",
        )


def render_backtesting_page() -> None:
    """Render the Streamlit backtesting page."""
    st.title("Backtesting Lab")
    st.caption("Sprint 68 — Backtesting Engine Foundation")

    st.markdown(
        """
Use this page to test a moving-average crossover strategy against historical market data.

The Streamlit page displays the results. The calculation engine lives in the `backtesting/`
and `strategies/` modules.
"""
    )

    with st.sidebar:
        st.header("Backtest Settings")

        ticker = st.text_input(
            "Ticker",
            value="AAPL",
            key="backtest_ticker_input",
        ).strip().upper()

        period = st.selectbox(
            "Historical Period",
            options=["6mo", "1y", "2y", "5y"],
            index=1,
            key="backtest_period_select",
        )

        starting_cash = st.number_input(
            "Starting Cash",
            min_value=100.0,
            max_value=1_000_000.0,
            value=10_000.0,
            step=500.0,
            key="backtest_starting_cash_input",
        )

        short_window = st.number_input(
            "Short Moving Average Window",
            min_value=2,
            max_value=100,
            value=20,
            step=1,
            key="backtest_short_window_input",
        )

        long_window = st.number_input(
            "Long Moving Average Window",
            min_value=5,
            max_value=300,
            value=50,
            step=1,
            key="backtest_long_window_input",
        )

        trade_size_pct = st.slider(
            "Trade Size",
            min_value=0.10,
            max_value=1.00,
            value=1.00,
            step=0.05,
            format="%.2f",
            key="backtest_trade_size_slider",
        )

        run_backtest = st.button(
            "Run Backtest",
            type="primary",
            key="run_backtest_button",
        )

    if not ticker:
        st.warning("Enter a ticker symbol to run a backtest.")
        return

    if short_window >= long_window:
        st.error("Short moving average window must be less than long moving average window.")
        return

    if not run_backtest:
        st.info("Set your parameters in the sidebar, then click Run Backtest.")
        return

    try:
        with st.spinner("Loading market data and running backtest..."):
            price_data = load_backtest_price_data(ticker=ticker, period=period)

            if price_data.empty:
                st.error("No market data returned for this ticker and period.")
                return

            strategy = MovingAverageCrossoverStrategy(
                short_window=int(short_window),
                long_window=int(long_window),
            )

            engine = BacktestEngine(
                strategy=strategy,
                ticker=ticker,
                starting_cash=float(starting_cash),
                trade_size_pct=float(trade_size_pct),
            )

            result = engine.run(price_data)

    except Exception as error:
        st.error(f"Backtest failed: {error}")
        posthog_analytics.capture_exception(error)
        return

    posthog_analytics.capture("backtest_run", {
        "ticker": ticker,
        "period": period,
        "starting_cash": float(starting_cash),
        "short_window": int(short_window),
        "long_window": int(long_window),
        "trade_size_pct": float(trade_size_pct),
        "total_return_pct": round(float(result.get("total_return_pct", 0.0)), 2),
        "sharpe_ratio": round(float(result.get("sharpe_ratio", 0.0)), 2),
        "number_of_trades": int(result.get("number_of_trades", 0)),
        "risk_level": classify_risk_level(result).get("overall_rating"),
    })

    st.subheader(f"{ticker} Backtest Results")
    render_metric_row(result)
    render_risk_dashboard_summary_section(result)
    render_risk_alerts_section(result)
    render_risk_metric_section(result)
    render_risk_report_export_section(result)
    render_drawdown_section(result)
    render_rolling_volatility_section(result)

    equity_curve = result["equity_curve"]
    benchmark_equity_curve = result["benchmark_equity_curve"]
    trades = result["trades"]
    completed_trade_details = result["completed_trade_details"]
    signals = result["signals"]

    st.subheader("Strategy vs Benchmark Equity Curve")

    if not equity_curve.empty and not benchmark_equity_curve.empty:
        strategy_chart = equity_curve[["Date", "total_value"]].copy()
        strategy_chart = strategy_chart.rename(
            columns={"total_value": "Strategy Value"}
        )

        benchmark_chart = benchmark_equity_curve[
            ["Date", "benchmark_total_value"]
        ].copy()
        benchmark_chart = benchmark_chart.rename(
            columns={"benchmark_total_value": "Buy-and-Hold Value"}
        )

        chart_data = strategy_chart.merge(
            benchmark_chart,
            on="Date",
            how="inner",
        ).set_index("Date")

        st.line_chart(chart_data)
    elif not equity_curve.empty:
        chart_data = equity_curve.set_index("Date")[["total_value"]]
        st.line_chart(chart_data)
    else:
        st.info("No equity curve data available.")

    render_strategy_comparison_section(
        price_data=price_data,
        ticker=ticker,
        starting_cash=float(starting_cash),
        short_window=int(short_window),
        long_window=int(long_window),
        trade_size_pct=float(trade_size_pct),
    )

    render_technical_factor_section(price_data)

    st.subheader("Strategy Signals")

    signal_columns = [
        column
        for column in ["Date", "Close", "short_ma", "long_ma", "signal"]
        if column in signals.columns
    ]

    st.dataframe(
        signals[signal_columns].tail(100),
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Trade Log")

    if trades.empty:
        st.info("No trades were generated for this period and strategy configuration.")
    else:
        st.dataframe(
            trades,
            use_container_width=True,
            hide_index=True,
        )

    st.subheader("Completed Trade PnL")

    if completed_trade_details.empty:
        st.info("No completed buy/sell trade pairs available yet.")
    else:
        st.dataframe(
            completed_trade_details,
            use_container_width=True,
            hide_index=True,
        )

    with st.expander("Backtesting Methodology", expanded=False):
        st.markdown(
            """
### Strategy Logic

The current strategy is a moving-average crossover.

- Buy signal: short moving average crosses above long moving average.
- Sell signal: short moving average crosses below long moving average.

### Engine Logic

The backtesting engine:

1. Validates standardized price data.
2. Generates strategy signals.
3. Simulates long-only buy/sell trades.
4. Tracks cash, shares, position value, and total portfolio value.
5. Builds an equity curve.
6. Returns basic metrics.

### Rolling Volatility Logic

The rolling volatility section uses the strategy equity curve to measure how unstable daily returns are over time.

Current implementation:

- Calculates daily returns from total portfolio value
- Uses a 20-period rolling window
- Annualizes volatility using 252 trading periods per year
- Displays latest, average, and maximum rolling volatility
- Exports the full rolling volatility series as CSV

This view helps identify periods where the strategy became more unstable, even if the final return looked acceptable.

### Drawdown Analysis Logic

The drawdown section uses the strategy equity curve to measure declines from previous portfolio highs.

Drawdown is calculated as:

- Current total value minus running peak
- Divided by running peak
- Expressed as a percentage

A drawdown near zero means the strategy is close to its equity high. A deeply negative drawdown means the strategy is far below a prior peak.

This view helps evaluate downside risk and recovery pressure.

### Risk Report Export Logic

The risk report export section creates downloadable TXT and CSV summaries from the current backtest result.

The TXT export is designed for human review.

The CSV export is designed for spreadsheet analysis and comparison across runs.

The exported report includes:

- Backtest summary
- Benchmark comparison
- Strategy excess return
- Risk metrics
- Trade metrics
- Educational disclaimer

### Risk Alerts Logic

The risk alerts section applies rule-based threshold checks to the current backtest result.

Current alert checks:

- Annualized volatility above moderate or high thresholds
- Sharpe ratio below acceptable thresholds
- Maximum drawdown above moderate or high thresholds
- Historical Value at Risk above moderate or high thresholds
- Negative total return
- Strategy underperformance versus the benchmark

The alerts are not investment advice. They are engineering guardrails that help decide whether a strategy should move forward to optimization, paper trading, or live execution.

### Risk Dashboard Summary Logic

The risk dashboard summary converts detailed risk metrics into quick review ratings.

Current review areas:

- Overall risk
- Sharpe rating
- Volatility rating
- Drawdown rating
- Value at Risk rating

The rating system is rule-based and uses thresholds from the current backtest result.

This panel is not investment advice. It is a portfolio-project decision aid that helps identify whether a strategy needs more review before optimization, paper trading, or live execution.

### Risk Analytics Logic

The risk analytics section uses the reusable `risk/risk_metrics.py` module.

Current risk metrics include:

- Annualized return
- Annualized volatility
- Sharpe-style ratio
- Sortino-style ratio
- Maximum drawdown
- Drawdown duration
- Historical Value at Risk at 95%
- Historical Conditional Value at Risk at 95%
- Calmar-style ratio

These metrics help evaluate whether a strategy's return is worth the risk taken.

### Strategy Comparison Logic

The strategy comparison section uses `backtesting/comparison.py` to run multiple strategies against the same standardized price data.

Current comparison:

- Moving Average Crossover
- Buy and Hold

The comparison table shows:

- Ending value
- Total return
- Maximum drawdown
- Number of trades
- Completed trades
- Win rate
- Exposure

Risk-adjusted comparison fields include:

- Annualized return
- Annualized volatility
- Sharpe-style ratio
- Sortino-style ratio
- Risk maximum drawdown
- Drawdown duration
- Value at Risk
- Conditional Value at Risk
- Calmar-style ratio

This creates the foundation for comparing more strategies later, including momentum, mean reversion, and machine-learning-driven strategies.

### Technical Factor Logic

The technical factor section is powered by the reusable `factors/technical.py` module.

Current factors include:

- Daily return
- Cumulative return
- Moving averages
- Rolling volatility
- Momentum
- RSI
- MACD
- Rolling average volume
- Price distance from moving average

These factors are not yet used to make trading decisions in this sprint. They are exposed for research and will support future strategy comparison, risk analytics, optimization, and machine learning.

### Benchmark Logic

The benchmark uses a simple buy-and-hold approach:

1. Invest all starting cash at the first available close price.
2. Hold the same number of shares through the full historical period.
3. Compare ending value, total return, and drawdown against the strategy.

### Current Limitations

This first version does not yet include:

- Transaction costs
- Slippage
- Taxes
- Dividends
- Short selling
- Stop losses
- Multi-asset portfolios
- Broker execution

Those should be added in later Sprint 68 features.
"""
        )


render_backtesting_page()
