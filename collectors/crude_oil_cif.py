"""
財務省「普通貿易統計」から原油（HS 2709）の月次 CIF 価格（円/KL）を取得する。

データフロー:
  1. e-Stat のファイル一覧ページ（HTML）から stat_infid を収集（API キー不要）
  2. e-Stat のファイルダウンロードエンドポイントから CSV を取得
  3. CSV から HS 2709 の行を抽出し、月別の数量（KL）・金額（千円）を読み取る
  4. 金額(千円) × 1,000 ÷ 数量(KL) で CIF 円/KL を計算

CSV 列構成（46 列）:
  Exp or Imp, Year, HS, Unit1, Unit2,
  Quantity1-Year, Quantity2-Year, Value-Year,
  [Quantity1-Jan, Quantity2-Jan, Value-Jan, ...] × 12 ヶ月
  ※ Exp or Imp = 2 が輸入、Unit1 または Unit2 が "KL" の列が数量
  ※ Value 単位は 千円

e-Stat ファイル一覧 URL:
  https://www.e-stat.go.jp/stat-search/files
    ?toukei=00350300&tstat=000001013141
    &tclass1=000001013183&tclass2=000001013185
    &cycle=1&year={YEAR}0

ファイルダウンロード URL:
  https://www.e-stat.go.jp/stat-search/file-download?statInfId={ID}&fileKind=1
"""

import csv
import io
import os
import re
import sys
from datetime import datetime

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8")

import requests
from dotenv import load_dotenv

ENV_PATH = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(ENV_PATH)

# ─── 設定（固定値） ────────────────────────────────────────────────────────
DATALIST_URL = "https://www.e-stat.go.jp/stat-search/files"
DOWNLOAD_URL = "https://www.e-stat.go.jp/stat-search/file-download"

_DATALIST_PARAMS = {
    "toukei":     "00350300",      # 普通貿易統計
    "tstat":      "000001013141",  # 貿易統計_全国分
    "tclass1":    "000001013183",  # 統計品別表
    "tclass2":    "000001013185",  # 輸入
    "tclass3val": "0",
    "cycle":      "1",             # 月次ファイル
    "layout":     "datalist",
    "page":       "1",
}

HS_CODE     = "2709"  # 原油・粗油
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "crude_oil_cif_monthly.csv")

# CSV の列位置
_COL_EXP_IMP   = 0
_COL_YEAR      = 1
_COL_HS        = 2
_COL_UNIT1     = 3
_COL_UNIT2     = 4
_COL_MONTH_BASE = 8   # Quantity1-Jan の列インデックス
_COLS_PER_MONTH = 3   # Quantity1, Quantity2, Value（千円）

_MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


# ─── ユーティリティ ──────────────────────────────────────────────────────
def _to_float(s: str) -> float | None:
    try:
        v = s.replace(",", "").strip()
        return float(v) if v else None
    except ValueError:
        return None


# ─── Step 1: e-Stat ファイル一覧ページから stat_infid を収集 ─────────────
def _collect_stat_infids(year: int) -> list[str]:
    """
    指定年の「統計品別表 輸入」ファイル一覧ページから
    CSV ダウンロード用 stat_infid を取得して返す（重複なし・出現順）。
    """
    params = {**_DATALIST_PARAMS, "year": f"{year}0"}
    try:
        resp = requests.get(DATALIST_URL, params=params, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"ファイル一覧取得失敗 ({year}年): {e}") from e

    # HTML 中の statInfId を抽出（&amp; と & 両方に対応）
    ids = re.findall(r'statInfId=(\d{12})(?:&amp;|&)fileKind=1', resp.text)
    return list(dict.fromkeys(ids))  # 重複除去・出現順保持


# ─── Step 2: CSV ファイルのダウンロード ─────────────────────────────────
def _download_csv(stat_infid: str) -> str:
    """e-Stat から CSV をダウンロードしてテキストとして返す（API キー不要）。"""
    params = {"statInfId": stat_infid, "fileKind": "1"}
    try:
        resp = requests.get(DOWNLOAD_URL, params=params, timeout=120)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"CSV ダウンロード失敗 ({stat_infid}): {e}") from e

    resp.encoding = resp.apparent_encoding or "shift_jis"
    return resp.text


# ─── Step 3: CSV から HS 2709 の月次データを抽出 ────────────────────────
def _parse_monthly(csv_text: str) -> dict[str, dict]:
    """
    CSV テキストを解析し、HS 2709 輸入の月次データを返す。

    Returns:
        {"YYYY-MM": {"quantity_kl": float, "value_1000yen": float}}
    """
    result: dict[str, dict] = {}
    reader = csv.reader(io.StringIO(csv_text))
    next(reader, None)  # ヘッダー行をスキップ

    for row in reader:
        min_cols = _COL_MONTH_BASE + _COLS_PER_MONTH
        if len(row) < min_cols:
            continue
        if row[_COL_EXP_IMP].strip() != "2":                    # 輸入のみ
            continue
        if not row[_COL_HS].strip().strip("'").startswith(HS_CODE):  # HS 2709
            continue

        year_str = row[_COL_YEAR].strip()
        unit1    = row[_COL_UNIT1].strip().upper()
        unit2    = row[_COL_UNIT2].strip().upper()

        # KL 単位の Quantity 列を特定
        if "KL" in unit1:
            qty_offset = 0   # Quantity1 を使用
        elif "KL" in unit2:
            qty_offset = 1   # Quantity2 を使用
        else:
            continue  # KL 単位なし → スキップ

        # Step 4: 月別に数量・金額を抽出して円/KL を計算
        for i in range(len(_MONTH_NAMES)):
            base = _COL_MONTH_BASE + i * _COLS_PER_MONTH
            if base + 2 >= len(row):
                break

            qty = _to_float(row[base + qty_offset])
            val = _to_float(row[base + 2])          # Value（千円）

            if qty is None or val is None or qty == 0:
                continue

            ym = f"{year_str}-{i + 1:02d}"
            result[ym] = {"quantity_kl": qty, "value_1000yen": val}

    return result


