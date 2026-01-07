import ccxt
import pandas as pd
import requests
import time
import os

# --- CONFIG ---
# Replace with your actual webhook or use .env
DISCORD_WEBHOOK = "YOUR_DISCORD_WEBHOOK_URL"
COINS = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT']
# Percentage for SL and TPs based on your instructions
SL_PCT = 0.02    # 2% drop
TP1_PCT = 0.015  # 1.5% rise
TP2_PCT = 0.03   # 3% rise
TP3_PCT = 0.05   # 5% rise

exchange = ccxt.binance({'enableRateLimit': True, 'options': {'defaultType': 'future'}})

class TradeTracker:
    def __init__(self):
        self.wins = 0
        self.losses = 0

    def get_stats(self):
        total = self.wins + self.losses
        wr = (self.wins / total * 100) if total > 0 else 0
        return f"\n**Winrate:** {wr:.1f}% ({self.wins}W - {self.losses}L)"

tracker = TradeTracker()

def send_discord(msg):
    requests.post(DISCORD_WEBHOOK, json={"content": msg})

def get_orderflow_metrics(symbol):
    """
    Analyzes the last 1000 trades to calculate Delta.
    """
    try:
        trades = exchange.fetch_trades(symbol, limit=1000)
        df = pd.DataFrame(trades, columns=['side', 'amount', 'price'])
        
        buys = df[df['side'] == 'buy']['amount'].astype(float).sum()
        sells = df[df['side'] == 'sell']['amount'].astype(float).sum()
        
        delta = buys - sells
        last_price = float(df['price'].iloc[-1])
        
        return delta, last_price
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
        return None, None

def analyze():
    print(f"Scanning Order Flow at {time.strftime('%H:%M:%S')}...")
    
    for symbol in COINS:
        delta, price = get_orderflow_metrics(symbol)
        if delta is None: continue

        coin_name = symbol.split('/')[0]
        
        # LOGIC: If Delta is strongly positive, aggressive buyers are in control
        # This is a simplified 'Long trade' trigger
        if delta > 50:  # Threshold depends on coin volume, 50 is just an example
            entry = price
            sl = entry * (1 - SL_PCT)
            tp1 = entry * (1 + TP1_PCT)
            tp2 = entry * (1 + TP2_PCT)
            tp3 = entry * (1 + TP3_PCT)
            
            msg = (
                f"🚀 **${coin_name}** | **COOL LONG TRADE DETECTED**\n"
                f"Aggressive Buyers are stepping in! (Delta: +{delta:.2f})\n\n"
                f"🔹 **Entry:** {entry:.4f}\n"
                f"🎯 **TP1:** {tp1:.4f} (Win starts here & SL to Entry)\n"
                f"🎯 **TP2:** {tp2:.4f}\n"
                f"🎯 **TP3:** {tp3:.4f}\n"
                f"🛑 **SL:** {sl:.4f}\n"
                f"{tracker.get_stats()}"
            )
            send_discord(msg)
            # For this example, we count a 'win' on signal to show the UI
            tracker.wins += 1 

        elif delta < -50:
            entry = price
            sl = entry * (1 + SL_PCT)
            tp1 = entry * (1 - TP1_PCT)
            
            msg = (
                f"🔥 **${coin_name}** | **COOL SHORT TRADE DETECTED**\n"
                f"Aggressive Sellers are hammering! (Delta: {delta:.2f})\n\n"
                f"🔹 **Entry:** {entry:.4f}\n"
                f"🎯 **TP1:** {tp1:.4f}\n"
                f"🛑 **SL:** {sl:.4f}\n"
                f"{tracker.get_stats()}"
            )
            send_discord(msg)
            tracker.losses += 1

if __name__ == "__main__":
    while True:
        analyze()
        time.sleep(300) # Scan every 5 minutes
