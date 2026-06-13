from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import math

import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf
import plotly.graph_objects as go

st.set_page_config(page_title="短线雷达", page_icon="📈", layout="centered")

# -----------------------------------------------------------------------------
# 数据池：先市场，再板块，再股票。注意：这是公开行情源，实时性不等同券商。
# -----------------------------------------------------------------------------

US_SECTORS: Dict[str, List[Tuple[str, str, str]]] = {
    "AI/芯片": [
        ("NVDA", "英伟达", "AI/芯片"), ("AMD", "AMD", "AI/芯片"),
        ("AVGO", "博通", "AI/芯片"), ("ARM", "Arm", "AI/芯片"),
        ("MU", "美光科技", "AI/芯片"), ("SMCI", "超微电脑", "AI/芯片"),
        ("TSM", "台积电ADR", "AI/芯片"), ("ASML", "阿斯麦", "AI/芯片"),
        ("SMH", "半导体ETF", "AI/芯片"), ("SOXL", "三倍半导体ETF", "杠杆ETF"),
    ],
    "大型科技": [
        ("AAPL", "苹果", "大型科技"), ("MSFT", "微软", "大型科技"),
        ("AMZN", "亚马逊", "大型科技"), ("GOOGL", "谷歌", "大型科技"),
        ("META", "Meta", "大型科技"), ("NFLX", "奈飞", "大型科技"),
        ("TSLA", "特斯拉", "高波动"), ("PLTR", "Palantir", "AI/软件"),
        ("APP", "AppLovin", "高波动"),
    ],
    "加密/金融科技": [
        ("COIN", "Coinbase", "加密"), ("MSTR", "MicroStrategy", "加密"),
        ("HOOD", "Robinhood", "金融科技"), ("PYPL", "PayPal", "金融科技"),
        ("SQ", "Block", "金融科技"), ("AFRM", "Affirm", "金融科技"),
    ],
    "军工/航天": [
        ("LMT", "洛克希德马丁", "军工"), ("RTX", "RTX", "军工"),
        ("NOC", "诺斯罗普", "军工"), ("BA", "波音", "航天航空"),
        ("RKLB", "Rocket Lab", "航天"), ("SPCE", "维珍银河", "高波动"),
    ],
    "杠杆ETF": [
        ("TQQQ", "纳指三倍多", "杠杆ETF"), ("SOXL", "三倍半导体ETF", "杠杆ETF"),
        ("TECL", "科技三倍多", "杠杆ETF"), ("SPXL", "标普三倍多", "杠杆ETF"),
    ],
}

CN_SECTORS: Dict[str, List[Tuple[str, str, str]]] = {
    "A股AI/算力": [
        ("002230", "科大讯飞", "AI/算力"), ("000977", "浪潮信息", "AI/算力"),
        ("300308", "中际旭创", "AI/算力"), ("300394", "天孚通信", "AI/算力"),
        ("300502", "新易盛", "AI/算力"), ("002463", "沪电股份", "AI/算力"),
        ("000063", "中兴通讯", "AI/算力"),
    ],
    "A股芯片/半导体": [
        ("688981", "中芯国际", "芯片"), ("603986", "兆易创新", "芯片"),
        ("002371", "北方华创", "芯片"), ("300782", "卓胜微", "芯片"),
        ("002049", "紫光国微", "芯片"), ("002156", "通富微电", "芯片"),
        ("600584", "长电科技", "芯片"),
    ],
    "A股机器人": [
        ("300124", "汇川技术", "机器人"), ("002747", "埃斯顿", "机器人"),
        ("688097", "博众精工", "机器人"), ("002050", "三花智控", "机器人"),
        ("603728", "鸣志电器", "机器人"), ("300024", "机器人", "机器人"),
    ],
    "A股低空经济": [
        ("002085", "万丰奥威", "低空经济"), ("000099", "中信海直", "低空经济"),
        ("688297", "中无人机", "低空经济"), ("002097", "山河智能", "低空经济"),
        ("600038", "中直股份", "低空经济"),
    ],
    "A股证券金融": [
        ("600030", "中信证券", "证券金融"), ("601688", "华泰证券", "证券金融"),
        ("601211", "国泰君安", "证券金融"), ("601318", "中国平安", "证券金融"),
        ("600036", "招商银行", "证券金融"),
    ],
    "A股高成交核心": [
        ("600519", "贵州茅台", "核心资产"), ("300750", "宁德时代", "核心资产"),
        ("002594", "比亚迪", "核心资产"), ("601899", "紫金矿业", "核心资产"),
        ("000858", "五粮液", "核心资产"), ("600276", "恒瑞医药", "核心资产"),
    ],
}

