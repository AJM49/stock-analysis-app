from __future__ import annotations

import pandas as pd

from portfolio import build_portfolio_dataframe, calculate_portfolio_data_health


def build_portfolio_data_health(portfolio_df):
    return calculate_portfolio_data_health(
        portfolio_df
    )


def build_portfolio_dashboard_data(portfolio_positions) -> pd.DataFrame:
    return build_portfolio_dataframe(portfolio_positions)
