import yfinance as yf

ticker = "AAPL"

stock = yf.Ticker(ticker)
history = stock.history(period="5d")

print(f"\n{ticker} 5-Day Stock History")
print(history)
