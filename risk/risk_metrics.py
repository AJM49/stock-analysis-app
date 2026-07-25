from __future__ import annotations

import pandas as pd


TRADING_DAYS_PER_YEAR = 252


def calculate_daily_returns(equity_curve: pd.DataFrame) -> pd.Series:
    """Calculate daily returns from an equity curve."""
    if equity_curve.empty:
        raise ValueError("equity_curve cannot be empty")

    if "total_value" not in equity_curve.columns:
        raise ValueError("equity_curve must contain total_value column")

    total_value = pd.to_numeric(equity_curve["total_value"], errors="coerce")

    if total_value.isna().any():
        raise ValueError("total_value cannot contain missing values")

    if (total_value <= 0).any():
        raise ValueError("total_value must contain positive values")

    return total_value.pct_change().fillna(0.0)


def calculate_annualized_return(
    equity_curve: pd.DataFrame,
    periods_per_year: int = TRADING_DAYS_PER_YEAR,
) -> float:
    """Calculate annualized return percentage."""
    if equity_curve.empty:
        raise ValueError("equity_curve cannot be empty")

    total_value = pd.to_numeric(equity_curve["total_value"], errors="coerce")

    starting_value = float(total_value.iloc[0])
    ending_value = float(total_value.iloc[-1])
    periods = len(total_value)

    if starting_value <= 0:
        raise ValueError("starting total_value must be positive")

    if periods <= 1:
        return 0.0

    total_return = ending_value / starting_value

    annualized_return = (total_return ** (periods_per_year / periods)) - 1

    return float(annualized_return * 100)


def calculate_rolling_volatility(
    equity_curve: pd.DataFrame,
    window: int = 20,
    periods_per_year: int = TRADING_DAYS_PER_YEAR,
) -> pd.DataFrame:
    """Calculate rolling annualized volatility from an equity curve."""
    if window <= 1:
        raise ValueError("window must be greater than 1")

    daily_returns = calculate_daily_returns(equity_curve)

    volatility = (
        daily_returns
        .rolling(window=window, min_periods=2)
        .std()
        .fillna(0.0)
        * (periods_per_year ** 0.5)
        * 100
    )

    result = equity_curve[["Date", "total_value"]].copy()
    result[f"rolling_volatility_{window}"] = volatility

    return result


def calculate_annualized_volatility(
    equity_curve: pd.DataFrame,
    periods_per_year: int = TRADING_DAYS_PER_YEAR,
) -> float:
    """Calculate annualized volatility percentage."""
    daily_returns = calculate_daily_returns(equity_curve)

    if len(daily_returns) <= 1:
        return 0.0

    volatility = daily_returns.std() * (periods_per_year ** 0.5)

    return float(volatility * 100)


def calculate_sharpe_ratio(
    equity_curve: pd.DataFrame,
    risk_free_rate_pct: float = 0.0,
    periods_per_year: int = TRADING_DAYS_PER_YEAR,
) -> float:
    """Calculate Sharpe-style risk-adjusted return."""
    annualized_return = calculate_annualized_return(
        equity_curve=equity_curve,
        periods_per_year=periods_per_year,
    )

    annualized_volatility = calculate_annualized_volatility(
        equity_curve=equity_curve,
        periods_per_year=periods_per_year,
    )

    if annualized_volatility == 0:
        return 0.0

    return float((annualized_return - risk_free_rate_pct) / annualized_volatility)


def calculate_sortino_ratio(
    equity_curve: pd.DataFrame,
    risk_free_rate_pct: float = 0.0,
    periods_per_year: int = TRADING_DAYS_PER_YEAR,
) -> float:
    """Calculate Sortino-style downside-risk-adjusted return."""
    daily_returns = calculate_daily_returns(equity_curve)

    downside_returns = daily_returns[daily_returns < 0]

    if downside_returns.empty:
        return 0.0

    downside_deviation = downside_returns.std() * (periods_per_year ** 0.5)

    if downside_deviation == 0:
        return 0.0

    annualized_return = calculate_annualized_return(
        equity_curve=equity_curve,
        periods_per_year=periods_per_year,
    )

    return float((annualized_return - risk_free_rate_pct) / (downside_deviation * 100))