# ─── Step 5: メイン関数 ──────────────────────────────────────────────────
def get_crude_oil_cif_price(months: int = 12) -> list[dict]:
    """
    原油（HS 2709）の月次 CIF 価格（円/KL）を返す。

    Args:
        months: 取得する月数（デフォルト: 12）

    Returns:
        新しい月から降順のリスト:
        [
            {
                "year_month":     "2024-12",
                "quantity_kl":    12345678.0,
                "value_1000yen":  987654.0,
                "cif_yen_per_kl": 79900
            },
            ...
        ]

    Raises:
        RuntimeError: ファイル取得失敗
    """
    current_year = datetime.today().year
    years_back   = (months + 11) // 12 + 1   # months から必要年数を計算
    start_year   = current_year - years_back
    all_data: dict[str, dict] = {}

    for year in range(start_year, current_year + 1):
        try:
            infids = _collect_stat_infids(year)
        except RuntimeError as e:
            print(f"  [WARN] {e}", file=sys.stderr)
            continue

        if not infids:
            print(f"  [WARN] {year}年: ファイルが見つかりません", file=sys.stderr)
            continue

        print(f"  {year}年: {len(infids)} 件のファイルを発見", file=sys.stderr)

        # 出現順の逆（古い→新しい）に処理し、新しいファイルで上書きして確々報を優先
        for infid in reversed(infids):
            try:
                csv_text = _download_csv(infid)
            except RuntimeError as e:
                print(f"    [WARN] {e}", file=sys.stderr)
                continue

            monthly = _parse_monthly(csv_text)
            if monthly:
                print(f"    {infid}: HS 2709 データ {len(monthly)} 件", file=sys.stderr)
            all_data.update(monthly)

    # 降順ソート → 直近 months ヶ月を返す
    sorted_months = sorted(all_data.keys(), reverse=True)[:months]

    return [
        {
            "year_month":     ym,
            "quantity_kl":    all_data[ym]["quantity_kl"],
            "value_1000yen":  all_data[ym]["value_1000yen"],
            "cif_yen_per_kl": round(
                all_data[ym]["value_1000yen"] * 1000 / all_data[ym]["quantity_kl"]
            ),
        }
        for ym in sorted_months
    ]


# ─── CSV 保存 ────────────────────────────────────────────────────────────
def _save_csv(records: list[dict]) -> None:
    """取得データを CSV に差分追記する（既存月は上書きしない）。"""
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    existing: dict[str, dict] = {}
    if os.path.exists(OUTPUT_PATH):
        with open(OUTPUT_PATH, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing[row["date"]] = {
                    "cif_yen_per_kl":  row["cif_yen_per_kl"],
                    "quantity_mankl":   row.get("quantity_mankl", ""),
                }

    new_count = sum(1 for r in records if r["year_month"] not in existing)
    combined  = dict(existing)
    for r in records:
        combined[r["year_month"]] = {
            "cif_yen_per_kl": str(r["cif_yen_per_kl"]),
            "quantity_mankl":  str(round(r["quantity_kl"] / 10000, 1)),
        }

    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "cif_yen_per_kl", "quantity_mankl"])
        for date_key, vals in sorted(combined.items()):
            writer.writerow([date_key, vals["cif_yen_per_kl"], vals["quantity_mankl"]])

    if new_count > 0:
        print(f"  {new_count} 行を追記 → 合計 {len(combined)} 行")
    else:
        latest = sorted(combined.keys())[-1] if combined else "-"
        print(f"  新規データなし（最新: {latest}）")


# ─── メイン ──────────────────────────────────────────────────────────────
def main() -> None:
    print("=== 原油 CIF 価格取得 ===")
    print("データソース: 財務省 普通貿易統計 / HS 2709 / 輸入 / 月次\n")

    try:
        records = get_crude_oil_cif_price(months=120)
    except RuntimeError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)

    if not records:
        print("[WARNING] データが取得できませんでした", file=sys.stderr)
        return

    print("\n【保存】")
    _save_csv(records)
    print(f"保存先: {os.path.abspath(OUTPUT_PATH)}")

    latest = records[0]
    prev   = records[1] if len(records) >= 2 else None
    diff   = (f"  前月比: {latest['cif_yen_per_kl'] - prev['cif_yen_per_kl']:+,.0f} 円/KL"
              if prev else "")
    print(f"\n--- 最新値サマリー ---")
    print(f"  原油CIF: {latest['cif_yen_per_kl']:>10,.0f} 円/KL  ({latest['year_month']}){diff}")
    print("\n完了")


# ─── 動作確認 ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== 原油 CIF 価格取得テスト ===\n")

    main()
