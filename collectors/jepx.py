"""
JEPX（日本電力取引所）スポット市場データ取得スクリプト

取得データ:
  - スポット市場の約定結果（システムプライス・エリアプライス・約定量）
  - 対象: 当年度と前年度（デフォルト）

出力:
  - data/jepx_spot.csv

CSVフォーマット（JEPX公開仕様）:
  受渡日, 時刻コード, 売り約定量(kWh), 買い約定量(kWh), 差引約定量(kWh),
  システムプライス(円/kWh),
  エリアプライス 北海道〜九州(円/kWh) x9エリア,
  売り/買いブロック約定量(kWh) x4列
"""

import csv
import io
import os
import sys
import time
from datetime import date

import requests

# ── 設定 ──────────────────────────────────────────
BASE_URL = "https://www.jepx.jp"
DOWNLOAD_URL = f"{BASE_URL}/_download.php"
REFERER_URL = f"{BASE_URL}/electricpower/market-data/spot/"

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "jepx_spot.csv")

# 出力するカラム（エリアプライスは代表として東京・関西・九州を含める）
FIELDNAMES = [
    "date",
    "time_code",
    "sell_volume_kwh",
    "buy_volume_kwh",
    "net_volume_kwh",
    "system_price_jpy_kwh",
    "area_price_hokkaido",
    "area_price_tohoku",
    "area_price_tokyo",
    "area_price_chubu",
    "area_price_hokuriku",
    "area_price_kansai",
    "area_price_chugoku",
    "area_price_shikoku",
    "area_price_kyushu",
]


def _target_fiscal_years() -> list[int]:
    """当年度と前年度を返す（年度は4月始まり）。"""
    today = date.today()
    current_fy = today.year if today.month >= 4 else today.year - 1
    return [current_fy - 1, current_fy]


# ── データ取得 ────────────────────────────────────
def fetch_spot_csv(fiscal_year: int) -> list[dict]:
    """指定年度のJEPXスポット市場CSVをダウンロードしてパースする。"""
    filename = f"spot_summary_{fiscal_year}.csv"
    print(f"  取得中: {fiscal_year}年度 ({filename})")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": REFERER_URL,
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {"dir": "spot_summary", "file": filename}

    try:
        resp = requests.post(DOWNLOAD_URL, headers=headers, data=data, timeout=60)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  [ERROR] {fiscal_year}年度の取得に失敗: {e}", file=sys.stderr)
        return []

    if len(resp.content) < 100:
        print(f"  [WARNING] {fiscal_year}年度: レスポンスが空または不正です", file=sys.stderr)
        return []

    # JEPXはShift-JISで配信
    try:
        text = resp.content.decode("shift_jis")
    except UnicodeDecodeError:
        text = resp.content.decode("utf-8", errors="replace")

    rows = _parse_csv(text)
    print(f"  → {len(rows)} 行取得")
    return rows


def _parse_csv(text: str) -> list[dict]:
    """CSVテキストをパースして統一フォーマットのdictリストに変換する。"""
    reader = csv.reader(io.StringIO(text))
    rows = []

    for i, line in enumerate(reader):
        if i == 0:
            continue  # ヘッダ行をスキップ
        if len(line) < 14:
            continue

        try:
            row = {
                "date": line[0].strip(),
                "time_code": line[1].strip(),
                "sell_volume_kwh": _to_float(line[2]),
                "buy_volume_kwh": _to_float(line[3]),
                "net_volume_kwh": _to_float(line[4]),
                "system_price_jpy_kwh": _to_float(line[5]),
                "area_price_hokkaido": _to_float(line[6]),
                "area_price_tohoku": _to_float(line[7]),
                "area_price_tokyo": _to_float(line[8]),
                "area_price_chubu": _to_float(line[9]),
                "area_price_hokuriku": _to_float(line[10]),
                "area_price_kansai": _to_float(line[11]),
                "area_price_chugoku": _to_float(line[12]),
                "area_price_shikoku": _to_float(line[13]),
                "area_price_kyushu": _to_float(line[14]) if len(line) > 14 else None,
            }
            if row["date"]:
                rows.append(row)
        except (IndexError, ValueError):
            continue

    return rows


def _to_float(val: str) -> float | None:
    try:
        return float(str(val).replace(",", "").strip())
    except (ValueError, TypeError):
        return None


# ── 保存 ─────────────────────────────────────────
def save_csv(rows: list[dict], path: str) -> None:
    """取得データをCSVに保存する（既存ファイルがある場合は差分追記）。"""
    os.makedirs(os.path.dirname(path), exist_ok=True)

    existing_keys: set[tuple] = set()
    write_header = True

    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                existing_keys.add((r["date"], r["time_code"]))
        write_header = False

    new_rows = [r for r in rows if (r["date"], r["time_code"]) not in existing_keys]

    mode = "w" if write_header else "a"
    with open(path, mode, newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if write_header:
            writer.writeheader()
        writer.writerows(new_rows)

    print(f"  → 新規 {len(new_rows)} 行を保存 (重複スキップ: {len(rows) - len(new_rows)} 行)")


# ── サマリー表示 ──────────────────────────────────
def _print_summary(rows: list[dict]) -> None:
    prices = [r["system_price_jpy_kwh"] for r in rows if r["system_price_jpy_kwh"] is not None]
    if not prices:
        return

    # 日次平均を計算
    daily: dict[str, list[float]] = {}
    for r in rows:
        if r["system_price_jpy_kwh"] is not None:
            daily.setdefault(r["date"], []).append(r["system_price_jpy_kwh"])
    daily_avgs = {d: sum(v) / len(v) for d, v in daily.items()}
    sorted_dates = sorted(daily_avgs.keys())

    print("\n--- システムプライス サマリー ---")
    print(f"  期間      : {sorted_dates[0]} 〜 {sorted_dates[-1]}")
    print(f"  日数      : {len(sorted_dates)} 日")
    print(f"  コマ数    : {len(prices)} コマ（48コマ/日）")
    print(f"  全期間平均: {sum(prices)/len(prices):.2f} 円/kWh")
    print(f"  最高      : {max(prices):.2f} 円/kWh")
    print(f"  最低      : {min(prices):.2f} 円/kWh")

    # 直近7日の平均
    recent_dates = sorted_dates[-7:]
    recent_prices = [p for d in recent_dates for p in daily[d]]
    if recent_prices:
        print(f"  直近7日平均: {sum(recent_prices)/len(recent_prices):.2f} 円/kWh")


# ── メイン ────────────────────────────────────────
def main() -> None:
    print("=== JEPX スポット市場データ取得 ===")
    fiscal_years = _target_fiscal_years()
    print(f"対象年度: {fiscal_years[0]}年度〜{fiscal_years[-1]}年度\n")

    all_rows: list[dict] = []
    for fy in fiscal_years:
        rows = fetch_spot_csv(fy)
        all_rows.extend(rows)
        time.sleep(1)  # サーバー負荷軽減

    if not all_rows:
        print("[ERROR] データを1件も取得できませんでした。", file=sys.stderr)
        sys.exit(1)

    print()
    save_csv(all_rows, OUTPUT_PATH)
    print(f"\n保存先: {os.path.abspath(OUTPUT_PATH)}")

    _print_summary(all_rows)


if __name__ == "__main__":
    main()
