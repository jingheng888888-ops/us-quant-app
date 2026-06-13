from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import math

import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf
import plotly.graph_objects as go


# =============================
# 基础配置
# =============================
st.set_page_config(
    page_title="短线投机者雷达 v13",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# 只做稳定的轻量 CSS，不用 HTML 卡片，避免乱码
st.markdown(
    """
<style>
.block-container {padding-top: 1.2rem; padding-bottom: 2.5rem; max-width: 980px;}
div[data-testid="stMetric"] {border: 1px solid rgba(128,128,128,.22); border-radius: 16px; padding: .75rem; background: rgba(127,127,127,.06);} 
.stButton > button {border-radius: 999px; height: 3.2rem; font-size: 1.05rem; font-weight: 800;}
.stDownloadButton > button {border-radius: 999px;}
[data-testid="stDataFrame"] {border-radius: 14px; overflow: hidden;}
@media (max-width: 640px) {
  .block-container {padding-left: .85rem; padding-right: .85rem; padding-top: .8rem;}
  h1 {font-size: 2.0rem !important; line-height: 1.1;}
  h2 {font-size: 1.35rem !important;}
  h3 {font-size: 1.12rem !important;}
  div[data-testid="stMetric"] {padding: .6rem;}
}
</style>
""",
    unsafe_allow_html=True,
)


@dataclass
class ScanConfig:
    period: str = "6mo"
    interval: str = "1d"
    min_amount_us: float = 20_000_000      # 美股最低成交额，美元
    min_amount_cn: float = 200_000_000     # A股最低成交额，人民币/近似
    buy_target: int = 10
    watch_target: int = 20
    max_sector_count: int = 5


# =============================
# 股票池与名称
# =============================
US_SECTORS: Dict[str, List[str]] = {
    "AI/芯片": ["NVDA", "AMD", "AVGO", "ARM", "MU", "SMCI", "TSM", "ASML", "QCOM", "INTC", "MRVL", "SMH", "SOXL"],
    "大型科技": ["AAPL", "MSFT", "META", "AMZN", "GOOGL", "NFLX", "ORCL", "ADBE", "CRM", "NOW"],
    "加密/金融科技": ["MSTR", "COIN", "HOOD", "SQ", "PYPL", "MARA", "RIOT", "IBIT", "BITO"],
    "新能源/汽车": ["TSLA", "RIVN", "LI", "XPEV", "NIO", "F", "GM", "ON", "ENPH"],
    "高波动热门": ["PLTR", "APP", "ROKU", "SHOP", "SNOW", "CRWD", "DDOG", "NET", "CELH"],
    "杠杆ETF": ["TQQQ", "SQQQ", "SOXL", "SOXS", "SPXL", "SPXS", "TSLL", "NVDL"],
}

CN_SECTORS: Dict[str, List[str]] = {
    "A股AI/算力": ["000977", "603019", "300308", "002230", "300502", "300394", "002236", "688041", "688256", "300496"],
    "A股芯片/半导体": ["688981", "603986", "002371", "300661", "688012", "688008", "688099", "002156", "600584", "002049"],
    "A股低空经济": ["002085", "000099", "688297", "300699", "300424", "300900", "688066", "002097", "000801"],
    "A股机器人": ["300024", "002747", "002031", "300124", "300276", "002896", "688017", "603728", "000837"],
    "A股证券金融": ["600030", "601688", "300059", "601211", "600837", "000776", "601881", "600958", "601066"],
    "A股高成交核心": ["600519", "300750", "002594", "601318", "000001", "600036", "000858", "601899", "002475", "000333"],
}

NAME_MAP: Dict[str, str] = {
    # US
    "NVDA": "英伟达", "AMD": "AMD", "AVGO": "博通", "ARM": "Arm", "MU": "美光科技", "SMCI": "超微电脑", "TSM": "台积电", "ASML": "阿斯麦", "QCOM": "高通", "INTC": "英特尔", "MRVL": "Marvell", "SMH": "半导体ETF", "SOXL": "三倍做多半导体",
    "AAPL": "苹果", "MSFT": "微软", "META": "Meta", "AMZN": "亚马逊", "GOOGL": "谷歌", "NFLX": "奈飞", "ORCL": "甲骨文", "ADBE": "Adobe", "CRM": "Salesforce", "NOW": "ServiceNow",
    "MSTR": "MicroStrategy", "COIN": "Coinbase", "HOOD": "Robinhood", "SQ": "Block", "PYPL": "PayPal", "MARA": "Marathon", "RIOT": "Riot", "IBIT": "比特币现货ETF", "BITO": "比特币期货ETF",
    "TSLA": "特斯拉", "RIVN": "Rivian", "LI": "理想汽车", "XPEV": "小鹏汽车", "NIO": "蔚来", "F": "福特", "GM": "通用汽车", "ON": "安森美", "ENPH": "Enphase",
    "PLTR": "Palantir", "APP": "AppLovin", "ROKU": "Roku", "SHOP": "Shopify", "SNOW": "Snowflake", "CRWD": "CrowdStrike", "DDOG": "Datadog", "NET": "Cloudflare", "CELH": "Celsius",
    "TQQQ": "三倍做多纳指", "SQQQ": "三倍做空纳指", "SOXS": "三倍做空半导体", "SPXL": "三倍做多标普", "SPXS": "三倍做空标普", "TSLL": "特斯拉杠杆ETF", "NVDL": "英伟达杠杆ETF",
    # CN
    "600519": "贵州茅台", "300750": "宁德时代", "002594": "比亚迪", "601318": "中国平安", "000001": "平安银行", "600036": "招商银行", "000858": "五粮液", "601899": "紫金矿业", "002475": "立讯精密", "000333": "美的集团",
    "000977": "浪潮信息", "603019": "中科曙光", "300308": "中际旭创", "002230": "科大讯飞", "300502": "新易盛", "300394": "天孚通信", "002236": "大华股份", "688041": "海光信息", "688256": "寒武纪", "300496": "中科创达",
    "688981": "中芯国际", "603986": "兆易创新", "002371": "北方华创", "300661": "圣邦股份", "688012": "中微公司", "688008": "澜起科技", "688099": "晶晨股份", "002156": "通富微电", "600584": "长电科技", "002049": "紫光国微",
    "002085": "万丰奥威", "000099": "中信海直", "688297": "中无人机", "300699": "光威复材", "300424": "航新科技", "300900": "广联航空", "688066": "航天宏图", "002097": "山河智能", "000801": "四川九洲",
    "300024": "机器人", "002747": "埃斯顿", "002031": "巨轮智能", "300124": "汇川技术", "300276": "三丰智能", "002896": "中大力德", "688017": "绿的谐波", "603728": "鸣志电器", "000837": "秦川机床",
    "600030": "中信证券", "601688": "华泰证券", "300059": "东方财富", "601211": "国泰海通", "600837": "海通证券", "000776": "广发证券", "601881": "中国银河", "600958": "东方证券", "601066": "中信建投",
}


# =============================
# 工具函数
# =============================
def is_cn_code(code: str) -> bool:
    code = code.strip().upper().replace(".SS", "").replace(".SZ", "")
    return code.isdigit() and len(code) == 6


def to_yf_symbol(code: str) -> str:
    raw = code.strip().upper()
    if raw.endswith((".SS", ".SZ")):
        return raw
    if is_cn_code(raw):
        # 6/688/900 上海，其余深圳/创业板
        if raw.startswith(("6", "9")):
            return raw + ".SS"
        return raw + ".SZ"
    return raw


def display_code(symbol: str) -> str:
    return symbol.upper().replace(".SS", "").replace(".SZ", "")


def cn_name(symbol: str) -> str:
    code = display_code(symbol)
    return NAME_MAP.get(code, NAME_MAP.get(symbol.upper(), code))


def parse_manual(raw: str) -> List[str]:
    out = []
    for x in raw.replace("\n", ",").split(","):
        c = x.strip().upper()
        if not c:
            continue
        s = to_yf_symbol(c)
        if s not in out:
            out.append(s)
    return out


@st.cache_data(show_spinner=False, ttl=60 * 20)
def load_history(symbol: str, period: str = "6mo", interval: str = "1d") -> pd.DataFrame:
    try:
        df = yf.download(symbol, period=period, interval=interval, auto_adjust=True, progress=False, threads=False)
        if df is None or df.empty:
            return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex):
            # yfinance may return columns like ('Close','NVDA')
            if symbol in df.columns.get_level_values(-1):
                df = df.xs(symbol, axis=1, level=-1)
            else:
                df.columns = [str(c[0]).title() for c in df.columns]
        df = df.rename(columns={c: str(c).title() for c in df.columns})
        need = ["Open", "High", "Low", "Close", "Volume"]
        if not all(c in df.columns for c in need):
            return pd.DataFrame()
        df = df[need].dropna()
        df.index = pd.to_datetime(df.index)
        return df
    except Exception:
        return pd.DataFrame()


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy()
    x["涨跌幅%"] = x["Close"].pct_change() * 100
    x["5日线"] = x["Close"].rolling(5).mean()
    x["20日线"] = x["Close"].rolling(20).mean()
    x["20日高点"] = x["High"].rolling(20).max()
    x["20日低点"] = x["Low"].rolling(20).min()
    x["均量20"] = x["Volume"].rolling(20).mean()
    x["量比"] = x["Volume"] / x["均量20"]
    x["成交额"] = x["Close"] * x["Volume"]
    x["振幅%"] = (x["High"] - x["Low"]) / x["Close"] * 100
    return x


