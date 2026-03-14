"""
EIA（米国エネルギー情報局）データ取得スクリプト

取得指標:
  [月次]
  - US LNG輸出価格 (N9133US3)   USD/MCF
      グローバルLNG市場の代理指標。Henry Hubを基準としたUS LNG輸出の着地価格。
  [週次]
  - 米国天然ガス地下在庫 (NW2_EPG0_SWO_NUS_BCF)   BCF（十億立方フィート）
      ガス価格の先行指標。在庫減少 → 価格上昇圧力。

出力:
  - data/eia_monthly.csv   （月次指標）
  - data/eia_weekly.csv    （週次指標）

前提:
  - .env ファイルに EIA_API_KEY=xxxx を設定
"""

import csv
import os
import sys
import time
from datetime import date

import pandas as pd
import requests
from dotenv import load_dotenv

# ── 設定 ──────────────────────────────────────────
ENV_PATH = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(ENV_PATH)

EIA_API_KEY = os.getenv("EIA_API_KEY")
BASE_URL = "https://api.eia.gov/v2"

OUTPUT_MONTHLY = os.path.join(os.path.dirname(__file__), "..", "data", "eia_monthly.csv")
OUTPUT_WEEKLY = os.path.join(os.path.dirname(__file__), "..", "data", "eia_weekly.csv")

START_DATE = "2015-01-01"
START_MONTH = "2015-01"


# ── 月次データ ───────────────────────────────────
def fetch_lng_export_price() -> pd.DataFrame:
    """
    US LNG輸出価格（月次）を取得する。
    series: N9133US3 = Price of Liquefied U.S. Natural Gas Exports ($/MCF)
    1 MCF（千立方フィート）≒ 1.055 MMBtu なので、おおよそ Henry Hub と比較可能。
    """
    print("  US LNG輸出価格 (月次)...")
    rows = _fetch_data(
        endpoint="/natural-gas/move/expc/data/",
        frequency="monthly",
        facets={"process": ["PNG"], "duoarea": ["NUS-Z00"]},
        start=START_MONTH,
    )
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)[["period", "value"]].copy()
    df = df.rename(columns={"period": "date", "value": "us_lng_export_price_usd_mcf"})
    df["date"] = pd.to_datetime(df["date"])
    df["us_lng_export_price_usd_mcf"] = pd.to_numeric(df["us_lng_export_price_usd_mcf"], errors="coerce")
    df = df.set_index("date").sort_index()

    latest = df.dropna().iloc[-1]
    print(f"    → {len(df)} 件  最新: {df.dropna().index[-1].date()} = {latest['us_lng_export_price_usd_mcf']:.3f} USD/MCF")
    return df


# ── 週次データ ───────────────────────────────────
def fetch_gas_storage() -> pd.DataFrame:
    """
    米国天然ガス地下在庫（週次・全米合計）を取得する。
    process=SWO: Underground Storage - Working Gas（稼働ガス量）
    duoarea=NUS: 全米合計
    """
    print("  米国天然ガス在庫 (週次)...")
    rows = _fetch_data(
        endpoint="/natural-gas/stor/wkly/data/",
        frequency="weekly",
        facets={"process": ["SWO"], "duoarea": ["R48"]},
        start=START_DATE,
    )
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)[["period", "value"]].copy()
    df = df.rename(columns={"period": "date", "value": "us_gas_storage_bcf"})
    df["date"] = pd.to_datetime(df["date"])
    df["us_gas_storage_bcf"] = pd.to_numeric(df["us_gas_storage_bcf"], errors="coerce")
    df = df.set_index("date").sort_index()
    df = df[~df.index.duplicated(keep="last")]  # 重複日付を除去

    latest = df.dropna().iloc[-1]
    print(f"    → {len(df)} 件  最新: {df.dropna().index[-1].date()} = {latest['us_gas_storage_bcf']:.0f} BCF")
    return df


