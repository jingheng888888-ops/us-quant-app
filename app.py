import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

try:
    import plotly.graph_objects as go
except Exception:  # pragma: no cover
    go = None


st.set_page_config(page_title="短线情绪板块选股器", page_icon="📈", layout="wide")

# -----------------------------
# UI 样式：TradingView / 富途式清爽行情列表
# -----------------------------
st.markdown(
    """
<style>
:root {
  --bg: #f6f7fb;
  --card: #ffffff;
  --text: #111827;
  --muted: #6b7280;
  --line: #e5e7eb;
  --red: #ef4444;
  --green: #059669;
  --blue: #2563eb;
  --soft-red: #fff1f2;
  --soft-green: #ecfdf5;
  --soft-blue: #eff6ff;
}
html, body, [data-testid="stAppViewContainer"] {
  background: var(--bg);
  color: var(--text);
}
.block-container {
  padding-top: 1.05rem;
  padding-bottom: 4rem;
  max-width: 1080px;
}
[data-testid="stHeader"] { background: rgba(246,247,251,.85); backdrop-filter: blur(10px); }
[data-testid="stToolbar"] { display: none; }
.main-title {
  font-size: 1.55rem;
  font-weight: 850;
  letter-spacing: -.03em;
  margin: .15rem 0 .15rem 0;
}
.sub-title {
  color: var(--muted);
  font-size: .92rem;
  margin-bottom: .65rem;
}
.top-card {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 22px;
  padding: 16px 16px 14px 16px;
  box-shadow: 0 12px 30px rgba(15,23,42,.07);
  margin-bottom: .8rem;
}
.metric-grid {
  display:grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin: .65rem 0 .2rem;
}
.mini-metric {
  background: #fbfbfd;
  border: 1px solid var(--line);
  border-radius: 18px;
  padding: 12px;
}
.mini-label { color: var(--muted); font-size:.78rem; }
.mini-value { font-size:1.25rem; font-weight:850; margin-top:.25rem; }
.action-row { display:flex; gap: 10px; align-items:center; flex-wrap:wrap; }
.stButton > button {
  border-radius: 999px !important;
  height: 3.0rem;
  font-weight: 760;
  border: 0 !important;
  box-shadow: 0 10px 22px rgba(239,68,68,.18);
}
.stDownloadButton > button { border-radius: 999px !important; }
[data-testid="stBaseButton-primary"] {
  background: linear-gradient(135deg, #ff6b6b 0%, #ef4444 100%) !important;
}
.stRadio [role="radiogroup"] { gap: .45rem; }
.stRadio label {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: .35rem .65rem;
  box-shadow: 0 6px 18px rgba(15,23,42,.04);
}
.list-card {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 20px;
  overflow: hidden;
  box-shadow: 0 10px 28px rgba(15,23,42,.06);
  margin: .55rem 0 1.0rem;
}
.stock-row {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 10px;
  align-items: center;
  padding: 13px 14px;
  border-bottom: 1px solid var(--line);
  background: #fff;
}
.stock-row:last-child { border-bottom: 0; }
.stock-code { font-size:1.05rem; font-weight:850; letter-spacing:-.01em; }
.stock-name { color: var(--muted); font-size:.85rem; margin-top:.15rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width: 14rem; }
.stock-right { text-align:right; }
.price { font-weight:850; font-size:1.05rem; }
.up { color: var(--green); }
.down { color: var(--red); }
.flat { color: var(--muted); }
.badge {
  display:inline-flex; align-items:center; justify-content:center;
  border-radius: 999px; padding: .16rem .48rem; font-size:.72rem; font-weight:750; margin-left:.25rem;
}
.badge-buy { background: var(--soft-red); color: #be123c; }
.badge-watch { background: var(--soft-blue); color: #1d4ed8; }
.badge-risk { background: #f3f4f6; color: #4b5563; }
.sector-row {
  display:grid; grid-template-columns: 1fr auto; gap: 8px; align-items:center;
  padding: 13px 14px; border-bottom:1px solid var(--line); background:#fff;
}
.sector-row:last-child { border-bottom:0; }
.sector-name { font-weight:850; font-size:1.02rem; }
.sector-meta { color:var(--muted); font-size:.82rem; margin-top:.18rem; }
.sector-score { font-weight:900; font-size:1.25rem; color:#ef4444; }
.reason-box {
  background: var(--soft-blue); color:#1e3a8a; padding:12px 13px; border-radius:16px; font-size:.9rem; line-height:1.55;
}
.warn-box {
  background:#fff7ed; color:#9a3412; padding:12px 13px; border-radius:16px; font-size:.9rem; line-height:1.55;
}
.small-note { color:var(--muted); font-size:.82rem; line-height:1.45; }
hr { border:0; border-top:1px solid var(--line); margin: .7rem 0; }
@media (max-width: 640px) {
  .block-container { padding-left: .75rem; padding-right: .75rem; }
  .main-title { font-size:1.35rem; }
  .metric-grid { grid-template-columns: repeat(2, minmax(0,1fr)); }
  .stock-name { max-width: 12rem; }
  .top-card { border-radius:20px; padding:14px; }
  .stock-row, .sector-row { padding: 12px 12px; }
  [data-testid="stTabs"] button { font-size: .92rem; }
}
</style>
""",
    unsafe_allow_html=True,
)


