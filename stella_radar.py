import akshare as ak
import ccxt
import pandas as pd
import pandas_ta as ta
from datetime import datetime

# --- 配置 ---
TARGET_PRICES = [5.21, 52.1]
CRYPTO_SYMBOLS = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'ORDI/USDT', 'PEPE/USDT']

def get_stock_logic():
    """A股核心逻辑：踩位、断崖、5.21、成交量分析"""
    results = []
    try:
        stocks = ak.stock_zh_a_spot_em().head(800) # 为保证速度先扫800只
        for _, row in stocks.iterrows():
            code, name, price = row['代码'], row['名称'], row['最新价']
            # 获取历史数据
            df = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq").tail(400)
            if len(df) < 321: continue
            
            df['ma156'] = ta.sma(df['收盘'], length=156)
            df['ma321'] = ta.sma(df['收盘'], length=321)
            df['vol_ma20'] = ta.sma(df['成交量'], length=20)
            
            curr = df.iloc[-1]
            m156, m321, vol_ratio = curr['ma156'], curr['ma321'], curr['成交量']/curr['vol_ma20']
            
            hits = []
            # 踩位逻辑
            if abs(price - m156)/m156 < 0.012: hits.append(f"MA156踩位({'缩量' if vol_ratio<0.8 else '有量'})")
            if abs(price - m321)/m321 < 0.012: hits.append("MA321关键踩位")
            # 5.21逻辑 (60日内)
            if any((df['最高'].tail(60) >= p) & (df['最低'].tail(60) <= p) for p in TARGET_PRICES):
                hits.append("5.21价格锚点")
            # 断崖逻辑
            drop_3d = (price - df['收盘'].iloc[-4]) / df['收盘'].iloc[-4]
            if m321 > m156 > price and drop_3d < -0.12:
                hits.append(f"断崖暴跌({drop_3d:.1%})")

            if hits:
                results.append({'name': name, 'code': code, 'price': price, 'tags': hits})
    except: pass
    return results

def get_crypto_logic():
    """币圈逻辑：秒级插针与回踩"""
    results = []
    ex = ccxt.binance()
    for symbol in CRYPTO_SYMBOLS:
        try:
            bars = ex.fetch_ohlcv(symbol, timeframe='1m', limit=100)
            df = pd.DataFrame(bars, columns=['t','o','h','l','c','v'])
            bb = ta.bbands(df['c'], length=20)
            c_price = df['c'].iloc[-1]
            if df['l'].iloc[-1] < bb['BBL_20_2.0'].iloc[-1] and c_price > bb['BBL_20_2.0'].iloc[-1]:
                results.append({'name': symbol, 'price': c_price, 'tags': ['秒级下轨插针']})
        except: pass
    return results

def get_genetics_logic():
    """妖股基因审判：近30日连板共性提取"""
    try:
        zt_pool = ak.stock_zt_pool_em(date=datetime.now().strftime('%Y%m%d'))
        leaders = zt_pool[zt_pool['连板数'] >= 3].head(10)
        genetics = []
        for _, row in leaders.iterrows():
            genetics.append({
                'name': row['名称'],
                'lb': row['连板数'],
                'hy': row['所属行业'],
                'mv': f"{row['流通市值']/1e8:.1f}亿",
                'turn': f"{row['换手率']:.1f}%"
            })
        return genetics
    except: return []

def generate_html(stocks, cryptos, genes):
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    def cards(data):
        return "".join([f'<div class="card"><div class="ticker">{i["name"]}</div><div class="price">{i["price"]}</div>'
                        f'{"".join([f"<span class=\"badge\">{t}</span>" for t in i["tags"]])}</div>' for i in data])
    
    gene_rows = "".join([f"<tr><td>{g['name']}</td><td>{g['lb']}连</td><td>{g['hy']}</td><td>{g['mv']}</td><td>{g['turn']}</td></tr>" for g in genes])

    html = f"""
    <!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        :root {{ --gold: #D4AF37; --blue: #4A90E2; --bg: #050505; --card: #121212; }}
        body {{ background: var(--bg); color: #ccc; font-family: monospace; padding: 15px; }}
        .container {{ display: flex; flex-wrap: wrap; gap: 20px; }}
        .col {{ flex: 1; min-width: 300px; }}
        .card {{ background: var(--card); padding: 15px; margin-bottom: 10px; border-left: 3px solid var(--gold); }}
        .ticker {{ color: var(--gold); font-size: 1.1rem; font-weight: bold; }}
        .price {{ color: #fff; font-size: 1.1rem; margin: 5px 0; }}
        .badge {{ background: #222; color: #888; padding: 2px 6px; font-size: 10px; margin-right: 5px; border-radius: 3px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 0.8rem; background: #111; }}
        th, td {{ padding: 10px; border: 1px solid #222; text-align: left; }}
        th {{ color: var(--gold); }}
    </style></head><body>
    <h1 style="color:var(--gold);">STELLA QUANT RADAR V1.0 <span style="font-size:0.7rem; color:#444;">{now}</span></h1>
    <div class="container">
        <div class="col"><h2>A-SHARE MONITOR</h2>{cards(stocks)}</div>
        <div class="col"><h2>CRYPTO 1M SCAN</h2>{cards(cryptos)}</div>
    </div>
    <h2>MARKET GENETICS (WINNERS DNA)</h2>
    <table><thead><tr><th>名称</th><th>连板</th><th>行业</th><th>市值</th><th>换手</th></tr></thead><tbody>{gene_rows}</tbody></table>
    </body></html>
    """
    with open("index.html", "w", encoding="utf-8") as f: f.write(html)

if __name__ == "__main__":
    generate_html(get_stock_logic(), get_crypto_logic(), get_genetics_logic())
