import akshare as ak
import ccxt
import pandas as pd
from datetime import datetime

# --- 配置 ---
TARGET_PRICES = [5.21, 52.1]
CRYPTO_SYMBOLS = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'ORDI/USDT']

def get_stock_logic():
    results = []
    try:
        stocks = ak.stock_zh_a_spot_em().head(300) # 先扫300只确保速度
        for _, row in stocks.iterrows():
            code, name, price = row['代码'], row['名称'], row['最新价']
            df = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq").tail(400)
            if len(df) < 321: continue
            
            # 原生计算指标，不依赖外部库
            df['ma156'] = df['收盘'].rolling(window=156).mean()
            df['ma321'] = df['收盘'].rolling(window=321).mean()
            df['vol_ma20'] = df['成交量'].rolling(window=20).mean()
            
            curr = df.iloc[-1]
            m156, m321, vol_ratio = curr['ma156'], curr['ma321'], curr['成交量']/curr['vol_ma20']
            
            hits = []
            if abs(price - m156)/m156 < 0.012: hits.append(f"MA156踩位")
            if abs(price - m321)/m321 < 0.012: hits.append("MA321关键点")
            drop_3d = (price - df['收盘'].iloc[-4]) / df['收盘'].iloc[-4]
            if m321 > m156 > price and drop_3d < -0.12:
                hits.append(f"断崖({drop_3d:.1%})")

            if hits:
                results.append({'name': name, 'code': code, 'price': price, 'tags': hits})
    except: pass
    return results

def get_crypto_logic():
    results = []
    ex = ccxt.binance()
    for symbol in CRYPTO_SYMBOLS:
        try:
            bars = ex.fetch_ohlcv(symbol, timeframe='1m', limit=100)
            df = pd.DataFrame(bars, columns=['t','o','h','l','c','v'])
            # 原生布林带计算
            ma20 = df['c'].rolling(window=20).mean()
            std20 = df['c'].rolling(window=20).std()
            bbl = ma20 - (2 * std20)
            
            c_price = df['c'].iloc[-1]
            if df['l'].iloc[-1] < bbl.iloc[-1] and c_price > bbl.iloc[-1]:
                results.append({'name': symbol, 'price': c_price, 'tags': ['插针收回']})
        except: pass
    return results

def get_genetics_logic():
    try:
        zt_pool = ak.stock_zt_pool_em()
        leaders = zt_pool[zt_pool['连板数'] >= 3].head(10)
        return [{'name': r['名称'], 'lb': r['连板数'], 'hy': r['所属行业'], 'mv': f"{r['流通市值']/1e8:.1f}亿"} for _, r in leaders.iterrows()]
    except: return []

def generate_html(stocks, cryptos, genes):
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    def cards(data):
        return "".join([f'<div class="card"><div class="ticker">{i["name"]}</div><div class="price">{i["price"]}</div>'
                        f'{"".join([f"<span class=\"badge\">{t}</span>" for t in i["tags"]])}</div>' for i in data])
    
    gene_rows = "".join([f"<tr><td>{g['name']}</td><td>{g['lb']}</td><td>{g['hy']}</td><td>{g['mv']}</td></tr>" for g in genes])

    html = f"""
    <!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{ background:#050505; color:#ccc; font-family:monospace; padding:15px; }}
        .container {{ display: flex; flex-wrap: wrap; gap: 20px; }}
        .col {{ flex: 1; min-width: 300px; }}
        .card {{ background: #111; padding: 15px; margin-bottom: 10px; border-left: 3px solid #D4AF37; }}
        .ticker {{ color: #D4AF37; font-size: 1.1rem; font-weight: bold; }}
        .price {{ color: #fff; font-size: 1.1rem; }}
        .badge {{ background: #222; color: #888; padding: 2px 6px; font-size: 10px; margin-right: 5px; border-radius: 3px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ padding: 8px; border: 1px solid #222; text-align: left; font-size: 12px; }}
        th {{ color: #D4AF37; }}
    </style></head><body>
    <h1>STELLA RADAR V1.0 <span style="font-size:0.7rem; color:#444;">{now}</span></h1>
    <div class="container">
        <div class="col"><h2>A-SHARE</h2>{cards(stocks)}</div>
        <div class="col"><h2>CRYPTO</h2>{cards(cryptos)}</div>
    </div>
    <h2>GENETICS</h2>
    <table><tr><th>名称</th><th>连板</th><th>行业</th><th>市值</th></tr>{gene_rows}</table>
    </body></html>
    """
    with open("index.html", "w", encoding="utf-8") as f: f.write(html)

if __name__ == "__main__":
    generate_html(get_stock_logic(), get_crypto_logic(), get_genetics_logic())