# -----------------------------
# 数据池：公开数据源可读范围内的固定热门池
# -----------------------------
US_SECTORS: Dict[str, Dict[str, List[str]]] = {
    "AI/芯片": {
        "tags": ["AI", "芯片"],
        "tickers": ["NVDA", "AMD", "AVGO", "ARM", "MU", "SMCI", "TSM", "ASML", "QCOM", "MRVL", "INTC", "SMH", "SOXL"],
    },
    "大型科技": {
        "tags": ["大型科技"],
        "tickers": ["AAPL", "MSFT", "META", "AMZN", "GOOGL", "NFLX", "TSLA", "PLTR", "APP", "ORCL", "CRM"],
    },
    "加密/金融科技": {
        "tags": ["加密", "金融科技"],
        "tickers": ["MSTR", "COIN", "HOOD", "MARA", "RIOT", "CLSK", "PYPL", "SQ", "IBIT", "BITO"],
    },
    "高波动/新股观察": {
        "tags": ["新股", "高波动"],
        "tickers": ["SPCX", "RDDT", "ARM", "DJT", "RIVN", "LCID", "IONQ", "RKLB", "ASTS"],
    },
    "杠杆ETF": {
        "tags": ["杠杆ETF"],
        "tickers": ["TQQQ", "SOXL", "UPRO", "QLD", "TSLL", "NVDL", "TECL"],
    },
}

CN_SECTORS: Dict[str, Dict[str, List[str]]] = {
    "A股AI/算力": {
        "tags": ["AI", "算力"],
        "tickers": ["300308", "000977", "002230", "002281", "603019", "300502", "688041", "300418", "000938", "601138"],
    },
    "A股芯片/半导体": {
        "tags": ["芯片", "半导体"],
        "tickers": ["688981", "603986", "002371", "300782", "002156", "688012", "688008", "600584", "002049", "300661"],
    },
    "A股证券金融": {
        "tags": ["证券", "金融"],
        "tickers": ["600030", "601688", "600837", "000776", "601901", "601995", "601099", "600999", "601318", "600036"],
    },
    "A股高成交核心": {
        "tags": ["高成交", "核心资产"],
        "tickers": ["600519", "300750", "002594", "601318", "000001", "600036", "000858", "601899", "002475", "601012"],
    },
    "A股机器人/低空": {
        "tags": ["机器人", "低空经济"],
        "tickers": ["300124", "002085", "000099", "688297", "002747", "300580", "002031", "002050", "300024", "002444"],
    },
    "A股消费医药": {
        "tags": ["消费", "医药"],
        "tickers": ["600519", "000858", "600887", "000333", "600276", "300760", "000661", "603259", "000568", "600809"],
    },
}