def tag_for_sector(sector: str, symbol: str) -> str:
    code = display_code(symbol)
    tags = []
    if "芯片" in sector or "AI" in sector or "算力" in sector:
        tags.append("AI/芯片")
    if "加密" in sector or code in ["MSTR", "COIN", "HOOD", "IBIT", "BITO"]:
        tags.append("加密")
    if "杠杆" in sector or code in ["TQQQ", "SQQQ", "SOXL", "SOXS", "SPXL", "SPXS", "TSLL", "NVDL"]:
        tags.append("杠杆ETF")
    if "低空" in sector:
        tags.append("低空经济")
    if not tags:
        tags.append(sector.replace("A股", ""))
    return " / ".join(tags)


def evaluate_stock(symbol: str, sector: str, market: str, cfg: ScanConfig) -> Dict:
    df = load_history(symbol, cfg.period, cfg.interval)
    code = display_code(symbol)
    base = {
        "代码": code,
        "名称": cn_name(symbol),
        "市场": market,
        "板块": sector,
        "标签": tag_for_sector(sector, symbol),
        "信号": "无数据",
        "分数": 0,
        "现价": np.nan,
        "涨跌幅%": np.nan,
        "量比": np.nan,
        "成交额": np.nan,
        "入场": np.nan,
        "止损": np.nan,
        "止盈1": np.nan,
        "止盈2": np.nan,
        "止盈3": np.nan,
        "仓位": "不交易",
        "原因": "没有读取到稳定行情数据",
        "风险": "无数据",
        "symbol": symbol,
    }
    if df.empty or len(df) < 35:
        return base

    ind = add_indicators(df).dropna()
    if ind.empty or len(ind) < 5:
        return base
    last = ind.iloc[-1]
    prev = ind.iloc[-2]
    close = float(last["Close"])
    change = float(last["涨跌幅%"])
    vol_ratio = float(last["量比"])
    amount = float(last["成交额"])
    ma5 = float(last["5日线"])
    ma20 = float(last["20日线"])
    high20 = float(last["20日高点"])
    low20 = float(last["20日低点"])
    prev_high = float(prev["High"])
    prev_low = float(prev["Low"])

    min_amount = cfg.min_amount_cn if market == "A股" else cfg.min_amount_us
    enough_liq = amount >= min_amount
    above20 = close > ma20
    above5 = close > ma5
    momentum = change >= 2.0
    strong_momentum = change >= 5.0
    volume_ok = vol_ratio >= 1.35
    near_high = close >= high20 * 0.96
    breakout = close >= high20 * 0.995
    red_flag_high = change >= 9.0 and vol_ratio >= 2.5
    negative = change < -1.5

    score = 0
    reasons = []
    risks = []
    if enough_liq:
        score += 18; reasons.append("成交额达标")
    else:
        risks.append("成交额偏低")
    if above20:
        score += 18; reasons.append("趋势在20日线上")
    else:
        risks.append("趋势弱于20日线")
    if above5:
        score += 10; reasons.append("站上5日线")
    if momentum:
        score += 18; reasons.append("涨幅强")
    if strong_momentum:
        score += 8; reasons.append("强势大阳")
    if volume_ok:
        score += 16; reasons.append("放量")
    if near_high:
        score += 12; reasons.append("接近20日新高")
    if breakout:
        score += 8; reasons.append("突破/贴近短期高点")
    if negative:
        score -= 16; risks.append("当日走弱")
    if red_flag_high:
        score -= 6; risks.append("涨幅过大，追高风险")
    if "杠杆ETF" in tag_for_sector(sector, symbol):
        score -= 6; risks.append("杠杆ETF，仓位必须小")

    # 信号逻辑：投机者语言
    if not enough_liq:
        signal = "低成交过滤"
    elif score >= 78 and above20 and momentum and volume_ok:
        signal = "强攻观察"
    elif score >= 68 and above20 and volume_ok:
        signal = "突破触发"
    elif score >= 58 and above20:
        signal = "回踩观察"
    elif red_flag_high or (change >= 6 and not volume_ok):
        signal = "高位风险"
    elif score >= 48:
        signal = "弱观察"
    else:
        signal = "弱势过滤"

    # 交易计划：短线投机者纪律
    # 入场：突破昨日高点或现价上方1%，取更接近的触发价
    entry = max(close * 1.006, prev_high * 1.002)
    # 止损：前低、5%止损、20日线三者中取更紧但不能高于入场
    stop_candidates = [entry * 0.95, prev_low * 0.995, ma20 * 0.985]
    stop = max([x for x in stop_candidates if x < entry], default=entry * 0.95)
    # 止盈：分档
    tp1 = entry * 1.055
    tp2 = entry * 1.105
    tp3 = max(entry * 1.17, high20 * 1.03)

    if signal == "强攻观察":
        pos = "试仓20%-30%，不补仓"
    elif signal == "突破触发":
        pos = "只在突破时试仓10%-20%"
    elif signal == "回踩观察":
        pos = "等回踩承接，不追高"
    else:
        pos = "不交易/只观察"

    base.update({
        "信号": signal,
        "分数": int(max(0, min(100, round(score)))),
        "现价": round(close, 3),
        "涨跌幅%": round(change, 2),
        "量比": round(vol_ratio, 2) if math.isfinite(vol_ratio) else np.nan,
        "成交额": round(amount, 0),
        "入场": round(entry, 3),
        "止损": round(stop, 3),
        "止盈1": round(tp1, 3),
        "止盈2": round(tp2, 3),
        "止盈3": round(tp3, 3),
        "仓位": pos,
        "原因": "；".join(reasons) if reasons else "条件不足",
        "风险": "；".join(risks) if risks else "暂未发现硬伤",
    })
    return base


