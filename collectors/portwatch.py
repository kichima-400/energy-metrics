"""
IMF PortWatch「ホルムズ海峡日次通過隻数」データ取得スクリプト

取得指標:
  - 通過総隻数 (n_total)
  - タンカー隻数 (n_tanker)

ソース:
  https://portwatch.imf.org/pages/chokepoint6
  ArcGIS FeatureServer（認証不要、商用利用可）
  更新: 毎週火曜 JST 23:00（最大7日のラグ）

出力:
  - data/portwatch_daily.csv
"""

import os
import sys

import pandas as pd
import requests

OUTPUT = os.path.join(os.path.dirname(__file__), "..", "data", "portwatch_daily.csv")

PORTWATCH_URL = (
    "https://services9.arcgis.com/weJ1QsnbMYJlCHdG/arcgis/rest/services"
    "/Daily_Chokepoints_Data/FeatureServer/0/query"
)
PAGE_SIZE = 1000


# ── データ取得 ────────────────────────────────────────────
def fetch_all() -> pd.DataFrame:
    """全履歴を1000件ずつページネーションで取得する。"""
    rows = []
    offset = 0

    while True:
        params = {
            "where": "portid='chokepoint6'",
            "outFields": "year,month,day,n_total,n_tanker",
            "orderByFields": "date ASC",
            "resultRecordCount": PAGE_SIZE,
            "resultOffset": offset,
            "f": "json",
        }
        try:
            resp = requests.get(PORTWATCH_URL, params=params, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"  [ERROR] 取得失敗 (offset={offset}): {e}", file=sys.stderr)
            break

        features = resp.json().get("features", [])
        if not features:
            break

        for feat in features:
            a = feat["attributes"]
            date_str = f"{a['year']}-{a['month']:02d}-{a['day']:02d}"
            rows.append({
                "date": date_str,
                "n_total": a.get("n_total"),
                "n_tanker": a.get("n_tanker"),
            })

        print(f"  取得: {len(rows)} 件目まで完了 (offset={offset})")

        if len(features) < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()
    df["n_total"] = pd.to_numeric(df["n_total"], errors="coerce")
    df["n_tanker"] = pd.to_numeric(df["n_tanker"], errors="coerce")
    return df


# ── 保存 ─────────────────────────────────────────────────
def save_csv(df: pd.DataFrame, path: str) -> None:
    if df.empty:
        print("  [WARNING] データなし、スキップ")
        return

    os.makedirs(os.path.dirname(path), exist_ok=True)

    if os.path.exists(path):
        existing = pd.read_csv(path, index_col="date", parse_dates=True)
        new_rows = df[~df.index.isin(existing.index)]
        if new_rows.empty:
            print(f"  新規データなし（最新: {df.dropna().index[-1].date()}）")
            return
        combined = pd.concat([existing, new_rows]).sort_index()
        combined.to_csv(path)
        print(f"  {len(new_rows)} 行を追記 → 合計 {len(combined)} 行")
    else:
        df.to_csv(path)
        print(f"  {len(df)} 行を新規保存")


# ── メイン ────────────────────────────────────────────────
def main() -> None:
    print("=== IMF PortWatch ホルムズ海峡通過隻数 ===\n")
    print("【データ取得】")

    df = fetch_all()

    if df.empty:
        print("[ERROR] データ取得に失敗しました", file=sys.stderr)
        sys.exit(1)

    latest = df.dropna(subset=["n_total"])
    if not latest.empty:
        last = latest.iloc[-1]
        print(
            f"  最新: {latest.index[-1].date()}"
            f"  総隻数={int(last['n_total'])} 隻"
            f"  タンカー={int(last['n_tanker']) if pd.notna(last['n_tanker']) else 'N/A'} 隻"
        )

    print("\n【保存】")
    save_csv(df, OUTPUT)

    print(f"\n完了: {os.path.abspath(OUTPUT)}")


if __name__ == "__main__":
    main()