NAME_MAP = {
    # US
    "NVDA": "英伟达", "AMD": "AMD", "AVGO": "博通", "ARM": "ARM", "MU": "美光科技", "SMCI": "超微电脑",
    "TSM": "台积电", "ASML": "阿斯麦", "QCOM": "高通", "MRVL": "迈威尔", "INTC": "英特尔", "SMH": "半导体ETF", "SOXL": "三倍半导体ETF",
    "AAPL": "苹果", "MSFT": "微软", "META": "Meta", "AMZN": "亚马逊", "GOOGL": "谷歌", "NFLX": "奈飞", "TSLA": "特斯拉", "PLTR": "Palantir", "APP": "AppLovin", "ORCL": "甲骨文", "CRM": "赛富时",
    "MSTR": "MicroStrategy", "COIN": "Coinbase", "HOOD": "Robinhood", "MARA": "MARA", "RIOT": "Riot", "CLSK": "CleanSpark", "PYPL": "PayPal", "SQ": "Block", "IBIT": "比特币ETF", "BITO": "比特币期货ETF",
    "SPCX": "SpaceX", "RDDT": "Reddit", "DJT": "特朗普媒体", "RIVN": "Rivian", "LCID": "Lucid", "IONQ": "IonQ", "RKLB": "Rocket Lab", "ASTS": "AST SpaceMobile", "TQQQ": "三倍纳指ETF", "UPRO": "三倍标普ETF", "QLD": "两倍纳指ETF", "TSLL": "特斯拉杠杆ETF", "NVDL": "英伟达杠杆ETF", "TECL": "三倍科技ETF",
    # CN
    "600519": "贵州茅台", "300750": "宁德时代", "002594": "比亚迪", "601318": "中国平安", "000001": "平安银行", "600036": "招商银行", "000858": "五粮液", "601899": "紫金矿业", "002475": "立讯精密", "601012": "隆基绿能",
    "300308": "中际旭创", "000977": "浪潮信息", "002230": "科大讯飞", "002281": "光迅科技", "603019": "中科曙光", "300502": "新易盛", "688041": "海光信息", "300418": "昆仑万维", "000938": "紫光股份", "601138": "工业富联",
    "688981": "中芯国际", "603986": "兆易创新", "002371": "北方华创", "300782": "卓胜微", "002156": "通富微电", "688012": "中微公司", "688008": "澜起科技", "600584": "长电科技", "002049": "紫光国微", "300661": "圣邦股份",
    "600030": "中信证券", "601688": "华泰证券", "600837": "海通证券", "000776": "广发证券", "601901": "方正证券", "601995": "中金公司", "601099": "太平洋", "600999": "招商证券",
    "300124": "汇川技术", "002085": "万丰奥威", "000099": "中信海直", "688297": "中无人机", "002747": "埃斯顿", "300580": "贝斯特", "002031": "巨轮智能", "002050": "三花智控", "300024": "机器人", "002444": "巨星科技",
    "600887": "伊利股份", "000333": "美的集团", "600276": "恒瑞医药", "300760": "迈瑞医疗", "000661": "长春高新", "603259": "药明康德", "000568": "泸州老窖", "600809": "山西汾酒",
}


@dataclass
class ScanSettings:
    markets: List[str]
    top_sector_count: int = 4
    buy_target: int = 10
    watch_target: int = 20
    min_us_turnover_m: float = 20.0
    min_cn_turnover_m: float = 150.0
    min_ret_pct: float = 1.2
    strong_ret_pct: float = 2.0
    vol_ratio: float = 1.3
    period: str = "3mo"


# -----------------------------
# 数据与指标
# -----------------------------
def to_yf_symbol(raw: str, market: str) -> str:
    s = str(raw).strip().upper()
    if market == "美股":
        return s
    code = s.split(".")[0]
    if code.startswith(("6", "9")) or code.startswith("688"):
        return f"{code}.SS"
    return f"{code}.SZ"


def display_code(symbol: str, market: str) -> str:
    if market == "美股":
        return symbol.upper()
    return symbol.split(".")[0]


def stock_name(code: str) -> str:
    return NAME_MAP.get(code.split(".")[0].upper(), code.split(".")[0].upper())


@st.cache_data(show_spinner=False, ttl=60 * 15)
def load_history(yf_symbol: str, period: str = "3mo") -> pd.DataFrame:
    try:
        df = yf.download(yf_symbol, period=period, interval="1d", auto_adjust=True, progress=False, threads=False)
    except Exception:
        return pd.DataFrame()
    if df is None or df.empty:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        # yfinance 有时返回 MultiIndex：优先压成 OHLCV
        for level in range(df.columns.nlevels):
            vals = [str(v).upper() for v in df.columns.get_level_values(level)]
            if yf_symbol.upper() in vals:
                try:
                    df = df.xs(yf_symbol.upper(), level=level, axis=1, drop_level=True)
                    break
                except Exception:
                    pass
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [str(c[-1]) if str(c[-1]) else str(c[0]) for c in df.columns]
    df = df.rename(columns={c: str(c).title() for c in df.columns})
    need = ["Open", "High", "Low", "Close", "Volume"]
    if not all(c in df.columns for c in need):
        return pd.DataFrame()
    out = df[need].dropna().copy()
    out.index = pd.to_datetime(out.index)
    return out


