"""
CSVファイルを読み込んで統一フォーマットのDataFrameに変換するサービス。
"""

import os
from functools import lru_cache
from datetime import date, timedelta

import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")

# ── 指標の定義 ─────────────────────────────────────────────────────────────
# key: 指標ID（APIで使用）
# csv: ソースCSVファイル名
# column: CSV内の列名
# label: 表示名
# unit: 単位
# frequency: データ頻度

INDICATORS: list[dict] = [
    # 国際原油（Yahoo Finance 先物価格 CL=F / BZ=F — FREDより約4日早い）
    {"id": "wti_crude",      "csv": "shipping_daily.csv", "column": "wti_crude_usd",   "label": "WTI原油",   "unit": "USD/バレル", "frequency": "daily", "category": "原油"},
    {"id": "brent_crude",    "csv": "shipping_daily.csv", "column": "brent_crude_usd", "label": "Brent原油", "unit": "USD/バレル", "frequency": "daily", "category": "原油"},
    # 天然ガス
    {"id": "henry_hub",      "csv": "fred_daily.csv",    "column": "henry_hub_usd",      "label": "Henry Hub LNG",       "unit": "USD/MMBtu",  "frequency": "daily",   "category": "天然ガス"},
    {"id": "ttf_gas",        "csv": "shipping_daily.csv", "column": "ttf_gas_eur_mwh",   "label": "欧州天然ガス(TTF)",   "unit": "EUR/MWh",    "frequency": "daily",   "category": "天然ガス"},
    {"id": "jkm_lng",        "csv": "fred_monthly.csv",  "column": "jkm_lng_usd",        "label": "アジアLNG(JKM)",     "unit": "USD/MMBtu",  "frequency": "monthly", "category": "天然ガス"},
    {"id": "gas_storage",    "csv": "eia_weekly.csv",    "column": "us_gas_storage_bcf", "label": "米国ガス在庫",         "unit": "BCF",        "frequency": "weekly",  "category": "天然ガス"},
    # 石炭
    {"id": "coal_australia", "csv": "fred_monthly.csv",  "column": "coal_australia_usd", "label": "豪州石炭",         "unit": "USD/トン",   "frequency": "monthly", "category": "石炭"},
    # 為替・金利
    {"id": "usd_jpy",        "csv": "shipping_daily.csv", "column": "usd_jpy",           "label": "ドル円",           "unit": "円/ドル",    "frequency": "daily",   "category": "為替"},
    {"id": "dollar_index",   "csv": "shipping_daily.csv", "column": "dollar_index",      "label": "ドル指数(DXY)",    "unit": "指数",       "frequency": "daily",   "category": "為替"},
    {"id": "fed_funds_rate", "csv": "fred_monthly.csv",  "column": "fed_funds_rate",     "label": "米国政策金利",     "unit": "%",          "frequency": "monthly", "category": "金利"},
    # 国内エネルギー価格（CPI指数）
    {"id": "electricity",    "csv": "estat_monthly.csv", "column": "electricity_index",  "label": "電気代指数",       "unit": "指数(2020=100)", "frequency": "monthly", "category": "国内"},
    {"id": "city_gas",       "csv": "estat_monthly.csv", "column": "city_gas_index",     "label": "都市ガス代指数",   "unit": "指数(2020=100)", "frequency": "monthly", "category": "国内"},
    {"id": "gasoline",       "csv": "estat_monthly.csv", "column": "gasoline_index",     "label": "ガソリン指数",     "unit": "指数(2020=100)", "frequency": "monthly", "category": "国内"},
    {"id": "kerosene",       "csv": "estat_monthly.csv", "column": "kerosene_index",     "label": "灯油指数",         "unit": "指数(2020=100)", "frequency": "monthly", "category": "国内"},
    # 国内石油製品小売価格（エネ庁・週次）
    {"id": "premium_weekly",  "csv": "enecho_weekly.csv", "column": "premium_price_jpy_l",    "label": "ハイオク小売価格",   "unit": "円/L",   "frequency": "weekly", "category": "国内"},
    {"id": "gasoline_weekly", "csv": "enecho_weekly.csv", "column": "gasoline_price_jpy_l",   "label": "ガソリン小売価格",   "unit": "円/L",   "frequency": "weekly", "category": "国内"},
    {"id": "kerosene_weekly", "csv": "enecho_weekly.csv", "column": "kerosene_price_jpy_18l", "label": "灯油小売価格",       "unit": "円/18L", "frequency": "weekly", "category": "国内"},
    # 卸売電力
    {"id": "jepx_system",   "csv": "jepx_spot.csv",     "column": "system_price_jpy_kwh", "label": "JEPX システムプライス", "unit": "円/kWh", "frequency": "daily", "category": "国内"},
    {"id": "jepx_tokyo",    "csv": "jepx_spot.csv",     "column": "area_price_tokyo",   "label": "JEPX 東京エリア",     "unit": "円/kWh",   "frequency": "daily",   "category": "国内"},
    # 海運（中東情勢で注目）
    {"id": "bdry",  "csv": "shipping_daily.csv", "column": "bdry", "label": "ドライバルク運賃(BDRY)",    "unit": "USD",  "frequency": "daily", "category": "海運"},
    {"id": "bwet",  "csv": "shipping_daily.csv", "column": "bwet", "label": "タンカー運賃ETF(BWET)",     "unit": "USD",  "frequency": "daily", "category": "海運"},
    {"id": "zim",   "csv": "shipping_daily.csv", "column": "zim",  "label": "コンテナ海運株(ZIM)",       "unit": "USD",  "frequency": "daily", "category": "海運"},
]

