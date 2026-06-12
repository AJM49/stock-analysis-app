from __future__ import annotations

import pandas as pd

from portfolio import build_portfolio_dataframe


def build_portfolio_dashboard_data(portfolio_positions) -> pd.DataFrame:
    return build_portfolio_dataframe(portfolio_positions)