def compute_metrics(df: pd.DataFrame) -> Dict[str, float]:
    if df.empty or len(df) < 25:
        raise ValueError("数据不足")
    d = df.copy()
    d["ma5"] = d["Close"].rolling(5).mean()
    d["ma20"] = d["Close"].rolling(20).mean()
    d["vol20"] = d["Volume"].rolling(20).mean()
    d["ret"] = d["Close"].pct_change() * 100
    d["high20"] = d["Close"].rolling(20).max()
    last = d.dropna().iloc[-1]
    price = float(last["Close"])
    ret = float(last["ret"])
    volr = float(last["Volume"] / last["vol20"]) if last["vol20"] else 0.0
    turnover = float(last["Close"] * last["Volume"] / 1_000_000)
    near_high = float(last["Close"] / last["high20"] * 100) if last["high20"] else 0.0
    trend = bool(last["Close"] > last["ma20"] and last["ma5"] > last["ma20"])
    draw20 = float(last["Close"] / last["high20"] - 1) * 100 if last["high20"] else 0.0
    return {
        "现价": price,
        "涨跌幅%": ret,
        "量比": volr,
        "成交额百万": turnover,
        "20日新高接近度%": near_high,
        "趋势通过": trend,
        "20日回撤%": draw20,
        "MA5": float(last["ma5"]),
        "MA20": float(last["ma20"]),
    }


def score_stock(row: Dict, settings: ScanSettings) -> Tuple[int, str, str]:
    market = row["市场"]
    min_turnover = settings.min_us_turnover_m if market == "美股" else settings.min_cn_turnover_m
    ret = row["涨跌幅%"]
    volr = row["量比"]
    turnover = row["成交额百万"]
    near = row["20日新高接近度%"]
    trend = row["趋势通过"]
    tags = row.get("标签", "")

    score = 0
    reasons = []
    risk = []

    if turnover >= min_turnover:
        score += 16
        reasons.append("成交额达标")
    else:
        risk.append("成交额偏低")

    if trend:
        score += 20
        reasons.append("趋势在20日线上")
    else:
        risk.append("趋势未确认")

    if ret >= settings.strong_ret_pct:
        score += 22
        reasons.append("涨幅强")
    elif ret >= settings.min_ret_pct:
        score += 12
        reasons.append("小幅走强")
    elif ret < 0:
        risk.append("当日走弱")

    if volr >= settings.vol_ratio:
        score += 18
        reasons.append("放量")
    elif volr < 0.8:
        risk.append("量能不足")

    if near >= 96:
        score += 14
        reasons.append("接近20日新高")
    elif near < 90:
        risk.append("距离近期高点较远")

    # A股涨停近似，美股大阳线近似
    if market == "A股" and ret >= 9.0:
        score += 12
        reasons.append("接近涨停/强势大阳")
    if market == "美股" and ret >= 5.0:
        score += 8
        reasons.append("美股强势大阳")

    if "杠杆ETF" in tags:
        score -= 8
        risk.append("杠杆ETF，波动大")
    if "新股" in tags or "高波动" in tags:
        score -= 4
        risk.append("高波动标的")

    score = max(0, min(100, int(score)))
    if turnover < min_turnover * 0.45:
        signal = "低成交过滤"
    elif score >= 82:
        signal = "买入观察"
    elif score >= 65:
        signal = "观察"
    elif score >= 48:
        signal = "弱观察"
    else:
        signal = "过滤"

    if risk and signal in ["买入观察", "观察"]:
        # 有风险但分数够，仍可观察，但原因要提示
        pass

    reason_text = "；".join(reasons) if reasons else "无明显强势信号"
    risk_text = "；".join(risk) if risk else "暂未发现硬伤"
    return score, signal, f"{reason_text}｜风险：{risk_text}"