def scan_universe(market_choice: str, manual: str, cfg: ScanConfig) -> Tuple[pd.DataFrame, pd.DataFrame]:
    sectors: Dict[Tuple[str, str], List[str]] = {}
    if market_choice in ["全部", "美股"]:
        for sec, codes in US_SECTORS.items():
            sectors[("美股", sec)] = [to_yf_symbol(x) for x in codes]
    if market_choice in ["全部", "A股"]:
        for sec, codes in CN_SECTORS.items():
            sectors[("A股", sec)] = [to_yf_symbol(x) for x in codes]

    manual_symbols = parse_manual(manual)
    if manual_symbols:
        sectors[("手动", "手动加入")] = manual_symbols

    rows = []
    total_symbols = sum(len(v) for v in sectors.values())
    progress = st.progress(0, text="正在扫描板块与股票…")
    done = 0
    for (market, sector), symbols in sectors.items():
        for sym in symbols:
            m = "A股" if is_cn_code(display_code(sym)) else ("美股" if market == "手动" else market)
            rows.append(evaluate_stock(sym, sector, m, cfg))
            done += 1
            progress.progress(min(done / max(total_symbols, 1), 1.0), text=f"扫描中：{done}/{total_symbols}")
    progress.empty()

    all_df = pd.DataFrame(rows)
    if all_df.empty:
        return pd.DataFrame(), pd.DataFrame()

    # 板块评分
    sector_rows = []
    for (market, sector), g in all_df.groupby(["市场", "板块"], dropna=False):
        valid = g[g["信号"] != "无数据"]
        if valid.empty:
            continue
        up_rate = float((valid["涨跌幅%"].fillna(-999) > 0).mean() * 100)
        strong_count = int(valid["信号"].isin(["强攻观察", "突破触发"]).sum())
        vol_count = int((valid["量比"].fillna(0) >= 1.35).sum())
        avg_change = float(valid["涨跌幅%"].fillna(0).mean())
        top3 = valid.sort_values("分数", ascending=False).head(3)
        score = min(100, int(up_rate * 0.35 + strong_count * 18 + vol_count * 7 + max(avg_change, 0) * 4))
        sector_rows.append({
            "市场": market,
            "板块": sector,
            "强度分": score,
            "上涨率%": round(up_rate, 1),
            "强势股数": strong_count,
            "放量股数": vol_count,
            "平均涨幅%": round(avg_change, 2),
            "前排": "、".join([f"{r['名称']}({r['代码']})" for _, r in top3.iterrows()]),
        })
    sector_df = pd.DataFrame(sector_rows).sort_values("强度分", ascending=False) if sector_rows else pd.DataFrame()

    # 只让强板块进入买入观察，减少弱板块假信号
    if not sector_df.empty:
        strong_keys = set((r["市场"], r["板块"]) for _, r in sector_df.head(cfg.max_sector_count).iterrows())
        all_df["强板块"] = all_df.apply(lambda r: (r["市场"], r["板块"]) in strong_keys, axis=1)
    else:
        all_df["强板块"] = False

    return sector_df, all_df


