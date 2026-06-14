import pandas as pd


def calculate_rsi(history, window=14):
    delta = history["Close"].diff()

    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)

    average_gain = gains.rolling(window=window).mean()
    average_loss = losses.rolling(window=window).mean()

    relative_strength = average_gain / average_loss
    rsi = 100 - (100 / (1 + relative_strength))

    return rsi


def calculate_macd(history):
    ema_12 = history["Close"].ewm(
        span=12,
        adjust=False
    ).mean()

    ema_26 = history["Close"].ewm(
        span=26,
        adjust=False
    ).mean()

    macd_line = ema_12 - ema_26

    signal_line = macd_line.ewm(
        span=9,
        adjust=False
    ).mean()

    macd_histogram = macd_line - signal_line

    return macd_line, signal_line, macd_histogram


def calculate_volatility(history):
    daily_returns = history["Close"].pct_change()
    volatility = daily_returns.std() * 100
    return daily_returns, volatility


def add_technical_indicators(history):
    history["MA20"] = history["Close"].rolling(window=20).mean()
    history["MA50"] = history["Close"].rolling(window=50).mean()
    history["RSI"] = calculate_rsi(history)

    macd_line, signal_line, macd_histogram = calculate_macd(history)

    history["MACD"] = macd_line
    history["Signal Line"] = signal_line
    history["MACD Histogram"] = macd_histogram

    daily_returns, volatility = calculate_volatility(history)

    history["Daily Return %"] = daily_returns * 100

    return history, volatility


def get_rsi_signal(rsi_value):
    if pd.isna(rsi_value):
        return "Not enough data"

    if rsi_value >= 70:
        return "Overbought"

    if rsi_value <= 30:
        return "Oversold"

    return "Neutral"


def get_macd_signal(macd_value, signal_value):
    if pd.isna(macd_value) or pd.isna(signal_value):
        return "Not enough data"

    if macd_value > signal_value:
        return "Bullish momentum"

    if macd_value < signal_value:
        return "Bearish momentum"

    return "Neutral momentum"


def get_volatility_signal(volatility_value):
    if pd.isna(volatility_value):
        return "Not enough data"

    if volatility_value >= 3:
        return "High volatility"

    if volatility_value >= 1.5:
        return "Moderate volatility"

    return "Low volatility"

def get_volatility_signal(volatility_value):
    if volatility_value is None:
        return "Neutral"

    try:
        volatility_value = float(volatility_value)
    except (TypeError, ValueError):
        return "Neutral"

    if volatility_value >= 40:
        return "High Risk"
    if volatility_value >= 20:
        return "Moderate Risk"

    return "Low Risk"

def get_volatility_signal(volatility_value):
    if volatility_value is None:
        return "Neutral"

    try:
        volatility_value = float(volatility_value)
    except (TypeError, ValueError):
        return "Neutral"

    if volatility_value >= 40:
        return "High Risk"
    if volatility_value >= 20:
        return "Moderate Risk"

    return "Low Risk"
