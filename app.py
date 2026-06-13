import math
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional

import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf
import plotly.graph_objects as go

# =========================
# 页面与样式
# =========================
st.set_page_config(page_title="短线情绪板块选股器", page_icon="📈", layout="wide")

CSS = """
<style>
:root {
  --bg: #f7f8fb;
  --card: #ffffff;
  --text: #111827;
  --muted: #6b7280;
  --line: #e5e7eb;
  --green: #059669;
  --red: #dc2626;
  --blue: #2563eb;
  --orange: #f97316;
  --shadow: 0 8px 26px rgba(15, 23, 42, .08);
}
.stApp { background: var(--bg); color: var(--text); }
.block-container { padding-top: .55rem; padding-bottom: 2.2rem; max-width: 1180px; }
section[data-testid="stSidebar"] { background: #ffffff; border-right: 1px solid var(--line); }
section[data-testid="stSidebar"] .block-container { padding-top: 1rem; }
[data-testid="stDecoration"] { display:none; }
#MainMenu, footer, header { visibility: hidden; height: 0; }

.tv-topbar {
  position: sticky; top: 0; z-index: 999; background: rgba(247,248,251,.86);
  backdrop-filter: blur(18px); -webkit-backdrop-filter: blur(18px);
  border-bottom: 1px solid rgba(229,231,235,.65);
  padding: .65rem .2rem .75rem .2rem; margin: -.55rem 0 .8rem 0;
}
.tv-title { font-size: 1.45rem; font-weight: 850; letter-spacing: -.02em; line-height: 1.1; }
.tv-subtitle { color: var(--muted); font-size: .92rem; margin-top: .2rem; }

.kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: .72rem; margin: .75rem 0 .9rem; }
.kpi-card { background: var(--card); border:1px solid var(--line); border-radius: 18px; box-shadow: var(--shadow); padding: .88rem; }
.kpi-label { color: var(--muted); font-size: .78rem; }
.kpi-value { font-size: 1.35rem; font-weight: 850; margin-top:.28rem; }
.kpi-note { color: var(--muted); font-size: .76rem; margin-top:.2rem; }

.list-card { background: var(--card); border:1px solid var(--line); border-radius: 18px; box-shadow: var(--shadow); padding: .3rem .35rem; margin: .55rem 0; }
.row-card { display: grid; grid-template-columns: 52px 1fr auto; gap: .72rem; align-items: center; padding: .72rem .55rem; border-bottom:1px solid var(--line); }
.row-card:last-child { border-bottom:none; }
.logo-dot { width: 42px; height: 42px; border-radius: 50%; display:flex; align-items:center; justify-content:center; font-weight:850; color:white; background: linear-gradient(135deg,#2563eb,#7c3aed); font-size: .85rem; }
.sym { font-size:1.05rem; font-weight:850; letter-spacing:.01em; }
.name { font-size:.82rem; color:var(--muted); margin-top:.12rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 360px; }
.price { text-align:right; font-size:1.04rem; font-weight:820; }
.chg-pos { color: var(--green); font-weight: 800; }
.chg-neg { color: var(--red); font-weight: 800; }
.signal-pill { display:inline-block; border-radius:999px; padding:.18rem .48rem; font-size:.72rem; font-weight:850; margin-left:.3rem; }
.pill-buy { background:#fee2e2; color:#b91c1c; }
.pill-watch { background:#dbeafe; color:#1d4ed8; }
.pill-risk { background:#f3f4f6; color:#4b5563; }
.pill-limit { background:#ffedd5; color:#c2410c; }

.sector-grid { display:grid; grid-template-columns: repeat(2, 1fr); gap:.75rem; }
.sector-card { background:var(--card); border:1px solid var(--line); border-radius:18px; box-shadow:var(--shadow); padding:.9rem; }
.sector-name { font-weight:850; font-size:1.02rem; }
.sector-score { font-size:1.55rem; font-weight:900; margin:.35rem 0 .15rem; }
.muted { color:var(--muted); }
.reason-box { background:#fff; border:1px solid var(--line); border-radius:16px; padding:.85rem; box-shadow: var(--shadow); }
.warning-box { background:#fff7ed; border:1px solid #fed7aa; color:#9a3412; border-radius:16px; padding:.85rem; }
.good-box { background:#ecfdf5; border:1px solid #a7f3d0; color:#065f46; border-radius:16px; padding:.85rem; }

.stButton > button { border-radius: 999px; padding: .68rem 1.05rem; font-weight: 850; border: 0; box-shadow: var(--shadow); }
.stDataFrame, div[data-testid="stDataFrame"] { border-radius: 18px; overflow: hidden; }

@media(max-width: 760px) {
 .block-container { padding-left: .72rem; padding-right: .72rem; }
 .tv-title { font-size: 1.22rem; }
 .tv-subtitle { font-size: .82rem; }
 .kpi-grid { grid-template-columns: repeat(2, 1fr); gap:.55rem; }
 .kpi-card { padding:.72rem; border-radius:16px; }
 .kpi-value { font-size:1.15rem; }
 .sector-grid { grid-template-columns: 1fr; }
 .row-card { grid-template-columns: 44px 1fr auto; gap:.55rem; padding:.65rem .36rem; }
 .logo-dot { width:36px; height:36px; font-size:.74rem; }
 .sym { font-size:.95rem; }
 .name { max-width: 150px; font-size:.76rem; }
 .price { font-size:.92rem; }
 .signal-pill { font-size:.66rem; padding:.12rem .38rem; }
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# =========================
# 数据池：可扩展
# =========================
US_SECTORS: Dict[str, List[str]] = {
    "AI/芯片": ["NVDA", "AMD", "AVGO", "ARM", "MU", "SMCI", "MRVL", "TSM", "ASML", "SMH", "SOXL"],
    "大型科技": ["AAPL", "MSFT", "META", "AMZN", "GOOGL", "NFLX", "TSLA", "PLTR", "APP", "ORCL", "NOW"],
    "加密/金融科技": ["COIN", "MSTR", "HOOD", "MARA", "RIOT", "CLSK", "SQ", "PYPL", "IBIT", "BITO"],
    "军工/太空": ["SPCX", "RKLB", "LMT", "NOC", "RTX", "BA", "GE", "ASTS", "LUNR"],
    "能源/核电": ["CCJ", "CEG", "OKLO", "SMR", "URA", "XOM", "CVX", "OXY", "SLB"],
    "医疗/生物科技": ["LLY", "NVO", "MRNA", "REGN", "VRTX", "UNH", "PFE", "XBI"],
    "ETF/指数": ["SPY", "QQQ", "DIA", "IWM", "TQQQ", "SQQQ", "SMH", "SOXL"],
}

CN_SECTORS: Dict[str, List[str]] = {
    "A股AI/算力": ["300308", "002230", "300502", "601138", "002415", "000938", "603019", "688041", "688256", "300474"],
    "A股芯片/半导体": ["688981", "600584", "002371", "603986", "688012", "300604", "002049", "688008", "300782", "002475"],
    "A股机器人": ["300024", "002527", "002031", "300124", "603960", "002747", "688017", "301029"],
    "A股低空经济": ["002085", "600316", "300424", "300159", "000099", "600879", "300900", "688297"],
    "A股证券金融": ["600030", "601688", "000776", "601211", "600837", "600999", "300059", "601099"],
    "A股新能源/汽车": ["300750", "002594", "601012", "002466", "002812", "600438", "002460", "600418", "601127"],
    "A股高成交核心": ["600519", "000858", "601318", "600036", "601899", "601398", "600900", "000001", "000333", "600276"],
}

NAME_MAP: Dict[str, str] = {
    # US
    "NVDA":"英伟达", "AMD":"AMD", "AVGO":"博通", "ARM":"Arm", "MU":"美光科技", "SMCI":"超微电脑", "MRVL":"迈威尔", "TSM":"台积电", "ASML":"阿斯麦", "SMH":"半导体ETF", "SOXL":"三倍做多半导体ETF",
    "AAPL":"苹果", "MSFT":"微软", "META":"Meta", "AMZN":"亚马逊", "GOOGL":"谷歌", "NFLX":"奈飞", "TSLA":"特斯拉", "PLTR":"Palantir", "APP":"AppLovin", "ORCL":"甲骨文", "NOW":"ServiceNow",
    "COIN":"Coinbase", "MSTR":"MicroStrategy", "HOOD":"Robinhood", "MARA":"MARA", "RIOT":"Riot", "CLSK":"CleanSpark", "SQ":"Block", "PYPL":"PayPal", "IBIT":"比特币ETF", "BITO":"比特币期货ETF",
    "SPCX":"SpaceX", "RKLB":"Rocket Lab", "LMT":"洛克希德马丁", "NOC":"诺斯罗普", "RTX":"RTX", "BA":"波音", "GE":"GE Aerospace", "ASTS":"AST SpaceMobile", "LUNR":"Intuitive Machines",
    "CCJ":"Cameco", "CEG":"Constellation Energy", "OKLO":"Oklo", "SMR":"NuScale", "URA":"铀矿ETF", "XOM":"埃克森美孚", "CVX":"雪佛龙", "OXY":"西方石油", "SLB":"斯伦贝谢",
    "LLY":"礼来", "NVO":"诺和诺德", "MRNA":"Moderna", "REGN":"再生元", "VRTX":"Vertex", "UNH":"联合健康", "PFE":"辉瑞", "XBI":"生物科技ETF",
    "SPY":"标普500ETF", "QQQ":"纳指100ETF", "DIA":"道指ETF", "IWM":"罗素2000ETF", "TQQQ":"三倍做多纳指ETF", "SQQQ":"三倍做空纳指ETF",
    # CN
    "600519":"贵州茅台", "000858":"五粮液", "601318":"中国平安", "600036":"招商银行", "601899":"紫金矿业", "601398":"工商银行", "600900":"长江电力", "000001":"平安银行", "000333":"美的集团", "600276":"恒瑞医药",
    "300750":"宁德时代", "002594":"比亚迪", "601012":"隆基绿能", "002466":"天齐锂业", "002812":"恩捷股份", "600438":"通威股份", "002460":"赣锋锂业", "600418":"江淮汽车", "601127":"赛力斯",
    "300308":"中际旭创", "002230":"科大讯飞", "300502":"新易盛", "601138":"工业富联", "002415":"海康威视", "000938":"紫光股份", "603019":"中科曙光", "688041":"海光信息", "688256":"寒武纪", "300474":"景嘉微",
    "688981":"中芯国际", "600584":"长电科技", "002371":"北方华创", "603986":"兆易创新", "688012":"中微公司", "300604":"长川科技", "002049":"紫光国微", "688008":"澜起科技", "300782":"卓胜微", "002475":"立讯精密",
    "300024":"机器人", "002527":"新时达", "002031":"巨轮智能", "300124":"汇川技术", "603960":"克来机电", "002747":"埃斯顿", "688017":"绿的谐波", "301029":"怡合达",
    "002085":"万丰奥威", "600316":"洪都航空", "300424":"航新科技", "300159":"新研股份", "000099":"中信海直", "600879":"航天电子", "300900":"广联航空", "688297":"中无人机",
    "600030":"中信证券", "601688":"华泰证券", "000776":"广发证券", "601211":"国泰君安", "600837":"海通证券", "600999":"招商证券", "300059":"东方财富", "601099":"太平洋",
}

CATALYST_TAGS: Dict[str, str] = {
    "AI/芯片": "AI/芯片", "大型科技": "大型科技", "加密/金融科技": "加密/金融科技", "军工/太空": "军工/太空", "能源/核电": "能源/核电", "医疗/生物科技": "医疗", "ETF/指数":"ETF",
    "A股AI/算力":"AI/算力", "A股芯片/半导体":"芯片", "A股机器人":"机器人", "A股低空经济":"低空经济", "A股证券金融":"证券金融", "A股新能源/汽车":"新能源车", "A股高成交核心":"核心资产",
}

LEVERAGED = {"SOXL", "TQQQ", "SQQQ"}
HIGH_VOL = {"SPCX", "SMCI", "RKLB", "LUNR", "ASTS", "MSTR", "COIN", "MARA", "RIOT", "CLSK", "OKLO", "SMR"}

# =========================
# 参数和工具函数
# =========================
@dataclass
class ScanConfig:
    scope: str = "美股+A股"
    top_sector_count: int = 5
    target_buy: int = 10
    target_watch: int = 20
    min_us_dollar_vol: float = 20_000_000
    min_cn_turnover: float = 200_000_000
    period: str = "6mo"
    interval: str = "1d"
    news_weight: bool = False


def cn_to_yf(code: str) -> str:
    s = str(code).strip().upper().replace(".SS", "").replace(".SZ", "")
    if not s.isdigit() or len(s) != 6:
        return s
    if s.startswith(("6", "9")):
        return f"{s}.SS"
    return f"{s}.SZ"


def base_symbol(ticker: str) -> str:
    return ticker.upper().replace(".SS", "").replace(".SZ", "")


def is_cn_symbol(ticker: str) -> bool:
    b = base_symbol(ticker)
    return b.isdigit() and len(b) == 6


def display_name(ticker: str) -> str:
    return NAME_MAP.get(base_symbol(ticker), NAME_MAP.get(ticker.upper(), base_symbol(ticker)))


def yf_symbol(ticker: str) -> str:
    return cn_to_yf(ticker) if is_cn_symbol(ticker) else ticker.upper()


def market_of(ticker: str) -> str:
    return "A股" if is_cn_symbol(ticker) else "美股"


def unique_ordered(items: List[str]) -> List[str]:
    out = []
    for x in items:
        if x not in out:
            out.append(x)
    return out


def selected_sectors(scope: str) -> Dict[str, List[str]]:
    if scope == "美股":
        return US_SECTORS
    if scope == "A股":
        return CN_SECTORS
    merged = {}
    merged.update(US_SECTORS)
    merged.update(CN_SECTORS)
    return merged


@st.cache_data(ttl=60 * 15, show_spinner=False)
def fetch_ohlcv(raw_ticker: str, period: str = "6mo", interval: str = "1d") -> pd.DataFrame:
    yft = yf_symbol(raw_ticker)
    try:
        df = yf.download(yft, period=period, interval=interval, auto_adjust=True, progress=False, threads=False)
        if df is None or df.empty:
            return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex):
            # yfinance sometimes returns (Price, Ticker)
            if yft in df.columns.get_level_values(-1):
                df = df.xs(yft, axis=1, level=-1)
            else:
                df.columns = [str(c[0]) for c in df.columns]
        df = df.rename(columns={c: str(c).title() for c in df.columns})
        need = ["Open", "High", "Low", "Close", "Volume"]
        if not all(c in df.columns for c in need):
            return pd.DataFrame()
        out = df[need].dropna().copy()
        out.index = pd.to_datetime(out.index)
        return out
    except Exception:
        return pd.DataFrame()


def add_metrics(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["MA5"] = out["Close"].rolling(5).mean()
    out["MA20"] = out["Close"].rolling(20).mean()
    out["RET1"] = out["Close"].pct_change()
    out["RET5"] = out["Close"].pct_change(5)
    out["VOL_MA20"] = out["Volume"].rolling(20).mean()
    out["VOL_RATIO"] = out["Volume"] / out["VOL_MA20"]
    out["HIGH20"] = out["Close"].rolling(20).max()
    out["NEAR_HIGH20"] = out["Close"] / out["HIGH20"]
    out["TURNOVER"] = out["Close"] * out["Volume"]
    return out


def signal_cn(sig: str) -> str:
    mp = {
        "BUY": "买入观察", "WATCH": "观察", "WEAK": "弱观察", "FILTER": "已过滤", "RISK": "风险退出", "NODATA": "无数据", "LOWLIQ": "低成交过滤", "LIMIT": "涨停观察"
    }
    return mp.get(sig, sig)


def score_stock(ticker: str, sector: str, cfg: ScanConfig) -> Dict:
    df = fetch_ohlcv(ticker, cfg.period, cfg.interval)
    b = base_symbol(ticker)
    mkt = market_of(ticker)
    if df.empty or len(df) < 25:
        return {"代码": b, "名称": display_name(ticker), "市场": mkt, "板块": sector, "信号": "无数据", "分数": 0, "现价": np.nan, "涨跌幅%": np.nan, "量比": np.nan, "成交额": np.nan, "标签": CATALYST_TAGS.get(sector, ""), "原因": "数据不足或数据源暂不可用", "raw_signal":"NODATA"}
    md = add_metrics(df).dropna()
    if md.empty:
        return {"代码": b, "名称": display_name(ticker), "市场": mkt, "板块": sector, "信号": "无数据", "分数": 0, "现价": np.nan, "涨跌幅%": np.nan, "量比": np.nan, "成交额": np.nan, "标签": CATALYST_TAGS.get(sector, ""), "原因": "指标计算数据不足", "raw_signal":"NODATA"}
    last = md.iloc[-1]
    close = float(last["Close"])
    ret1 = float(last["RET1"] * 100)
    ret5 = float(last["RET5"] * 100) if not math.isnan(float(last["RET5"])) else 0.0
    vr = float(last["VOL_RATIO"]) if not math.isnan(float(last["VOL_RATIO"])) else 0.0
    turnover = float(last["TURNOVER"])
    trend = close > float(last["MA20"]) and float(last["MA5"]) >= float(last["MA20"])
    near_high = float(last["NEAR_HIGH20"]) >= 0.97
    strong_day = ret1 >= (9.2 if mkt == "A股" else 3.0)
    big_up = ret1 >= (5.0 if mkt == "A股" else 2.0)
    liquid = turnover >= (cfg.min_cn_turnover if mkt == "A股" else cfg.min_us_dollar_vol)

    score = 0
    reasons = []
    if liquid:
        score += 15; reasons.append("成交额达标")
    else:
        reasons.append("成交额偏低")
    if trend:
        score += 22; reasons.append("趋势在20日线之上")
    else:
        reasons.append("趋势未确认")
    if big_up:
        score += 18; reasons.append("涨幅有强度")
    if vr >= 1.5:
        score += 18; reasons.append("明显放量")
    elif vr >= 1.15:
        score += 9; reasons.append("温和放量")
    if near_high:
        score += 15; reasons.append("接近20日新高")
    if ret5 > 5:
        score += 8; reasons.append("5日动量强")
    if strong_day:
        score += 15; reasons.append("大阳/近涨停强度")
    if b in LEVERAGED:
        score -= 8; reasons.append("杠杆ETF，风险加倍")
    if b in HIGH_VOL:
        score -= 5; reasons.append("高波动标的，谨慎追高")
    if ret1 < -2:
        score -= 20; reasons.append("当日走弱")
    if not liquid:
        raw = "LOWLIQ"
    elif mkt == "A股" and strong_day and score >= 75:
        raw = "LIMIT"
    elif score >= 85:
        raw = "BUY"
    elif score >= 70:
        raw = "WATCH"
    elif score >= 55:
        raw = "WEAK"
    else:
        raw = "FILTER"
    return {
        "代码": b,
        "名称": display_name(ticker),
        "市场": mkt,
        "板块": sector,
        "信号": signal_cn(raw),
        "分数": int(max(0, min(100, score))),
        "现价": round(close, 3),
        "涨跌幅%": round(ret1, 2),
        "5日涨幅%": round(ret5, 2),
        "量比": round(vr, 2),
        "成交额": round(turnover, 0),
        "标签": tag_for(b, sector),
        "原因": "；".join(reasons[:5]),
        "raw_signal": raw,
    }


def tag_for(symbol: str, sector: str) -> str:
    tags = [CATALYST_TAGS.get(sector, sector)]
    if symbol in LEVERAGED:
        tags.append("杠杆ETF")
    if symbol in HIGH_VOL:
        tags.append("高波动")
    if symbol in {"SPCX", "RKLB", "LUNR", "ASTS"}:
        tags.append("太空")
    return " / ".join(unique_ordered([t for t in tags if t]))


def score_sector(sector: str, tickers: List[str], cfg: ScanConfig) -> Tuple[Dict, pd.DataFrame]:
    rows = [score_stock(t, sector, cfg) for t in tickers]
    df = pd.DataFrame(rows)
    valid = df[~df["信号"].isin(["无数据"])]
    if valid.empty:
        return {"板块": sector, "强度分": 0, "上涨率%": 0, "强势数": 0, "放量数": 0, "前排": "无", "成员数": len(tickers), "标签": CATALYST_TAGS.get(sector, "")}, df
    up_rate = (valid["涨跌幅%"] > 0).mean() * 100
    strong_count = valid[valid["分数"] >= 70].shape[0]
    vol_count = valid[valid["量比"] >= 1.5].shape[0]
    top3 = valid.sort_values("涨跌幅%", ascending=False).head(3)
    top3_ret = top3["涨跌幅%"].mean() if not top3.empty else 0
    avg_score = valid["分数"].mean()
    sector_score = min(100, max(0, avg_score * .45 + up_rate * .20 + strong_count * 8 + vol_count * 5 + top3_ret * 2))
    return {
        "板块": sector,
        "强度分": int(round(sector_score)),
        "上涨率%": round(up_rate, 1),
        "强势数": int(strong_count),
        "放量数": int(vol_count),
        "前排": "、".join([f"{r['名称']}({r['代码']})" for _, r in top3.iterrows()]),
        "成员数": len(tickers),
        "标签": CATALYST_TAGS.get(sector, ""),
    }, df


def run_scan(cfg: ScanConfig, manual: str = "", sectors_override: Optional[Dict[str, List[str]]] = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
    sectors = sectors_override if sectors_override is not None else selected_sectors(cfg.scope)
    # manual added into a synthetic sector, but won't drive sector-first logic too hard
    manual_list = []
    if manual.strip():
        manual_list = [x.strip().upper() for x in manual.replace("\n", ",").split(",") if x.strip()]
        sectors = {**sectors, "手动追加": manual_list}

    sector_rows = []
    all_stock_frames = []
    progress = st.progress(0, text="正在扫描板块强度...")
    total = max(1, len(sectors))
    for i, (sec, ticks) in enumerate(sectors.items(), 1):
        progress.progress(i / total, text=f"正在扫描板块：{sec}")
        srow, sdf = score_sector(sec, ticks, cfg)
        sector_rows.append(srow)
        all_stock_frames.append(sdf)
    progress.empty()
    sector_df = pd.DataFrame(sector_rows).sort_values("强度分", ascending=False).reset_index(drop=True)
    top_secs = sector_df.head(cfg.top_sector_count)["板块"].tolist()

    stock_df = pd.concat(all_stock_frames, ignore_index=True) if all_stock_frames else pd.DataFrame()
    if stock_df.empty:
        return sector_df, stock_df
    stock_df["是否热门板块"] = stock_df["板块"].isin(top_secs)
    # only promote hot-sector names; keep all rows for review
    stock_df["排序"] = stock_df["是否热门板块"].astype(int) * 1000 + stock_df["分数"].fillna(0) + stock_df["涨跌幅%"].fillna(0)
    stock_df = stock_df.sort_values("排序", ascending=False).drop(columns=["排序"]).reset_index(drop=True)
    # de-duplicate tickers by best score
    stock_df = stock_df.sort_values(["代码", "分数"], ascending=[True, False]).drop_duplicates("代码", keep="first")
    stock_df = stock_df.sort_values(["是否热门板块", "分数", "涨跌幅%"], ascending=[False, False, False]).reset_index(drop=True)
    return sector_df, stock_df


def fmt_turnover(v):
    if pd.isna(v):
        return "--"
    v = float(v)
    if v >= 1e9:
        return f"{v/1e9:.1f}亿"
    if v >= 1e8:
        return f"{v/1e8:.1f}亿"
    if v >= 1e6:
        return f"{v/1e6:.1f}百万"
    return f"{v:.0f}"


def render_list(df: pd.DataFrame, max_rows: int = 30):
    if df.empty:
        st.info("没有符合条件的股票。市场不给机会时，空仓是正确动作。")
        return
    html = ['<div class="list-card">']
    for _, r in df.head(max_rows).iterrows():
        chg = r.get("涨跌幅%", np.nan)
        chg_cls = "chg-pos" if pd.notna(chg) and chg >= 0 else "chg-neg"
        raw = r.get("raw_signal", "")
        pill = "pill-buy" if raw in ["BUY"] else "pill-watch" if raw in ["WATCH", "WEAK"] else "pill-limit" if raw == "LIMIT" else "pill-risk"
        sym = str(r.get("代码", "--"))
        logo = sym[:2] if not sym[:2].isdigit() else sym[-2:]
        price = r.get("现价", "--")
        try:
            chg_txt = f"{float(chg):+.2f}%" if pd.notna(chg) else "--"
        except Exception:
            chg_txt = "--"
        html.append(
            f'<div class="row-card">'
            f'<div class="logo-dot">{logo}</div>'
            f'<div>'
            f'<div class="sym">{sym} <span class="signal-pill {pill}">{r.get("信号", "")}</span></div>'
            f'<div class="name">{r.get("名称", "")} · {r.get("板块", "")} · {r.get("标签", "")}</div>'
            f'</div>'
            f'<div class="price"><div>{price}</div><div class="{chg_cls}">{chg_txt}</div></div>'
            f'</div>'
        )
    html.append('</div>')
    st.markdown("".join(html), unsafe_allow_html=True)


def render_sector_cards(sector_df: pd.DataFrame):
    if sector_df.empty:
        st.info("没有板块数据。")
        return
    html = ['<div class="sector-grid">']
    for _, r in sector_df.head(8).iterrows():
        html.append(
            f'<div class="sector-card">'
            f'<div class="sector-name">🔥 {r["板块"]}</div>'
            f'<div class="sector-score">{int(r["强度分"])}</div>'
            f'<div class="muted">上涨率 {r["上涨率%"]}% · 强势 {r["强势数"]} · 放量 {r["放量数"]}</div>'
            f'<div class="muted" style="margin-top:.35rem; font-size:.82rem;">前排：{r["前排"]}</div>'
            f'</div>'
        )
    html.append('</div>')
    st.markdown("".join(html), unsafe_allow_html=True)


def plot_kline(ticker: str, period="6mo"):
    df = fetch_ohlcv(ticker, period=period, interval="1d")
    if df.empty:
        st.warning("该股票K线数据暂时读取失败。")
        return
    md = add_metrics(df)
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=md.index, open=md["Open"], high=md["High"], low=md["Low"], close=md["Close"], name="K线"))
    fig.add_trace(go.Scatter(x=md.index, y=md["MA5"], mode="lines", name="5日均线", line=dict(width=1.4)))
    fig.add_trace(go.Scatter(x=md.index, y=md["MA20"], mode="lines", name="20日均线", line=dict(width=1.4)))
    fig.update_layout(height=430, margin=dict(l=10, r=10, t=20, b=10), xaxis_rangeslider_visible=False, template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)


# =========================
# UI - 控制台
# =========================
with st.sidebar:
    st.markdown("### ① 勾选市场")
    use_us = st.checkbox("美股", value=True)
    use_cn = st.checkbox("A股", value=True)

    st.markdown("### ② 选择板块")
    selected_us_sectors = []
    selected_cn_sectors = []
    if use_us:
        selected_us_sectors = st.multiselect(
            "美股板块",
            list(US_SECTORS.keys()),
            default=["AI/芯片", "大型科技", "加密/金融科技"],
            help="先选你关心的方向，程序会在这些板块里自动找最强板块。",
        )
    if use_cn:
        selected_cn_sectors = st.multiselect(
            "A股板块",
            list(CN_SECTORS.keys()),
            default=["A股AI/算力", "A股芯片/半导体", "A股高成交核心"],
            help="A股短线优先看题材强度、涨停/大阳、放量和成交额。",
        )

    # 由市场+板块生成候选池
    sectors_to_scan: Dict[str, List[str]] = {}
    for sec in selected_us_sectors:
        sectors_to_scan[sec] = US_SECTORS[sec]
    for sec in selected_cn_sectors:
        sectors_to_scan[sec] = CN_SECTORS[sec]

    st.markdown("### ③ 可选：指定股票")
    stock_option_map: Dict[str, str] = {}
    for sec, ticks in sectors_to_scan.items():
        for t in ticks:
            b = base_symbol(t)
            label = f"{b} · {display_name(t)} · {sec}"
            stock_option_map[label] = b
    picked_labels = st.multiselect(
        "股票池里勾选股票（可空）",
        list(stock_option_map.keys()),
        default=[],
        help="不选则扫描所选板块全部候选股；选了股票后，可选择只扫描这些股票。",
    )
    only_picked = st.checkbox("只扫描我勾选的股票", value=False, help="开启后，程序不会扫描整个板块，只看你勾选的股票。")

    if only_picked and picked_labels:
        picked_codes = {stock_option_map[x] for x in picked_labels}
        filtered: Dict[str, List[str]] = {}
        for sec, ticks in sectors_to_scan.items():
            keep = [t for t in ticks if base_symbol(t) in picked_codes]
            if keep:
                filtered[sec] = keep
        sectors_to_scan = filtered

    st.markdown("### ④ 输出目标")
    top_sector_count = st.slider("自动选择最强板块数", 2, 8, 5)
    target_buy = st.slider("买入观察最多显示", 3, 15, 10)
    target_watch = st.slider("观察名单最多显示", 5, 30, 20)

    st.markdown("### 🧹 过滤条件")
    min_us = st.number_input("美股最低成交额/美元", min_value=1_000_000, max_value=500_000_000, value=20_000_000, step=5_000_000)
    min_cn = st.number_input("A股最低成交额/人民币", min_value=10_000_000, max_value=2_000_000_000, value=200_000_000, step=50_000_000)
    manual = st.text_area("手动追加代码（可空）", placeholder="例如：SPCX, NVDA, 600519, 300750", height=76)

    st.markdown("---")
    selected_market_text = " + ".join((["美股"] if use_us else []) + (["A股"] if use_cn else [])) or "未选择"
    st.caption(f"当前市场：{selected_market_text}｜板块数：{len(sectors_to_scan)}｜候选股约：{sum(len(v) for v in sectors_to_scan.values())}只")
    st.caption("龙虎榜、实时盘前榜、新闻催化需要专业数据源。本版本先用行情强度做漏斗筛选。")

scope_label = "美股+A股" if use_us and use_cn else "美股" if use_us else "A股" if use_cn else "未选择"
cfg = ScanConfig(scope=scope_label, top_sector_count=top_sector_count, target_buy=target_buy, target_watch=target_watch, min_us_dollar_vol=float(min_us), min_cn_turnover=float(min_cn))

st.markdown('''
<div class="tv-topbar">
  <div class="tv-title">短线情绪板块选股器</div>
  <div class="tv-subtitle">勾选市场 → 选择板块 → 可选股票 → 先板块后个股自动筛选</div>
</div>
''', unsafe_allow_html=True)

col_a, col_b = st.columns([1, 1])
with col_a:
    run_btn = st.button("开始扫描：市场→板块→股票", type="primary", use_container_width=True)
with col_b:
    clear_btn = st.button("清除本次结果", use_container_width=True)
if clear_btn:
    st.session_state.pop("sector_df", None)
    st.session_state.pop("stock_df", None)

if run_btn or ("sector_df" not in st.session_state):
    if run_btn:
        with st.spinner("正在执行：市场选择 → 板块强度扫描 → 热门板块建池 → 个股漏斗筛选..."):
            if not sectors_to_scan and not manual.strip():
                st.warning("请至少勾选一个市场和一个板块，或者在手动追加里输入股票代码。")
                sector_df, stock_df = pd.DataFrame(), pd.DataFrame()
            else:
                sector_df, stock_df = run_scan(cfg, manual=manual, sectors_override=sectors_to_scan)
            st.session_state["sector_df"] = sector_df
            st.session_state["stock_df"] = stock_df
    else:
        st.info("先在左侧勾选美股/A股，再选择板块；不懂就保持默认，然后点击上方按钮开始扫描。")

sector_df = st.session_state.get("sector_df", pd.DataFrame())
stock_df = st.session_state.get("stock_df", pd.DataFrame())

# KPI
if not stock_df.empty:
    hot_count = int(stock_df["是否热门板块"].sum())
    buy_df = stock_df[(stock_df["是否热门板块"]) & (stock_df["raw_signal"].isin(["BUY", "LIMIT"]))].head(target_buy)
    watch_df = stock_df[(stock_df["是否热门板块"]) & (stock_df["raw_signal"].isin(["WATCH", "WEAK"]))].head(target_watch)
    mood_score = int(sector_df["强度分"].head(3).mean()) if not sector_df.empty else 0
    mood = "强" if mood_score >= 75 else "中" if mood_score >= 58 else "弱"
else:
    hot_count = 0; buy_df = pd.DataFrame(); watch_df = pd.DataFrame(); mood_score=0; mood="等待扫描"

st.markdown(f'''
<div class="kpi-grid">
  <div class="kpi-card"><div class="kpi-label">短线温度</div><div class="kpi-value">{mood}</div><div class="kpi-note">板块均分 {mood_score}</div></div>
  <div class="kpi-card"><div class="kpi-label">热门板块股票</div><div class="kpi-value">{hot_count}</div><div class="kpi-note">只在强板块里找前排</div></div>
  <div class="kpi-card"><div class="kpi-label">买入观察</div><div class="kpi-value">{len(buy_df)}</div><div class="kpi-note">不是下单命令</div></div>
  <div class="kpi-card"><div class="kpi-label">观察名单</div><div class="kpi-value">{len(watch_df)}</div><div class="kpi-note">等待确认</div></div>
</div>
''', unsafe_allow_html=True)

if not sector_df.empty and mood == "弱":
    st.markdown('<div class="warning-box">今天板块情绪偏弱，程序不会硬凑买点。没有买入观察时，最好的交易就是不交易。</div>', unsafe_allow_html=True)
elif not sector_df.empty:
    st.markdown('<div class="good-box">已按“先板块、后龙头”的漏斗逻辑完成扫描。先看最强板块，再看买入观察。</div>', unsafe_allow_html=True)

# Tabs
tabs = st.tabs(["🔥 最强板块", "🎯 买入观察", "👀 观察名单", "📊 个股详情", "🧹 过滤原因", "📋 全部数据"])

with tabs[0]:
    st.subheader("最强板块排行榜")
    render_sector_cards(sector_df)
    if not sector_df.empty:
        st.dataframe(sector_df, use_container_width=True, hide_index=True)

with tabs[1]:
    st.subheader("买入观察名单")
    st.caption("只展示热门板块里的前排。这里依然只是观察，不是让你直接买。")
    render_list(buy_df, target_buy)
    if not buy_df.empty:
        show = buy_df[["代码","名称","市场","板块","信号","分数","现价","涨跌幅%","量比","成交额","标签","原因"]].copy()
        show["成交额"] = show["成交额"].apply(fmt_turnover)
        st.dataframe(show, use_container_width=True, hide_index=True)

with tabs[2]:
    st.subheader("观察名单")
    render_list(watch_df, target_watch)
    if not watch_df.empty:
        show = watch_df[["代码","名称","市场","板块","信号","分数","现价","涨跌幅%","量比","成交额","标签","原因"]].copy()
        show["成交额"] = show["成交额"].apply(fmt_turnover)
        st.dataframe(show, use_container_width=True, hide_index=True)

with tabs[3]:
    st.subheader("个股详情与K线")
    if stock_df.empty:
        st.info("先扫描，再查看个股详情。")
    else:
        option_df = stock_df.copy()
        option_df["选择"] = option_df["代码"] + " · " + option_df["名称"] + " · " + option_df["信号"]
        pick = st.selectbox("选择股票", option_df["选择"].tolist())
        row = option_df[option_df["选择"] == pick].iloc[0]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("现价", row["现价"])
        c2.metric("涨跌幅", f"{row['涨跌幅%']:+.2f}%")
        c3.metric("量比", row["量比"])
        c4.metric("信号", row["信号"])
        st.markdown(
            f'<div class="reason-box"><b>{row["名称"]}（{row["代码"]}）</b><br>'
            f'市场：{row["市场"]}　板块：{row["板块"]}　标签：{row["标签"]}<br>'
            f'判断原因：{row["原因"]}<br>'
            f'风险提示：买入观察不是买入命令，必须结合盘中承接、止损位和仓位控制。</div>',
            unsafe_allow_html=True,
        )
        plot_kline(row["代码"])

with tabs[4]:
    st.subheader("过滤原因")
    if stock_df.empty:
        st.info("先扫描。")
    else:
        filtered = stock_df[~stock_df["raw_signal"].isin(["BUY", "LIMIT", "WATCH", "WEAK"])]
        if filtered.empty:
            st.success("本次没有明显过滤项。")
        else:
            show = filtered[["代码","名称","市场","板块","信号","分数","涨跌幅%","量比","成交额","原因"]].copy()
            show["成交额"] = show["成交额"].apply(fmt_turnover)
            st.dataframe(show, use_container_width=True, hide_index=True)

with tabs[5]:
    st.subheader("全部扫描结果")
    if stock_df.empty:
        st.info("暂无数据。")
    else:
        show = stock_df[["代码","名称","市场","板块","是否热门板块","信号","分数","现价","涨跌幅%","5日涨幅%","量比","成交额","标签","原因"]].copy()
        show["成交额"] = show["成交额"].apply(fmt_turnover)
        st.dataframe(show, use_container_width=True, hide_index=True)
        st.download_button("下载全部结果CSV", show.to_csv(index=False).encode("utf-8-sig"), file_name="短线选股结果.csv", mime="text/csv")

# 底部说明
st.caption("数据说明：本工具使用可用公开行情源，非交易所实时专业行情。A股涨停/炸板率、龙虎榜席位、实时盘前榜和新闻催化需要接入专业数据源后才能做成准实时版本。")
