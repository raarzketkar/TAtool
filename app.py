from flask import Flask, render_template, request, jsonify
import yfinance as yf
import pandas as pd
import talib as tb
import json

app = Flask(__name__)

patterns = [
    ("Engulfing Pattern", tb.CDLENGULFING),
    ("Hammer", tb.CDLHAMMER),
    ("Inverted Hammer", tb.CDLINVERTEDHAMMER),
    ("Shooting Star", tb.CDLSHOOTINGSTAR),
    ("Hanging Man", tb.CDLHANGINGMAN),
    ("Doji", tb.CDLDOJI),
    ("Dragonfly Doji", tb.CDLDRAGONFLYDOJI),
    ("Gravestone Doji", tb.CDLGRAVESTONEDOJI),
    ("Morning Star", tb.CDLMORNINGSTAR),
    ("Evening Star", tb.CDLEVENINGSTAR),
    ("Piercing Pattern", tb.CDLPIERCING),
    ("Dark Cloud Cover", tb.CDLDARKCLOUDCOVER),
    ("Three White Soldiers", tb.CDL3WHITESOLDIERS),
    ("Three Black Crows", tb.CDL3BLACKCROWS),
]

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.json
    ticker = data.get("ticker", "").strip().upper() + ".NS"
    period = data.get("period", "3mo")
    interval = data.get("interval", "1d")

    df = yf.download(ticker, period=period, interval=interval, progress=False)

    if df.empty:
        return jsonify({"error": f"No data found for '{ticker}'. Check the ticker symbol."}), 404

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df[["Open", "High", "Low", "Close", "Volume"]].astype(float).dropna()

    if df.empty:
        return jsonify({"error": "Data returned but was empty after cleaning."}), 400

    # Build OHLCV for chart
    candles = []
    for date, row in df.iterrows():
        candles.append({
            "date": date.strftime("%Y-%m-%d"),
            "open": round(row["Open"], 2),
            "high": round(row["High"], 2),
            "low": round(row["Low"], 2),
            "close": round(row["Close"], 2),
            "volume": int(row["Volume"]),
        })

    # Pattern detection
    detected = []
    for name, func in patterns:
        results = func(df["Open"], df["High"], df["Low"], df["Close"])
        for date, signal in zip(df.index, results):
            if signal == 100:
                detected.append({"date": date.strftime("%Y-%m-%d"), "pattern": name, "type": "bullish"})
            elif signal == -100:
                detected.append({"date": date.strftime("%Y-%m-%d"), "pattern": name, "type": "bearish"})

    bullish_count = sum(1 for d in detected if d["type"] == "bullish")
    bearish_count = sum(1 for d in detected if d["type"] == "bearish")

    if bullish_count > bearish_count:
        bias = "BULLISH"
    elif bearish_count > bullish_count:
        bias = "BEARISH"
    else:
        bias = "NEUTRAL"

    # Price stats
    latest_close = round(df["Close"].iloc[-1], 2)
    prev_close = round(df["Close"].iloc[-2], 2)
    change = round(latest_close - prev_close, 2)
    change_pct = round((change / prev_close) * 100, 2)
    high_52w = round(df["High"].max(), 2)
    low_52w = round(df["Low"].min(), 2)

    return jsonify({
        "ticker": ticker,
        "candles": candles,
        "detected": detected,
        "bullish_count": bullish_count,
        "bearish_count": bearish_count,
        "bias": bias,
        "latest_close": latest_close,
        "change": change,
        "change_pct": change_pct,
        "high": high_52w,
        "low": low_52w,
    })

if __name__ == "__main__":
    app.run(debug=True)