# ── 汎用取得関数 ──────────────────────────────────
def _fetch_data(endpoint: str, frequency: str, facets: dict, start: str) -> list[dict]:
    """EIA API v2 からデータをページネーションしながら全件取得する。"""
    url = f"{BASE_URL}{endpoint}"
    all_rows = []
    offset = 0
    page_size = 5000

    while True:
        params = {
            "api_key": EIA_API_KEY,
            "frequency": frequency,
            "data[0]": "value",
            "start": start,
            "length": page_size,
            "offset": offset,
            "sort[0][column]": "period",
            "sort[0][direction]": "asc",
        }
        for i, (facet_key, facet_vals) in enumerate(facets.items()):
            for val in facet_vals:
                params[f"facets[{facet_key}][]"] = val

        try:
            resp = requests.get(url, params=params, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"    [ERROR] {endpoint}: {e}", file=sys.stderr)
            break

        data = resp.json()
        rows = data.get("response", {}).get("data", [])
        if not rows:
            break

        all_rows.extend(rows)

        # 全件取得済みか確認
        total = int(data.get("response", {}).get("total", len(rows)))
        if offset + len(rows) >= total:
            break

        offset += page_size
        time.sleep(0.3)

    return all_rows


# ── 保存 ─────────────────────────────────────────
def save_csv(df: pd.DataFrame, path: str, label: str) -> None:
    """DataFrameをCSVに保存する（既存ファイルがある場合は差分追記）。"""
    if df.empty:
        print(f"  [WARNING] {label}: データなし、スキップ")
        return

    os.makedirs(os.path.dirname(path), exist_ok=True)

    if os.path.exists(path):
        existing = pd.read_csv(path, index_col="date", parse_dates=True)
        new_rows = df[~df.index.isin(existing.index)]
        if new_rows.empty:
            print(f"  {label}: 新規データなし（最新: {df.dropna().index[-1].date()}）")
            return
        combined = pd.concat([existing, new_rows]).sort_index()
        combined.to_csv(path)
        print(f"  {label}: {len(new_rows)} 行を追記 → 合計 {len(combined)} 行")
    else:
        df.to_csv(path)
        print(f"  {label}: {len(df)} 行を新規保存")


# ── サマリー表示 ──────────────────────────────────
def _print_summary(monthly_df: pd.DataFrame, weekly_df: pd.DataFrame) -> None:
    print("\n--- 最新値サマリー ---")

    if not monthly_df.empty and "us_lng_export_price_usd_mcf" in monthly_df.columns:
        col = monthly_df["us_lng_export_price_usd_mcf"].dropna()
        prev = col.iloc[-2] if len(col) >= 2 else None
        diff = f"  前月比: {col.iloc[-1]-prev:+.3f}" if prev else ""
        print(f"  US LNG輸出価格: {col.iloc[-1]:>8.3f} USD/MCF  ({col.index[-1].date()}){diff}")

    if not weekly_df.empty and "us_gas_storage_bcf" in weekly_df.columns:
        col = weekly_df["us_gas_storage_bcf"].dropna()
        prev = col.iloc[-2] if len(col) >= 2 else None
        diff = f"  前週比: {col.iloc[-1]-prev:+.0f} BCF" if prev else ""
        print(f"  米国ガス在庫  : {col.iloc[-1]:>8.0f} BCF    ({col.index[-1].date()}){diff}")


# ── メイン ────────────────────────────────────────
def main() -> None:
    if not EIA_API_KEY:
        print("[ERROR] EIA_API_KEY が設定されていません。.env ファイルを確認してください。", file=sys.stderr)
        sys.exit(1)

    print("=== EIA データ取得 ===")
    print(f"取得開始日: {START_DATE}\n")

    print("【月次指標】")
    monthly_df = fetch_lng_export_price()

    print("\n【週次指標】")
    weekly_df = fetch_gas_storage()

    print("\n【保存】")
    save_csv(monthly_df, OUTPUT_MONTHLY, "月次データ")
    save_csv(weekly_df, OUTPUT_WEEKLY, "週次データ")

    _print_summary(monthly_df, weekly_df)

    print(f"\n完了")
    print(f"  月次: {os.path.abspath(OUTPUT_MONTHLY)}")
    print(f"  週次: {os.path.abspath(OUTPUT_WEEKLY)}")


if __name__ == "__main__":
    main()
