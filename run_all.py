"""
全データ収集スクリプトを順番に実行する。

使用方法:
  python run_all.py

終了コード:
  0 = 全て成功
  1 = 1つ以上のコレクターが失敗
"""

import importlib
import sys
import traceback
from datetime import datetime

COLLECTORS = [
    ("FRED",          "collectors.fred"),
    ("EIA",           "collectors.eia"),
    ("JEPX",          "collectors.jepx"),
    ("e-Stat",        "collectors.estat"),
    ("Yahoo Finance", "collectors.shipping"),
    # エネ庁（資源エネルギー庁）は海外IPからアクセス不可のため
    # run_collect.bat（Windowsローカル）で個別実行
]


def main() -> None:
    print(f"{'='*50}")
    print(f"  データ収集開始: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}\n")

    results: dict[str, bool] = {}

    for label, module_path in COLLECTORS:
        print(f"\n{'─'*50}")
        print(f"  [{label}]")
        print(f"{'─'*50}")
        try:
            module = importlib.import_module(module_path)
            module.main()
            results[label] = True
        except SystemExit as e:
            # collectors が sys.exit(1) で終了した場合
            if e.code != 0:
                print(f"\n[FAILED] {label}: 異常終了 (exit code={e.code})", file=sys.stderr)
                results[label] = False
            else:
                results[label] = True
        except Exception:
            print(f"\n[FAILED] {label}: 予期しないエラー", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            results[label] = False

    # 結果サマリー
    print(f"\n{'='*50}")
    print(f"  実行結果サマリー")
    print(f"{'='*50}")
    failed = []
    for label, ok in results.items():
        status = "OK  " if ok else "FAIL"
        print(f"  [{status}] {label}")
        if not ok:
            failed.append(label)

    print(f"\n  完了: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if failed:
        print(f"\n  失敗したコレクター: {', '.join(failed)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