def scan_stock(raw_symbol: str, market: str, sector: str, tags: List[str], settings: ScanSettings) -> Optional[Dict]:
    yf_symbol = to_yf_symbol(raw_symbol, market)
    code = display_code(yf_symbol, market)
    df = load_history(yf_symbol, settings.period)
    if df.empty:
        return {
            "代码": code,
            "名称": stock_name(code),
            "市场": market,
            "板块": sector,
            "信号": "无数据",
            "分数": 0,
            "现价": None,
            "涨跌幅%": None,
            "量比": None,
            "成交额百万": None,
            "标签": " / ".join(tags),
            "原因": "公开数据源未读取到行情",
            "yf_symbol": yf_symbol,
        }
    try:
        metrics = compute_metrics(df)
    except Exception:
        return {
            "代码": code,
            "名称": stock_name(code),
            "市场": market,
            "板块": sector,
            "信号": "无数据",
            "分数": 0,
            "现价": None,
            "涨跌幅%": None,
            "量比": None,
            "成交额百万": None,
            "标签": " / ".join(tags),
            "原因": "历史数据不足，无法计算指标",
            "yf_symbol": yf_symbol,
        }

    row = {
        "代码": code,
        "名称": stock_name(code),
        "市场": market,
        "板块": sector,
        "标签": " / ".join(tags),
        "yf_symbol": yf_symbol,
        **metrics,
    }
    score, signal, reason = score_stock(row, settings)
    row["分数"] = score
    row["信号"] = signal
    row["原因"] = reason
    return row


def sector_pool_for_markets(markets: List[str]) -> List[Tuple[str, str, Dict]]:
    pools = []
    if "美股" in markets:
        for sector, data in US_SECTORS.items():
            pools.append(("美股", sector, data))
    if "A股" in markets:
        for sector, data in CN_SECTORS.items():
            pools.append(("A股", sector, data))
    return pools


def score_sector(rows: List[Dict], market: str, sector: str) -> Dict:
    valid = [r for r in rows if r and r.get("信号") != "无数据" and r.get("涨跌幅%") is not None]
    if not valid:
        return {"市场": market, "板块": sector, "强度分": 0, "上涨率%": 0, "强势数": 0, "放量数": 0, "前排": "无", "样本数": 0}
    rets = [float(r["涨跌幅%"] or 0) for r in valid]
    vols = [float(r["量比"] or 0) for r in valid]
    scores = [int(r["分数"] or 0) for r in valid]
    up_rate = sum(1 for x in rets if x > 0) / len(rets) * 100
    strong_cnt = sum(1 for r in valid if (r.get("涨跌幅%") or 0) >= 2 and (r.get("分数") or 0) >= 55)
    vol_cnt = sum(1 for v in vols if v >= 1.3)
    near_cnt = sum(1 for r in valid if (r.get("20日新高接近度%") or 0) >= 96)
    top3 = sorted(valid, key=lambda r: (r.get("分数") or 0, r.get("涨跌幅%") or 0), reverse=True)[:3]
    top3_ret = np.mean([r.get("涨跌幅%") or 0 for r in top3]) if top3 else 0
    raw = up_rate * 0.22 + strong_cnt * 8 + vol_cnt * 5 + near_cnt * 4 + max(top3_ret, 0) * 2.5 + np.mean(scores) * 0.22
    strength = int(max(0, min(100, raw)))
    leaders = "、".join([f"{r['名称']}({r['代码']})" for r in top3])
    return {
        "市场": market,
        "板块": sector,
        "强度分": strength,
        "上涨率%": round(up_rate, 1),
        "强势数": strong_cnt,
        "放量数": vol_cnt,
        "接近新高数": near_cnt,
        "前排": leaders,
        "样本数": len(valid),
    }


