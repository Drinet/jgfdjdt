import ccxt
import pandas as pd
import requests
import os
import sys

# --- CONFIG ---
DISCORD_WEBHOOK = os.getenv('DISCORD_WEBHOOK_URL')

# Exchanges that usually work on GitHub Actions (No US blocking for public data)
EXCHANGE_LIST = ['kraken', 'kucoin', 'okx', 'bitfinex', 'gateio']
SYMBOLS = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']

def send_discord(msg):
    if not DISCORD_WEBHOOK: return
    try:
        requests.post(DISCORD_WEBHOOK, json={"content": msg}, timeout=10)
    except:
        pass

def get_order_flow(exchange_id, symbol):
    """Fetches and calculates market aggression for a specific exchange."""
    try:
        # Dynamically load the exchange class from ccxt
        ex_class = getattr(ccxt, exchange_id)
        ex = ex_class({'enableRateLimit': True, 'timeout': 10000})
        
        # Some exchanges use different naming for USDT pairs (e.g. BTC/USD)
        # We try to fetch the trades for the provided symbol
        trades = ex.fetch_trades(symbol, limit=200)
        if not trades: return None
            
        df = pd.DataFrame(trades, columns=['side', 'amount', 'price'])
        df['amount'] = df['amount'].astype(float)
        
        buys = df[df['side'] == 'buy']['amount'].sum()
        sells = df[df['side'] == 'sell']['amount'].sum()
        
        delta = buys - sells
        total_vol = buys + sells
        aggression = (delta / total_vol) if total_vol > 0 else 0
        price = float(df['price'].iloc[-1])
        
        return aggression, price
    except Exception as e:
        print(f"Skipping {exchange_id} for {symbol}: {e}")
        return None

def main():
    print(f"Starting Multi-Exchange Scan...")
    
    for symbol in SYMBOLS:
        results = []
        for ex_id in EXCHANGE_LIST:
            data = get_order_flow(ex_id, symbol)
            if data:
                agg, price = data
                results.append({'ex': ex_id, 'agg': agg, 'price': price})
        
        if not results: continue

        # Calculate an average 'Market Sentiment' across all available exchanges
        avg_agg = sum(r['agg'] for r in results) / len(results)
        avg_price = sum(r['price'] for r in results) / len(results)
        coin = symbol.split('/')[0]

        # Alert if the collective market aggression is high (>15%)
        if abs(avg_agg) > 0.15:
            status = "BULLISH FLOW 🟢" if avg_agg > 0 else "BEARISH FLOW 🔴"
            ex_names = ", ".join([r['ex'].upper() for r in results])
            
            msg = (
                f"🌎 **${coin} GLOBAL ORDER FLOW**\n"
                f"**Status:** {status}\n"
                f"**Avg Aggression:** {avg_agg:.1%}\n"
                f"**Avg Price:** ${avg_price:,.2f}\n"
                f"**Data From:** {ex_names}\n"
                f"---"
            )
            send_discord(msg)

    print("Scan complete. Exiting...")
    sys.exit(0)

if __name__ == "__main__":
    main()
