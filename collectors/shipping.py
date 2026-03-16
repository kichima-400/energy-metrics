"""
海運指数データ取得スクリプト

取得指標 (すべて Yahoo Finance):
  - BDRY  Breakwave Dry Bulk ETF   (バルチック海運指数 BDI 連動)  日次 2018-
  - BWET  Breakwave Tanker ETF     (タンカー運賃 BDTI/BCTI 連動)  日次 2023-
  - ZIM   ZIM Integrated Shipping  (コンテナ運賃の動向参照)       日次 2021-

注記:
  - BDI・BDTI・BCTI の実データは Baltic Exchange の有料サービス。
  - BDRY / BWET は Baltic Exchange 連動を目的に設計された専用 ETF。
  - ZIM はコンテナ運賃の先行指標として機能。

出力:
  - data/shipping_daily.csv
"""

import os
import sys
from datetime import date

import pandas as pd

OUTPUT_DAILY = os.path.join(os.path.dirname(__file__), "..", "data", "shipping_daily.csv")
START_DATE = "2015-01-01"

# Yahoo Finance ティッカー
TICKERS: dict[str, str] = {
    "wti_crude_usd":   "CL=F",   # WTI原油先物 (USD/バレル)
    "brent_crude_usd": "BZ=F",   # Brent原油先物 (USD/バレル)
    "ttf_gas_eur_mwh": "TTF=F",  # TTF欧州天然ガス先物 (EUR/MWh)
    "usd_jpy":         "JPY=X",   # ドル円為替レート (円/ドル) ← FREDより1日早い
    "dollar_index":    "DX-Y.NYB", # DXY ドル指数（6通貨、ICE） ← FREDより1日早い
    "bdry": "BDRY",  # Breakwave Dry Bulk Shipping ETF (BDI 連動)
    "bwet": "BWET",  # Breakwave Tanker Shipping ETF   (BDTI/BCTI 連動)
    "zim":  "ZIM",   # ZIM Integrated Shipping          (コンテナ運賃連動株)
}


# ── データ取得 ────────────────────────────────────────────────
def fetch_all() -> pd.DataFrame:
    try:
        import yfinance as yf
    except ImportError:
        print("[ERROR] yfinance がインストールされていません。`pip install yfinance` を実行してください。", file=sys.stderr)
        return pd.DataFrame()

    frames: dict[str, pd.Series] = {}
    print("【海運指数】")

    for col_name, ticker in TICKERS.items():
        s = _fetch_ticker(yf, ticker, col_name)
        if s is not None:
            frames[col_name] = s

    if not frames:
        return pd.DataFrame()

    df = pd.DataFrame(frames)
    df.index.name = "date"
    df = df.sort_index()
    return df


def _fetch_ticker(yf, ticker: str, label: str) -> "pd.Series | None":
    try:
        data = yf.download(ticker, start=START_DATE, progress=False, auto_adjust=True)
        if data.empty:
            print(f"  [WARNING] {label} ({ticker}): データなし", file=sys.stderr)
            return None

        # yfinance >= 0.2.x は MultiIndex を返す場合がある
        if isinstance(data.columns, pd.MultiIndex):
            s = data[("Close", ticker)]
        else:
            s = data["Close"]

        s = s.squeeze()
        s.name = label
        s = s.dropna()
        s.index = pd.to_datetime(s.index).tz_localize(None)
        print(f"  {label:8s} ({ticker}): {len(s)} 件  最新: {s.index[-1].date()} = {s.iloc[-1]:.2f}")
        return s
    except Exception as e:
        print(f"  [ERROR] {label} ({ticker}): {e}", file=sys.stderr)
        return None


# ── 保存 ─────────────────────────────────────────────────────
def save_csv(df: pd.DataFrame) -> None:
    if df.empty:
        print("  [WARNING] 海運データなし、スキップ")
        return

    os.makedirs(os.path.dirname(OUTPUT_DAILY), exist_ok=True)

    if os.path.exists(OUTPUT_DAILY):
        existing = pd.read_csv(OUTPUT_DAILY, index_col="date", parse_dates=True)
        new_cols = [c for c in df.columns if c not in existing.columns]
        if new_cols:
            merged = existing.join(df[new_cols], how="outer")
            new_rows = df[~df.index.isin(merged.index)]
            combined = pd.concat([merged, new_rows]).sort_index()
            combined.to_csv(OUTPUT_DAILY)
            print(f"  海運日次: 新列 {new_cols} を追加 → 合計 {len(combined)} 行")
            return

        new_rows = df[~df.index.isin(existing.index)]
        if new_rows.empty:
            print(f"  海運日次: 新規データなし（最新: {df.index[-1].date()}）")
            return
        combined = pd.concat([existing, new_rows]).sort_index()
        combined.to_csv(OUTPUT_DAILY)
        print(f"  海運日次: {len(new_rows)} 行を追記 → 合計 {len(combined)} 行")
    else:
        df.to_csv(OUTPUT_DAILY)
        print(f"  海運日次: {len(df)} 行を新規保存")


# ── メイン ────────────────────────────────────────────────────
def main() -> None:
    print("=== 海運指数データ取得 ===")
    print(f"取得開始日: {START_DATE}\n")

    df = fetch_all()
    print("\n【保存】")
    save_csv(df)
    print(f"\n完了: {os.path.abspath(OUTPUT_DAILY)}")


if __name__ == "__main__":
    main()
