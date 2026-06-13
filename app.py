from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf


# -----------------------------
# Page
# -----------------------------
st.set_page_config(
    page_title="消闲派板块优先选股器",
    page_icon="🧭",
    layout="wide",
)

st.markdown(
    """
    <style>
    :root{
      --bg0:#05070d;
      --bg1:#0b1020;
      --glass:rgba(255,255,255,.075);
      --glass-strong:rgba(255,255,255,.12);
      --line:rgba(255,255,255,.14);
      --text:#f8fafc;
      --muted:#94a3b8;
      --blue:#0A84FF;
      --green:#30D158;
      --orange:#FF9F0A;
      --red:#FF453A;
      --purple:#BF5AF2;
    }
    .stApp{
      background:
        radial-gradient(900px 480px at 8% -10%, rgba(10,132,255,.28), transparent 60%),
        radial-gradient(800px 520px at 95% 5%, rgba(191,90,242,.18), transparent 62%),
        linear-gradient(180deg, #05070d 0%, #0b1020 46%, #090b12 100%);
      color:var(--text);
    }
    .block-container{padding-top:.9rem; padding-bottom:2rem; max-width:1180px;}
    header[data-testid="stHeader"]{background:rgba(5,7,13,.55); backdrop-filter:blur(18px);}
    footer{visibility:hidden;}
    #MainMenu{visibility:hidden;}

    .apple-hero{
      position:relative;
      overflow:hidden;
      border:1px solid var(--line);
      border-radius:30px;
      padding:28px 28px 24px;
      background:
        linear-gradient(135deg, rgba(255,255,255,.13), rgba(255,255,255,.04)),
        radial-gradient(520px 260px at 85% 15%, rgba(10,132,255,.35), transparent 70%),
        radial-gradient(420px 240px at 20% 0%, rgba(48,209,88,.16), transparent 70%);
      box-shadow:0 24px 80px rgba(0,0,0,.38);
      backdrop-filter: blur(24px);
      margin-bottom:18px;
    }
    .hero-kicker{font-size:.86rem; color:#b8c1d6; letter-spacing:.08em; text-transform:uppercase; margin-bottom:10px;}
    .hero-title{font-size:2.25rem; line-height:1.08; font-weight:850; letter-spacing:-.035em; margin:0 0 12px;}
    .hero-sub{font-size:1.02rem; color:#cbd5e1; line-height:1.75; max-width:780px;}
    .hero-pills{display:flex; flex-wrap:wrap; gap:10px; margin-top:18px;}
    .pill{
      display:inline-flex; align-items:center; gap:6px;
      padding:8px 12px; border-radius:999px;
      color:#eaf2ff; background:rgba(255,255,255,.08);
      border:1px solid rgba(255,255,255,.14);
      font-size:.86rem; backdrop-filter:blur(18px);
    }
    .mini-card{
      border:1px solid var(--line);
      border-radius:22px;
      background:linear-gradient(180deg, rgba(255,255,255,.105), rgba(255,255,255,.045));
      padding:18px 18px 16px;
      box-shadow:0 16px 42px rgba(0,0,0,.25);
      min-height:112px;
      backdrop-filter:blur(22px);
    }
    .mini-label{font-size:.82rem; color:#9fb0c6; margin-bottom:7px;}
    .mini-value{font-size:1.75rem; font-weight:850; letter-spacing:-.02em;}
    .mini-note{font-size:.82rem; color:#9aa7bd; margin-top:8px; line-height:1.45;}
    .section-title{font-size:1.25rem; font-weight:800; letter-spacing:-.02em; margin:22px 0 10px;}
    .section-caption{color:#94a3b8; font-size:.92rem; line-height:1.6; margin-top:-4px; margin-bottom:12px;}
    .glass-panel{
      border:1px solid var(--line);
      border-radius:26px;
      background:rgba(255,255,255,.065);
      box-shadow:0 18px 60px rgba(0,0,0,.30);
      padding:18px;
      backdrop-filter:blur(24px);
      margin:14px 0;
    }
    .rank-card{
      border:1px solid rgba(255,255,255,.12);
      border-radius:22px;
      background:rgba(255,255,255,.07);
      padding:16px;
      min-height:130px;
    }
    .rank-num{font-size:.82rem; color:#8ea0bd; margin-bottom:8px;}
    .rank-name{font-size:1.35rem; font-weight:840; letter-spacing:-.02em;}
    .rank-score{font-size:2rem; font-weight:900; color:#0A84FF; margin-top:8px;}
    .rank-note{font-size:.84rem; color:#a8b3c7; margin-top:8px; line-height:1.45;}
    .signal-buy{color:#30D158; font-weight:800;}
    .signal-watch{color:#FF9F0A; font-weight:800;}
    .signal-risk{color:#FF453A; font-weight:800;}
    .small-note{color:#9fb0c6;font-size:.92rem;line-height:1.65;}

    div[data-testid="stSidebar"] > div:first-child{
      background:rgba(10,14,24,.82);
      backdrop-filter: blur(26px);
      border-right:1px solid rgba(255,255,255,.10);
    }
    div[data-testid="stMetric"]{
      border:1px solid rgba(255,255,255,.13);
      background:linear-gradient(180deg, rgba(255,255,255,.10), rgba(255,255,255,.045));
      padding:14px 16px; border-radius:22px;
      box-shadow:0 12px 36px rgba(0,0,0,.22);
    }
    div[data-testid="stMetricLabel"]{color:#aab6cb;}
    div[data-testid="stMetricValue"]{font-weight:850; letter-spacing:-.03em;}
    .stButton > button{
      width:100%;
      border:0;
      border-radius:18px;
      padding:.82rem 1rem;
      font-weight:800;
      letter-spacing:.01em;
      background:linear-gradient(135deg, #0A84FF, #5E5CE6) !important;
      color:white !important;
      box-shadow:0 16px 40px rgba(10,132,255,.32);
      transition:transform .18s ease, box-shadow .18s ease, filter .18s ease;
    }
    .stButton > button:hover{transform:translateY(-1px); filter:brightness(1.07); box-shadow:0 18px 46px rgba(10,132,255,.42);}
    div[data-testid="stDataFrame"]{
      border-radius:22px !important;
      overflow:hidden;
      border:1px solid rgba(255,255,255,.12);
      box-shadow:0 16px 48px rgba(0,0,0,.26);
    }
    .stTabs [data-baseweb="tab-list"]{gap:8px; background:rgba(255,255,255,.055); border-radius:18px; padding:6px; border:1px solid rgba(255,255,255,.10);}
    .stTabs [data-baseweb="tab"]{border-radius:14px; padding:9px 14px; font-weight:700; color:#cbd5e1;}
    .stTabs [aria-selected="true"]{background:rgba(255,255,255,.13); color:#fff;}
    .stAlert{border-radius:20px; border:1px solid rgba(255,255,255,.12);}
    @media (max-width: 700px){
      .block-container{padding-left:.65rem; padding-right:.65rem;}
      .apple-hero{border-radius:24px; padding:22px 18px 20px;}
      .hero-title{font-size:1.55rem;}
      .hero-sub{font-size:.92rem;}
      .pill{font-size:.78rem; padding:7px 10px;}
      .mini-card{border-radius:20px; padding:14px; min-height:94px;}
      .mini-value{font-size:1.35rem;}
      .rank-card{min-height:108px;}
      .rank-name{font-size:1.05rem;}
      .rank-score{font-size:1.45rem;}
      h1{font-size:1.4rem !important;}
      h2,h3{font-size:1.08rem !important;}
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# -----------------------------
# Pools and tags
# -----------------------------
US_POOLS: Dict[str, List[str]] = {
    "AI/芯片": [
        "NVDA", "AMD", "AVGO", "ARM", "MU", "SMCI", "TSM", "ASML", "QCOM", "MRVL",
        "INTC", "ON", "AMAT", "LRCX", "KLAC", "SMH", "SOXX", "SOXL",
    ],
    "大型科技": [
        "MSFT", "AAPL", "META", "AMZN", "GOOGL", "GOOG", "NFLX", "CRM", "ORCL", "ADBE", "NOW", "SHOP",
    ],
    "高波动成长": [
        "TSLA", "PLTR", "APP", "UBER", "ABNB", "RBLX", "ROKU", "SNOW", "DDOG", "CRWD", "NET", "OKTA", "ZS",
    ],
    "加密/金融科技": [
        "MSTR", "COIN", "HOOD", "RIOT", "MARA", "CLSK", "IREN", "HUT", "IBIT", "ETHE", "SQ", "PYPL",
    ],
    "杠杆ETF": [
        "TQQQ", "SQQQ", "SOXL", "SOXS", "UPRO", "SPXL", "SPXS", "TECL", "TECS", "TNA", "LABU",
    ],
    "新股/高波动关注": [
        "SPCX", "CRCL", "RDDT", "ARM", "CAVA", "BIRK", "KVUE", "IOT", "SOUN", "BBAI",
    ],
}

CN_POOLS_RAW: Dict[str, List[str]] = {
    "A股AI/算力": [
        "002230", "000977", "002415", "300308", "603019", "600570", "688256", "688041", "300502", "300033",
    ],
    "A股芯片/半导体": [
        "688981", "603501", "002371", "300223", "688008", "688012", "600584", "002156", "600460", "002049", "300782",
    ],
    "A股新能源/汽车": [
        "300750", "002594", "601012", "002812", "300274", "002466", "600438", "300014", "002459", "601127",
    ],
    "A股高成交核心": [
        "600519", "000858", "601899", "600030", "601318", "600036", "601166", "601398", "000001", "300760", "000651",
    ],
    "A股军工/机器人/高端制造": [
        "002179", "600150", "600760", "000768", "300124", "002050", "300024", "002475", "300450", "002236",
    ],
}


def cn_to_yahoo(code: str) -> str:
    s = str(code).strip().upper()
    if not s:
        return ""
    if s.endswith(".SS") or s.endswith(".SZ"):
        return s
    if not s.isdigit():
        return s
    if s.startswith(("6", "9", "688")):
        return f"{s}.SS"
    return f"{s}.SZ"


def yahoo_to_display(ticker: str) -> str:
    return ticker.replace(".SS", "").replace(".SZ", "")


# Build tags
TAG_MAP: Dict[str, List[str]] = {}
for pool_name, tickers in US_POOLS.items():
    for t in tickers:
        TAG_MAP.setdefault(t, []).append(pool_name.replace("A股", ""))
for pool_name, codes in CN_POOLS_RAW.items():
    for c in codes:
        TAG_MAP.setdefault(cn_to_yahoo(c), []).append(pool_name)

for t in ["TQQQ", "SQQQ", "SOXL", "SOXS", "UPRO", "SPXL", "SPXS", "TECL", "TECS", "TNA", "LABU"]:
    TAG_MAP.setdefault(t, []).append("杠杆ETF")
for t in ["MSTR", "COIN", "HOOD", "RIOT", "MARA", "CLSK", "IREN", "HUT", "IBIT", "ETHE"]:
    TAG_MAP.setdefault(t, []).append("加密/金融科技")
for t in ["SPCX", "CRCL", "RDDT", "ARM", "CAVA", "BIRK"]:
    TAG_MAP.setdefault(t, []).append("新股/高波动")


# -----------------------------
# Params and data
# -----------------------------
@dataclass
class ScanParams:
    market: str
    period: str
    interval: str
    short_ma: int
    long_ma: int
    vol_window: int
    min_gain_pct: float
    vol_ratio_min: float
    min_turnover_m: float
    max_scan: int
    target_buy: int
    target_watch: int
    include_filtered: bool


@st.cache_data(show_spinner=False, ttl=60 * 20)
def yf_batch_download(tickers_tuple: Tuple[str, ...], period: str, interval: str) -> pd.DataFrame:
    tickers = list(tickers_tuple)
    if not tickers:
        return pd.DataFrame()
    try:
        return yf.download(
            tickers=tickers,
            period=period,
            interval=interval,
            group_by="ticker",
            auto_adjust=True,
            progress=False,
            threads=True,
        )
    except Exception:
        return pd.DataFrame()


@st.cache_data(show_spinner=False, ttl=60 * 20)
def yf_single_download(ticker: str, period: str, interval: str) -> pd.DataFrame:
    try:
        return yf.download(
            ticker,
            period=period,
            interval=interval,
            auto_adjust=True,
            progress=False,
            threads=False,
        )
    except Exception:
        return pd.DataFrame()


def get_ticker_frame(batch: pd.DataFrame, ticker: str, period: str, interval: str) -> pd.DataFrame:
    def normalize(df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame()
        out = df.copy()
        if isinstance(out.columns, pd.MultiIndex):
            # Try both common yfinance shapes.
            upper = ticker.upper()
            for level in range(out.columns.nlevels):
                values = [str(v).upper() for v in out.columns.get_level_values(level)]
                if upper in values:
                    try:
                        out = out.xs(ticker, level=level, axis=1, drop_level=True)
                    except Exception:
                        try:
                            out = out.xs(upper, level=level, axis=1, drop_level=True)
                        except Exception:
                            pass
                    break
        out = out.rename(columns={c: str(c).title() for c in out.columns})
        need = ["Open", "High", "Low", "Close", "Volume"]
        if any(c not in out.columns for c in need):
            return pd.DataFrame()
        out = out[need].dropna()
        out.index = pd.to_datetime(out.index)
        return out

    if batch is not None and not batch.empty:
        if isinstance(batch.columns, pd.MultiIndex):
            for level in range(batch.columns.nlevels):
                values = [str(v).upper() for v in batch.columns.get_level_values(level)]
                if ticker.upper() in values:
                    try:
                        return normalize(batch.xs(ticker, axis=1, level=level, drop_level=True))
                    except Exception:
                        pass
        else:
            one = normalize(batch)
            if not one.empty and len(tickers_from_text(ticker)) == 1:
                return one

    return normalize(yf_single_download(ticker, period, interval))


def add_indicators(df: pd.DataFrame, p: ScanParams) -> pd.DataFrame:
    out = df.copy()
    out["MA5"] = out["Close"].rolling(p.short_ma).mean()
    out["MA20"] = out["Close"].rolling(p.long_ma).mean()
    out["VOL_MA"] = out["Volume"].rolling(p.vol_window).mean()
    out["RET_1D_%"] = out["Close"].pct_change() * 100
    out["RET_5D_%"] = out["Close"].pct_change(5) * 100
    out["VOL_RATIO"] = out["Volume"] / out["VOL_MA"]
    out["HIGH20"] = out["Close"].rolling(20).max()
    out["NEAR_HIGH20"] = out["Close"] / out["HIGH20"]
    out["TURNOVER_M"] = out["Close"] * out["Volume"] / 1_000_000
    return out


def chinese_signal(raw: str) -> str:
    return {
        "LIMIT_WATCH": "涨停观察",
        "BUY_WATCH": "买入观察",
        "WATCH": "观察",
        "FILTER_LOW_LIQ": "低成交过滤",
        "NO_TRADE": "暂不交易",
        "NO_DATA": "无数据",
        "EXIT_RISK": "风险退出",
        "FILTERED": "已过滤",
    }.get(raw, raw)


def classify(ticker: str, last: pd.Series, p: ScanParams) -> Tuple[str, int, str]:
    ret1 = float(last.get("RET_1D_%", np.nan))
    ret5 = float(last.get("RET_5D_%", np.nan))
    volr = float(last.get("VOL_RATIO", np.nan))
    close = float(last.get("Close", np.nan))
    ma5 = float(last.get("MA5", np.nan))
    ma20 = float(last.get("MA20", np.nan))
    turnover_m = float(last.get("TURNOVER_M", 0.0))
    near_high = float(last.get("NEAR_HIGH20", np.nan))

    if np.isnan(close) or np.isnan(ma20) or np.isnan(volr):
        return "NO_DATA", 0, "数据不足"

    if turnover_m < p.min_turnover_m:
        return "FILTER_LOW_LIQ", 0, f"成交额偏低：{turnover_m:.1f}M"

    trend_ok = close > ma20 and ma5 > ma20
    momentum_ok = ret1 >= p.min_gain_pct
    volume_ok = volr >= p.vol_ratio_min
    near_high_ok = near_high >= 0.97
    ret5_ok = ret5 > 0

    score = 0
    score += 30 if trend_ok else 0
    score += 25 if momentum_ok else 0
    score += 20 if volume_ok else 0
    score += 15 if near_high_ok else 0
    score += 10 if ret5_ok else 0

    reasons = []
    reasons.append("趋势向上" if trend_ok else "趋势不足")
    reasons.append("当日强" if momentum_ok else "当日涨幅不足")
    reasons.append("放量" if volume_ok else "量能不足")
    reasons.append("接近20日高点" if near_high_ok else "未接近高点")
    reasons.append("5日动量正" if ret5_ok else "5日动量弱")

    # A-share near-limit / strong move observation. This is a rough filter, not real limit-up board data.
    if ticker.endswith((".SS", ".SZ")) and ret1 >= 8.5 and volume_ok and trend_ok:
        return "LIMIT_WATCH", min(100, score + 5), " / ".join(reasons)

    if score >= 80 and trend_ok and momentum_ok and volume_ok:
        return "BUY_WATCH", score, " / ".join(reasons)
    if score >= 55 and (trend_ok or volume_ok):
        return "WATCH", score, " / ".join(reasons)
    return "FILTERED", score, " / ".join(reasons)


def tickers_from_text(raw: str) -> List[str]:
    out = []
    for x in str(raw).replace("\n", ",").split(","):
        s = x.strip().upper()
        if s and s not in out:
            out.append(s)
    return out


def unique(seq: Iterable[str]) -> List[str]:
    out = []
    for x in seq:
        if x and x not in out:
            out.append(x)
    return out


def build_scan_universe(mode: str, selected_us_pools: List[str], selected_cn_pools: List[str], manual: str) -> List[str]:
    symbols: List[str] = []
    if mode in ["美股热门池", "美股+A股热门池"]:
        for name in selected_us_pools:
            symbols.extend(US_POOLS.get(name, []))
    if mode in ["A股热门池", "美股+A股热门池"]:
        for name in selected_cn_pools:
            symbols.extend([cn_to_yahoo(c) for c in CN_POOLS_RAW.get(name, [])])
    if mode == "手动输入" or manual.strip():
        manual_tickers = tickers_from_text(manual)
        for t in manual_tickers:
            symbols.append(cn_to_yahoo(t) if t.isdigit() else t)
    return unique(symbols)




def build_sector_defs(mode: str, selected_us_pools: List[str], selected_cn_pools: List[str]) -> Dict[str, List[str]]:
    """Return selected sector pools in Yahoo ticker format."""
    out: Dict[str, List[str]] = {}
    if mode in ["美股热门池", "美股+A股热门池"]:
        for name in selected_us_pools:
            out[name] = unique(US_POOLS.get(name, []))
    if mode in ["A股热门池", "美股+A股热门池"]:
        for name in selected_cn_pools:
            out[name] = unique([cn_to_yahoo(c) for c in CN_POOLS_RAW.get(name, [])])
    return out


def rank_strong_sectors(sector_defs: Dict[str, List[str]], p: ScanParams) -> Tuple[pd.DataFrame, Dict[str, List[str]]]:
    """消闲派式板块强度：先看联动，再看放量，再看龙头。"""
    rows: List[dict] = []
    leader_map: Dict[str, List[str]] = {}

    for sector, tickers in sector_defs.items():
        tickers = unique(tickers)
        if not tickers:
            continue
        batch = yf_batch_download(tuple(tickers), p.period, p.interval)
        stock_rows = []
        for ticker in tickers:
            df = get_ticker_frame(batch, ticker, p.period, p.interval)
            if df.empty or len(df) < max(p.long_ma, p.vol_window) + 5:
                continue
            ind = add_indicators(df, p).dropna()
            if ind.empty:
                continue
            last = ind.iloc[-1]
            try:
                ret1 = float(last["RET_1D_%"])
                ret5 = float(last["RET_5D_%"])
                volr = float(last["VOL_RATIO"])
                close = float(last["Close"])
                ma5 = float(last["MA5"])
                ma20 = float(last["MA20"])
                near_high = float(last["NEAR_HIGH20"])
                turnover_m = float(last["TURNOVER_M"])
            except Exception:
                continue
            if np.isnan(ret1) or np.isnan(volr) or np.isnan(close) or np.isnan(ma20):
                continue
            trend_ok = close > ma20 and ma5 > ma20
            strong_ok = trend_ok and ret1 >= p.min_gain_pct and volr >= p.vol_ratio_min
            volume_ok = volr >= p.vol_ratio_min
            near_high_ok = near_high >= 0.97
            limit_like = ret1 >= 8.5 if ticker.endswith((".SS", ".SZ")) else ret1 >= 6.0
            stock_score = 0
            stock_score += 35 if strong_ok else 0
            stock_score += 25 if volume_ok else 0
            stock_score += 20 if near_high_ok else 0
            stock_score += max(0, min(ret1, 12)) * 2
            stock_score += max(0, min(ret5, 20)) * 0.8
            stock_score += min(max(turnover_m / max(p.min_turnover_m, 1), 0), 5) * 3
            stock_rows.append({
                "ticker": ticker,
                "display": yahoo_to_display(ticker),
                "ret1": ret1,
                "ret5": ret5,
                "volr": volr,
                "turnover_m": turnover_m,
                "trend_ok": trend_ok,
                "strong_ok": strong_ok,
                "volume_ok": volume_ok,
                "near_high_ok": near_high_ok,
                "limit_like": limit_like,
                "stock_score": stock_score,
            })

        n = len(stock_rows)
        if n == 0:
            rows.append({
                "板块": sector, "强度分": 0, "有效股票数": 0, "上涨率%": 0,
                "强势股数": 0, "放量股数": 0, "近高股数": 0, "涨停/大阳数": 0,
                "平均涨幅%": None, "TOP3涨幅%": None, "龙头候选": "无数据", "龙头涨幅%": None,
                "龙头放量": None, "板块结论": "无数据",
            })
            leader_map[sector] = []
            continue

        rets = [r["ret1"] for r in stock_rows]
        up_count = sum(1 for r in stock_rows if r["ret1"] > 0)
        strong_count = sum(1 for r in stock_rows if r["strong_ok"])
        vol_count = sum(1 for r in stock_rows if r["volume_ok"])
        high_count = sum(1 for r in stock_rows if r["near_high_ok"])
        limit_count = sum(1 for r in stock_rows if r["limit_like"])
        avg_ret = float(np.mean(rets))
        top3_ret = float(np.mean(sorted(rets, reverse=True)[: min(3, n)]))

        up_rate = up_count / n
        strong_rate = strong_count / n
        vol_rate = vol_count / n
        high_rate = high_count / n
        limit_rate = limit_count / n
        raw_score = (
            25 * up_rate
            + 30 * strong_rate
            + 20 * vol_rate
            + 15 * high_rate
            + 15 * limit_rate
            + max(0, min(top3_ret, 12)) * 1.8
            + max(0, min(avg_ret, 8)) * 1.2
        )
        score = round(min(100, raw_score), 1)

        ranked_stocks = sorted(stock_rows, key=lambda x: (x["strong_ok"], x["stock_score"], x["ret1"], x["volr"]), reverse=True)
        leaders = ranked_stocks[:5]
        leader_map[sector] = [x["ticker"] for x in ranked_stocks]
        leader_text = ", ".join([f"{x['display']}({x['ret1']:.1f}%)" for x in leaders[:3]])
        top = leaders[0]

        if score >= 65 and strong_count >= 2:
            verdict = "强板块：优先找龙头"
        elif score >= 45 and (strong_count >= 1 or vol_count >= 2):
            verdict = "可观察：等确认"
        else:
            verdict = "弱板块：先过滤"

        rows.append({
            "板块": sector,
            "强度分": score,
            "有效股票数": n,
            "上涨率%": round(up_rate * 100, 1),
            "强势股数": strong_count,
            "放量股数": vol_count,
            "近高股数": high_count,
            "涨停/大阳数": limit_count,
            "平均涨幅%": round(avg_ret, 2),
            "TOP3涨幅%": round(top3_ret, 2),
            "龙头候选": leader_text,
            "龙头涨幅%": round(top["ret1"], 2),
            "龙头放量": round(top["volr"], 2),
            "板块结论": verdict,
        })

    sector_df = pd.DataFrame(rows)
    if not sector_df.empty:
        sector_df = sector_df.sort_values(["强度分", "强势股数", "TOP3涨幅%"], ascending=[False, False, False]).reset_index(drop=True)
    return sector_df, leader_map


def build_sector_ordered_universe(sector_df: pd.DataFrame, leader_map: Dict[str, List[str]], sector_defs: Dict[str, List[str]], top_sector_limit: int, manual: str) -> List[str]:
    """先扫最强板块的龙头，再扫同板块其余票，最后才扫弱板块。"""
    ordered: List[str] = []
    if sector_df is not None and not sector_df.empty:
        strong_sectors = list(sector_df.head(int(top_sector_limit))["板块"])
        remaining_sectors = [s for s in list(sector_df["板块"]) if s not in strong_sectors]
        for sector in strong_sectors + remaining_sectors:
            ordered.extend(leader_map.get(sector, []))
            ordered.extend(sector_defs.get(sector, []))
    else:
        for symbols in sector_defs.values():
            ordered.extend(symbols)

    if manual.strip():
        for t in tickers_from_text(manual):
            ordered.append(cn_to_yahoo(t) if t.isdigit() else t)
    return unique(ordered)

def scan_universe(symbols: List[str], p: ScanParams) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, List[str]]:
    scanned_rows = []
    buy_rows = []
    watch_rows = []
    filtered_rows = []
    rounds_log = []

    symbols = unique(symbols)[: p.max_scan]
    batch_size = 25

    for start in range(0, len(symbols), batch_size):
        chunk = symbols[start : start + batch_size]
        rounds_log.append(f"第 {start // batch_size + 1} 轮：扫描 {len(chunk)} 只，累计已找到 买入观察 {len(buy_rows)} / {p.target_buy}，观察 {len(watch_rows)} / {p.target_watch}")

        batch = yf_batch_download(tuple(chunk), p.period, p.interval)
        for ticker in chunk:
            df = get_ticker_frame(batch, ticker, p.period, p.interval)
            if df.empty or len(df) < max(p.long_ma, p.vol_window) + 5:
                row = {
                    "代码": yahoo_to_display(ticker),
                    "信号": "无数据",
                    "评分": 0,
                    "收盘价": None,
                    "当日涨幅%": None,
                    "5日涨幅%": None,
                    "放量倍数": None,
                    "成交额M": None,
                    "标签": " / ".join(TAG_MAP.get(ticker, [])),
                    "原因": "数据不足或数据源暂不可用",
                }
                filtered_rows.append(row)
                scanned_rows.append(row)
                continue

            ind = add_indicators(df, p).dropna()
            if ind.empty:
                row = {
                    "代码": yahoo_to_display(ticker),
                    "信号": "无数据",
                    "评分": 0,
                    "收盘价": None,
                    "当日涨幅%": None,
                    "5日涨幅%": None,
                    "放量倍数": None,
                    "成交额M": None,
                    "标签": " / ".join(TAG_MAP.get(ticker, [])),
                    "原因": "指标计算数据不足",
                }
                filtered_rows.append(row)
                scanned_rows.append(row)
                continue

            last = ind.iloc[-1]
            raw_signal, score, reason = classify(ticker, last, p)
            signal_cn = chinese_signal(raw_signal)
            row = {
                "代码": yahoo_to_display(ticker),
                "信号": signal_cn,
                "评分": int(score),
                "收盘价": round(float(last["Close"]), 2),
                "当日涨幅%": round(float(last["RET_1D_%"]), 2),
                "5日涨幅%": round(float(last["RET_5D_%"]), 2),
                "放量倍数": round(float(last["VOL_RATIO"]), 2),
                "成交额M": round(float(last["TURNOVER_M"]), 1),
                "标签": " / ".join(unique(TAG_MAP.get(ticker, []))),
                "原因": reason,
            }
            scanned_rows.append(row)
            if raw_signal in ["BUY_WATCH", "LIMIT_WATCH"]:
                buy_rows.append(row)
            elif raw_signal == "WATCH":
                watch_rows.append(row)
            else:
                filtered_rows.append(row)

        if len(buy_rows) >= p.target_buy and len(watch_rows) >= p.target_watch:
            rounds_log.append("目标已达到：停止继续扫描，避免无意义扩大范围。")
            break

    def sort_df(rows: List[dict]) -> pd.DataFrame:
        df = pd.DataFrame(rows)
        if df.empty:
            return df
        order = {"涨停观察": 0, "买入观察": 1, "观察": 2, "风险退出": 3, "暂不交易": 4, "低成交过滤": 5, "已过滤": 6, "无数据": 7}
        df["_order"] = df["信号"].map(order).fillna(9)
        df = df.sort_values(["_order", "评分", "当日涨幅%", "放量倍数"], ascending=[True, False, False, False]).drop(columns=["_order"])
        return df.reset_index(drop=True)

    buy_df = sort_df(buy_rows).head(p.target_buy)
    watch_df = sort_df(watch_rows).head(p.target_watch)
    filtered_df = sort_df(filtered_rows)
    all_df = sort_df(scanned_rows)
    return buy_df, watch_df, filtered_df, rounds_log, all_df


# -----------------------------
# UI helpers
# -----------------------------
def render_hero() -> None:
    st.markdown(
        """
        <div class="apple-hero">
          <div class="hero-kicker">Sector first · Momentum funnel · Mobile ready</div>
          <div class="hero-title">消闲派思维选股器</div>
          <div class="hero-sub">
            先找最强板块，再找龙头候选。弱板块自动靠后，低成交和无效信号自动过滤，最终只输出“买入观察”和“观察名单”。
          </div>
          <div class="hero-pills">
            <span class="pill">🔥 最强板块排序</span>
            <span class="pill">🎯 10只买入观察</span>
            <span class="pill">👀 20只观察名单</span>
            <span class="pill">🧹 自动过滤垃圾票</span>
            <span class="pill">📱 iPhone 优化</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric_card(label: str, value: str, note: str = "") -> str:
    return f"""
    <div class="mini-card">
      <div class="mini-label">{label}</div>
      <div class="mini-value">{value}</div>
      <div class="mini-note">{note}</div>
    </div>
    """


def render_rank_cards(sector_df: pd.DataFrame) -> None:
    if sector_df is None or sector_df.empty:
        return
    top = sector_df.head(3).reset_index(drop=True)
    cols = st.columns(len(top))
    for i, (_, row) in enumerate(top.iterrows()):
        with cols[i]:
            st.markdown(
                f"""
                <div class="rank-card">
                  <div class="rank-num">NO.{i+1} · 最强板块</div>
                  <div class="rank-name">{row.get('板块', '-')}</div>
                  <div class="rank-score">{row.get('强度分', 0)}</div>
                  <div class="rank-note">龙头：{row.get('龙头候选', '无')}<br/>结论：{row.get('板块结论', '-')}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_result_summary(buy_df: pd.DataFrame, watch_df: pd.DataFrame, all_df: pd.DataFrame) -> None:
    cols = st.columns(3)
    with cols[0]:
        st.markdown(metric_card("买入观察", f"{len(buy_df)} 只", "只代表进入重点盯盘池，不是下单命令"), unsafe_allow_html=True)
    with cols[1]:
        st.markdown(metric_card("观察名单", f"{len(watch_df)} 只", "有强度但还没到最佳状态"), unsafe_allow_html=True)
    with cols[2]:
        st.markdown(metric_card("实际扫描", f"{len(all_df)} 只", "已按板块强弱和个股强度排序"), unsafe_allow_html=True)


# -----------------------------
# UI
# -----------------------------
render_hero()

with st.sidebar:
    st.markdown("### ⚙️ 扫描控制台")
    mode = st.selectbox("扫描范围", ["美股热门池", "A股热门池", "美股+A股热门池", "手动输入"], index=0)

    selected_us = []
    selected_cn = []
    if mode in ["美股热门池", "美股+A股热门池"]:
        selected_us = st.multiselect("美股板块池", list(US_POOLS.keys()), default=["AI/芯片", "大型科技", "加密/金融科技"])
    if mode in ["A股热门池", "美股+A股热门池"]:
        selected_cn = st.multiselect("A股板块池", list(CN_POOLS_RAW.keys()), default=["A股AI/算力", "A股芯片/半导体", "A股高成交核心"])

    manual = st.text_area("手动追加代码", value="", height=72, placeholder="例如：SPCX, NVDA, 600519, 300750")

    st.markdown("### 🎯 输出目标")
    target_buy = st.number_input("买入观察数量", min_value=1, max_value=30, value=10, step=1)
    target_watch = st.number_input("观察数量", min_value=1, max_value=60, value=20, step=1)
    max_scan = st.number_input("最多扫描股票数", min_value=20, max_value=300, value=160, step=10)

    st.markdown("### 🔥 板块优先")
    use_sector_first = st.checkbox("先找最强板块，再找龙头", value=True)
    top_sector_limit = st.number_input("优先扫描最强板块数", min_value=1, max_value=10, value=3, step=1)

    st.markdown("### 🧹 过滤参数")
    period = st.selectbox("历史周期", ["3mo", "6mo", "1y"], index=1)
    interval = "1d"
    short_ma = st.number_input("短均线", min_value=2, max_value=30, value=5, step=1)
    long_ma = st.number_input("长均线", min_value=10, max_value=120, value=20, step=1)
    min_gain = st.number_input("最小当日涨幅%", min_value=0.0, max_value=20.0, value=2.0, step=0.5)
    vol_ratio = st.number_input("最小放量倍数", min_value=1.0, max_value=10.0, value=1.5, step=0.1)
    min_turnover = st.number_input("最低成交额M", min_value=0.0, max_value=5000.0, value=50.0, step=10.0)
    include_filtered = st.checkbox("显示已过滤股票", value=False)

params = ScanParams(
    market=mode,
    period=period,
    interval=interval,
    short_ma=int(short_ma),
    long_ma=int(long_ma),
    vol_window=20,
    min_gain_pct=float(min_gain),
    vol_ratio_min=float(vol_ratio),
    min_turnover_m=float(min_turnover),
    max_scan=int(max_scan),
    target_buy=int(target_buy),
    target_watch=int(target_watch),
    include_filtered=bool(include_filtered),
)

sector_defs = build_sector_defs(mode, selected_us, selected_cn)
base_symbols = build_scan_universe(mode, selected_us, selected_cn, manual)

st.markdown("<div class='section-title'>今日扫描任务</div>", unsafe_allow_html=True)
col_a, col_b, col_c = st.columns(3)
with col_a:
    st.markdown(metric_card("候选池", f"{len(base_symbols)} 只", "来自你选择的板块池和手动追加"), unsafe_allow_html=True)
with col_b:
    st.markdown(metric_card("目标买入观察", f"{target_buy} 只", "强趋势 + 强动量 + 强放量"), unsafe_allow_html=True)
with col_c:
    st.markdown(metric_card("目标观察", f"{target_watch} 只", "有潜力，但还要继续确认"), unsafe_allow_html=True)

st.markdown(
    "<div class='small-note'>严肃提醒：这里的“买入观察”不是下单命令。它只是告诉你：这只票值得放进第二天盯盘池。真正交易还要看大盘、新闻、盘中承接、止损位置。</div>",
    unsafe_allow_html=True,
)

run_scan = st.button("🚀 开始智能漏斗扫描", type="primary")

if run_scan:
    if not base_symbols:
        st.error("候选池为空。请选择板块池或手动输入股票代码。")
    else:
        sector_df = pd.DataFrame()
        leader_map: Dict[str, List[str]] = {}
        symbols = base_symbols

        with st.spinner("第一步：正在按消闲派思路给板块排序。先找最强方向，不在弱板块里浪费子弹..."):
            if use_sector_first and mode != "手动输入" and sector_defs:
                sector_df, leader_map = rank_strong_sectors(sector_defs, params)
                symbols = build_sector_ordered_universe(sector_df, leader_map, sector_defs, int(top_sector_limit), manual)

        with st.spinner("第二步：按板块强弱顺序漏斗扫描。弱票自动过滤，继续寻找下一批候选..."):
            buy_df, watch_df, filtered_df, rounds_log, all_df = scan_universe(symbols, params)

        render_result_summary(buy_df, watch_df, all_df)

        tabs = st.tabs(["🔥 最强板块", "✅ 买入观察", "👀 观察名单", "🧭 扫描过程", "📊 全部结果"])

        with tabs[0]:
            if use_sector_first and mode != "手动输入" and not sector_df.empty:
                top_sector_name = str(sector_df.iloc[0]["板块"])
                st.markdown("<div class='section-title'>最强板块排行榜</div>", unsafe_allow_html=True)
                render_rank_cards(sector_df)
                st.success(f"当前最强板块：{top_sector_name}。优先从这个方向找龙头，不在弱板块里找奇迹。")
                st.dataframe(sector_df, use_container_width=True, hide_index=True)
            elif use_sector_first and mode != "手动输入":
                st.warning("板块排序没有拿到足够数据，已退回普通漏斗扫描。")
            else:
                st.info("手动输入模式下不做板块排行榜。")

        with tabs[1]:
            st.markdown("<div class='section-title'>今日买入观察名单</div>", unsafe_allow_html=True)
            st.markdown("<div class='section-caption'>这张表是今天最重要的输出。没有票，就不要硬做。</div>", unsafe_allow_html=True)
            if buy_df.empty:
                st.warning("没有找到满足条件的买入观察股票。今天不要硬做。")
            else:
                st.dataframe(buy_df, use_container_width=True, hide_index=True)
                st.download_button("下载买入观察名单 CSV", buy_df.to_csv(index=False).encode("utf-8-sig"), "buy_watch.csv", "text/csv")

        with tabs[2]:
            st.markdown("<div class='section-title'>今日观察名单</div>", unsafe_allow_html=True)
            st.markdown("<div class='section-caption'>这些是备选，不是立刻买。明天继续看是否转强。</div>", unsafe_allow_html=True)
            if watch_df.empty:
                st.info("没有观察名单。")
            else:
                st.dataframe(watch_df, use_container_width=True, hide_index=True)
                st.download_button("下载观察名单 CSV", watch_df.to_csv(index=False).encode("utf-8-sig"), "watch_list.csv", "text/csv")

        with tabs[3]:
            st.markdown("<div class='section-title'>扫描过程</div>", unsafe_allow_html=True)
            for line in rounds_log:
                st.write("- " + line)
            if include_filtered:
                st.markdown("<div class='section-title'>已过滤股票</div>", unsafe_allow_html=True)
                st.dataframe(filtered_df, use_container_width=True, hide_index=True)

        with tabs[4]:
            st.markdown("<div class='section-title'>全部扫描结果</div>", unsafe_allow_html=True)
            st.dataframe(all_df, use_container_width=True, hide_index=True)
            st.download_button("下载全部结果 CSV", all_df.to_csv(index=False).encode("utf-8-sig"), "all_scan_results.csv", "text/csv")

else:
    st.markdown(
        """
        <div class="glass-panel">
          <div class="section-title" style="margin-top:0">使用逻辑</div>
          <div class="small-note">
            1）先选市场和板块池；2）点击“开始智能漏斗扫描”；3）先看“最强板块”，再看“买入观察”；4）没有买入观察就空仓，不要为了交易而交易。
            <br/><br/>
            核心原则：短线资金只认最强方向。弱板块里的股票，即使看起来便宜，也先放弃。
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