def temperature(sector_df: pd.DataFrame, all_df: pd.DataFrame) -> Tuple[str, str]:
    if sector_df.empty or all_df.empty:
        return "等待扫描", "先点击开始扫描"
    avg_top = sector_df.head(3)["强度分"].mean() if not sector_df.empty else 0
    strong = int(all_df["信号"].isin(["强攻观察", "突破触发"]).sum())
    if avg_top >= 80 and strong >= 4:
        return "强", "可以找前排，但必须按计划止损"
    if avg_top >= 62 and strong >= 2:
        return "中", "只看最强板块，不追杂毛"
    return "弱", "没有好机会时空仓，不要硬凑交易"


def money_format(x: float) -> str:
    if pd.isna(x):
        return "--"
    x = float(x)
    if x >= 1e9:
        return f"{x/1e9:.2f}B"
    if x >= 1e8:
        return f"{x/1e8:.2f}亿"
    if x >= 1e6:
        return f"{x/1e6:.1f}M"
    return f"{x:.0f}"


def line_list(df: pd.DataFrame, title: str, limit: int = 20) -> None:
    st.subheader(title)
    if df.empty:
        st.info("暂无股票。市场不给机会时，不要硬交易。")
        return
    for _, r in df.head(limit).iterrows():
        with st.container(border=True):
            c1, c2 = st.columns([1.5, 1])
            with c1:
                st.markdown(f"### {r['代码']}  {r['名称']}")
                st.caption(f"{r['市场']} · {r['板块']} · {r['标签']}")
                st.write(f"**信号：{r['信号']}** ｜ 分数 {r['分数']} ｜ 量比 {r['量比']} ｜ 成交额 {money_format(r['成交额'])}")
            with c2:
                chg = r["涨跌幅%"]
                sign = "+" if pd.notna(chg) and chg >= 0 else ""
                st.metric("现价", r["现价"], f"{sign}{chg}%" if pd.notna(chg) else None)
            st.write(f"入场 **{r['入场']}** ｜ 止损 **{r['止损']}** ｜ 止盈 **{r['止盈1']} / {r['止盈2']} / {r['止盈3']}**")
            st.caption(f"原因：{r['原因']} ｜ 风险：{r['风险']} ｜ 仓位：{r['仓位']}")