LEVERAGED = {"SOXL", "TQQQ", "TECL", "SPXL"}
HIGH_VOL = {"TSLA", "PLTR", "APP", "MSTR", "COIN", "HOOD", "RKLB", "SPCE"}

@dataclass
class StockMeta:
    ticker: str
    name: str
    market: str
    sector: str
    tag: str


def cn_to_yahoo(code: str) -> str:
    s = str(code).strip().upper()
    if s.endswith(".SS") or s.endswith(".SZ"):
        return s
    if s.startswith(("6", "9", "688", "689")):
        return f"{s}.SS"
    return f"{s}.SZ"


def display_code(yf_code: str) -> str:
    return yf_code.replace(".SS", "").replace(".SZ", "")


def build_universe(scope: str) -> List[StockMeta]:
    items: List[StockMeta] = []
    seen = set()
    if scope in ("全部", "美股"):
        for sector, rows in US_SECTORS.items():
            for code, name, tag in rows:
                if code not in seen:
                    seen.add(code)
                    items.append(StockMeta(code, name, "美股", sector, tag))
    if scope in ("全部", "A股"):
        for sector, rows in CN_SECTORS.items():
            for code, name, tag in rows:
                yf_code = cn_to_yahoo(code)
                if yf_code not in seen:
                    seen.add(yf_code)
                    items.append(StockMeta(yf_code, name, "A股", sector, tag))
    return items


@st.cache_data(show_spinner=False, ttl=60 * 20)
def load_history(ticker: str, period: str = "6mo") -> pd.DataFrame:
    try:
        df = yf.download(ticker, period=period, interval="1d", auto_adjust=True, progress=False, threads=False)
        if df is None or df.empty:
            return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex):
            # yfinance sometimes returns MultiIndex columns. Reduce to price fields.
            if ticker in df.columns.get_level_values(-1):
                df = df.xs(ticker, axis=1, level=-1)
            else:
                df.columns = [str(c[0]) for c in df.columns]
        df = df.rename(columns={c: str(c).title() for c in df.columns})
        cols = ["Open", "High", "Low", "Close", "Volume"]
        if not all(c in df.columns for c in cols):
            return pd.DataFrame()
        df = df[cols].dropna()
        df.index = pd.to_datetime(df.index)
        return df
    except Exception:
        return pd.DataFrame()


