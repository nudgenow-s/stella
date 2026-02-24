import akshare as ak
import ccxt
import pandas as pd
from datetime import datetime

# --- 配置 ---
TARGET_PRICES = [5.21, 52.1]
CRYPTO_SYMBOLS = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'ORDI/USDT']

def get_stock_logic():
    """全市场扫描逻辑：先筛选活跃标的，再深度计算"""
    results = []
    try:
        # 1. 一次性获取全市场 5000+ 股票的实时行情
        all_stocks = ak.stock_zh_a_spot_em()
        
        # 2. 预筛选：剔除停牌、ST、以及成交额过低（流动性差）的垃圾标的
        # 私募策略：成交额排名后 20% 的不看
        all_stocks = all_stocks[all_stocks['成交额'] > all_stocks['成交额'].quantile(0.2)]
        
        # 3. 遍历全市场标的
        for _, row in all_stocks.iterrows():
            code, name, price = row['代码'], row['名称'], row['最新价']
            
            # 这里的异常处理很重要，全市场扫描难免会有个别数据缺失
            try:
                # 深度拉取 K 线（全市场扫描建议只拉取近 400 天数据，减少流量）
                df = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq").tail(400)
                
                if len(df) < 321: continue # 剔除上市不满一年的新股
                
                # --- 原生计算（速度极快） ---
                close_series = df['收盘']
                ma156 = close_series.rolling(window=156).mean().iloc[-1]
                ma321 = close_series.rolling(window=321).mean().iloc[-1]
                
                # 成交量分析
                vol_series = df['成交量']
                vol_ma20 = vol_series.rolling(window=20).mean().iloc[-1]
                vol_ratio = vol_series.iloc[-1] / vol_ma20
                
                hits = []
                # 踩位：宽限至 2% 以适配全市场波动
                if abs(price - ma156) / ma156 < 0.02:
                    hits.append(f"MA156线(距:{abs(price-ma156)/ma156:.1%})")
                
                # 5.21 心理价位：检查 60 日内是否触碰
                if (df['最低'].tail(60).min() <= 5.21 <= df['最高'].tail(60).max()):
                    hits.append("5.21心理区")
                    
                # 断崖：3日跌幅 > 10%
                drop_3d = (price - close_series.iloc[-4]) / close_series.iloc[-4]
                if price < ma156 and drop_3d < -0.10:
                    hits.append(f"断崖({drop_3d:.1%})")

                if hits:
                    results.append({'name': name, 'code': code, 'price': price, 'tags': hits})
                    
            except:
                continue # 个别个股失败不影响全局
                
    except Exception as e:
        print(f"全市场扫描中断: {e}")
        
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
