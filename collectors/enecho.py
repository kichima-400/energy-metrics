"""
資源エネルギー庁「石油製品価格調査（給油所小売価格）」データ取得スクリプト

取得指標（週次・全国平均）:
  - レギュラーガソリン小売価格  (円/L)
  - 灯油（民生用）小売価格      (円/18L)

ソース:
  https://www.enecho.meti.go.jp/statistics/petroleum_and_lpgas/pl007/
  毎週月曜調査 → 火曜公表
  URLパターン: /xlsx/YYMMDD s5.xlsx（YYMMDD = 直近火曜日）

出力:
  - data/enecho_weekly.csv
"""

import io
import os
import sys
from datetime import date, timedelta

import pandas as pd
import requests

OUTPUT = os.path.join(os.path.dirname(__file__), "..", "data", "enecho_weekly.csv")
BASE_URL = "https://www.enecho.meti.go.jp/statistics/petroleum_and_lpgas/pl007/xlsx/"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

SHEET_PREMIUM  = 0  # ハイオクガソリン
SHEET_REGULAR  = 1  # レギュラーガソリン
SHEET_KEROSENE = 3  # 灯油（民生用）


# ── 日付計算 ──────────────────────────────────────────
def _latest_wednesday() -> date:
    """直近の水曜日（公表日）を返す。"""
    today = date.today()
    days_since = (today.weekday() - 2) % 7  # 0=月,2=水,...
    return today - timedelta(days=days_since)


# ── ダウンロード ──────────────────────────────────────
def _download(survey_date: date) -> bytes | None:
    """指定日付のExcelファイルをダウンロードする。s5/a5 を両方試みる。"""
    for suffix in ["s5", "a5"]:
        fname = f"{survey_date.strftime('%y%m%d')}{suffix}.xlsx"
        url = BASE_URL + fname
        try:
            r = requests.get(url, headers=HEADERS, timeout=60)
            if r.status_code == 200:
                print(f"  取得: {fname} ({len(r.content)//1024} KB)")
                return r.content
        except requests.RequestException as e:
            print(f"  [WARN] {fname}: {e}", file=sys.stderr)
    return None


# ── パース ────────────────────────────────────────────
def _parse_sheet(xl: pd.ExcelFile, sheet_idx: int, col_name: str) -> pd.Series:
    """シートから日付・全国平均のSeriesを返す。"""
    df = xl.parse(sheet_idx, header=None)
    # 列1=調査日、列2=全国平均
    data = df[[1, 2]].copy()
    data[1] = pd.to_datetime(data[1], errors="coerce")
    data[2] = pd.to_numeric(data[2], errors="coerce")
    data = data.dropna()
    s = data.set_index(1)[2]
    s.index.name = "date"
    s.name = col_name
    return s.sort_index()


# ── データ取得 ────────────────────────────────────────
def fetch_all() -> pd.DataFrame:
    """最新ファイルを取得してDataFrameを返す。最大4週さかのぼる。"""
    print("【エネ庁 石油製品価格調査】")
    for weeks_back in range(4):
        target = _latest_wednesday() - timedelta(weeks=weeks_back)
        content = _download(target)
        if content is None:
            continue
        try:
            xl = pd.ExcelFile(io.BytesIO(content))
            premium  = _parse_sheet(xl, SHEET_PREMIUM,  "premium_price_jpy_l")
            gasoline = _parse_sheet(xl, SHEET_REGULAR,  "gasoline_price_jpy_l")
            kerosene = _parse_sheet(xl, SHEET_KEROSENE, "kerosene_price_jpy_18l")
            df = pd.concat([premium, gasoline, kerosene], axis=1).sort_index()
            latest = df.dropna().iloc[-1]
            print(f"  最新: {df.dropna().index[-1].date()}"
                  f"  ハイオク={latest['premium_price_jpy_l']:.1f}円/L"
                  f"  ガソリン={latest['gasoline_price_jpy_l']:.1f}円/L"
                  f"  灯油={latest['kerosene_price_jpy_18l']:.0f}円/18L")
            return df
        except Exception as e:
            print(f"  [ERROR] パース失敗: {e}", file=sys.stderr)
    print("[ERROR] ファイル取得に失敗しました", file=sys.stderr)
    return pd.DataFrame()


# ── 保存 ─────────────────────────────────────────────
def save_csv(df: pd.DataFrame) -> None:
    if df.empty:
        print("  [WARNING] データなし、スキップ")
        return

    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)

    if os.path.exists(OUTPUT):
        existing = pd.read_csv(OUTPUT, index_col="date", parse_dates=True)
        new_cols = [c for c in df.columns if c not in existing.columns]
        if new_cols:
            merged = existing.join(df[new_cols], how="outer")
            new_rows = df[~df.index.isin(merged.index)]
            combined = pd.concat([merged, new_rows]).sort_index()
            combined.to_csv(OUTPUT)
            print(f"  新列 {new_cols} を追加 → 合計 {len(combined)} 行")
            return
        new_rows = df[~df.index.isin(existing.index)]
        if new_rows.empty:
            print(f"  新規データなし（最新: {df.dropna().index[-1].date()}）")
            return
        combined = pd.concat([existing, new_rows]).sort_index()
        combined.to_csv(OUTPUT)
        print(f"  {len(new_rows)} 行を追記 → 合計 {len(combined)} 行")
    else:
        df.to_csv(OUTPUT)
        print(f"  {len(df)} 行を新規保存")


# ── メイン ────────────────────────────────────────────
def main() -> None:
    print("=== エネ庁 石油製品価格調査 ===\n")
    df = fetch_all()
    print("\n【保存】")
    save_csv(df)
    print(f"\n完了: {os.path.abspath(OUTPUT)}")


if __name__ == "__main__":
    main()
