import math
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional

import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="美股+A股热门股自动扫描器",
    page_icon="📈",
    layout="centered",
)

st.markdown(
    """
    <style>
    .block-container {padding-top: 1.0rem; padding-bottom: 1.2rem; max-width: 980px;}
    div[data-testid="stMetric"] {background:#11182710; border:1px solid #37415133; padding:0.65rem; border-radius:0.75rem;}
    .small-note {font-size: 0.88rem; color: #9ca3af;}
    @media (max-width: 640px) {
        .block-container {padding-left:0.65rem; padding-right:0.65rem;}
        h1 {font-size:1.35rem !important;}
        h2, h3 {font-size:1.08rem !important;}
        .stDataFrame {font-size:0.78rem;}
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# 股票池：只做“热门池”，不是全市场。
# -----------------------------
US_POOLS: Dict[str, List[str]] = {
    "AI/芯片": ["NVDA", "AMD", "AVGO", "ARM", "MU", "SMCI", "MRVL", "QCOM", "TSM", "ASML", "AMAT", "LRCX", "INTC", "SMH"],
    "大型科技": ["MSFT", "AAPL", "META", "AMZN", "GOOGL", "NFLX", "TSLA", "PLTR", "ORCL", "NOW", "APP", "CRM"],
    "加密/金融科技": ["COIN", "MSTR", "HOOD", "MARA", "RIOT", "CLSK", "IBIT", "BITO"],
    "杠杆ETF": ["SOXL", "SOXS", "TQQQ", "SQQQ", "TECL", "FNGU", "UVXY"],
    "新股/热门": ["SPCX", "RDDT", "ARM", "CRCL", "IREN", "OKLO", "TEM", "BBAI"],
}

CN_POOLS: Dict[str, List[str]] = {
    "AI/算力/软件": ["002230", "300308", "000977", "300496", "688111", "688041", "603019", "300033", "600570", "002415"],
    "芯片/半导体": ["688981", "688256", "603986", "002371", "300782", "688012", "600584", "688008", "688072", "002409"],
    "新能源/车/机器人": ["300750", "002594", "601012", "300124", "002475", "300014", "002050", "300274", "002920", "002466"],
    "核心大盘/金融消费": ["600519", "000858", "601318", "600036", "600030", "601899", "000001", "601166", "600900", "000333"],
    "高波动/题材观察": ["300750", "002594", "002475", "300308", "603019", "300033", "688981", "688111"],
}

TAG_MAP: Dict[str, List[str]] = {
    # US
    "NVDA": ["AI", "芯片"], "AMD": ["AI", "芯片"], "AVGO": ["AI", "芯片"], "ARM": ["AI", "芯片", "新股/热门"],
    "MU": ["芯片"], "SMCI": ["AI", "服务器"], "MRVL": ["芯片"], "QCOM": ["芯片"], "TSM": ["芯片"], "ASML": ["芯片"],
    "SMH": ["芯片ETF"], "SOXL": ["杠杆ETF", "芯片"], "SOXS": ["杠杆ETF", "反向"],
    "TQQQ": ["杠杆ETF"], "SQQQ": ["杠杆ETF", "反向"], "TECL": ["杠杆ETF"], "FNGU": ["杠杆ETF"], "UVXY": ["杠杆ETF", "高风险"],
    "TSLA": ["科技", "高波动"], "PLTR": ["AI", "高波动"], "META": ["大型科技"], "MSFT": ["AI", "大型科技"],
    "AAPL": ["大型科技"], "AMZN": ["大型科技"], "GOOGL": ["AI", "大型科技"], "NFLX": ["大型科技"], "APP": ["AI", "高波动"],
    "COIN": ["加密"], "MSTR": ["加密", "高波动"], "HOOD": ["金融科技", "加密"], "MARA": ["加密", "高波动"], "RIOT": ["加密", "高波动"], "CLSK": ["加密"],
    "SPCX": ["新股/热门", "航天", "高波动"], "RDDT": ["新股/热门"], "CRCL": ["新股/热门", "加密"],
    # CN
    "002230": ["AI", "算力"], "300308": ["AI", "算力"], "000977": ["AI", "服务器"], "300496": ["AI"],
    "688111": ["AI", "芯片"], "688041": ["AI", "芯片"], "603019": ["AI", "软件"], "300033": ["金融科技"], "600570": ["金融科技"],
    "688981": ["芯片"], "688256": ["芯片"], "603986": ["芯片"], "002371": ["芯片"], "300782": ["芯片"], "688012": ["芯片"], "600584": ["芯片"],
    "300750": ["新能源", "锂电"], "002594": ["新能源车"], "601012": ["新能源"], "002475": ["新能源", "锂电"],
    "600519": ["消费", "核心资产"], "000858": ["消费", "核心资产"], "601318": ["金融"], "600036": ["金融"], "600030": ["券商"], "601899": ["资源"],
}

@dataclass
class Params:
    short_ma: int = 5
    long_ma: int = 20
    vol_window: int = 20
    vol_multi: float = 1.5
    min_ret: float = 2.0
    stop_loss: float = 5.0
    max_hold: int = 5
    min_dollar_vol_us: float = 50_000_000
    min_turnover_cn: float = 200_000_000
    max_scan: int = 60


def unique(seq: List[str]) -> List[str]:
    out = []
    for x in seq:
        if x and x not in out:
            out.append(x)
    return out


def parse_tickers(raw: str) -> List[str]:
    return unique([x.strip().upper().replace(" ", "") for x in raw.replace("\n", ",").split(",") if x.strip()])


def cn_to_yahoo(code: str) -> str:
    s = code.strip().upper()
    if s.endswith(".SS") or s.endswith(".SZ"):
        return s
    s = s.replace("SH", "").replace("SZ", "")
    if s.startswith(("6", "9")) or s.startswith("688"):
        return f"{s}.SS"
    return f"{s}.SZ"


def display_code(yahoo_code: str) -> str:
    return yahoo_code.replace(".SS", "").replace(".SZ", "")


def tags_for(code: str) -> str:
    base = display_code(code).upper()
    tags = TAG_MAP.get(base, TAG_MAP.get(code.upper(), []))
    return " / ".join(tags) if tags else "—"


def get_pool(scope: str, us_cats: List[str], cn_cats: List[str], include_leverage: bool, include_hot: bool) -> Tuple[List[Tuple[str, str]], str]:
    """Return list of (market, ticker). market is US or CN."""
    items: List[Tuple[str, str]] = []
    if scope in ("美股热门池", "美股+A股热门池"):
        for cat in us_cats:
            if cat == "杠杆ETF" and not include_leverage:
                continue
            if cat == "新股/热门" and not include_hot:
                continue
            for t in US_POOLS.get(cat, []):
                items.append(("US", t))
    if scope in ("A股热门池", "美股+A股热门池"):
        for cat in cn_cats:
            for c in CN_POOLS.get(cat, []):
                items.append(("CN", cn_to_yahoo(c)))
    # Deduplicate by market+ticker
    dedup = []
    seen = set()
    for m, t in items:
        key = f"{m}:{t}"
        if key not in seen:
            seen.add(key)
            dedup.append((m, t))
    return dedup, f"自动热门池：{len(dedup)}只"


@st.cache_data(show_spinner=False, ttl=60 * 20)
def load_history(ticker: str, period: str = "6mo", interval: str = "1d") -> pd.DataFrame:
    try:
        df = yf.download(
            ticker,
            period=period,
            interval=interval,
            auto_adjust=True,
            progress=False,
            threads=False,
        )
    except Exception:
        return pd.DataFrame()

    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()
    if isinstance(out.columns, pd.MultiIndex):
        # yfinance sometimes returns MultiIndex even for one ticker.
        t_up = ticker.upper()
        for level in range(out.columns.nlevels):
            vals = [str(v).upper() for v in out.columns.get_level_values(level)]
            if t_up in vals:
                try:
                    out = out.xs(t_up, level=level, axis=1, drop_level=True)
                    break
                except Exception:
                    pass
        if isinstance(out.columns, pd.MultiIndex):
            out.columns = ["_".join([str(x) for x in col if str(x)]) for col in out.columns]

    out = out.rename(columns={c: str(c).title() for c in out.columns})
    req = ["Open", "High", "Low", "Close", "Volume"]
    if any(c not in out.columns for c in req):
        return pd.DataFrame()
    out = out[req].dropna()
    out.index = pd.to_datetime(out.index)
    return out


def add_indicators(df: pd.DataFrame, p: Params) -> pd.DataFrame:
    out = df.copy()
    out["MA_SHORT"] = out["Close"].rolling(p.short_ma).mean()
    out["MA_LONG"] = out["Close"].rolling(p.long_ma).mean()
    out["VOL_MA"] = out["Volume"].rolling(p.vol_window).mean()
    out["RET_1D"] = out["Close"].pct_change()
    out["RET_5D"] = out["Close"].pct_change(5)
    out["VOL_RATIO"] = out["Volume"] / out["VOL_MA"]
    out["TURNOVER"] = out["Close"] * out["Volume"]
    out["HIGH_20"] = out["Close"].rolling(20).max()
    out["DRAWDOWN_20"] = out["Close"] / out["HIGH_20"] - 1
    return out


def scan_one(market: str, ticker: str, p: Params, period: str) -> Dict:
    df = load_history(ticker, period=period)
    name = display_code(ticker) if market == "CN" else ticker
    if df.empty or len(df) < max(p.long_ma, p.vol_window) + 5:
        return {
            "市场": "A股" if market == "CN" else "美股", "代码": name, "信号": "NO_DATA", "评分": 0,
            "收盘": None, "涨幅%": None, "5日%": None, "量比": None, "成交额": None,
            "标签": tags_for(ticker), "原因": "数据不足/暂时读不到"
        }
    ind = add_indicators(df, p).dropna()
    if ind.empty:
        return {
            "市场": "A股" if market == "CN" else "美股", "代码": name, "信号": "NO_DATA", "评分": 0,
            "收盘": None, "涨幅%": None, "5日%": None, "量比": None, "成交额": None,
            "标签": tags_for(ticker), "原因": "指标数据不足"
        }
    r = ind.iloc[-1]
    close = float(r["Close"])
    ret1 = float(r["RET_1D"] * 100)
    ret5 = float(r["RET_5D"] * 100)
    vol_ratio = float(r["VOL_RATIO"])
    turnover = float(r["TURNOVER"])

    trend = bool(r["Close"] > r["MA_LONG"] and r["MA_SHORT"] > r["MA_LONG"])
    momentum = bool(ret1 >= p.min_ret)
    volume = bool(vol_ratio >= p.vol_multi)
    exit_risk = bool(r["Close"] < r["MA_LONG"] or r["DRAWDOWN_20"] <= -p.stop_loss / 100)
    low_liq = False
    if market == "US":
        low_liq = bool(turnover < p.min_dollar_vol_us)
    else:
        low_liq = bool(turnover < p.min_turnover_cn)

    # Score: 只用于排序，不等于买入概率。
    score = 0
    score += 25 if trend else 0
    score += 25 if momentum else 0
    score += 25 if volume else 0
    score += 10 if ret5 > 0 else 0
    score += 15 if not low_liq else 0
    score = min(score, 100)

    reasons = []
    reasons.append("趋势强" if trend else "趋势弱")
    reasons.append("涨幅达标" if momentum else "涨幅不足")
    reasons.append("放量" if volume else "量能不足")
    if low_liq:
        reasons.append("低成交过滤")

    if low_liq:
        signal = "FILTER_LOW_LIQ"
    elif market == "CN" and ret1 >= 9.2 and volume:
        signal = "LIMIT_WATCH"
    elif trend and momentum and volume:
        signal = "BUY_WATCH"
    elif trend and (ret1 > 0 or vol_ratio >= 1.2):
        signal = "WATCH"
    elif exit_risk:
        signal = "EXIT_RISK"
    else:
        signal = "NO_TRADE"

    return {
        "市场": "A股" if market == "CN" else "美股",
        "代码": name,
        "信号": signal,
        "评分": int(score),
        "收盘": round(close, 2),
        "涨幅%": round(ret1, 2),
        "5日%": round(ret5, 2),
        "量比": round(vol_ratio, 2),
        "成交额": round(turnover / 100_000_000, 2),
        "标签": tags_for(ticker),
        "原因": " / ".join(reasons),
    }


def sort_result(df: pd.DataFrame) -> pd.DataFrame:
    order = {
        "LIMIT_WATCH": 0,
        "BUY_WATCH": 1,
        "WATCH": 2,
        "EXIT_RISK": 3,
        "NO_TRADE": 4,
        "FILTER_LOW_LIQ": 5,
        "NO_DATA": 6,
    }
    if df.empty:
        return df
    df = df.copy()
    df["_sort"] = df["信号"].map(order).fillna(9)
    return df.sort_values(["_sort", "评分", "涨幅%", "量比"], ascending=[True, False, False, False]).drop(columns=["_sort"])


def build_trade_signals(df: pd.DataFrame, p: Params) -> pd.DataFrame:
    out = add_indicators(df, p).dropna().copy()
    out["BUY"] = (
        (out["Close"] > out["MA_LONG"])
        & (out["MA_SHORT"] > out["MA_LONG"])
        & (out["RET_1D"] >= p.min_ret / 100)
        & (out["VOL_RATIO"] >= p.vol_multi)
    )
    out["SELL"] = (out["Close"] < out["MA_LONG"]) | (out["DRAWDOWN_20"] <= -p.stop_loss / 100)
    return out


def run_backtest(df: pd.DataFrame, p: Params) -> Tuple[pd.DataFrame, pd.DataFrame, Dict]:
    data = build_trade_signals(df, p)
    if data.empty:
        return pd.DataFrame(), pd.DataFrame(), {}
    cash = 1.0
    shares = 0.0
    in_pos = False
    entry_price = 0.0
    entry_date = None
    entry_i = 0
    trades = []
    curve = []
    for i in range(1, len(data)):
        prev = data.iloc[i - 1]
        today = data.iloc[i]
        date = data.index[i]
        open_p = float(today["Open"])
        close_p = float(today["Close"])
        if not in_pos and bool(prev["BUY"]):
            if open_p > 0:
                shares = cash / open_p
                cash = 0.0
                in_pos = True
                entry_price = open_p
                entry_date = date
                entry_i = i
        elif in_pos:
            hold = i - entry_i
            stop = open_p <= entry_price * (1 - p.stop_loss / 100)
            maxhold = hold >= p.max_hold
            sell = bool(prev["SELL"])
            if stop or maxhold or sell:
                exit_p = open_p
                cash = shares * exit_p
                shares = 0.0
                in_pos = False
                trades.append({
                    "买入日期": entry_date.date(),
                    "卖出日期": date.date(),
                    "买入价": round(entry_price, 2),
                    "卖出价": round(exit_p, 2),
                    "收益%": round((exit_p / entry_price - 1) * 100, 2),
                    "持仓天数": hold,
                    "退出原因": "止损" if stop else ("到期" if maxhold else "卖出信号"),
                })
        curve.append({"日期": date, "净值": cash + shares * close_p})
    eq = pd.DataFrame(curve).set_index("日期") if curve else pd.DataFrame()
    tr = pd.DataFrame(trades)
    if eq.empty:
        return eq, tr, {}
    total = float(eq["净值"].iloc[-1] - 1)
    dd = float((eq["净值"] / eq["净值"].cummax() - 1).min())
    win = float((tr["收益%"] > 0).mean()) if not tr.empty else 0.0
    avg = float(tr["收益%"].mean()) if not tr.empty else 0.0
    stats = {"总收益%": round(total * 100, 2), "最大回撤%": round(dd * 100, 2), "交易次数": len(tr), "胜率%": round(win * 100, 2), "单笔均值%": round(avg, 2)}
    return eq, tr, stats


# -----------------------------
# UI
# -----------------------------
st.title("📈 美股+A股热门股自动扫描器")
st.caption("自动扫描热门池，找涨幅强、成交量放大的股票，并标记 AI/芯片/加密/新股/杠杆ETF。不是下单机器。")

with st.sidebar:
    st.header("扫描设置")
    scope = st.selectbox("扫描范围", ["美股热门池", "A股热门池", "美股+A股热门池", "手动输入"], index=0)
    period = st.selectbox("历史周期", ["3mo", "6mo", "1y", "2y"], index=1)

    if scope in ("美股热门池", "美股+A股热门池"):
        us_cats = st.multiselect("美股板块", list(US_POOLS.keys()), default=["AI/芯片", "大型科技", "加密/金融科技"])
    else:
        us_cats = []
    if scope in ("A股热门池", "美股+A股热门池"):
        cn_cats = st.multiselect("A股板块", list(CN_POOLS.keys()), default=["AI/算力/软件", "芯片/半导体", "核心大盘/金融消费"])
    else:
        cn_cats = []

    include_leverage = st.checkbox("包含杠杆ETF", value=False)
    include_hot = st.checkbox("包含新股/高波动热门", value=True)

    manual_market = "US"
    manual_raw = ""
    if scope == "手动输入":
        manual_market_cn = st.selectbox("手动输入市场", ["美股", "A股"], index=0)
        manual_market = "CN" if manual_market_cn == "A股" else "US"
        manual_raw = st.text_area("股票池，用英文逗号分隔", value="NVDA, AMD, TSLA, PLTR, SMH, SOXL" if manual_market == "US" else "600519, 300750, 002594, 600036")

    st.divider()
    st.header("策略参数")
    p = Params(
        short_ma=int(st.number_input("短均线", 2, 60, 5)),
        long_ma=int(st.number_input("长均线", 5, 200, 20)),
        vol_multi=float(st.number_input("放量倍数", 1.0, 10.0, 1.5, step=0.1)),
        min_ret=float(st.number_input("最小当日涨幅%", -10.0, 20.0, 2.0, step=0.5)),
        stop_loss=float(st.number_input("止损/回撤阈值%", 1.0, 30.0, 5.0, step=0.5)),
        max_hold=int(st.number_input("最长持仓天数", 1, 60, 5)),
        min_dollar_vol_us=float(st.number_input("美股最低成交额/美元", 0.0, 500_000_000.0, 50_000_000.0, step=10_000_000.0)),
        min_turnover_cn=float(st.number_input("A股最低成交额/人民币", 0.0, 1_000_000_000.0, 200_000_000.0, step=50_000_000.0)),
        max_scan=int(st.number_input("最多扫描数量", 5, 120, 60)),
    )

if scope == "手动输入":
    raw_tickers = parse_tickers(manual_raw)
    scan_items = [(manual_market, cn_to_yahoo(t) if manual_market == "CN" else t) for t in raw_tickers]
    pool_note = f"手动股票池：{len(scan_items)}只"
else:
    scan_items, pool_note = get_pool(scope, us_cats, cn_cats, include_leverage, include_hot)

if len(scan_items) > p.max_scan:
    scan_items = scan_items[: p.max_scan]
    pool_note += f"；已按最多扫描数量截断到 {p.max_scan} 只"

tab1, tab2, tab3 = st.tabs(["自动扫描", "单股回测", "说明"])

with tab1:
    st.subheader("今日自动观察名单")
    st.write(pool_note)
    st.markdown("<span class='small-note'>规则：涨幅强 + 成交量放大 + 趋势强 + 过滤低成交。结果只用于观察，不是买入命令。</span>", unsafe_allow_html=True)

    if st.button("开始自动扫描", type="primary"):
        if not scan_items:
            st.error("股票池为空。请至少选择一个板块或输入股票。")
        else:
            rows = []
            progress = st.progress(0)
            status = st.empty()
            for i, (m, t) in enumerate(scan_items, start=1):
                status.write(f"正在扫描 {i}/{len(scan_items)}：{display_code(t) if m == 'CN' else t}")
                rows.append(scan_one(m, t, p, period))
                progress.progress(i / len(scan_items))
            progress.empty()
            status.empty()
            result = sort_result(pd.DataFrame(rows))

            watch = result[result["信号"].isin(["LIMIT_WATCH", "BUY_WATCH", "WATCH"])].copy()
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("扫描数量", len(result))
            c2.metric("观察名单", len(watch))
            c3.metric("强观察", int((result["信号"].isin(["LIMIT_WATCH", "BUY_WATCH"])).sum()))
            c4.metric("低成交过滤", int((result["信号"] == "FILTER_LOW_LIQ").sum()))

            if watch.empty:
                st.warning("今天没有强观察名单。正确动作：不急，不追。")
            else:
                st.success("今日观察名单：先观察，不要无脑买。")
                st.dataframe(watch, use_container_width=True, hide_index=True)

            st.write("完整扫描结果")
            st.dataframe(result, use_container_width=True, hide_index=True)
            st.download_button(
                "下载今日扫描结果 CSV",
                data=result.to_csv(index=False).encode("utf-8-sig"),
                file_name="auto_stock_scan_results.csv",
                mime="text/csv",
            )

            st.info("严格纪律：只看 LIMIT_WATCH / BUY_WATCH / WATCH。EXIT_RISK、NO_TRADE、FILTER_LOW_LIQ 不碰。")

with tab2:
    st.subheader("单股回测")
    bt_market_cn = st.selectbox("回测市场", ["美股", "A股"], index=0)
    default_bt = "NVDA" if bt_market_cn == "美股" else "300750"
    bt_code = st.text_input("代码", value=default_bt)
    if st.button("开始回测", type="primary"):
        market = "CN" if bt_market_cn == "A股" else "US"
        ticker = cn_to_yahoo(bt_code) if market == "CN" else bt_code.strip().upper()
        df = load_history(ticker, period=period)
        if df.empty:
            st.error("数据读不到。换一个代码，或稍后再试。")
        else:
            eq, tr, stats = run_backtest(df, p)
            if not stats:
                st.error("数据不足，无法回测。")
            else:
                c1, c2, c3, c4, c5 = st.columns(5)
                c1.metric("总收益", f"{stats['总收益%']}%")
                c2.metric("最大回撤", f"{stats['最大回撤%']}%")
                c3.metric("交易次数", stats["交易次数"])
                c4.metric("胜率", f"{stats['胜率%']}%")
                c5.metric("单笔均值", f"{stats['单笔均值%']}%")
                if not eq.empty:
                    st.line_chart(eq["净值"])
                if tr.empty:
                    st.info("该参数下没有完整交易。")
                else:
                    st.dataframe(tr, use_container_width=True, hide_index=True)

with tab3:
    st.subheader("信号说明")
    st.markdown(
        """
| 信号 | 含义 | 动作 |
|---|---|---|
| LIMIT_WATCH | A股接近/达到涨停强势观察 | 只观察，确认封板/题材后再说 |
| BUY_WATCH | 趋势、涨幅、放量都达标 | 重点观察，不是立刻买 |
| WATCH | 有一定强度 | 继续看，不急 |
| EXIT_RISK | 趋势或回撤风险高 | 不买 |
| NO_TRADE | 没机会 | 不买 |
| FILTER_LOW_LIQ | 成交额太低 | 不碰，容易被收割 |
| NO_DATA | 数据读不到 | 换代码或稍后再试 |

### 重要限制

这个版本是“热门池自动扫描”，不是全市场毫秒级行情系统。它适合帮你找观察对象和过滤垃圾机会，不适合当自动下单依据。

A股短线更高级的版本还应该加入：涨停封单、连板高度、炸板率、题材热度、龙虎榜、次日溢价统计。现在先做粗筛，不要过度相信。
"""
    )
