from contextlib import nullcontext
from unittest.mock import MagicMock

import pandas as pd

import ui.portfolio_views as portfolio_views


def test_dashboard_renders_valid_non_empty_portfolio(monkeypatch):
    portfolio_df = pd.DataFrame(
        [
            {
                "Ticker": "AAPL",
                "Quantity": 10.0,
                "Buy Price": 100.0,
                "Current Price": 120.0,
                "Cost Basis": 1000.0,
                "Current Value": 1200.0,
                "Gain/Loss": 200.0,
                "Gain/Loss %": 20.0,
            }
        ]
    )

    render_policy = {
        "mode": "full",
        "show_derived_analytics": True,
        "show_raw_holdings": True,
        "show_risk_analytics": True,
        "show_performance_analytics": True,
        "show_allocation_analytics": True,
        "show_caution": False,
    }

    st = MagicMock()
    st.expander.side_effect = (
        lambda *args, **kwargs: nullcontext()
    )
    st.columns.side_effect = (
        lambda spec, **kwargs: [
            MagicMock()
            for _ in range(
                spec if isinstance(spec, int) else len(spec)
            )
        ]
    )

    monkeypatch.setattr(
        portfolio_views,
        "st",
        st,
    )

    keep_real = {
        "render_portfolio_dashboard",
        "render_unrealized_gain_loss_summary",
    }

    for name in dir(portfolio_views):
        if (
            name.startswith("render_")
            and name not in keep_real
        ):
            monkeypatch.setattr(
                portfolio_views,
                name,
                lambda *args, **kwargs: None,
            )

    portfolio_views.render_portfolio_dashboard(
        portfolio_df,
        reliability=None,
        metric_gate=render_policy,
        analytics_df=portfolio_df,
    )

    st.subheader.assert_any_call(
        "Unrealized Gain/Loss"
    )
