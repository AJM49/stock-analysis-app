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
            "render_mode": "unavailable",
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
            "render_mode": "full",
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
            "render_mode": "caution",
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
        "render_mode": "restricted",
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
        return "unavailable"

    render_mode = reliability.get(
        "render_mode"
    )

    if render_mode in {
        "full",
        "caution",
        "restricted",
        "unavailable",
    }:
        return render_mode

    status = str(
        reliability.get(
            "status",
            "Unavailable",
        )
    )

    if status == "Reliable":
        return "full"

    if status == "Use With Caution":
        return "caution"

    if status == "Insufficient Data":
        return "restricted"

    return "unavailable"


def should_render_portfolio_summary_metrics(reliability):
    return (
        get_portfolio_analytics_render_mode(
            reliability
        )
        in {
            "full",
            "caution",
        }
    )



def build_portfolio_render_policy(reliability):
    if not reliability:
        return {
            "status": "Unavailable",
            "mode": "unavailable",
            "show_derived_analytics": False,
            "show_raw_holdings": True,
            "show_caution": True,
        }

    status = str(
        reliability.get(
            "status",
            "Unavailable",
        )
    )

    if status == "Reliable":
        return {
            "status": status,
            "mode": "full",
            "show_derived_analytics": True,
            "show_raw_holdings": True,
            "show_caution": False,
        }

    if status == "Use With Caution":
        return {
            "status": status,
            "mode": "caution",
            "show_derived_analytics": True,
            "show_raw_holdings": True,
            "show_caution": True,
        }

    if status == "Insufficient Data":
        return {
            "status": status,
            "mode": "restricted",
            "show_derived_analytics": False,
            "show_raw_holdings": True,
            "show_caution": True,
        }

    return {
        "status": status,
        "mode": "unavailable",
        "show_derived_analytics": False,
        "show_raw_holdings": True,
        "show_caution": True,
    }


def build_portfolio_snapshot_save_policy(reliability):
    status = str(
        (reliability or {}).get(
            "status",
            "Unavailable",
        )
    )

    if status == "Reliable":
        return {
            "allowed": True,
            "status": status,
            "message": (
                "Portfolio data reliability supports "
                "saving a derived analytics snapshot."
            ),
        }

    if status == "Use With Caution":
        return {
            "allowed": True,
            "status": status,
            "message": (
                "This snapshot will include analytics "
                "derived from stale or missing prices. "
                "Refresh market data when possible."
            ),
        }

    if status == "Insufficient Data":
        return {
            "allowed": False,
            "status": status,
            "message": (
                "Snapshot saving is disabled because "
                "market-data quality is insufficient for "
                "reliable valuation and risk metrics."
            ),
        }

    return {
        "allowed": False,
        "status": status,
        "message": (
            "Snapshot saving is unavailable until "
            "sufficient portfolio market data exists."
        ),
    }


def build_portfolio_metric_gate(reliability):
    policy = build_portfolio_render_policy(
        reliability
    )

    show_derived_analytics = bool(
        policy.get(
            "show_derived_analytics",
            False,
        )
    )

    return {
        "show_derived_analytics": show_derived_analytics,
        "show_derived_metrics": show_derived_analytics,
        "show_risk_analytics": show_derived_analytics,
        "show_performance_analytics": show_derived_analytics,
        "show_raw_holdings": bool(
            policy.get(
                "show_raw_holdings",
                True,
            )
        ),
        "mode": policy.get(
            "mode",
            "unavailable",
        ),
    }


def build_portfolio_analytics_render_mode(reliability):
    return get_portfolio_analytics_render_mode(
        reliability
    )


def build_priced_portfolio_analytics_data(portfolio_df):
    if portfolio_df is None or portfolio_df.empty:
        return pd.DataFrame()

    if "Price Status" not in portfolio_df.columns:
        return pd.DataFrame()

    return (
        portfolio_df.loc[
            portfolio_df["Price Status"] == "Available"
        ]
        .copy()
        .reset_index(drop=True)
    )


def should_render_portfolio_derived_analytics(
    reliability,
):
    return (
        get_portfolio_analytics_render_mode(
            reliability
        )
        in {
            "full",
            "caution",
        }
    )


def build_portfolio_analytics_render_policy(reliability):
    reliability = reliability or {}

    status = str(
        reliability.get(
            "status",
            "Unavailable",
        )
    )

    if status == "Reliable":
        return {
            "mode": "full",
            "allow_derived_analytics": True,
            "show_caution": False,
        }

    if status == "Use With Caution":
        return {
            "mode": "caution",
            "allow_derived_analytics": True,
            "show_caution": True,
        }

    if status == "Insufficient Data":
        return {
            "mode": "limited",
            "allow_derived_analytics": False,
            "show_caution": True,
        }

    return {
        "mode": "unavailable",
        "allow_derived_analytics": False,
        "show_caution": False,
    }


def build_portfolio_dashboard_data(portfolio_positions) -> pd.DataFrame:
    return build_portfolio_dataframe(portfolio_positions)
