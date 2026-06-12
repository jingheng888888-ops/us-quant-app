import math
from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf


st.set_page_config(
    page_title="美股短线量化扫描器",
    page_icon="📈",
    layout="centered",
)

st.markdown(
    """
    <style>
    .block-container {padding-top: 1.2rem; padding-bottom: 1.2rem;}
    div[data-testid="stMetric"] {background: #F8FAFC; border: 1px solid #E2E8F0; padding: 0.7rem; border-radius: 0.75rem;}
    @media (max-width: 640px) {
        .block-container {padding-left: 0.75rem; padding-right: 0.75rem;}
        h1 {font-size: 1.55rem !important;}
        h2, h3 {font-size: 1.15rem !important;}
        div[data-testid="stHorizontalBlock"] {gap: 0.35rem;}
        div[data-testid="stMetric"] {padding: 0.55rem;}
        .stDataFrame {font-size: 0.82rem;}
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@dataclass
class StrategyParams:
    short_ma: int = 5
    long_ma: int = 20
    volume_window: int = 20
    volume_multiplier: float = 1.5
    min_daily_return_pct: float = 2.0
    stop_loss_pct: float = 5.0
    max_hold_days: int = 5
    use_market_filter: bool = True
    market_ticker: str = "QQQ"


def _clean_ticker(ticker: str) -> str:
    return ticker.strip().upper().replace(" ", "")


def parse_tickers(raw: str) -> List[str]:
    tickers = []
    for item in raw.replace("\n", ",").split(","):
        t = _clean_ticker(item)
        if t and t not in tickers:
            tickers.append(t)
    return tickers


def normalize_yf_columns(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """Handle yfinance normal columns and MultiIndex columns."""
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()
    if isinstance(out.columns, pd.MultiIndex):
        levels = out.columns.names
        upper_ticker = ticker.upper()

        # Common shapes:
        # 1) columns = MultiIndex([('Close','AAPL'), ...])
        # 2) columns = MultiIndex([('AAPL','Close'), ...])
        for level in range(out.columns.nlevels):
            values = [str(v).upper() for v in out.columns.get_level_values(level)]
            if upper_ticker in values:
                try:
                    out = out.xs(upper_ticker, level=level, axis=1, drop_level=True)
                    break
                except Exception:
                    pass
        else:
            out.columns = ["_".join([str(x) for x in col if str(x) != ""]) for col in out.columns]

    out = out.rename(columns={c: str(c).title() for c in out.columns})
    required = ["Open", "High", "Low", "Close", "Volume"]
    missing = [c for c in required if c not in out.columns]
    if missing:
        return pd.DataFrame()

    out = out[required].dropna()
    out.index = pd.to_datetime(out.index)
    return out


@st.cache_data(show_spinner=False, ttl=60 * 30)
def load_history(ticker: str, period: str, interval: str) -> pd.DataFrame:
    ticker = _clean_ticker(ticker)
    try:
        df = yf.download(
            ticker,
            period=period,
            interval=interval,
            auto_adjust=True,
            progress=False,
            threads=False,
        )
        return normalize_yf_columns(df, ticker)
    except Exception:
        return pd.DataFrame()


def add_indicators(df: pd.DataFrame, params: StrategyParams) -> pd.DataFrame:
    out = df.copy()
    out["MA_SHORT"] = out["Close"].rolling(params.short_ma).mean()
    out["MA_LONG"] = out["Close"].rolling(params.long_ma).mean()
    out["VOL_MA"] = out["Volume"].rolling(params.volume_window).mean()
    out["RET_1D"] = out["Close"].pct_change()
    out["VOL_RATIO"] = out["Volume"] / out["VOL_MA"]
    out["HIGH_20"] = out["Close"].rolling(20).max()
    out["DRAWDOWN_20"] = out["Close"] / out["HIGH_20"] - 1
    out["RANGE_PCT"] = (out["High"] - out["Low"]) / out["Close"]
    return out


def market_ok(params: StrategyParams, period: str, interval: str) -> Tuple[bool, str]:
    if not params.use_market_filter:
        return True, "未启用市场过滤"
    mdf = load_history(params.market_ticker, period, interval)
    if mdf.empty or len(mdf) < params.long_ma + 2:
        return False, f"无法读取市场过滤标的 {params.market_ticker}"
    mdf = add_indicators(mdf, params).dropna()
    if mdf.empty:
        return False, f"{params.market_ticker} 数据不足"
    last = mdf.iloc[-1]
    ok = bool(last["Close"] > last["MA_LONG"])
    reason = f"{params.market_ticker}: 收盘 {last['Close']:.2f}，长均线 {last['MA_LONG']:.2f}"
    return ok, reason


def classify_signal(row: pd.Series, market_is_ok: bool, params: StrategyParams) -> Tuple[str, int, str]:
    trend_ok = bool(row["Close"] > row["MA_LONG"] and row["MA_SHORT"] > row["MA_LONG"])
    momentum_ok = bool(row["RET_1D"] >= params.min_daily_return_pct / 100)
    volume_ok = bool(row["VOL_RATIO"] >= params.volume_multiplier)
    risk_exit = bool(row["Close"] < row["MA_LONG"] or row["DRAWDOWN_20"] <= -params.stop_loss_pct / 100)

    score = 0
    score += 30 if trend_ok else 0
    score += 25 if momentum_ok else 0
    score += 25 if volume_ok else 0
    score += 20 if market_is_ok else 0

    reasons = []
    reasons.append("趋势强" if trend_ok else "趋势弱")
    reasons.append("有动量" if momentum_ok else "动量不足")
    reasons.append("放量" if volume_ok else "量能不足")
    reasons.append("大盘允许" if market_is_ok else "大盘过滤不通过")

    if risk_exit:
        signal = "EXIT_RISK"
    elif trend_ok and momentum_ok and volume_ok and market_is_ok:
        signal = "BUY_WATCH"
    elif trend_ok and market_is_ok:
        signal = "WATCH"
    else:
        signal = "NO_TRADE"

    return signal, int(score), " / ".join(reasons)


def scan_ticker(ticker: str, params: StrategyParams, period: str, interval: str, market_is_ok: bool) -> Dict:
    df = load_history(ticker, period, interval)
    if df.empty or len(df) < max(params.long_ma, params.volume_window) + 5:
        return {
            "Ticker": ticker,
            "Signal": "NO_DATA",
            "Score": 0,
            "Close": np.nan,
            "Ret_1D_%": np.nan,
            "Vol_Ratio": np.nan,
            "MA_Short": np.nan,
            "MA_Long": np.nan,
            "Risk": "数据不足",
            "Reason": "无法读取足够历史行情",
        }

    ind = add_indicators(df, params).dropna()
    if ind.empty:
        return {
            "Ticker": ticker,
            "Signal": "NO_DATA",
            "Score": 0,
            "Close": np.nan,
            "Ret_1D_%": np.nan,
            "Vol_Ratio": np.nan,
            "MA_Short": np.nan,
            "MA_Long": np.nan,
            "Risk": "数据不足",
            "Reason": "指标计算后数据不足",
        }

    last = ind.iloc[-1]
    signal, score, reason = classify_signal(last, market_is_ok, params)

    if signal == "BUY_WATCH":
        risk = "中：只观察，不盲追"
    elif signal == "WATCH":
        risk = "中：等突破确认"
    elif signal == "EXIT_RISK":
        risk = "高：趋势/回撤风险"
    else:
        risk = "低机会：不碰"

    return {
        "Ticker": ticker,
        "Signal": signal,
        "Score": score,
        "Close": round(float(last["Close"]), 2),
        "Ret_1D_%": round(float(last["RET_1D"] * 100), 2),
        "Vol_Ratio": round(float(last["VOL_RATIO"]), 2),
        "MA_Short": round(float(last["MA_SHORT"]), 2),
        "MA_Long": round(float(last["MA_LONG"]), 2),
        "Risk": risk,
        "Reason": reason,
    }


def build_trade_signals(df: pd.DataFrame, params: StrategyParams, market_series: pd.Series | None = None) -> pd.DataFrame:
    out = add_indicators(df, params).copy()
    out["MARKET_OK"] = True
    if market_series is not None:
        aligned = market_series.reindex(out.index).ffill().fillna(False)
        out["MARKET_OK"] = aligned.astype(bool)

    out["BUY_CONDITION"] = (
        (out["Close"] > out["MA_LONG"])
        & (out["MA_SHORT"] > out["MA_LONG"])
        & (out["RET_1D"] >= params.min_daily_return_pct / 100)
        & (out["VOL_RATIO"] >= params.volume_multiplier)
        & (out["MARKET_OK"])
    )
    out["SELL_CONDITION"] = (out["Close"] < out["MA_LONG"]) | (out["DRAWDOWN_20"] <= -params.stop_loss_pct / 100)
    return out.dropna().copy()


def run_backtest(df: pd.DataFrame, params: StrategyParams, market_series: pd.Series | None = None) -> Tuple[pd.DataFrame, pd.DataFrame, Dict]:
    data = build_trade_signals(df, params, market_series)
    if data.empty:
        return data, pd.DataFrame(), {}

    cash = 1.0
    shares = 0.0
    in_position = False
    entry_price = 0.0
    entry_date = None
    entry_i = None
    trades = []
    equity_curve = []

    for i in range(1, len(data)):
        prev = data.iloc[i - 1]
        today = data.iloc[i]
        date = data.index[i]
        open_price = float(today["Open"])
        close_price = float(today["Close"])

        # Signals are generated after previous close and executed at today's open.
        if not in_position and bool(prev["BUY_CONDITION"]):
            if open_price > 0:
                shares = cash / open_price
                cash = 0.0
                in_position = True
                entry_price = open_price
                entry_date = date
                entry_i = i

        elif in_position:
            hold_days = i - entry_i if entry_i is not None else 0
            stop_loss_hit = open_price <= entry_price * (1 - params.stop_loss_pct / 100)
            max_hold_hit = hold_days >= params.max_hold_days
            sell_signal = bool(prev["SELL_CONDITION"])
            if stop_loss_hit or max_hold_hit or sell_signal:
                exit_price = open_price
                cash = shares * exit_price
                shares = 0.0
                in_position = False
                ret = exit_price / entry_price - 1
                trades.append(
                    {
                        "Entry_Date": entry_date.date(),
                        "Exit_Date": date.date(),
                        "Entry": round(entry_price, 2),
                        "Exit": round(exit_price, 2),
                        "Return_%": round(ret * 100, 2),
                        "Hold_Days": hold_days,
                        "Exit_Reason": "stop_loss" if stop_loss_hit else ("max_hold" if max_hold_hit else "sell_signal"),
                    }
                )

        equity = cash + shares * close_price
        equity_curve.append({"Date": date, "Equity": equity})

    equity_df = pd.DataFrame(equity_curve).set_index("Date") if equity_curve else pd.DataFrame()
    trades_df = pd.DataFrame(trades)

    if equity_df.empty:
        stats = {}
    else:
        total_return = float(equity_df["Equity"].iloc[-1] - 1)
        rolling_max = equity_df["Equity"].cummax()
        max_drawdown = float((equity_df["Equity"] / rolling_max - 1).min())
        win_rate = float((trades_df["Return_%"] > 0).mean()) if not trades_df.empty else 0.0
        avg_trade = float(trades_df["Return_%"].mean()) if not trades_df.empty else 0.0
        stats = {
            "Total_Return_%": round(total_return * 100, 2),
            "Max_Drawdown_%": round(max_drawdown * 100, 2),
            "Trades": int(len(trades_df)),
            "Win_Rate_%": round(win_rate * 100, 2),
            "Avg_Trade_%": round(avg_trade, 2),
        }

    return equity_df, trades_df, stats


def build_market_series(params: StrategyParams, period: str, interval: str) -> pd.Series | None:
    if not params.use_market_filter:
        return None
    mdf = load_history(params.market_ticker, period, interval)
    if mdf.empty:
        return None
    mind = add_indicators(mdf, params)
    return (mind["Close"] > mind["MA_LONG"]).dropna()


st.title("📈 美股短线量化扫描器 + 回测工具")
st.caption("iPhone 可用网页版本：日线动量扫描 + 简化回测。先验证策略，不自动下单。")

with st.sidebar:
    st.header("参数设置")
    default_pool = "NVDA, TSLA, AMD, PLTR, SOXL, QQQ, META, MSFT, AAPL, AVGO"
    raw_tickers = st.text_area("股票池，用英文逗号分隔", value=default_pool, height=100)

    period = st.selectbox("历史周期", ["3mo", "6mo", "1y", "2y", "5y"], index=2)
    interval = st.selectbox("K线周期", ["1d"], index=0, help="第一版先做日线。盘中版下一版再做。")

    short_ma = st.number_input("短均线", min_value=2, max_value=50, value=5, step=1)
    long_ma = st.number_input("长均线", min_value=5, max_value=200, value=20, step=1)
    volume_multiplier = st.number_input("放量倍数", min_value=1.0, max_value=10.0, value=1.5, step=0.1)
    min_daily_return_pct = st.number_input("最小当日涨幅 %", min_value=-10.0, max_value=20.0, value=2.0, step=0.5)
    stop_loss_pct = st.number_input("止损/回撤阈值 %", min_value=1.0, max_value=30.0, value=5.0, step=0.5)
    max_hold_days = st.number_input("最长持仓天数", min_value=1, max_value=60, value=5, step=1)

    use_market_filter = st.checkbox("启用大盘过滤", value=True)
    market_ticker = st.text_input("大盘过滤标的", value="QQQ")

params = StrategyParams(
    short_ma=int(short_ma),
    long_ma=int(long_ma),
    volume_multiplier=float(volume_multiplier),
    min_daily_return_pct=float(min_daily_return_pct),
    stop_loss_pct=float(stop_loss_pct),
    max_hold_days=int(max_hold_days),
    use_market_filter=bool(use_market_filter),
    market_ticker=_clean_ticker(market_ticker or "QQQ"),
)

tickers = parse_tickers(raw_tickers)

tab_scan, tab_backtest, tab_manual = st.tabs(["信号扫描", "单股回测", "使用说明"])

with tab_scan:
    st.subheader("信号扫描")
    st.write("判断逻辑：趋势 + 动量 + 放量 + 大盘过滤。结果是观察信号，不是下单命令。")

    if st.button("开始扫描", type="primary"):
        if not tickers:
            st.error("请先输入股票代码。")
        else:
            with st.spinner("正在拉取行情并计算信号..."):
                m_ok, m_reason = market_ok(params, period, interval)
                rows = [scan_ticker(t, params, period, interval, m_ok) for t in tickers]
                result = pd.DataFrame(rows)
                sort_map = {"BUY_WATCH": 0, "WATCH": 1, "EXIT_RISK": 2, "NO_TRADE": 3, "NO_DATA": 4}
                result["_sort"] = result["Signal"].map(sort_map).fillna(9)
                result = result.sort_values(["_sort", "Score"], ascending=[True, False]).drop(columns=["_sort"])

            st.info(f"市场过滤：{m_reason}。当前状态：{'通过' if m_ok else '不通过'}")
            st.dataframe(result, use_container_width=True, hide_index=True)
            st.download_button(
                "下载扫描结果 CSV",
                data=result.to_csv(index=False).encode("utf-8-sig"),
                file_name="us_quant_scan_results.csv",
                mime="text/csv",
            )

            buy_watch = result[result["Signal"] == "BUY_WATCH"]
            if not buy_watch.empty:
                st.warning("BUY_WATCH 只代表满足模型条件。真正短线还要看盘前/盘中强弱、新闻真实性、流动性和止损。")

with tab_backtest:
    st.subheader("单股回测")
    selected = st.selectbox("选择回测股票", tickers if tickers else ["NVDA"])

    if st.button("开始回测", type="primary"):
        df = load_history(selected, period, interval)
        if df.empty:
            st.error("无法读取该股票数据。换一个代码，或检查网络。")
        else:
            market_series = build_market_series(params, period, interval)
            equity, trades, stats = run_backtest(df, params, market_series)

            if not stats:
                st.error("数据不足，无法回测。")
            else:
                c1, c2, c3, c4, c5 = st.columns(5)
                c1.metric("总收益", f"{stats['Total_Return_%']}%")
                c2.metric("最大回撤", f"{stats['Max_Drawdown_%']}%")
                c3.metric("交易次数", stats["Trades"])
                c4.metric("胜率", f"{stats['Win_Rate_%']}%")
                c5.metric("单笔均值", f"{stats['Avg_Trade_%']}%")

                if not equity.empty:
                    st.line_chart(equity["Equity"], height=320)

                ind = add_indicators(df, params).dropna()
                chart_df = ind[["Close", "MA_SHORT", "MA_LONG"]].rename(
                    columns={"Close": "收盘价", "MA_SHORT": "短均线", "MA_LONG": "长均线"}
                )
                st.line_chart(chart_df, height=320)

                st.write("交易明细")
                if trades.empty:
                    st.info("该参数下没有触发完整交易。")
                else:
                    st.dataframe(trades, use_container_width=True, hide_index=True)
                    st.download_button(
                        "下载回测交易 CSV",
                        data=trades.to_csv(index=False).encode("utf-8-sig"),
                        file_name=f"{selected}_backtest_trades.csv",
                        mime="text/csv",
                    )

with tab_manual:
    st.subheader("使用说明")
    st.markdown(
        """
### 这个工具适合做什么

- 收盘后扫描股票池
- 找出短线动量强、成交量异常的标的
- 验证一个粗糙策略是否有正反馈
- 帮你少碰弱势票和垃圾机会

### 这个工具不适合做什么

- 不能直接预测明天暴涨
- 不能替代真实盘中盯盘
- 不能自动下单
- 不能处理突发新闻、停牌、增发、财报黑天鹅

### 信号解释

| 信号 | 含义 |
|---|---|
| BUY_WATCH | 满足趋势、动量、放量、大盘过滤，进入观察池 |
| WATCH | 趋势尚可，但动量或量能不足，等确认 |
| EXIT_RISK | 跌破趋势或回撤风险加大 |
| NO_TRADE | 不符合交易条件 |
| NO_DATA | 数据不足或代码错误 |

### 严格建议

第一版只能当“过滤器”。如果你拿它直接重仓冲，那不是量化，是把主观冲动套了个软件壳。先复盘 20 个交易日，再谈实盘。
"""
    )