def chart_for(symbol: str, name: str) -> None:
    df = load_history(symbol, "6mo", "1d")
    if df.empty or len(df) < 30:
        st.warning("K线数据不足。")
        return
    ind = add_indicators(df).dropna()
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=ind.index,
        open=ind["Open"], high=ind["High"], low=ind["Low"], close=ind["Close"],
        name="K线",
        increasing_line_color="#26a69a",
        decreasing_line_color="#ef5350",
    ))
    fig.add_trace(go.Scatter(x=ind.index, y=ind["5日线"], mode="lines", name="5日线", line=dict(width=1.5)))
    fig.add_trace(go.Scatter(x=ind.index, y=ind["20日线"], mode="lines", name="20日线", line=dict(width=1.5)))
    fig.update_layout(
        title=f"{name}（{display_code(symbol)}）K线",
        height=430,
        margin=dict(l=10, r=10, t=45, b=10),
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig, use_container_width=True)


# =============================
# 页面
# =============================
st.title("⚡ 短线投机者交易面板 v13")
st.caption("市场 → 板块 → 前排股票。输出观察名单，也输出入场、硬止损、分批止盈。")

c1, c2 = st.columns([1.2, 1])
with c1:
    market_choice = st.segmented_control("扫描市场", ["全部", "美股", "A股"], default="全部")
