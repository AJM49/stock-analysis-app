import pandas as pd

def get_latest_price_for_ticker(ticker: str) -> float:
    """Return latest cached close price for a ticker."""
    from services.market_data_service import get_stock_data

    result = get_stock_data(ticker, cache_only=True)

    if isinstance(result, tuple):
        history = result[0]
    else:
        history = getattr(result, "history", None)

    if history is None or history.empty:
        return 0.0

    if "Close" not in history.columns:
        return 0.0

    latest_close = history["Close"].dropna()

    if latest_close.empty:
        return 0.0

    return float(latest_close.iloc[-1])


def empty_portfolio_dataframe():
    return pd.DataFrame(columns=PORTFOLIO_COLUMNS)




def build_portfolio_dataframe(portfolio_positions):
    """Build portfolio analytics dataframe from saved positions."""
    portfolio_rows = []

    if not portfolio_positions:
        return pd.DataFrame(portfolio_rows)

    for position in portfolio_positions:
        ticker = str(position.ticker).upper()
        shares = float(position.shares or 0)
        buy_price = float(position.buy_price or 0)

        current_price = get_latest_price_for_ticker(ticker)

        if current_price > 0:
            price_status = "Available"
        else:
            price_status = "Missing"

        cost_basis = shares * buy_price
        current_value = shares * current_price
        gain_loss = current_value - cost_basis

        if cost_basis > 0:
            gain_loss_pct = (gain_loss / cost_basis) * 100
        else:
            gain_loss_pct = 0.0

        portfolio_rows.append(
            {
                "Ticker": ticker,
                "Shares": shares,
                "Buy Price": buy_price,
                "Cost Basis": cost_basis,
                "Current Price": current_price,
                "Price Status": price_status,
                "Current Value": current_value,
                "Gain/Loss": gain_loss,
                "Gain/Loss %": gain_loss_pct,
            }
        )

    portfolio_df = pd.DataFrame(portfolio_rows)

    if portfolio_df.empty:
        return portfolio_df

    total_current_value = portfolio_df["Current Value"].sum()

    if total_current_value > 0:
        portfolio_df["Allocation %"] = (
            portfolio_df["Current Value"] / total_current_value
        ) * 100
    else:
        portfolio_df["Allocation %"] = 0.0

    return portfolio_df


def format_portfolio_dataframe(portfolio_df):
    formatted_df = portfolio_df.copy()

    money_columns = [
        "Buy Price",
        "Current Price",
        "Cost Basis",
        "Current Value",
        "Gain/Loss"
    ]

    for column in money_columns:
        formatted_df[column] = formatted_df[column].map(
            lambda value: f"${value:,.2f}"
        )

    percent_columns = [
        "Gain/Loss %",
        "Allocation %",
        "Volatility %"
    ]

    for column in percent_columns:
        formatted_df[column] = formatted_df[column].map(
            lambda value: f"{value:.2f}%"
        )

    return formatted_df


def calculate_portfolio_risk_score(portfolio_df):
    if portfolio_df.empty:
        return 0, "No portfolio data"

    max_allocation = portfolio_df["Allocation %"].max()
    average_volatility = portfolio_df["Volatility %"].mean()
    position_count = len(portfolio_df)

    score = 0

    if max_allocation >= 50:
        score += 40
    elif max_allocation >= 35:
        score += 25
    elif max_allocation >= 20:
        score += 10

    if average_volatility >= 3:
        score += 40
    elif average_volatility >= 2:
        score += 25
    elif average_volatility >= 1:
        score += 10

    if position_count <= 2:
        score += 20
    elif position_count <= 4:
        score += 10

    if score >= 70:
        label = "High Risk"
    elif score >= 40:
        label = "Moderate Risk"
    else:
        label = "Lower Risk"

    return score, label


def calculate_stop_loss(current_price, stop_loss_pct):
    stop_price = current_price * (1 - stop_loss_pct / 100)
    return stop_price


def calculate_target_price(current_price, target_gain_pct):
    target_price = current_price * (1 + target_gain_pct / 100)
    return target_price


def calculate_risk_reward(current_price, stop_price, target_price):
    downside_risk = current_price - stop_price
    upside_reward = target_price - current_price

    if downside_risk <= 0:
        return 0

    return upside_reward / downside_risk

