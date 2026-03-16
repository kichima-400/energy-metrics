"""
FRED（セントルイス連銀）データ取得スクリプト

取得指標:
  - WTI原油価格          (DCOILWTICO)     日次
  - Brent原油価格        (DCOILBRENTEU)   日次
  - ドル円為替           (DEXJPUS)        日次
  - Henry Hub天然ガス    (DHHNGSP)        日次
  - ドル指数（貿易加重） (DTWEXBGS)       日次
  - 豪州石炭価格         (PCOALAUUSDM)    月次
  - 米国政策金利         (FEDFUNDS)       月次
  - 日本政策金利         (INTGSTJPM193N)  月次
  - 欧州天然ガス(TTF連動)(PNGASEUUSDM)   月次  ← 中東情勢で高騰
  - アジアLNG現物(JKM)  (PNGASJPUSDM)   月次  ← 中東情勢で高騰

出力:
  - data/fred_daily.csv   （日次指標）
  - data/fred_monthly.csv （月次指標）

前提:
  - .env ファイルに FRED_API_KEY=xxxx を設定
"""

import csv
import os
import sys
import time
from datetime import date

import pandas as pd
from dotenv import load_dotenv
from fredapi import Fred

# ── 設定 ──────────────────────────────────────────
ENV_PATH = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(ENV_PATH)

FRED_API_KEY = os.getenv("FRED_API_KEY")

OUTPUT_DAILY = os.path.join(os.path.dirname(__file__), "..", "data", "fred_daily.csv")
OUTPUT_MONTHLY = os.path.join(os.path.dirname(__file__), "..", "data", "fred_monthly.csv")

# 取得開始日（10年分）
START_DATE = "2015-01-01"

# 取得する指標の定義
DAILY_SERIES = {
    "henry_hub_usd": "DHHNGSP",         # Henry Hub天然ガス (USD/MMBtu)
    "dollar_index": "DTWEXBGS",         # ドル指数（貿易加重）
    # usd_jpy は Yahoo Finance (shipping.py) に移行済み
}

MONTHLY_SERIES = {
    "coal_australia_usd": "PCOALAUUSDM",    # 豪州石炭 (USD/トン)
    "fed_funds_rate": "FEDFUNDS",            # 米国政策金利 (%)
    "japan_interest_rate": "INTGSTJPM193N", # 日本政策金利 (%)
    "ttf_gas_usd": "PNGASEUUSDM",           # 欧州天然ガス/TTF連動 (USD/MMBtu) ← 中東情勢で高騰
    "jkm_lng_usd": "PNGASJPUSDM",          # アジアLNG現物/JKM (USD/MMBtu)  ← 中東情勢で高騰
}


# ── データ取得 ────────────────────────────────────
def fetch_all(fred: Fred) -> tuple[pd.DataFrame, pd.DataFrame]:
    """全指標を取得してDataFrameとして返す。"""
    daily_frames = {}
    monthly_frames = {}

    print("【日次指標】")
    for col_name, series_id in DAILY_SERIES.items():
        df = _fetch_series(fred, series_id, col_name)
        if df is not None:
            daily_frames[col_name] = df
        time.sleep(0.5)  # APIレート制限対応

    print("\n【月次指標】")
    for col_name, series_id in MONTHLY_SERIES.items():
        df = _fetch_series(fred, series_id, col_name)
        if df is not None:
            monthly_frames[col_name] = df
        time.sleep(0.5)

    # 全指標を日付でJOIN
    daily_df = _join_series(daily_frames) if daily_frames else pd.DataFrame()
    monthly_df = _join_series(monthly_frames) if monthly_frames else pd.DataFrame()

    return daily_df, monthly_df


def _fetch_series(fred: Fred, series_id: str, label: str) -> pd.Series | None:
    """1つのFREDシリーズを取得する。"""
    try:
        s = fred.get_series(series_id, observation_start=START_DATE)
        s.name = label
        s = s.dropna()
        print(f"  {label:30s} ({series_id}): {len(s)} 件  最新: {s.index[-1].date()} = {s.iloc[-1]:.4f}")
        return s
    except Exception as e:
        print(f"  [ERROR] {label} ({series_id}): {e}", file=sys.stderr)
        return None


def _join_series(frames: dict[str, pd.Series]) -> pd.DataFrame:
    """複数のSeriesを日付インデックスでouterJOINして1つのDataFrameにまとめる。"""
    df = pd.DataFrame()
    for name, s in frames.items():
        if df.empty:
            df = s.to_frame()
        else:
            df = df.join(s.to_frame(), how="outer")
    df.index.name = "date"
    df = df.sort_index()
    return df