with c2:
    st.write("")
    st.write("")
    run = st.button("开始扫描", type="primary", use_container_width=True)

manual = st.text_input("手动加代码（可选，用英文逗号隔开）", placeholder="例如：SPCX, NVDA, 600519, 300750")

cfg = ScanConfig()

if "sector_df" not in st.session_state:
    st.session_state["sector_df"] = pd.DataFrame()
if "all_df" not in st.session_state:
    st.session_state["all_df"] = pd.DataFrame()

if run:
    with st.spinner("按短线漏斗扫描：市场 → 板块 → 前排股票…"):
        sector_df, all_df = scan_universe(market_choice, manual, cfg)
        st.session_state["sector_df"] = sector_df
        st.session_state["all_df"] = all_df

sector_df = st.session_state["sector_df"]
all_df = st.session_state["all_df"]
temp, temp_note = temperature(sector_df, all_df)

buy_df = pd.DataFrame()
watch_df = pd.DataFrame()
filtered_df = pd.DataFrame()
if not all_df.empty:
    # 强板块里的强信号才进入买入观察
    buy_df = all_df[(all_df["强板块"]) & (all_df["信号"].isin(["强攻观察", "突破触发"]))].sort_values("分数", ascending=False).head(cfg.buy_target)
    watch_df = all_df[(all_df["强板块"]) & (all_df["信号"].isin(["回踩观察", "弱观察", "高位风险"]))].sort_values("分数", ascending=False).head(cfg.watch_target)
    filtered_df = all_df[~all_df.index.isin(buy_df.index) & ~all_df.index.isin(watch_df.index)].sort_values("分数", ascending=False)