def calculate_drawdown_series(equity_curve: pd.DataFrame) -> pd.Series:
    """Calculate drawdown series from an equity curve."""
    if equity_curve.empty:
        raise ValueError("equity_curve cannot be empty")

    if "total_value" not in equity_curve.columns:
        raise ValueError("equity_curve must contain total_value column")

    total_value = pd.to_numeric(equity_curve["total_value"], errors="coerce")
    running_max = total_value.cummax()

    drawdown = (total_value - running_max) / running_max

    return drawdown * 100


def calculate_max_drawdown_pct(equity_curve: pd.DataFrame) -> float:
    """Calculate maximum drawdown percentage."""
    drawdown = calculate_drawdown_series(equity_curve)

    return float(drawdown.min())


def calculate_drawdown_duration(equity_curve: pd.DataFrame) -> int:
    """Calculate longest drawdown duration in periods."""
    drawdown = calculate_drawdown_series(equity_curve)

    max_duration = 0
    current_duration = 0

    for value in drawdown:
        if value < 0:
            current_duration += 1
            max_duration = max(max_duration, current_duration)
        else:
            current_duration = 0

    return int(max_duration)


def calculate_value_at_risk(
    equity_curve: pd.DataFrame,
    confidence_level: float = 0.95,
) -> float:
    """Calculate historical Value at Risk percentage from daily returns."""
    if not 0 < confidence_level < 1:
        raise ValueError("confidence_level must be between 0 and 1")

    daily_returns = calculate_daily_returns(equity_curve)

    percentile = (1 - confidence_level) * 100
    var_value = daily_returns.quantile(percentile / 100)

    return float(var_value * 100)


def calculate_conditional_value_at_risk(
    equity_curve: pd.DataFrame,
    confidence_level: float = 0.95,
) -> float:
    """Calculate historical Conditional Value at Risk percentage."""
    daily_returns = calculate_daily_returns(equity_curve)
    var_value = calculate_value_at_risk(
        equity_curve=equity_curve,
        confidence_level=confidence_level,
    ) / 100

    tail_returns = daily_returns[daily_returns <= var_value]

    if tail_returns.empty:
        return 0.0

    return float(tail_returns.mean() * 100)


def calculate_calmar_ratio(equity_curve: pd.DataFrame) -> float:
    """Calculate Calmar-style annual return divided by absolute max drawdown."""
    annualized_return = calculate_annualized_return(equity_curve)
    max_drawdown = abs(calculate_max_drawdown_pct(equity_curve))

    if max_drawdown == 0:
        return 0.0

    return float(annualized_return / max_drawdown)


def build_risk_metric_summary(
    equity_curve: pd.DataFrame,
    risk_free_rate_pct: float = 0.0,
) -> dict[str, float]:
    """Build standard risk metric summary from an equity curve."""
    return {
        "annualized_return_pct": calculate_annualized_return(equity_curve),
        "annualized_volatility_pct": calculate_annualized_volatility(equity_curve),
        "sharpe_ratio": calculate_sharpe_ratio(
            equity_curve=equity_curve,
            risk_free_rate_pct=risk_free_rate_pct,
        ),
        "sortino_ratio": calculate_sortino_ratio(
            equity_curve=equity_curve,
            risk_free_rate_pct=risk_free_rate_pct,
        ),
        "max_drawdown_pct": calculate_max_drawdown_pct(equity_curve),
        "drawdown_duration": calculate_drawdown_duration(equity_curve),
        "value_at_risk_95_pct": calculate_value_at_risk(equity_curve),
        "conditional_value_at_risk_95_pct": calculate_conditional_value_at_risk(
            equity_curve
        ),
        "calmar_ratio": calculate_calmar_ratio(equity_curve),
    }
