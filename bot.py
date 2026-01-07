import ccxt
import pandas as pd
import requests
import os
import sys

# --- CONFIG ---
DISCORD_WEBHOOK = os.getenv('DISCORD_WEBHOOK_URL')

# Initialize Exchange with a 10s timeout to prevent hanging
exchange = ccxt.binance({
    'enableRateLimit': True,
    'timeout': 10000, 
    'options': {'defaultType': 'future'}
})

def send_discord(msg):
    if not DISCORD_WEBHOOK:
        return
    try:
        # Added timeout=10 so it doesn't hang forever if Discord is slow
        requests.post(DISCORD_WEBHOOK, json={"content": msg}, timeout=10)
    except Exception as e:
        print(f"Discord Error: {e}")

def track_order_flow(symbol):
    try:
        # Fetch only the last 500 trades to keep it fast
        trades = exchange.fetch_trades(symbol, limit=500)
        if not trades:
            return None, None, None, None
            
        df = pd.DataFrame(trades, columns=['side', 'amount', 'price'])
        df['amount'] = df['amount'].astype(float)
        
        buys = df[df['side'] == 'buy']['amount'].sum()
        sells = df[df['side'] == 'sell']['amount'].sum()
        
        total_vol = buys + sells
        delta = buys - sells
        aggression = (delta / total_vol) if total_vol > 0 else 0
        current_price = float(df['price'].iloc[-1])
        
        return aggression, current_price, buys, sells
    except Exception as e:
        print(f"Error on {symbol}: {e}")
        return None, None, None, None

def main():
    symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT']
    
    for s in symbols:
        agg_ratio, price, buys, sells = track_order_flow(s)
        
        # Only alert if there is a significant move (>25% imbalance)
        if agg_ratio is not None and abs(agg_ratio) > 0.25:
            direction = "BULLISH FLOW 🟢" if agg_ratio > 0 else "BEARISH FLOW 🔴"
            coin = s.split('/')[0]
            
            msg = (
                f"📊 **${coin} ORDER FLOW**\n"
                f"**{direction}**\n"
                f"**Aggression:** {agg_ratio:.1%}\n"
                f"**Price:** ${price:,.2f}"
            )
            send_discord(msg)

    # CRITICAL: Force the script to exit so GitHub Actions stops the job
    print("Scan complete. Exiting...")
    sys.exit(0)

if __name__ == "__main__":
    main()
