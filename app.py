from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

# -----------------------------
# Page
# -----------------------------
st.set_page_config(
    page_title="短线投机者雷达",
    page_icon="⚡",
    layout="centered",
    initial_sidebar_state="collapsed",
)

CSS = """
<style>
:root{
  --bg:#f7f8fb; --card:#ffffff; --line:#e6e9ef; --text:#111827; --muted:#6b7280;
  --green:#089981; --red:#f23645; --blue:#2962ff; --orange:#ff9800;
}
html, body, [data-testid="stAppViewContainer"]{background:var(--bg)!important; color:var(--text)!important;}
.block-container{padding:1.0rem .85rem 5rem .85rem; max-width:760px;}
[data-testid="stHeader"]{background:rgba(247,248,251,.78)!important; backdrop-filter: blur(14px);}
#MainMenu, footer{visibility:hidden;}
.hero{display:flex; align-items:center; justify-content:space-between; margin:.2rem 0 1rem 0;}
.brand{font-size:1.55rem; font-weight:900; letter-spacing:-.03em; line-height:1.12;}
.sub{font-size:.88rem; color:var(--muted); margin-top:.24rem;}
.tv-card{background:var(--card); border:1px solid var(--line); border-radius:18px; box-shadow:0 10px 30px rgba(17,24,39,.06); padding:14px; margin:10px 0;}
.topbar{display:flex; gap:8px; align-items:center; overflow-x:auto; padding-bottom:2px;}
.pill{display:inline-flex; align-items:center; gap:6px; border:1px solid var(--line); border-radius:999px; padding:7px 12px; background:#fff; font-size:.86rem; white-space:nowrap;}
.pill.hot{background:#fff1f2; color:#be123c; border-color:#fecdd3; font-weight:800;}
.metric-grid{display:grid; grid-template-columns:repeat(3,1fr); gap:10px; margin:10px 0 2px;}
.metric{background:#fff; border:1px solid var(--line); border-radius:16px; padding:12px; min-height:78px;}
.metric .label{font-size:.78rem; color:var(--muted);}
.metric .value{font-size:1.45rem; font-weight:900; margin-top:6px;}
.metric .note{font-size:.72rem; color:var(--muted); margin-top:4px;}
.row{display:grid; grid-template-columns:42px 1fr auto; gap:10px; align-items:center; padding:12px 2px; border-bottom:1px solid var(--line);}
.row:last-child{border-bottom:0;}
.logo{width:38px; height:38px; border-radius:999px; background:#f1f5f9; display:flex; align-items:center; justify-content:center; font-weight:900; font-size:.85rem; color:#111827;}
.logo.us{background:#eef2ff; color:#3730a3;}
.logo.cn{background:#fff7ed; color:#c2410c;}
.code{font-size:1.06rem; font-weight:900; line-height:1.05;}
.name{font-size:.82rem; color:var(--muted); margin-top:4px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:270px;}
.price{text-align:right;}
.price .p{font-size:1.05rem; font-weight:900;}
.up{color:var(--green); font-weight:900;}
.down{color:var(--red); font-weight:900;}
.flat{color:var(--muted); font-weight:900;}
.tagline{font-size:.76rem; color:var(--muted); margin-top:4px;}
.badge{display:inline-flex; padding:3px 8px; border-radius:999px; font-size:.75rem; font-weight:900; margin-right:5px; white-space:nowrap;}
.badge-buy{background:#dcfce7; color:#166534;}
.badge-watch{background:#e0f2fe; color:#075985;}
.badge-weak{background:#fef9c3; color:#854d0e;}
.badge-filter{background:#f1f5f9; color:#475569;}
.badge-risk{background:#fee2e2; color:#991b1b;}
.sector-row{display:grid; grid-template-columns:1fr auto; gap:8px; border-bottom:1px solid var(--line); padding:11px 0;}
.sector-row:last-child{border-bottom:0;}
.sector-name{font-size:1.0rem; font-weight:900;}
.sector-meta{font-size:.78rem; color:var(--muted); margin-top:4px;}
.score{font-size:1.1rem; font-weight:900; color:var(--blue);}
.plan-grid{display:grid; grid-template-columns:repeat(3,1fr); gap:8px;}
.plan-box{border:1px solid var(--line); background:#fff; border-radius:14px; padding:10px;}
.plan-box .k{font-size:.76rem; color:var(--muted);}
.plan-box .v{font-size:1.06rem; font-weight:900; margin-top:4px;}
.reason{background:#eef6ff; border:1px solid #bfdbfe; color:#1e3a8a; border-radius:14px; padding:12px; font-size:.9rem; line-height:1.55;}
.warn{background:#fff7ed; border:1px solid #fed7aa; color:#9a3412; border-radius:14px; padding:12px; font-size:.9rem; line-height:1.55;}
.small{font-size:.78rem; color:var(--muted);}
.stButton > button{border-radius:999px!important; height:46px!important; font-weight:900!important; border:0!important; background:#111827!important; color:#fff!important;}
.stDownloadButton > button{border-radius:999px!important;}
.stRadio [role="radiogroup"]{display:flex; gap:8px; flex-wrap:wrap;}
.stRadio label{background:#fff; border:1px solid var(--line); border-radius:999px; padding:6px 10px;}
.stTabs [data-baseweb="tab-list"]{gap:4px; overflow-x:auto;}
.stTabs [data-baseweb="tab"]{white-space:nowrap; border-radius:999px; padding:8px 10px;}
[data-testid="stMetric"]{background:#fff; border:1px solid var(--line); border-radius:14px; padding:8px;}
@media(max-width:430px){
 .block-container{padding-left:.72rem; padding-right:.72rem;}
 .metric-grid{grid-template-columns:repeat(2,1fr);}
 .row{grid-template-columns:38px 1fr auto; gap:8px;}
 .logo{width:34px; height:34px; font-size:.75rem;}
 .code{font-size:1.0rem;}
 .name{max-width:190px;}
 .price .p{font-size:.98rem;}
 .plan-grid{grid-template-columns:repeat(2,1fr);}
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# -----------------------------
# Universe
# -----------------------------
@dataclass(frozen=True)
class StockMeta:
    symbol: str
    name: str
    market: str  # 美股 / A股
    sector: str
    tags: str

US = [
    StockMeta("NVDA", "英伟达", "美股", "AI/芯片", "AI/芯片"),
    StockMeta("AMD", "AMD", "美股", "AI/芯片", "AI/芯片"),
    StockMeta("AVGO", "博通", "美股", "AI/芯片", "AI/芯片"),
    StockMeta("ARM", "Arm", "美股", "AI/芯片", "AI/芯片"),
    StockMeta("MU", "美光科技", "美股", "AI/芯片", "存储芯片"),
    StockMeta("SMH", "半导体ETF", "美股", "AI/芯片", "ETF/芯片"),
    StockMeta("SOXL", "三倍做多半导体", "美股", "杠杆ETF", "杠杆ETF/高波动"),
    StockMeta("MSFT", "微软", "美股", "大型科技", "大型科技/AI"),
    StockMeta("AAPL", "苹果", "美股", "大型科技", "大型科技"),
    StockMeta("META", "Meta", "美股", "大型科技", "大型科技/AI"),
    StockMeta("AMZN", "亚马逊", "美股", "大型科技", "大型科技"),
    StockMeta("GOOGL", "谷歌A", "美股", "大型科技", "大型科技/AI"),
    StockMeta("NFLX", "奈飞", "美股", "大型科技", "大型科技"),
    StockMeta("TSLA", "特斯拉", "美股", "高波动热门", "高波动/汽车"),
    StockMeta("PLTR", "Palantir", "美股", "AI/软件", "AI/软件"),
    StockMeta("APP", "AppLovin", "美股", "AI/软件", "AI/广告"),
    StockMeta("MSTR", "MicroStrategy", "美股", "加密/金融科技", "加密/高波动"),
    StockMeta("COIN", "Coinbase", "美股", "加密/金融科技", "加密/交易所"),
    StockMeta("HOOD", "Robinhood", "美股", "加密/金融科技", "金融科技"),
    StockMeta("SPCX", "SpaceX", "美股", "新股/高波动", "新股/航天/高波动"),
]

CN = [
    StockMeta("300750", "宁德时代", "A股", "高成交核心", "新能源/核心"),
    StockMeta("600519", "贵州茅台", "A股", "高成交核心", "白酒/核心"),
    StockMeta("002594", "比亚迪", "A股", "高成交核心", "汽车/新能源"),
    StockMeta("601318", "中国平安", "A股", "高成交核心", "保险/权重"),
    StockMeta("600036", "招商银行", "A股", "高成交核心", "银行/权重"),
    StockMeta("600030", "中信证券", "A股", "证券金融", "券商/金融"),
    StockMeta("300059", "东方财富", "A股", "证券金融", "券商/金融科技"),
    StockMeta("000099", "中信海直", "A股", "低空经济", "低空经济"),
    StockMeta("002085", "万丰奥威", "A股", "低空经济", "低空经济/汽车"),
    StockMeta("688981", "中芯国际", "A股", "芯片/半导体", "芯片/半导体"),
    StockMeta("002371", "北方华创", "A股", "芯片/半导体", "半导体设备"),
    StockMeta("603986", "兆易创新", "A股", "芯片/半导体", "存储芯片"),
    StockMeta("300308", "中际旭创", "A股", "AI/算力", "AI/算力/CPO"),
    StockMeta("300502", "新易盛", "A股", "AI/算力", "AI/算力/CPO"),
    StockMeta("002463", "沪电股份", "A股", "AI/算力", "AI/PCB"),
    StockMeta("002475", "立讯精密", "A股", "AI/消费电子", "消费电子/AI硬件"),
    StockMeta("688256", "寒武纪", "A股", "AI/芯片", "AI芯片"),
    StockMeta("688041", "海光信息", "A股", "AI/芯片", "AI芯片/国产替代"),
    StockMeta("688297", "中无人机", "A股", "机器人/军工", "无人机/军工"),
    StockMeta("300124", "汇川技术", "A股", "机器人/自动化", "机器人/自动化"),
]

META = {s.symbol: s for s in US + CN}

# -----------------------------
# Helpers
# -----------------------------
def yf_symbol(meta: StockMeta) -> str:
    if meta.market == "美股":
        return meta.symbol
    code = meta.symbol
    if code.startswith("6"):
        return f"{code}.SS"
    return f"{code}.SZ"


def fmt_money(x: float, market: str) -> str:
    if x is None or not np.isfinite(x):
        return "--"
    if market == "美股":
        if x >= 1e9:
            return f"${x/1e9:.1f}B"
        if x >= 1e6:
            return f"${x/1e6:.0f}M"
        return f"${x:,.0f}"
    else:
        if x >= 1e9:
            return f"¥{x/1e8:.1f}亿"
        if x >= 1e8:
            return f"¥{x/1e8:.1f}亿"
        return f"¥{x/1e4:.0f}万"


def fmt_price(x: float) -> str:
    if x is None or not np.isfinite(x):
        return "--"
    if abs(x) >= 1000:
        return f"{x:,.2f}"
    if abs(x) >= 100:
        return f"{x:.2f}"
    return f"{x:.3f}" if abs(x) < 10 else f"{x:.2f}"


def pct_class(x: float) -> str:
    if not np.isfinite(x):
        return "flat"
    if x > 0:
        return "up"
    if x < 0:
        return "down"
    return "flat"


def signal_badge(sig: str) -> str:
    mp = {
        "买入观察": "badge-buy",
        "观察": "badge-watch",
        "弱观察": "badge-weak",
        "过滤": "badge-filter",
        "低成交过滤": "badge-filter",
        "无数据": "badge-risk",
        "风险退出": "badge-risk",
    }
    cls = mp.get(sig, "badge-filter")
    return f'<span class="badge {cls}">{sig}</span>'

@st.cache_data(ttl=60*20, show_spinner=False)
def load_history(symbol: str, period: str = "6mo") -> pd.DataFrame:
    try:
        raw = yf.download(symbol, period=period, interval="1d", auto_adjust=True, progress=False, threads=False)
        if raw is None or raw.empty:
            return pd.DataFrame()
        if isinstance(raw.columns, pd.MultiIndex):
            # Keep first ticker block or first level shape safely
            if symbol in raw.columns.get_level_values(-1):
                raw = raw.xs(symbol, level=-1, axis=1)
            else:
                raw.columns = [c[0] if isinstance(c, tuple) else c for c in raw.columns]
        raw.columns = [str(c).title() for c in raw.columns]
        need = ["Open", "High", "Low", "Close", "Volume"]
        if not all(c in raw.columns for c in need):
            return pd.DataFrame()
        df = raw[need].dropna().copy()
        df.index = pd.to_datetime(df.index)
        return df
    except Exception:
        return pd.DataFrame()


def indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["MA5"] = out["Close"].rolling(5).mean()
    out["MA20"] = out["Close"].rolling(20).mean()
    out["VOL20"] = out["Volume"].rolling(20).mean()
    out["RET1"] = out["Close"].pct_change() * 100
    out["RET5"] = out["Close"].pct_change(5) * 100
    out["VOLR"] = out["Volume"] / out["VOL20"]
    out["HIGH20"] = out["Close"].rolling(20).max()
    out["LOW10"] = out["Low"].rolling(10).min()
    out["TR"] = np.maximum(out["High"] - out["Low"], np.maximum(abs(out["High"] - out["Close"].shift()), abs(out["Low"] - out["Close"].shift())))
    out["ATR14"] = out["TR"].rolling(14).mean()
    return out


def analyze_one(meta: StockMeta) -> Dict:
    df = load_history(yf_symbol(meta))
    if df.empty or len(df) < 30:
        return dict(代码=meta.symbol, 名称=meta.name, 市场=meta.market, 板块=meta.sector, 标签=meta.tags,
                    信号="无数据", 分数=0, 现价=np.nan, 涨跌幅=np.nan, 量比=np.nan, 成交额=np.nan,
                    原因="行情源暂时无数据", 风险="无数据", 入场=np.nan, 止损=np.nan, 止盈1=np.nan, 止盈2=np.nan, 止盈3=np.nan)
    ind = indicators(df).dropna()
    if ind.empty:
        return dict(代码=meta.symbol, 名称=meta.name, 市场=meta.market, 板块=meta.sector, 标签=meta.tags,
                    信号="无数据", 分数=0, 现价=np.nan, 涨跌幅=np.nan, 量比=np.nan, 成交额=np.nan,
                    原因="指标数据不足", 风险="无数据", 入场=np.nan, 止损=np.nan, 止盈1=np.nan, 止盈2=np.nan, 止盈3=np.nan)
    last = ind.iloc[-1]
    prev = ind.iloc[-2]
    close = float(last.Close)
    ret1 = float(last.RET1)
    ret5 = float(last.RET5)
    volr = float(last.VOLR) if np.isfinite(last.VOLR) else 0
    turnover = float(last.Volume * last.Close)
    above20 = close > float(last.MA20)
    above5 = close > float(last.MA5)
    near_high = close >= float(last.HIGH20) * 0.96
    strong_big = ret1 >= (9.2 if meta.market == "A股" else 3.0)
    medium_up = ret1 >= (3.0 if meta.market == "A股" else 1.8)
    liquidity_ok = turnover >= (2e8 if meta.market == "A股" else 2e7)

    score = 0
    reasons = []
    if liquidity_ok:
        score += 10; reasons.append("成交额达标")
    else:
        reasons.append("成交额偏低")
    if above20:
        score += 18; reasons.append("趋势在20日线上")
    else:
        reasons.append("未站上20日线")
    if above5:
        score += 10; reasons.append("短线站上5日线")
    if medium_up:
        score += 18; reasons.append("当日涨幅强")
    if strong_big:
        score += 14; reasons.append("接近涨停/强势大阳")
    if volr >= 1.5:
        score += 18; reasons.append("放量")
    elif volr >= 1.1:
        score += 8; reasons.append("量能温和放大")
    if near_high:
        score += 12; reasons.append("接近20日新高")
    if ret5 > 5:
        score += 8; reasons.append("5日动量强")

    risk_notes = []
    if ret1 < -2:
        score -= 18; risk_notes.append("当日走弱")
    if close < float(last.MA20):
        score -= 15; risk_notes.append("趋势未确认")
    if "杠杆ETF" in meta.tags:
        score -= 6; risk_notes.append("杠杆ETF高波动")
    if "新股" in meta.tags:
        score -= 5; risk_notes.append("新股波动大")

    if not liquidity_ok:
        sig = "低成交过滤"
    elif score >= 82:
        sig = "买入观察"
    elif score >= 66:
        sig = "观察"
    elif score >= 52:
        sig = "弱观察"
    else:
        sig = "过滤"

    atr = float(last.ATR14) if np.isfinite(last.ATR14) else close * 0.04
    # 投机者视角：不追高，给“触发价”，不是立刻买入价
    entry = max(close, float(last.High) * 1.002)
    stop1 = max(0.01, min(float(last.Low) * 0.995, close - max(atr * 1.05, close * 0.035)))
    risk = max(entry - stop1, close * 0.02)
    tp1 = entry + risk * 1.2
    tp2 = entry + risk * 2.0
    tp3 = entry + risk * 3.0

    risk_text = "；".join(risk_notes) if risk_notes else "暂未发现硬伤"
    return dict(
        代码=meta.symbol, 名称=meta.name, 市场=meta.market, 板块=meta.sector, 标签=meta.tags,
        信号=sig, 分数=int(max(0, min(100, round(score)))), 现价=close, 涨跌幅=ret1, 五日涨幅=ret5,
        量比=volr, 成交额=turnover, 原因="；".join(reasons), 风险=risk_text,
        入场=entry, 止损=stop1, 止盈1=tp1, 止盈2=tp2, 止盈3=tp3,
    )


def universe_for(market_pick: str) -> List[StockMeta]:
    if market_pick == "美股":
        return US
    if market_pick == "A股":
        return CN
    return US + CN


def scan_universe(market_pick: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    metas = universe_for(market_pick)
    bar = st.progress(0, text="正在扫描市场 → 板块 → 股票...")
    for i, meta in enumerate(metas, 1):
        rows.append(analyze_one(meta))
        bar.progress(i/len(metas), text=f"扫描中：{meta.name}（{meta.symbol}）")
    bar.empty()
    df = pd.DataFrame(rows)
    if df.empty:
        return df, pd.DataFrame()

    # Sector scoring: first decide hot sectors, then promote stocks inside them
    sec_rows = []
    valid = df[~df["信号"].isin(["无数据", "低成交过滤"])]
    for (market, sector), g in valid.groupby(["市场", "板块"]):
        up_rate = (g["涨跌幅"] > 0).mean() * 100 if len(g) else 0
        avg_ret = g["涨跌幅"].mean() if len(g) else 0
        strong = (g["分数"] >= 66).sum()
        buy = (g["信号"] == "买入观察").sum()
        vol = (g["量比"] >= 1.3).sum()
        top3 = g.sort_values("分数", ascending=False).head(3)
        score = min(100, round(up_rate*0.22 + max(avg_ret,0)*6 + strong*10 + buy*12 + vol*5 + top3["分数"].mean()*0.25)) if len(g) else 0
        leaders = "、".join([f"{r['名称']}({r['代码']})" for _, r in top3.iterrows()])
        sec_rows.append(dict(市场=market, 板块=sector, 强度分=int(score), 上涨率=round(up_rate,1), 平均涨幅=round(avg_ret,2), 强势股数=int(strong), 放量股数=int(vol), 龙头候选=leaders))
    sec = pd.DataFrame(sec_rows).sort_values("强度分", ascending=False) if sec_rows else pd.DataFrame()

    # Promote top sectors and mark non-top sectors lower
    if not sec.empty:
        top_keys = set((r["市场"], r["板块"]) for _, r in sec.head(5).iterrows())
        df["热门板块"] = df.apply(lambda r: (r["市场"], r["板块"]) in top_keys, axis=1)
        df["最终分数"] = df["分数"] + df["热门板块"].map({True:8, False:-6})
        # downgrade if not in hot sector except already buy quality
        df.loc[(~df["热门板块"]) & (df["信号"] == "买入观察"), "信号"] = "观察"
    else:
        df["热门板块"] = False
        df["最终分数"] = df["分数"]

    order_map = {"买入观察":0, "观察":1, "弱观察":2, "过滤":3, "低成交过滤":4, "无数据":5}
    df["排序"] = df["信号"].map(order_map).fillna(9)
    df = df.sort_values(["排序", "最终分数", "涨跌幅"], ascending=[True, False, False]).reset_index(drop=True)
    return df, sec


def market_temp(df: pd.DataFrame) -> Tuple[str, str]:
    if df.empty:
        return "等待扫描", "--"
    valid = df[~df["信号"].isin(["无数据", "低成交过滤"])]
    if valid.empty:
        return "弱", "无有效行情"
    buy = (valid["信号"] == "买入观察").sum()
    watch = (valid["信号"] == "观察").sum()
    up = (valid["涨跌幅"] > 0).mean() * 100
    if buy >= 5 and up >= 55:
        return "强", f"买入观察 {buy}，上涨率 {up:.0f}%"
    if buy >= 2 or watch >= 8:
        return "中", f"买入观察 {buy}，观察 {watch}"
    return "弱", f"买入观察 {buy}，上涨率 {up:.0f}%"


def render_rows(df: pd.DataFrame, max_rows: int = 50):
    if df.empty:
        st.info("没有结果。")
        return
    html = ['<div class="tv-card" style="padding:4px 12px;">']
    for _, r in df.head(max_rows).iterrows():
        market_cls = "us" if r["市场"] == "美股" else "cn"
        pct = r["涨跌幅"] if np.isfinite(r["涨跌幅"]) else 0
        pc = pct_class(pct)
        first = str(r["名称"] or r["代码"])[0]
        html.append(f'''
        <div class="row">
          <div class="logo {market_cls}">{first}</div>
          <div>
            <div class="code">{r['代码']} <span class="small">· {r['市场']}</span></div>
            <div class="name">{r['名称']} · {r['板块']} · {r['标签']}</div>
            <div class="tagline">{signal_badge(r['信号'])}<span>分数 {int(r['最终分数']) if '最终分数' in r else int(r['分数'])} · 量比 {r['量比']:.2f} · 成交 {fmt_money(r['成交额'], r['市场'])}</span></div>
          </div>
          <div class="price">
            <div class="p">{fmt_price(r['现价'])}</div>
            <div class="{pc}">{pct:+.2f}%</div>
          </div>
        </div>
        ''')
    html.append('</div>')
    st.markdown("".join(html), unsafe_allow_html=True)


def render_sector(sec: pd.DataFrame):
    if sec.empty:
        st.info("等待扫描。")
        return
    html = ['<div class="tv-card">']
    for _, r in sec.head(8).iterrows():
        html.append(f'''
        <div class="sector-row">
          <div>
            <div class="sector-name">🔥 {r['市场']} · {r['板块']}</div>
            <div class="sector-meta">上涨率 {r['上涨率']}% · 平均涨幅 {r['平均涨幅']}% · 强势 {r['强势股数']} · 放量 {r['放量股数']}</div>
            <div class="sector-meta">前排：{r['龙头候选']}</div>
          </div>
          <div class="score">{r['强度分']}</div>
        </div>
        ''')
    html.append('</div>')
    st.markdown("".join(html), unsafe_allow_html=True)


def kline_figure(meta: StockMeta) -> Optional[go.Figure]:
    df = load_history(yf_symbol(meta), period="6mo")
    if df.empty or len(df) < 20:
        return None
    ind = indicators(df)
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=ind.index, open=ind["Open"], high=ind["High"], low=ind["Low"], close=ind["Close"], name="K线",
                                 increasing_line_color="#089981", decreasing_line_color="#f23645"))
    fig.add_trace(go.Scatter(x=ind.index, y=ind["MA5"], name="5日线", line=dict(color="#ff9800", width=1.8)))
    fig.add_trace(go.Scatter(x=ind.index, y=ind["MA20"], name="20日线", line=dict(color="#2962ff", width=1.8)))
    fig.update_layout(height=420, margin=dict(l=8,r=8,t=36,b=16), template="plotly_white", xaxis_rangeslider_visible=False,
                      title=f"{meta.name}（{meta.symbol}）", legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0))
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="#eef2f7")
    return fig

# -----------------------------
# UI
# -----------------------------
if "scan_df" not in st.session_state:
    st.session_state.scan_df = pd.DataFrame()
if "sector_df" not in st.session_state:
    st.session_state.sector_df = pd.DataFrame()
if "market_pick" not in st.session_state:
    st.session_state.market_pick = "全部"

st.markdown('''
<div class="hero">
  <div>
    <div class="brand">短线投机者雷达</div>
    <div class="sub">先找最强板块，再找前排股票；给你入场、止损、止盈参考。</div>
  </div>
  <div class="pill hot">LIVE</div>
</div>
''', unsafe_allow_html=True)

c1, c2 = st.columns([1, 1])
with c1:
    market_pick = st.radio("市场", ["全部", "美股", "A股"], horizontal=True, label_visibility="collapsed", index=["全部","美股","A股"].index(st.session_state.market_pick))
    st.session_state.market_pick = market_pick
with c2:
    run = st.button("⚡ 开始自动扫描", use_container_width=True)

st.markdown('<div class="topbar"><span class="pill">自动找热门板块</span><span class="pill">过滤低成交</span><span class="pill">10只买入观察</span><span class="pill">20只观察名单</span></div>', unsafe_allow_html=True)

if run:
    with st.spinner("正在按投机者漏斗扫描：市场 → 板块 → 股票..."):
        df, sec = scan_universe(market_pick)
        st.session_state.scan_df = df
        st.session_state.sector_df = sec

scan_df = st.session_state.scan_df
sector_df = st.session_state.sector_df
mt, mt_note = market_temp(scan_df)

buy_df = scan_df[scan_df["信号"] == "买入观察"].head(10) if not scan_df.empty else pd.DataFrame()
watch_df = scan_df[scan_df["信号"].isin(["观察", "弱观察"])].head(20) if not scan_df.empty else pd.DataFrame()
filter_df = scan_df[scan_df["信号"].isin(["过滤", "低成交过滤", "无数据"])] if not scan_df.empty else pd.DataFrame()

st.markdown(f'''
<div class="metric-grid">
  <div class="metric"><div class="label">短线温度</div><div class="value">{mt}</div><div class="note">{mt_note}</div></div>
  <div class="metric"><div class="label">买入观察</div><div class="value">{len(buy_df)}</div><div class="note">不是下单命令</div></div>
  <div class="metric"><div class="label">观察名单</div><div class="value">{len(watch_df)}</div><div class="note">等待确认</div></div>
</div>
''', unsafe_allow_html=True)

if scan_df.empty:
    st.markdown('<div class="reason">选择市场后点“开始自动扫描”。不用先选板块，程序会自动找热门板块，再从里面找前排股票。</div>', unsafe_allow_html=True)

tabs = st.tabs(["🔥 最强板块", "🎯 买入观察", "👀 观察名单", "📈 个股详情", "🧹 过滤原因", "📋 数据表"])

with tabs[0]:
    st.subheader("最强板块排行榜")
    render_sector(sector_df)

with tabs[1]:
    st.subheader("买入观察：最多10只")
    if buy_df.empty:
        st.markdown('<div class="warn">当前没有硬条件达标的买入观察。投机者最该会的是空仓，不是硬凑机会。</div>', unsafe_allow_html=True)
    render_rows(buy_df)

with tabs[2]:
    st.subheader("观察名单：最多20只")
    render_rows(watch_df)

with tabs[3]:
    st.subheader("个股详情 / K线 / 交易计划")
    if scan_df.empty:
        st.info("先扫描。")
    else:
        options = [f"{r['代码']} | {r['名称']} | {r['信号']}" for _, r in scan_df.head(30).iterrows()]
        pick = st.selectbox("选择股票", options)
        code = pick.split(" | ")[0]
        r = scan_df[scan_df["代码"] == code].iloc[0]
        meta = META.get(code)
        st.markdown(f"""
        <div class="tv-card">
          <div class="row" style="border-bottom:0;">
            <div class="logo {'us' if r['市场']=='美股' else 'cn'}">{r['名称'][0]}</div>
            <div>
              <div class="code">{r['名称']}（{r['代码']}）</div>
              <div class="name">{r['市场']} · {r['板块']} · {r['标签']}</div>
              <div class="tagline">{signal_badge(r['信号'])}<span>分数 {int(r['最终分数']) if '最终分数' in r else int(r['分数'])}</span></div>
            </div>
            <div class="price"><div class="p">{fmt_price(r['现价'])}</div><div class="{pct_class(r['涨跌幅'])}">{r['涨跌幅']:+.2f}%</div></div>
          </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(f'<div class="reason"><b>为什么入选/观察：</b>{r["原因"]}<br><b>风险：</b>{r["风险"]}</div>', unsafe_allow_html=True)
        st.markdown("#### 如果我是投机者，我会这样处理")
        st.markdown(f"""
        <div class="plan-grid">
          <div class="plan-box"><div class="k">触发入场</div><div class="v">{fmt_price(r['入场'])}</div></div>
          <div class="plan-box"><div class="k">硬止损</div><div class="v down">{fmt_price(r['止损'])}</div></div>
          <div class="plan-box"><div class="k">止盈1</div><div class="v up">{fmt_price(r['止盈1'])}</div></div>
          <div class="plan-box"><div class="k">止盈2</div><div class="v up">{fmt_price(r['止盈2'])}</div></div>
          <div class="plan-box"><div class="k">止盈3</div><div class="v up">{fmt_price(r['止盈3'])}</div></div>
          <div class="plan-box"><div class="k">纪律</div><div class="v">不补仓</div></div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown('<div class="warn">买入观察不是立刻追。我的规则：只在突破触发价且成交继续放大时小仓试；跌破硬止损就走；到止盈1先减一部分，别把盈利单做成亏损单。</div>', unsafe_allow_html=True)
        if meta:
            fig = kline_figure(meta)
            if fig:
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            else:
                st.info("该股票K线暂时无数据。")

with tabs[4]:
    st.subheader("过滤原因")
    if filter_df.empty:
        st.info("暂无过滤结果。")
    else:
        cols = ["代码", "名称", "市场", "板块", "信号", "分数", "现价", "涨跌幅", "量比", "成交额", "原因", "风险"]
        show = filter_df[cols].copy()
        show["成交额"] = show.apply(lambda x: fmt_money(x["成交额"], x["市场"]), axis=1)
        st.dataframe(show, use_container_width=True, hide_index=True)

with tabs[5]:
    st.subheader("全部扫描数据")
    if scan_df.empty:
        st.info("先扫描。")
    else:
        show = scan_df[["代码","名称","市场","板块","信号","最终分数","现价","涨跌幅","量比","成交额","标签","原因","风险","入场","止损","止盈1","止盈2"]].copy()
        show["成交额"] = show.apply(lambda x: fmt_money(x["成交额"], x["市场"]), axis=1)
        for c in ["现价","入场","止损","止盈1","止盈2"]:
            show[c] = show[c].map(fmt_price)
        st.dataframe(show, use_container_width=True, hide_index=True)
        st.download_button("下载CSV", show.to_csv(index=False).encode("utf-8-sig"), file_name="短线扫描结果.csv", mime="text/csv")
