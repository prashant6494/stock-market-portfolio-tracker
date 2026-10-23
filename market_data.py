
import pandas as pd
import yfinance as yf


def normalize_symbol(symbol):
    symbol = str(symbol).strip().upper()

    if symbol and not symbol.endswith((".NS", ".BO")):
        symbol += ".NS"

    return symbol


def get_history(symbol, period="6mo", interval="1d"):
    try:
        ticker = normalize_symbol(symbol)
        data = yf.Ticker(ticker).history(
            period=period,
            interval=interval,
            auto_adjust=False
        )

        if data.empty:
            return pd.DataFrame()

        return data.dropna(
            subset=["Open", "High", "Low", "Close"]
        )
    except Exception:
        return pd.DataFrame()


def get_latest_price(symbol):
    try:
        data = yf.Ticker(normalize_symbol(symbol)).history(
            period="5d",
            interval="1d",
            auto_adjust=True
        )

        if data.empty or "Close" not in data.columns:
            return None, None

        data = data.dropna(subset=["Close"])

        if data.empty:
            return None, None

        price = float(data["Close"].iloc[-1])
        timestamp = data.index[-1].to_pydatetime()

        if timestamp.tzinfo is not None:
            timestamp = timestamp.replace(tzinfo=None)

        return price, timestamp

    except Exception:
        return None, None