# ── 保存 ─────────────────────────────────────────
def save_csv(df: pd.DataFrame, path: str, label: str) -> None:
    """DataFrameをCSVに保存する（既存ファイルがある場合は差分追記）。"""
    if df.empty:
        print(f"  [WARNING] {label}: データなし、スキップ")
        return

    os.makedirs(os.path.dirname(path), exist_ok=True)

    if os.path.exists(path):
        existing = pd.read_csv(path, index_col="date", parse_dates=True)
        # 新しい列が追加された場合は既存データにジョインして更新
        new_cols = [c for c in df.columns if c not in existing.columns]
        if new_cols:
            merged = existing.join(df[new_cols], how="outer")
            new_rows = df[~df.index.isin(merged.index)]
            combined = pd.concat([merged, new_rows]).sort_index()
            combined.to_csv(path)
            print(f"  {label}: 新列 {new_cols} を追加 → 合計 {len(combined)} 行")
            return
        # 既存にない日付の行のみ追記
        new_rows = df[~df.index.isin(existing.index)]
        if new_rows.empty:
            print(f"  {label}: 新規データなし（最新: {df.index[-1].date()}）")
            return
        combined = pd.concat([existing, new_rows]).sort_index()
        combined.to_csv(path)
        print(f"  {label}: {len(new_rows)} 行を追記 → 合計 {len(combined)} 行")
    else:
        df.to_csv(path)
        print(f"  {label}: {len(df)} 行を新規保存")


# ── サマリー表示 ──────────────────────────────────
def _print_summary(daily_df: pd.DataFrame, monthly_df: pd.DataFrame) -> None:
    print("\n--- 最新値サマリー ---")

    labels = {
        "wti_crude_usd": "WTI原油      ",
        "brent_crude_usd": "Brent原油    ",
        "usd_jpy": "ドル円       ",
        "henry_hub_usd": "Henry Hub LNG",
        "dollar_index": "ドル指数     ",
    }
    units = {
        "wti_crude_usd": "USD/バレル",
        "brent_crude_usd": "USD/バレル",
        "usd_jpy": "円/ドル",
        "henry_hub_usd": "USD/MMBtu",
        "dollar_index": "指数",
    }

    for col, label in labels.items():
        if col in daily_df.columns:
            latest = daily_df[col].dropna().iloc[-1]
            dt = daily_df[col].dropna().index[-1].date()
            print(f"  {label}: {latest:>10.4f} {units[col]}  ({dt})")

    m_labels = {
        "coal_australia_usd": "豪州石炭     ",
        "fed_funds_rate": "米国政策金利 ",
        "japan_interest_rate": "日本政策金利 ",
        "ttf_gas_usd": "欧州天然ガス  ",
        "jkm_lng_usd": "アジアLNG    ",
    }
    m_units = {
        "coal_australia_usd": "USD/トン",
        "fed_funds_rate": "%",
        "japan_interest_rate": "%",
        "ttf_gas_usd": "USD/MMBtu",
        "jkm_lng_usd": "USD/MMBtu",
    }
    for col, label in m_labels.items():
        if col in monthly_df.columns:
            latest = monthly_df[col].dropna().iloc[-1]
            dt = monthly_df[col].dropna().index[-1].date()
            print(f"  {label}: {latest:>10.4f} {m_units[col]}  ({dt})")


# ── メイン ────────────────────────────────────────
def main() -> None:
    if not FRED_API_KEY:
        print("[ERROR] FRED_API_KEY が設定されていません。.env ファイルを確認してください。", file=sys.stderr)
        sys.exit(1)

    print("=== FRED データ取得 ===")
    print(f"取得開始日: {START_DATE}\n")

    fred = Fred(api_key=FRED_API_KEY)
    daily_df, monthly_df = fetch_all(fred)

    print("\n【保存】")
    save_csv(daily_df, OUTPUT_DAILY, "日次データ")
    save_csv(monthly_df, OUTPUT_MONTHLY, "月次データ")

    _print_summary(daily_df, monthly_df)

    print(f"\n完了")
    print(f"  日次: {os.path.abspath(OUTPUT_DAILY)}")
    print(f"  月次: {os.path.abspath(OUTPUT_MONTHLY)}")


if __name__ == "__main__":
    main()
