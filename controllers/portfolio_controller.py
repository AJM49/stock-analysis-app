from __future__ import annotations

import pandas as pd

from portfolio import build_portfolio_dataframe, calculate_portfolio_data_health


def build_portfolio_data_health(portfolio_df):
    return calculate_portfolio_data_health(
        portfolio_df
    )


def build_portfolio_analytics_reliability(portfolio_health):
    if not portfolio_health:
        portfolio_health = {}

    total_positions = int(
        portfolio_health.get(
            "total_positions",
            0,
        )
    )

    quality_status = str(
        portfolio_health.get(
            "quality_status",
            "No Data",
        )
    )

    quality_score = float(
        portfolio_health.get(
            "quality_score",
            0.0,
        )
    )

    coverage_pct = float(
        portfolio_health.get(
            "coverage_pct",
            0.0,
        )
    )

    freshness_pct = float(
        portfolio_health.get(
            "freshness_pct",
            0.0,
        )
    )

    if total_positions == 0 or quality_status == "No Data":
        return {
            "status": "Unavailable",
            "severity": "info",
            "display_mode": "unavailable",
            "decision_ready": False,
            "quality_score": quality_score,
            "coverage_pct": coverage_pct,
            "freshness_pct": freshness_pct,
            "message": (
                "Portfolio analytics are unavailable because "
                "there are no positions with usable market data."
            ),
        }

    if quality_status in {
        "Excellent",
        "Good",
    }:
        return {
            "status": "Reliable",
            "severity": "success",
            "display_mode": "full",
            "decision_ready": True,
            "quality_score": quality_score,
            "coverage_pct": coverage_pct,
            "freshness_pct": freshness_pct,
            "message": (
                "Portfolio analytics are supported by strong "
                "market-data coverage and freshness."
            ),
        }

    if quality_status == "Fair":
        return {
            "status": "Use With Caution",
            "severity": "warning",
            "display_mode": "caution",
            "decision_ready": False,
            "quality_score": quality_score,
            "coverage_pct": coverage_pct,
            "freshness_pct": freshness_pct,
            "message": (
                "Portfolio calculations include stale or "
                "missing market prices. Refresh market data "
                "before relying on valuation, performance, "
                "or risk metrics for decisions."
            ),
        }

    return {
        "status": "Insufficient Data",
        "severity": "error",
        "display_mode": "restricted",
        "decision_ready": False,
        "quality_score": quality_score,
        "coverage_pct": coverage_pct,
        "freshness_pct": freshness_pct,
        "message": (
            "Portfolio market-data quality is too weak for "
            "reliable valuation, performance, or risk "
            "conclusions."
        ),
    }


def get_portfolio_analytics_render_mode(reliability):
    if not reliability:
        return "full"

    status = str(
        reliability.get(
            "status",
            "Reliable",
        )
    )

    if status == "Use With Caution":
        return "caution"

    if status in {
        "Insufficient Data",
        "Unavailable",
    }:
        return "holdings_only"

    return "full"


def build_portfolio_dashboard_data(portfolio_positions) -> pd.DataFrame:
    return build_portfolio_dataframe(portfolio_positions)