_INDICATOR_MAP: dict[str, dict] = {ind["id"]: ind for ind in INDICATORS}


# ── CSV読み込み（キャッシュ） ──────────────────────────────────────────────
@lru_cache(maxsize=10)
def _load_csv(filename: str) -> pd.DataFrame:
    path = os.path.join(DATA_DIR, filename)
    df = pd.read_csv(path, index_col=0)
    df.index = pd.to_datetime(df.index, errors="coerce")
    df = df[df.index.notna()].sort_index()
    return df


def _get_df(indicator: dict) -> pd.Series:
    """指標定義からSeriesを取得する。JEPXは日次平均に集約する。"""
    path = os.path.join(DATA_DIR, indicator["csv"])
    if not os.path.exists(path):
        return pd.Series(dtype=float)
    df = _load_csv(indicator["csv"])
    col = indicator["column"]
    if col not in df.columns:
        return pd.Series(dtype=float)
    s = df[col].dropna()

    # JEPX は48コマ/日 → 日次平均に変換
    if indicator["csv"] == "jepx_spot.csv":
        s = s.groupby(s.index.date).mean()
        s.index = pd.to_datetime(s.index)

    return s


# ── 公開API ────────────────────────────────────────────────────────────────
def get_indicators() -> list[dict]:
    """利用可能な指標一覧を返す。"""
    return [
        {
            "id": ind["id"],
            "label": ind["label"],
            "unit": ind["unit"],
            "frequency": ind["frequency"],
            "category": ind["category"],
        }
        for ind in INDICATORS
    ]


def get_chart_data(
    indicator_ids: list[str],
    start: date | None = None,
    end: date | None = None,
) -> dict:
    """
    複数指標の時系列データをチャート用に返す。

    Returns:
        {
            "dates": ["2024-01-01", ...],
            "series": [
                {"id": "wti_crude", "label": "WTI原油", "unit": "...", "values": [...]},
                ...
            ]
        }
    """
    if start is None:
        start = date.today() - timedelta(days=365)
    if end is None:
        end = date.today()

    series_list = []
    all_dates: set[pd.Timestamp] = set()

    for ind_id in indicator_ids:
        ind = _INDICATOR_MAP.get(ind_id)
        if not ind:
            continue
        s = _get_df(ind)
        s = s[
            (s.index >= pd.Timestamp(start)) &
            (s.index <= pd.Timestamp(end))
        ]
        all_dates.update(s.index)
        series_list.append((ind, s))

    # 共通日付軸でそろえる（欠損はnullのまま）
    sorted_dates = sorted(all_dates)
    date_strs = [d.strftime("%Y-%m-%d") for d in sorted_dates]

    result_series = []
    for ind, s in series_list:
        values = [
            round(float(s[d]), 4) if d in s.index and pd.notna(s[d]) else None
            for d in sorted_dates
        ]
        result_series.append({
            "id": ind["id"],
            "label": ind["label"],
            "unit": ind["unit"],
            "category": ind["category"],
            "values": values,
        })

    return {"dates": date_strs, "series": result_series}


def get_summary() -> list[dict]:
    """各指標の最新値・前日比・前月比を返す。"""
    result = []
    for ind in INDICATORS:
        s = _get_df(ind)
        if s.empty:
            continue

        latest_val = float(s.iloc[-1])
        latest_date = s.index[-1].strftime("%Y-%m-%d")

        # 前の値との差分
        s_prev = s[s.index < s.index[-1]]
        prev_day = s_prev.iloc[-1] if len(s_prev) >= 1 else None
        prev_date = s_prev.index[-1].strftime("%Y-%m-%d") if len(s_prev) >= 1 else None
        diff_prev = round(float(latest_val - prev_day), 4) if prev_day is not None else None

        # 約1ヶ月前
        one_month_ago = s.index[-1] - pd.DateOffset(months=1)
        s_month = s[s.index <= one_month_ago]
        prev_month = float(s_month.iloc[-1]) if not s_month.empty else None
        diff_month = round(float(latest_val - prev_month), 4) if prev_month is not None else None

        result.append({
            "id": ind["id"],
            "label": ind["label"],
            "unit": ind["unit"],
            "category": ind["category"],
            "latest_value": round(latest_val, 4),
            "latest_date": latest_date,
            "diff_prev": diff_prev,
            "prev_date": prev_date,
            "diff_month": diff_month,
        })

    return result