m1, m2, m3, m4 = st.columns(4)
m1.metric("短线温度", temp, temp_note)
m2.metric("强板块", 0 if sector_df.empty else len(sector_df.head(cfg.max_sector_count)))
m3.metric("买入观察", len(buy_df))
m4.metric("观察名单", len(watch_df))

if temp == "弱" and not all_df.empty:
    st.warning("当前短线温度偏弱：不要为了交易而交易。没有强攻观察，就空仓。")

# Tabs
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["🔥 板块", "🎯 买入观察", "👀 观察名单", "📊 个股详情", "🧹 过滤", "📋 全部"])

with tab1:
    st.subheader("最强板块")
    if sector_df.empty:
        st.info("点击开始扫描后，这里会显示最强板块。")
    else:
        st.dataframe(
            sector_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "强度分": st.column_config.ProgressColumn("强度分", min_value=0, max_value=100),
            },
        )

with tab2:
    line_list(buy_df, "买入观察：只在触发价有效突破时试仓", cfg.buy_target)

with tab3:
    line_list(watch_df, "观察名单：等确认，不追高", cfg.watch_target)

with tab4:
    if all_df.empty:
        st.info("先扫描，再看个股详情。")
    else:
        options_df = pd.concat([buy_df, watch_df, all_df], ignore_index=True).drop_duplicates(subset=["symbol"])
        labels = [f"{r['代码']} {r['名称']}｜{r['信号']}｜{r['板块']}" for _, r in options_df.iterrows()]
        idx = st.selectbox("选择股票", range(len(labels)), format_func=lambda i: labels[i])
        r = options_df.iloc[idx]
        st.markdown(f"## {r['名称']}（{r['代码']}）")
        a, b, c, d = st.columns(4)
        a.metric("现价", r["现价"], f"{r['涨跌幅%']}%")
        b.metric("信号", r["信号"], f"分数 {r['分数']}")
        c.metric("量比", r["量比"])
        d.metric("成交额", money_format(r["成交额"]))
        st.info(f"为什么入选/观察：{r['原因']}\n\n风险提示：{r['风险']}")
        st.success(f"交易计划：入场 {r['入场']} ｜ 硬止损 {r['止损']} ｜ 止盈 {r['止盈1']} / {r['止盈2']} / {r['止盈3']} ｜ 仓位：{r['仓位']}")
        st.write("**如果我是投机者：** 只在突破入场价且成交继续放大时试仓；跌破硬止损直接走；到止盈1先减仓；不补仓，不把盈利单做成亏损单。")
        chart_for(r["symbol"], r["名称"])

with tab5:
    st.subheader("过滤原因")
    if filtered_df.empty:
        st.info("暂无过滤结果。")
    else:
        cols = ["代码", "名称", "市场", "板块", "信号", "分数", "现价", "涨跌幅%", "量比", "成交额", "风险"]
        show = filtered_df[cols].copy()
        show["成交额"] = show["成交额"].apply(money_format)
        st.dataframe(show, use_container_width=True, hide_index=True)

with tab6:
    st.subheader("全部扫描数据")
    if all_df.empty:
        st.info("暂无数据。")
    else:
        cols = ["代码", "名称", "市场", "板块", "标签", "信号", "分数", "现价", "涨跌幅%", "量比", "成交额", "入场", "止损", "止盈1", "止盈2", "止盈3", "原因", "风险"]
        show = all_df[cols].sort_values(["分数"], ascending=False).copy()
        st.dataframe(show, use_container_width=True, hide_index=True)
        st.download_button("下载全部结果CSV", show.to_csv(index=False).encode("utf-8-sig"), "scan_results.csv", "text/csv")

st.caption("纪律：强信号也只是观察；触发价不突破不进；跌破止损就走；不要补仓。")
