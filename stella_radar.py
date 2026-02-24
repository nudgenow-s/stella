import akshare as ak
import pandas as pd
from datetime import datetime, timedelta, timezone
import random

# --- 1. 时间定义 ---
def get_bj_time():
    utc_now = datetime.utcnow().replace(tzinfo=timezone.utc)
    beijing_now = utc_now.astimezone(timezone(timedelta(hours=8)))
    return beijing_now

# --- 2. 核心探测：A股全市场并行逻辑 ---
def get_stock_logic():
    results = []
    try:
        # 获取全量快照，仅作为代码和基础价格来源
        all_stocks = ak.stock_zh_a_spot_em()
        # 预过滤：只看成交额排名前 800 的活跃票，确保护航全市场扫描速度
        active_stocks = all_stocks.sort_values('成交额', ascending=False).head(800)
        
        for _, row in active_stocks.iterrows():
            code, name, price = row['代码'], row['名称'], row['最新价']
            try:
                # 抓取历史 K 线用于并行指标计算
                df = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq").tail(350)
                if len(df) < 321: continue
                
                hits = []
                # 指标 A：断崖探测 (5日跌幅 > 15%)
                drop_5d = (price - df['收盘'].iloc[-6]) / df['收盘'].iloc[-6]
                if drop_5d <= -0.15: hits.append(f"🚨断崖({drop_5d:.1%})")

                # 指标 B：156/321 均线踩位 (误差 2.5%)
                ma156 = df['收盘'].rolling(window=156).mean().iloc[-1]
                if abs(price - ma156) / ma156 < 0.025: hits.append("📏MA156踩位")

                # 指标 C：价格锚点 (5.21 / 52.1)
                if any((df['最低'].tail(20).min() <= p <= df['最高'].tail(20).max()) for p in [5.21, 52.1]):
                    hits.append("🎯价格共振")

                if hits:
                    results.append({'name': name, 'code': code, 'price': price, 'tags': hits})
            except: continue
    except Exception as e:
        print(f"A股扫描异常: {e}")
    return results

# --- 3. 核心探测：近一个月连板基因穿透 ---
def get_genetics_logic():
    """扫描全市场，筛选近 30 天内出现过 3 连板以上的股票"""
    genetics = []
    try:
        # 1. 抓取涨停股池统计（最近一个月的每日记录）
        # 这里我们利用历史涨停池接口扫描过去 20 个交易日（约一个月）
        today = datetime.now()
        found_stocks = {}

        for i in range(22): # 扫描过去 22 个交易日
            target_date = (today - timedelta(days=i)).strftime('%Y%m%d')
            try:
                # 抓取历史涨停池数据
                df = ak.stock_zt_pool_previous_em(date=target_date)
                if df.empty: continue
                
                # 筛选连板数 >= 3 的真妖股
                leaders = df[df['连板数'] >= 3]
                for _, row in leaders.iterrows():
                    name = row['名称']
                    # 如果这只股票在这个月内多次出现，记录其最高连板数
                    if name not in found_stocks or row['连板数'] > found_stocks[name]['lb_num']:
                        found_stocks[name] = {
                            'name': name,
                            'lb_num': row['连板数'],
                            'hy': row['所属行业'],
                            'mv': f"{row['流通市值']/1e8:.1f}亿",
                            'date': target_date
                        }
            except: continue
            if len(found_stocks) > 30: break # 抓够 30 只就不抓了，确保运行速度

        # 转换为列表并按连板强度排序
        genetics = sorted(found_stocks.values(), key=lambda x: x['lb_num'], reverse=True)
    except Exception as e:
        print(f"连板基因扫描异常: {e}")
    return genetics

# --- 4. HTML 生成与展示 ---
def generate_html(stocks, genes):
    bj_time = get_bj_time().strftime('%Y-%m-%d %H:%M:%S')
    
    def cards(data):
        if not data: return '<p style="color:#444;">[探测器在线，当前无并行信号]</p>'
        return "".join([f'<div style="background:#111; padding:15px; margin-bottom:10px; border-left:4px solid #D4AF37;">'
                        f'<div style="color:#D4AF37; font-weight:bold;">{i["name"]} ({i["code"]})</div>'
                        f'<div style="color:#fff;">{i["price"]}</div>'
                        f'{"".join([f"<span style=\"background:#222; font-size:10px; padding:2px 5px; margin-right:5px; border-radius:3px;\">{t}</span>" for t in i["tags"]])}</div>' for i in data])

    gene_rows = "".join([f"<tr><td>{g['name']}</td><td>{g['lb_num']}连</td><td>{g['hy']}</td><td>{g['mv']}</td><td>{g['date']}</td></tr>" for g in genes])

    html = f"""
    <!DOCTYPE html><html><head><meta charset="utf-8">
    <title>STELLA RADAR V2.0</title>
    <style>
        body {{ background:#000; color:#ccc; font-family:monospace; padding:20px; }}
        table {{ width:100%; border-collapse:collapse; margin-top:20px; }}
        th, td {{ border:1px solid #222; padding:10px; text-align:left; }}
        th {{ color:#D4AF37; background:#111; }}
        .header {{ border-bottom:1px solid #333; padding-bottom:10px; margin-bottom:20px; }}
    </style></head><body>
    <div class="header">
        <h1>STELLA RADAR <span style="color:#D4AF37;">V2.0</span></h1>
        <p style="color:#666;">[北京时间: {bj_time}] | 扫描范围: 全市场/近30日</p>
    </div>
    <div style="display:flex; gap:20px;">
        <div style="flex:1;"><h2>A-SHARE 并行探测 (断崖/踩位/5.21)</h2>{cards(stocks)}</div>
        <div style="flex:1;"><h2>近一个月连板基因审计</h2>
            <table><tr><th>名称</th><th>最高连板</th><th>行业</th><th>市值</th><th>活跃日期</th></tr>{gene_rows}</table>
        </div>
    </div>
    <div style="margin-top:20px; color:#111;">Pulse: {random.random()}</div>
    </body></html>
    """
    with open("index.html", "w", encoding="utf-8") as f: f.write(html)

if __name__ == "__main__":
    s_data = get_stock_logic()
    g_data = get_genetics_logic()
    generate_html(s_data, g_data)
