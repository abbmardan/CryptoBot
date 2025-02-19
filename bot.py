import requests
import pandas as pd
import asyncio
import logging
from telegram import Bot

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = "7902652853:AAHbysUqMXFb7idVZrgvV_o4AHRp2DNaiCc"
TELEGRAM_CHAT_ID = "1113817751"
bot = Bot(token=TELEGRAM_BOT_TOKEN)

# List of top 15 cryptocurrencies (USDT pairs)
SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT",
    "SOLUSDT", "DOGEUSDT", "AVAXUSDT", "DOTUSDT", "MATICUSDT",
    "LTCUSDT", "TRXUSDT", "LINKUSDT", "ATOMUSDT", "UNIUSDT"
]

# Function to fetch historical price data from Binance (15m timeframe)
def get_binance_data(symbol, interval="15m", limit=100):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    response = requests.get(url)
    if response.status_code != 200:
        logging.error(f"Failed to fetch data for {symbol}")
        return None

    data = response.json()
    df = pd.DataFrame(data, columns=[
        "timestamp", "open", "high", "low", "close", "volume", "close_time",
        "quote_asset_volume", "trades", "taker_buy_base", "taker_buy_quote", "ignore"
    ])
    
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df["close"] = df["close"].astype(float)
    
    df["EMA_20"] = df["close"].ewm(span=20, adjust=False).mean()
    df["EMA_50"] = df["close"].ewm(span=50, adjust=False).mean()
    df["EMA_200"] = df["close"].ewm(span=200, adjust=False).mean()
    
    return df

# Function to send Telegram message (async)
async def send_telegram_message(message):
    """Sends a message to the Telegram bot asynchronously."""
    try:
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.info(f"Sent Telegram alert: {message}")
    except Exception as e:
        logging.error(f"Failed to send Telegram message: {e}")

# Function to detect EMA crossovers and trends
async def detect_crossover(symbol):
    df = get_binance_data(symbol)
    if df is None or len(df) < 3:
        return

    # Check for EMA crossovers
    if df["EMA_20"].iloc[-2] > df["EMA_50"].iloc[-2] and df["EMA_20"].iloc[-1] < df["EMA_50"].iloc[-1]:
        message = f"🔴 {symbol} - Bearish EMA Crossover detected!"
        await send_telegram_message(message)

    elif df["EMA_20"].iloc[-2] < df["EMA_50"].iloc[-2] and df["EMA_20"].iloc[-1] > df["EMA_50"].iloc[-1]:
        message = f"🟢 {symbol} - Bullish EMA Crossover detected!"
        await send_telegram_message(message)

    # Detect potential crossover using EMA gap and reversal
    ema_20_gap = abs(df["EMA_20"].iloc[-1] - df["EMA_50"].iloc[-1])
    ema_20_reversal = (
        df["EMA_20"].iloc[-3] < df["EMA_20"].iloc[-2] and  # EMA 20 was rising
        df["EMA_20"].iloc[-2] > df["EMA_20"].iloc[-1]    # Now it's falling
    )

    dynamic_threshold = 0.005 * df["close"].iloc[-1]  # 0.5% of the latest closing price
    threshold = max(0.005, dynamic_threshold)  # Ensure minimum threshold

    if ema_20_gap > threshold and ema_20_reversal:
        message = f"⏳ {symbol} - Potential EMA crossover soon!"
        await send_telegram_message(message)

# Main loop to check signals for all cryptocurrencies
async def main():
    while True:
        tasks = [detect_crossover(symbol) for symbol in SYMBOLS]
        await asyncio.gather(*tasks)
        
        logging.info("Waiting for next check...")
        await asyncio.sleep(900)  # Wait for 15 minutes before next check

if __name__ == "__main__":
    asyncio.run(main())