def run_scan(settings: ScanSettings, manual: str = "") -> Tuple[pd.DataFrame, pd.DataFrame]:
    all_rows: List[Dict] = []
    sector_scores: List[Dict] = []
    pools = sector_pool_for_markets(settings.markets)

    # 第一层：逐板块扫描，计算板块强弱
    for market, sector, data in pools:
        rows = []
        for t in data["tickers"]:
            r = scan_stock(t, market, sector, data.get("tags", []), settings)
            rows.append(r)
        all_rows.extend(rows)
        sector_scores.append(score_sector(rows, market, sector))

    sector_df = pd.DataFrame(sector_scores).sort_values("强度分", ascending=False).reset_index(drop=True)
    if sector_df.empty:
        return sector_df, pd.DataFrame(all_rows)

    hot_keys = set(zip(sector_df.head(settings.top_sector_count)["市场"], sector_df.head(settings.top_sector_count)["板块"]))
    result = pd.DataFrame(all_rows)
    if result.empty:
        return sector_df, result
    result["热门板块"] = result.apply(lambda r: (r["市场"], r["板块"]) in hot_keys, axis=1)

    # 手动加入：用户可以输入 SPCX/NVDA/600519 等，放入“手动添加”板块
    manual_rows: List[Dict] = []
    manual_items = [x.strip().upper() for x in manual.replace("\n", ",").split(",") if x.strip()]
    for item in manual_items:
        if item.isdigit() or item.split(".")[0].isdigit():
            m = "A股"
        else:
            m = "美股"
        if m in settings.markets:
            manual_rows.append(scan_stock(item, m, "手动添加", ["手动"], settings))
    if manual_rows:
        manual_df = pd.DataFrame(manual_rows)
        manual_df["热门板块"] = True
        result = pd.concat([result, manual_df], ignore_index=True)

    # 只让强板块里的股票进入核心输出；弱板块只能作为全部数据
    result["核心候选"] = result["热门板块"] & result["信号"].isin(["买入观察", "观察", "弱观察"])
    result = result.sort_values(["核心候选", "分数", "涨跌幅%"], ascending=[False, False, False], na_position="last").reset_index(drop=True)
    return sector_df, result


# -----------------------------
# 显示组件
# -----------------------------
def fmt_num(x, digits=2, suffix=""):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "--"
    try:
        return f"{float(x):,.{digits}f}{suffix}"
    except Exception:
        return "--"


def signal_badge(signal: str) -> str:
    if signal == "买入观察":
        return "badge badge-buy"
    if signal in ["观察", "弱观察"]:
        return "badge badge-watch"
    return "badge badge-risk"


def color_class(ret) -> str:
    try:
        r = float(ret)
    except Exception:
        return "flat"
    if r > 0:
        return "up"
    if r < 0:
        return "down"
    return "flat"


