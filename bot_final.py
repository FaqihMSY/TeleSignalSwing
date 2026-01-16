import yfinance as yf
import ccxt
import pandas as pd
import pandas_ta as ta
import requests
import os
from datetime import datetime

# --- CONFIG ---
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

RSI_LIMIT = 40  # RSI di bawah 40

ASSETS = {
    'CRYPTO': {
        'symbols': ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'DOGE/USDT', 'AVAX/USDT'],
        'source': 'ccxt',
        'interval': '4h'
    },
    'SAHAM_INDO': {
        'symbols': ['BBRI.JK', 'BBCA.JK', 'BMRI.JK', 'TLKM.JK', 'ADRO.JK', 'ASII.JK', 'ICBP.JK'],
        'source': 'yfinance',
        'interval': '1d'
    },
    'SAHAM_US': {
        'symbols': ['AAPL', 'TSLA', 'NVDA', 'META', 'GOOGL', 'JPM', 'KO'],
        'source': 'yfinance',
        'interval': '1d'
    },
    'FOREX': {
        'symbols': ['EURUSD=X', 'GBPUSD=X', 'USDJPY=X'],
        'source': 'yfinance',
        'interval': '1h'
    },
    'GOLD': {
        'symbols': ['GC=F'], 
        'source': 'yfinance',
        'interval': '1h'
    }
}

def send_telegram(msg):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': msg, 'parse_mode': 'Markdown'}
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print(f"✅ Pesan terkirim ke Telegram") 
        else:
            print(f"❌ Telegram API Error: {response.text}")
    except Exception as e:
        print(f"Error Telegram: {e}")

def check_hammer_rsi(df, symbol, asset_type, interval):
    if df is None or len(df) < 20:
        return

    # Hitung RSI saja
    df['rsi'] = ta.rsi(df['close'], length=14)
    df = df.dropna(subset=['rsi'])
    if df.empty: return
    
    last = df.iloc[-1]
    
    # 1. Filter RSI di bawah 40
    if last['rsi'] > RSI_LIMIT: return

    # 2. Filter pola Hammer
    body = abs(last['close'] - last['open'])
    lower_shadow = min(last['close'], last['open']) - last['low']
    upper_shadow = last['high'] - max(last['close'], last['open'])
    
    # Syarat Hammer: Ekor bawah panjang, ekor atas pendek/tidak ada
    is_hammer = (lower_shadow >= 2 * body) and (upper_shadow <= body) and (body > 0)
    
    if is_hammer:
        price_fmt = f"{last['close']:.2f}" if last['close'] > 1 else f"{last['close']:.6f}"
        emoji = {"CRYPTO": "🚀", "SAHAM_INDO": "🇮🇩", "SAHAM_US": "🇺🇸", "FOREX": "💱", "GOLD": "🥇"}
        current_emoji = emoji.get(asset_type, "📈")
        
        msg = (f"{current_emoji} **SIGNAL {asset_type}**\n"
               f"Symbol: `{symbol}`\n"
               f"Price: `{price_fmt}`\n"
               f"RSI: `{last['rsi']:.2f}`\n"
               f"TF: `{interval}`\n"
               f"Note: Pola Hammer terdeteksi")
        
        send_telegram(msg)

def run_scanner():
    print(f"--- SCANNING START {datetime.now()} ---")
    for category, data in ASSETS.items():
        if data['source'] == 'ccxt':
            exchange = ccxt.binance()
            for sym in data['symbols']:
                try:
                    bars = exchange.fetch_ohlcv(sym, timeframe=data['interval'], limit=100)
                    df = pd.DataFrame(bars, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
                    check_hammer_rsi(df, sym, category, data['interval'])
                except: continue
                
        elif data['source'] == 'yfinance':
            for sym in data['symbols']:
                try:
                    period = "1mo" if "h" in data['interval'] else "6mo"
                    df = yf.download(sym, period=period, interval=data['interval'], progress=False)
                    if df.empty: continue
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = df.columns.get_level_values(0)
                    df.columns = [str(col).lower() for col in df.columns]
                    check_hammer_rsi(df, sym, category, data['interval'])
                except: continue
                
    msg_finish = f"✅ **Scan Selesai** ({datetime.now().strftime('%H:%M')})\nMarket telah dipantau dengan RSI < 40."
    send_telegram(msg_finish)
    print("--- SCANNING SELESAI ---")

if __name__ == "__main__":
    run_scanner()