def enrich(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["涨跌幅%"] = out["Close"].pct_change() * 100
    out["5日线"] = out["Close"].rolling(5).mean()
    out["20日线"] = out["Close"].rolling(20).mean()
    out["20日新高"] = out["High"].rolling(20).max()
    out["量比"] = out["Volume"] / out["Volume"].rolling(20).mean()
    prev_close = out["Close"].shift(1)
    tr = pd.concat([
        out["High"] - out["Low"],
        (out["High"] - prev_close).abs(),
        (out["Low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    out["ATR"] = tr.rolling(14).mean()
    out["成交额"] = out["Close"] * out["Volume"]
    return out.dropna()


def fmt_money(x: float) -> str:
    if x is None or not np.isfinite(x):
        return "--"
    if x >= 1e9:
        return f"{x/1e9:.1f}B"
    if x >= 1e8:
        return f"{x/1e8:.1f}亿"
    if x >= 1e6:
        return f"{x/1e6:.1f}M"
    if x >= 1e4:
        return f"{x/1e4:.1f}万"
    return f"{x:.0f}"


def scan_one(meta: StockMeta) -> Dict:
    df = load_history(meta.ticker)
    if df.empty or len(df) < 35:
        return {
            "代码": display_code(meta.ticker), "名称": meta.name, "市场": meta.market, "板块": meta.sector,
            "标签": meta.tag, "信号": "无数据", "分数": 0, "现价": np.nan, "涨跌幅%": np.nan,
            "量比": np.nan, "成交额": 0.0, "原因": "公开行情源未返回足够数据", "风险": "无法判断",
            "ticker_raw": meta.ticker,
        }
    ind = enrich(df)
    if ind.empty:
        return {
            "代码": display_code(meta.ticker), "名称": meta.name, "市场": meta.market, "板块": meta.sector,
            "标签": meta.tag, "信号": "无数据", "分数": 0, "现价": np.nan, "涨跌幅%": np.nan,
            "量比": np.nan, "成交额": 0.0, "原因": "指标计算后数据不足", "风险": "无法判断",
            "ticker_raw": meta.ticker,
        }
    last = ind.iloc[-1]
    close = float(last["Close"])
    ret = float(last["涨跌幅%"])
    vol_ratio = float(last["量比"])
    ma5 = float(last["5日线"])
    ma20 = float(last["20日线"])
    high20 = float(last["20日新高"])
    turnover = float(last["成交额"])

    min_turnover = 20_000_000 if meta.market == "美股" else 120_000_000
    low_liq = turnover < min_turnover
    trend_ok = close > ma20
    ma_ok = ma5 > ma20
    momentum_ok = ret >= 2.0 if meta.market == "美股" else ret >= 3.0
    volume_ok = vol_ratio >= 1.35
    near_high = close >= high20 * 0.965
    strong_bar = ret >= 5.0 if meta.market == "美股" else ret >= 7.0
    limit_like = meta.market == "A股" and ret >= 9.2

    score = 0
    if turnover >= min_turnover: score += 15
    if trend_ok: score += 18
    if ma_ok: score += 12
    if momentum_ok: score += 20
    if volume_ok: score += 15
    if near_high: score += 10
    if strong_bar: score += 8
    if limit_like: score += 12
    score = min(100, score)

    risk_notes = []
    if meta.ticker in LEVERAGED:
        risk_notes.append("杠杆ETF，只能短线，不能扛")
    if meta.ticker in HIGH_VOL:
        risk_notes.append("高波动标的，仓位要小")
    if close < ma20:
        risk_notes.append("仍在20日线下方")
    if low_liq:
        risk_notes.append("成交额偏低")

    if low_liq:
        signal = "低成交过滤"
    elif score >= 78:
        signal = "买入观察"
    elif score >= 60:
        signal = "观察名单"
    elif score >= 45:
        signal = "弱观察"
    else:
        signal = "过滤"

    reasons = []
    if turnover >= min_turnover: reasons.append("成交额达标")
    if trend_ok: reasons.append("趋势在20日线上")
    if momentum_ok: reasons.append("涨幅强")
    if volume_ok: reasons.append("放量")
    if near_high: reasons.append("接近20日新高")
    if limit_like: reasons.append("接近涨停/强势大阳")
    if not reasons: reasons.append("强度不足")

    return {
        "代码": display_code(meta.ticker), "名称": meta.name, "市场": meta.market, "板块": meta.sector,
        "标签": meta.tag, "信号": signal, "分数": int(score), "现价": round(close, 3),
        "涨跌幅%": round(ret, 2), "量比": round(vol_ratio, 2), "成交额": turnover,
        "成交额显示": fmt_money(turnover), "原因": "；".join(reasons), "风险": "；".join(risk_notes) if risk_notes else "暂未发现硬伤",
        "ticker_raw": meta.ticker,
    }


def sector_rank(all_rows: pd.DataFrame) -> pd.DataFrame:
    if all_rows.empty:
        return pd.DataFrame()
    rows = []
    for (market, sector), g in all_rows.groupby(["市场", "板块"]):
        valid = g[~g["信号"].isin(["无数据", "低成交过滤"])]
        if valid.empty:
            continue
        up_rate = float((valid["涨跌幅%"] > 0).mean() * 100)
        avg_ret = float(valid["涨跌幅%"].mean())
        strong = int(valid["信号"].isin(["买入观察", "观察名单"]).sum())
        volume = int((valid["量比"] >= 1.35).sum())
        top_names = "、".join(valid.sort_values("分数", ascending=False).head(3).apply(lambda r: f"{r['名称']}({r['代码']})", axis=1).tolist())
        score = int(min(100, max(0, up_rate * 0.35 + avg_ret * 4 + strong * 12 + volume * 6)))
        rows.append({
            "市场": market, "板块": sector, "板块强度": score, "上涨率%": round(up_rate, 1),
            "平均涨幅%": round(avg_ret, 2), "前排数量": strong, "放量数量": volume, "龙头候选": top_names,
        })
    return pd.DataFrame(rows).sort_values("板块强度", ascending=False).reset_index(drop=True)


def trade_plan(row: pd.Series) -> Dict[str, float | str]:
    ticker = row["ticker_raw"]
    df = load_history(ticker)
    if df.empty:
        px = float(row.get("现价", np.nan))
        atr = px * 0.04 if np.isfinite(px) else np.nan
    else:
        ind = enrich(df)
        last = ind.iloc[-1]
        px = float(last["Close"])
        atr = float(last["ATR"]) if np.isfinite(last["ATR"]) and last["ATR"] > 0 else px * 0.04
    entry = px * 1.01
    # 风险控制：高波动和杠杆ETF不能给太宽止损，避免越扛越深
    base_stop = px - max(1.2 * atr, px * 0.035)
    if ticker in LEVERAGED or ticker in HIGH_VOL:
        base_stop = max(base_stop, px * 0.94)
    risk = entry - base_stop
    tp1 = entry + risk
    tp2 = entry + risk * 1.8
    tp3 = entry + risk * 2.8
    return {
        "触发入场": round(entry, 3), "硬止损": round(base_stop, 3),
        "止盈1": round(tp1, 3), "止盈2": round(tp2, 3), "止盈3": round(tp3, 3),
        "纪律": "突破触发价且继续放量才试；跌破硬止损直接走；到止盈1先减仓，不补仓。",
    }


def kline_chart(ticker: str, name: str):
    df = load_history(ticker)
    if df.empty:
        st.warning("这个标的暂时没有K线数据。")
        return
    ind = enrich(df).tail(90)
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=ind.index, open=ind["Open"], high=ind["High"], low=ind["Low"], close=ind["Close"],
        name="K线", increasing_line_color="#16a085", decreasing_line_color="#e74c3c"
    ))
    fig.add_trace(go.Scatter(x=ind.index, y=ind["5日线"], mode="lines", name="5日线", line=dict(width=1.5)))
    fig.add_trace(go.Scatter(x=ind.index, y=ind["20日线"], mode="lines", name="20日线", line=dict(width=1.5)))
    fig.update_layout(
        title=f"{name}（{display_code(ticker)}）K线",
        xaxis_rangeslider_visible=False,
        height=420,
        margin=dict(l=8, r=8, t=45, b=8),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    st.plotly_chart(fig, use_container_width=True)


def scan(scope: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    universe = build_universe(scope)
    progress = st.progress(0, text="正在扫描市场→板块→股票...")
    rows = []
    for i, meta in enumerate(universe, 1):
        rows.append(scan_one(meta))
        progress.progress(i / len(universe), text=f"扫描中：{meta.name} {i}/{len(universe)}")
    progress.empty()
    df = pd.DataFrame(rows)
    sec = sector_rank(df)
    if not sec.empty:
        strong_sectors = set(sec.head(5).apply(lambda r: (r["市场"], r["板块"]), axis=1).tolist())
        df["强板块"] = df.apply(lambda r: (r["市场"], r["板块"]) in strong_sectors, axis=1)
        # 强板块加权，但不改原始事实字段
        df["综合分"] = df["分数"] + df["强板块"].map({True: 8, False: 0})
    else:
        df["强板块"] = False
        df["综合分"] = df["分数"]
    df = df.sort_values(["信号", "综合分", "涨跌幅%"], ascending=[True, False, False]).reset_index(drop=True)
    return df, sec


# -----------------------------------------------------------------------------
# UI：只用 Streamlit 原生组件，彻底避免 HTML 乱码/代码露出。
# -----------------------------------------------------------------------------
st.title("短线投机雷达")
st.caption("市场 → 板块 → 前排股票。给观察名单，也给入场、止损、止盈。")

scope = st.radio("扫描市场", ["全部", "美股", "A股"], index=0, horizontal=True)
manual = st.text_input("手动加入代码（可选，用英文逗号隔开）", placeholder="例如：SPCX, NVDA, 600519, 300750")

c1, c2 = st.columns([2, 1])
with c1:
    start = st.button("开始自动扫描", type="primary", use_container_width=True)
with c2:
    clear = st.button("清空结果", use_container_width=True)

if clear:
    st.session_state.pop("scan_df", None)
    st.session_state.pop("sector_df", None)

if start:
    df, sec = scan(scope)
    # 处理手动加入的代码
    extra_rows = []
    for x in [s.strip() for s in manual.split(",") if s.strip()]:
        # 简单判断A股/美股
        is_cn = x.isdigit() and len(x) == 6
        ticker = cn_to_yahoo(x) if is_cn else x.upper()
        meta = StockMeta(ticker, x.upper() if not is_cn else x, "A股" if is_cn else "美股", "手动加入", "手动加入")
        extra_rows.append(scan_one(meta))
    if extra_rows:
        df = pd.concat([df, pd.DataFrame(extra_rows)], ignore_index=True)
        sec = sector_rank(df)
    st.session_state["scan_df"] = df
    st.session_state["sector_df"] = sec

if "scan_df" not in st.session_state:
    st.info("点上面的按钮开始。结果只分三类：买入观察、观察名单、过滤。")
    st.stop()

df = st.session_state["scan_df"].copy()
sec = st.session_state.get("sector_df", pd.DataFrame()).copy()

buy = df[(df["信号"] == "买入观察") & (df["强板块"] == True)].sort_values("综合分", ascending=False).head(10)
watch = df[(df["信号"].isin(["观察名单", "弱观察"])) & (df["强板块"] == True)].sort_values("综合分", ascending=False).head(20)
filtered = df[~df.index.isin(buy.index) & ~df.index.isin(watch.index)].copy()

avg_sector_score = int(sec["板块强度"].mean()) if not sec.empty else 0
if avg_sector_score >= 75:
    temp = "强"
elif avg_sector_score >= 55:
    temp = "中"
else:
    temp = "弱"

m1, m2, m3, m4 = st.columns(4)
m1.metric("短线温度", temp)
m2.metric("强板块", len(sec.head(5)))
m3.metric("买入观察", len(buy))
m4.metric("观察名单", len(watch))

st.divider()

tabs = st.tabs(["🔥 最强板块", "🎯 买入观察", "👀 观察名单", "📊 个股交易计划", "🧹 过滤原因", "📋 全部结果"])

show_cols = ["代码", "名称", "市场", "板块", "信号", "综合分", "现价", "涨跌幅%", "量比", "成交额显示", "原因", "风险"]

with tabs[0]:
    st.subheader("最强板块排行榜")
    if sec.empty:
        st.warning("没有足够数据生成板块排行。")
    else:
        st.dataframe(sec, use_container_width=True, hide_index=True)
        st.caption("优先只看前3—5个板块。弱板块里的强票，短线也容易变成陷阱。")

with tabs[1]:
    st.subheader("买入观察：最多10只")
    if buy.empty:
        st.warning("当前没有买入观察。市场不给机会时，不要硬凑。")
    else:
        st.dataframe(buy[show_cols], use_container_width=True, hide_index=True)
        st.caption("买入观察不是立刻买。必须等触发价、成交继续放大、风险可控。")

with tabs[2]:
    st.subheader("观察名单：最多20只")
    if watch.empty:
        st.info("暂无观察名单。")
    else:
        st.dataframe(watch[show_cols], use_container_width=True, hide_index=True)

with tabs[3]:
    st.subheader("个股交易计划")
    candidates = pd.concat([buy, watch], ignore_index=True) if not buy.empty or not watch.empty else df
    if candidates.empty:
        st.info("暂无可查看标的。")
    else:
        options = candidates.apply(lambda r: f"{r['代码']}｜{r['名称']}｜{r['信号']}｜{r['板块']}", axis=1).tolist()
        choice = st.selectbox("选择一只股票", options)
        idx = options.index(choice)
        row = candidates.iloc[idx]
        p = trade_plan(row)
        a, b, c = st.columns(3)
        a.metric("现价", row["现价"])
        b.metric("涨跌幅", f"{row['涨跌幅%']}%")
        c.metric("量比", row["量比"])
        st.write(f"**为什么入选/观察：** {row['原因']}")
        st.write(f"**风险提示：** {row['风险']}")
        st.write("**如果我是投机者，我会这样处理：**")
        st.write(p["纪律"])
        plan_df = pd.DataFrame([{k: v for k, v in p.items() if k != "纪律"}])
        st.dataframe(plan_df, use_container_width=True, hide_index=True)
        kline_chart(row["ticker_raw"], row["名称"])

with tabs[4]:
    st.subheader("过滤原因")
    if filtered.empty:
        st.info("没有过滤项。")
    else:
        st.dataframe(filtered[show_cols], use_container_width=True, hide_index=True)
        st.caption("这里不是垃圾桶，是风险提示：低成交、弱趋势、无数据、非强板块，都不要硬做。")

with tabs[5]:
    st.subheader("全部扫描结果")
    st.dataframe(df[show_cols], use_container_width=True, hide_index=True)
    st.download_button("下载CSV", df[show_cols].to_csv(index=False).encode("utf-8-sig"), "scan_results.csv", "text/csv")