def render_stock_list(df: pd.DataFrame, limit: int = 20):
    if df is None or df.empty:
        st.info("暂无符合条件的股票。市场不给机会时，空仓是纪律。")
        return
    st.markdown('<div class="list-card">', unsafe_allow_html=True)
    for _, r in df.head(limit).iterrows():
        ret = r.get("涨跌幅%")
        cls = color_class(ret)
        sig = str(r.get("信号", ""))
        html = f"""
<div class="stock-row">
  <div>
    <div class="stock-code">{r.get('代码','--')} <span class="badge {signal_badge(sig).replace('badge ', '')}">{sig}</span></div>
    <div class="stock-name">{r.get('名称','--')} · {r.get('市场','--')} · {r.get('板块','--')}</div>
  </div>
  <div class="stock-right">
    <div class="price">{fmt_num(r.get('现价'), 2)}</div>
    <div class="{cls}">{fmt_num(ret, 2, '%')}</div>
  </div>
</div>
"""
        st.markdown(html, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def render_sector_list(df: pd.DataFrame, limit: int = 8):
    if df is None or df.empty:
        st.info("暂无板块数据。")
        return
    st.markdown('<div class="list-card">', unsafe_allow_html=True)
    for _, r in df.head(limit).iterrows():
        html = f"""
<div class="sector-row">
  <div>
    <div class="sector-name">🔥 {r.get('板块','--')} <span class="badge badge-watch">{r.get('市场','--')}</span></div>
    <div class="sector-meta">上涨率 {fmt_num(r.get('上涨率%'),1,'%')} · 强势 {int(r.get('强势数',0))} · 放量 {int(r.get('放量数',0))}</div>
    <div class="sector-meta">前排：{r.get('前排','--')}</div>
  </div>
  <div class="sector-score">{int(r.get('强度分',0))}</div>
</div>
"""
        st.markdown(html, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def clean_output(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    cols = ["代码", "名称", "市场", "板块", "信号", "分数", "现价", "涨跌幅%", "量比", "成交额百万", "标签", "原因"]
    out = df[[c for c in cols if c in df.columns]].copy()
    for c in ["现价", "涨跌幅%", "量比", "成交额百万"]:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce").round(2)
    return out


def kline_chart(symbol: str, title: str):
    df = load_history(symbol, "6mo")
    if df.empty:
        st.warning("该标的暂时没有K线数据。")
        return
    d = df.copy()
    d["MA5"] = d["Close"].rolling(5).mean()
    d["MA20"] = d["Close"].rolling(20).mean()
    if go is None:
        st.line_chart(d[["Close", "MA5", "MA20"]].dropna())
        return
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=d.index, open=d["Open"], high=d["High"], low=d["Low"], close=d["Close"], name="K线"))
    fig.add_trace(go.Scatter(x=d.index, y=d["MA5"], mode="lines", name="5日线"))
    fig.add_trace(go.Scatter(x=d.index, y=d["MA20"], mode="lines", name="20日线"))
    fig.update_layout(
        title=title,
        height=430,
        margin=dict(l=8, r=8, t=44, b=8),
        xaxis_rangeslider_visible=False,
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig, use_container_width=True)


# -----------------------------
# 页面：不使用侧边栏，手机首屏即操作
# -----------------------------
st.markdown('<div class="main-title">短线情绪板块选股器</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">先自动找热门板块，再从强板块里筛前排股票。不是下单命令，是观察清单。</div>', unsafe_allow_html=True)

with st.container():
    st.markdown('<div class="top-card">', unsafe_allow_html=True)
    c1, c2 = st.columns([1.35, 1])
    with c1:
        market_choice = st.radio("市场", ["全部", "美股", "A股"], horizontal=True, label_visibility="collapsed", index=0)
    with c2:
        st.write("")
        start = st.button("开始自动扫描", type="primary", use_container_width=True)

    with st.expander("少量设置 / 手动添加", expanded=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            top_sector_count = st.slider("热门板块数量", 2, 6, 4, 1)
        with c2:
            buy_target = st.slider("买入观察最多", 3, 15, 10, 1)
        with c3:
            watch_target = st.slider("观察名单最多", 5, 30, 20, 1)
        manual = st.text_input("手动追加股票，可不填", placeholder="例如：SPCX, NVDA, 600519, 300750")
        st.caption("小白保持默认即可。手动追加只用于你特别关注的股票。")
    st.markdown('</div>', unsafe_allow_html=True)

markets = ["美股", "A股"] if market_choice == "全部" else [market_choice]
settings = ScanSettings(markets=markets, top_sector_count=top_sector_count, buy_target=buy_target, watch_target=watch_target)

if "sector_df" not in st.session_state:
    st.session_state.sector_df = pd.DataFrame()
if "result_df" not in st.session_state:
    st.session_state.result_df = pd.DataFrame()
if "last_market" not in st.session_state:
    st.session_state.last_market = "未扫描"

if start:
    with st.spinner("正在先扫板块，再从强板块里找前排股票..."):
        sector_df, result_df = run_scan(settings, manual)
        st.session_state.sector_df = sector_df
        st.session_state.result_df = result_df
        st.session_state.last_market = market_choice

sector_df = st.session_state.sector_df
result_df = st.session_state.result_df

# 结果分组
if not result_df.empty:
    hot_df = result_df[result_df.get("热门板块", False) == True].copy()
    buy_df = hot_df[hot_df["信号"] == "买入观察"].sort_values("分数", ascending=False).head(settings.buy_target)
    watch_df = hot_df[hot_df["信号"].isin(["观察", "弱观察"])].sort_values("分数", ascending=False).head(settings.watch_target)
    filtered_df = result_df[~result_df.index.isin(buy_df.index) & ~result_df.index.isin(watch_df.index)].copy()
else:
    hot_df = buy_df = watch_df = filtered_df = pd.DataFrame()

# 顶部状态卡
avg_sector = int(sector_df["强度分"].mean()) if not sector_df.empty else 0
if avg_sector >= 70:
    temp = "偏强"
elif avg_sector >= 50:
    temp = "一般"
elif sector_df.empty:
    temp = "等待扫描"
else:
    temp = "偏弱"

st.markdown('<div class="metric-grid">', unsafe_allow_html=True)
st.markdown(f'<div class="mini-metric"><div class="mini-label">短线温度</div><div class="mini-value">{temp}</div></div>', unsafe_allow_html=True)
st.markdown(f'<div class="mini-metric"><div class="mini-label">最强板块</div><div class="mini-value">{len(sector_df) if not sector_df.empty else 0}</div></div>', unsafe_allow_html=True)
st.markdown(f'<div class="mini-metric"><div class="mini-label">买入观察</div><div class="mini-value">{len(buy_df)}</div></div>', unsafe_allow_html=True)
st.markdown(f'<div class="mini-metric"><div class="mini-label">观察名单</div><div class="mini-value">{len(watch_df)}</div></div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

if result_df.empty:
    st.markdown('<div class="reason-box">选择市场后点“开始自动扫描”。系统会先找热门板块，再从热门板块里筛股票。你不用先选板块。</div>', unsafe_allow_html=True)

# 主体 Tabs
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["🔥 最强板块", "🎯 买入观察", "👀 观察名单", "📊 个股详情", "🧹 过滤原因", "📋 全部数据"])

with tab1:
    st.subheader("最强板块排行榜")
    render_sector_list(sector_df, limit=10)
    if not sector_df.empty:
        st.dataframe(sector_df, use_container_width=True, hide_index=True)

with tab2:
    st.subheader("买入观察")
    st.caption("只从强板块里找前排；没有就是没有，不强行凑数。")
    render_stock_list(buy_df, limit=settings.buy_target)
    if not buy_df.empty:
        st.dataframe(clean_output(buy_df), use_container_width=True, hide_index=True)

with tab3:
    st.subheader("观察名单")
    render_stock_list(watch_df, limit=settings.watch_target)
    if not watch_df.empty:
        st.dataframe(clean_output(watch_df), use_container_width=True, hide_index=True)

with tab4:
    st.subheader("个股详情 / K线")
    detail_source = pd.concat([buy_df, watch_df, hot_df], ignore_index=True) if not result_df.empty else pd.DataFrame()
    if detail_source.empty:
        st.info("扫描后这里会出现可查看的股票。")
    else:
        detail_source = detail_source.drop_duplicates(subset=["市场", "代码"])
        options = [f"{r['代码']} · {r['名称']} · {r['市场']} · {r['信号']}" for _, r in detail_source.iterrows()]
        selected = st.selectbox("选择股票", options)
        idx = options.index(selected)
        r = detail_source.iloc[idx]
        cc1, cc2, cc3, cc4 = st.columns(4)
        cc1.metric("现价", fmt_num(r.get("现价"), 2))
        cc2.metric("涨跌幅", fmt_num(r.get("涨跌幅%"), 2, "%"))
        cc3.metric("量比", fmt_num(r.get("量比"), 2))
        cc4.metric("成交额", fmt_num(r.get("成交额百万"), 1, "百万"))
        st.markdown(f'<div class="reason-box">为什么入选/观察：{r.get("原因", "--")}</div>', unsafe_allow_html=True)
        st.write("")
        kline_chart(r.get("yf_symbol"), f"{r.get('名称')}（{r.get('代码')}）")

with tab5:
    st.subheader("过滤原因")
    st.caption("这个页面比买入名单更重要：它告诉你哪些票不该碰。")
    if filtered_df.empty:
        st.info("暂无过滤结果。")
    else:
        cols = ["代码", "名称", "市场", "板块", "信号", "分数", "涨跌幅%", "成交额百万", "原因"]
        st.dataframe(filtered_df[[c for c in cols if c in filtered_df.columns]].head(80), use_container_width=True, hide_index=True)

with tab6:
    st.subheader("全部扫描数据")
    if result_df.empty:
        st.info("还没有扫描。")
    else:
        out = clean_output(result_df)
        st.dataframe(out, use_container_width=True, hide_index=True)
        st.download_button("下载CSV", out.to_csv(index=False).encode("utf-8-sig"), file_name="短线情绪选股结果.csv", mime="text/csv")

st.markdown("---")
st.markdown('<div class="small-note">提示：公开数据源可能延迟或缺失。A股涨停/炸板率、龙虎榜席位、新闻催化属于专业数据源模块，本版本先保留结构，后续可以接入。</div>', unsafe_allow_html=True)
