"""
e-Stat（日本統計局）データ取得スクリプト

取得指標（消費者物価指数 2020年基準・全国・月次）:
  - 電気代     (cat01: 0056)  指数 (2020年=100)
  - 都市ガス代 (cat01: 0057)  指数 (2020年=100)
  - 灯油       (cat01: 0058)  指数 (2020年=100)
  - ガソリン   (cat01: 0054)  指数 (2020年=100)

統計ID: 0003427113（消費者物価指数 2020年基準）

時間コード形式: YYYY00MMMM（例: 2025001212 = 2025年12月）

出力:
  - data/estat_monthly.csv

前提:
  - .env ファイルに ESTAT_API_KEY=xxxx を設定
"""

import os
import sys
import time

import pandas as pd
import requests
from dotenv import load_dotenv

# ── 設定 ──────────────────────────────────────────
ENV_PATH = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(ENV_PATH)

ESTAT_API_KEY = os.getenv("ESTAT_API_KEY")
BASE_URL = "https://api.e-stat.go.jp/rest/3.0/app/json"

# 消費者物価指数 2020年基準
STATS_DATA_ID = "0003427113"

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "estat_monthly.csv")

# 取得する品目コードと列名の対応
ITEMS = {
    "0056": "electricity_index",   # 電気代
    "0057": "city_gas_index",      # 都市ガス代
    "0058": "kerosene_index",      # 灯油
    "0054": "gasoline_index",      # ガソリン
}

START_TIME = "2015000101"   # 2015年1月


# ── データ取得 ────────────────────────────────────
def fetch_cpi_items() -> pd.DataFrame:
    """指定品目の月次CPIデータを一括取得してDataFrameに変換する。"""
    cat_codes = ",".join(ITEMS.keys())
    print(f"  品目: {', '.join(ITEMS.values())}")

    params = {
        "appId": ESTAT_API_KEY,
        "statsDataId": STATS_DATA_ID,
        "cdCat01": cat_codes,
        "cdArea": "00000",      # 全国
        "cdTab": "1",           # 指数
        "startTime": START_TIME,
        "lang": "J",
        "limit": 10000,
    }

    try:
        resp = requests.get(f"{BASE_URL}/getStatsData", params=params, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  [ERROR] データ取得失敗: {e}", file=sys.stderr)
        return pd.DataFrame()

    data = resp.json()

    # エラーチェック
    result_code = data.get("GET_STATS_DATA", {}).get("RESULT", {}).get("STATUS", -1)
    if str(result_code) != "0":
        msg = data.get("GET_STATS_DATA", {}).get("RESULT", {}).get("ERROR_MSG", "不明なエラー")
        print(f"  [ERROR] e-Stat API エラー (status={result_code}): {msg}", file=sys.stderr)
        return pd.DataFrame()

    values = data["GET_STATS_DATA"]["STATISTICAL_DATA"]["DATA_INF"]["VALUE"]
    if isinstance(values, dict):
        values = [values]

    print(f"  → 取得レコード数: {len(values)} 件")

    # DataFrameに変換
    records = []
    for v in values:
        time_code = v.get("@time", "")
        date = _parse_time_code(time_code)
        if not date:
            continue
        cat = v.get("@cat01", "")
        col_name = ITEMS.get(cat)
        if not col_name:
            continue
        val = v.get("$", "")
        records.append({
            "date": date,
            "column": col_name,
            "value": _to_float(val),
        })

    if not records:
        print("  [WARNING] 有効なレコードがありません")
        return pd.DataFrame()

    # ピボット: 日付×品目
    df = pd.DataFrame(records)
    df = df.pivot_table(index="date", columns="column", values="value", aggfunc="first")
    df.columns.name = None
    df = df.sort_index()

    # 2015年以降のデータのみ保持
    df = df[df.index >= "2015-01"]

    return df


# ── ユーティリティ ────────────────────────────────
def _parse_time_code(code: str) -> str | None:
    """
    e-Statの時間コード（YYYY00MMMM形式）を YYYY-MM 文字列に変換する。
    例: '2025001212' → '2025-12'
         '2026000101' → '2026-01'
    """
    if len(code) < 8:
        return None
    try:
        year = code[0:4]
        month = code[6:8]
        if month == "00":   # 年間平均行はスキップ
            return None
        return f"{year}-{month}"
    except (IndexError, ValueError):
        return None


def _to_float(val: str) -> float | None:
    try:
        return float(str(val).replace(",", "").strip())
    except (ValueError, TypeError):
        return None


# ── 保存 ─────────────────────────────────────────
def save_csv(df: pd.DataFrame, path: str) -> None:
    """DataFrameをCSVに保存する（既存ファイルがある場合は差分追記）。"""
    if df.empty:
        print("  [WARNING] データなし、スキップ")
        return

    os.makedirs(os.path.dirname(path), exist_ok=True)

    if os.path.exists(path):
        existing = pd.read_csv(path, index_col="date")
        new_rows = df[~df.index.isin(existing.index)]
        if new_rows.empty:
            print(f"  新規データなし（最新: {df.index[-1]}）")
            return
        combined = pd.concat([existing, new_rows]).sort_index()
        combined.to_csv(path)
        print(f"  {len(new_rows)} 行を追記 → 合計 {len(combined)} 行")
    else:
        df.to_csv(path)
        print(f"  {len(df)} 行を新規保存")


# ── サマリー表示 ──────────────────────────────────
def _print_summary(df: pd.DataFrame) -> None:
    if df.empty:
        return

    labels = {
        "electricity_index": "電気代       ",
        "city_gas_index":    "都市ガス代   ",
        "kerosene_index":    "灯油         ",
        "gasoline_index":    "ガソリン     ",
    }

    print("\n--- 最新値サマリー（2020年=100） ---")
    latest_date = df.dropna(how="all").index[-1]
    prev_date = df.dropna(how="all").index[-2] if len(df) >= 2 else None

    for col, label in labels.items():
        if col not in df.columns:
            continue
        series = df[col].dropna()
        if series.empty:
            continue
        val = series.iloc[-1]
        dt = series.index[-1]
        diff = ""
        if prev_date and prev_date in df.index and not pd.isna(df.loc[prev_date, col]):
            prev_val = df.loc[prev_date, col]
            diff = f"  前月比: {val - prev_val:+.1f}"
        print(f"  {label}: {val:>7.1f}  ({dt}){diff}")


# ── メイン ────────────────────────────────────────
def main() -> None:
    if not ESTAT_API_KEY:
        print("[ERROR] ESTAT_API_KEY が設定されていません。.env ファイルを確認してください。", file=sys.stderr)
        sys.exit(1)

    print("=== e-Stat データ取得 ===")
    print(f"統計: 消費者物価指数 2020年基準（全国）")
    print(f"取得開始: 2015年1月\n")

    df = fetch_cpi_items()

    print("\n【保存】")
    save_csv(df, OUTPUT_PATH)
    print(f"保存先: {os.path.abspath(OUTPUT_PATH)}")

    _print_summary(df)

    print(f"\n完了")


if __name__ == "__main__":
    main()
