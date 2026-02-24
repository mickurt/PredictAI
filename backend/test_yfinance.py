import yfinance as yf

print("Testing yfinance...")

stocks = ["NVDA", "BTC-USD"]
tickers = yf.Tickers(" ".join(stocks))

for symbol in stocks:
    try:
        # Try both fast_info and history to see what works
        info = tickers.tickers[symbol].fast_info
        price = info.last_price
        print(f"SUCCESS: {symbol} price is {price}")
    except Exception as e:
        print(f"FAILED: {symbol} - {e}")
