# エネルギー価格相関ダッシュボード

原油・LNG・石炭・為替・海運指標と日本国内エネルギー価格の相関を可視化するWebアプリケーション。

**ライブデモ:** https://energy-metrics-uydn.vercel.app/

---

## 概要

世界情勢（原油・LNG・石炭・為替・海運）が日本の消費者エネルギー価格（ガソリン・電気料金・ガス料金）に与える影響を可視化する。毎日 JST 6:00 / 18:00 の2回、最新データを自動取得し、ダッシュボードに反映する。

### 主な機能

- **時系列チャート** — 複数指標を重ねて表示。正規化（初日=100）で単位の異なる指標を比較可能
- **表示期間選択** — 1ヶ月 / 3ヶ月 / 6ヶ月 / 1年 / 3年 / 5年 / 10年 / 全期間
- **指標トグル** — カテゴリ別に24指標をON/OFF切り替え
- **サマリーパネル** — 最新値・前値比・前月比をカテゴリ別に一覧表示

---

## 指標一覧

| カテゴリ | 指標 | ソース | 更新頻度 |
|---------|------|--------|---------|
| 原油 | WTI原油 | Yahoo Finance `CL=F` | 日次 |
| 原油 | Brent原油 | Yahoo Finance `BZ=F` | 日次 |
| 天然ガス | Henry Hub LNG | FRED `DHHNGSP` | 日次 |
| 天然ガス | 欧州天然ガス(TTF) | Yahoo Finance `TTF=F` | 日次 |
| 天然ガス | アジアLNG(JKM) | FRED `PNGASJPUSDM` | 月次 |
| 天然ガス | 米国ガス在庫 | EIA `NW2_EPG0_SWO_NUS_BCF` | 週次 |
| 石炭 | 豪州石炭 | FRED `PCOALAUUSDM` | 月次 |
| 為替 | ドル円 | Yahoo Finance `JPY=X` | 日次 |
| 為替 | ユーロ円 | Yahoo Finance `EURJPY=X` | 日次 |
| 為替 | 円名目実効為替レート(NEER) | FRED `NBJPBIS`（BIS） | 月次 |
| 金利 | 米国政策金利 | FRED `FEDFUNDS` | 月次 |
| 国内 | 電気代指数 | e-Stat CPI (2020=100) | 月次 |
| 国内 | 都市ガス代指数 | e-Stat CPI (2020=100) | 月次 |
| 国内 | ガソリン指数 | e-Stat CPI (2020=100) | 月次 |
| 国内 | 灯油指数 | e-Stat CPI (2020=100) | 月次 |
| 国内 | ガソリン元売り価格 | 資源エネルギー庁 石油製品価格調査 | 月次 ※1 |
| 国内 | ハイオク小売価格 | 資源エネルギー庁 石油製品価格調査 | 週次 ※1 |
| 国内 | ガソリン小売価格 | 資源エネルギー庁 石油製品価格調査 | 週次 ※1 |
| 国内 | 灯油小売価格 | 資源エネルギー庁 石油製品価格調査 | 週次 ※1 |
| 国内 | JEPX システムプライス | JEPX スポット市場 | 日次 |
| 国内 | JEPX 東京エリア | JEPX スポット市場 | 日次 |
| 海運 | ドライバルク運賃(BDRY) | Yahoo Finance `BDRY` | 日次 |
| 海運 | タンカー運賃ETF(BWET) | Yahoo Finance `BWET` | 日次 |
| 海運 | コンテナ海運株(ZIM) | Yahoo Finance `ZIM` | 日次 |

> ※1 資源エネルギー庁サイトは海外IPからアクセス不可のため、Windowsタスクスケジューラによるローカル収集を併用（後述）

---

## アーキテクチャ

```
【自動収集①】GitHub Actions（毎日 JST 6:00 / 18:00）
  └── Yahoo Finance・FRED・EIA・e-Stat・JEPX のデータを取得
  └── data/*.csv をリポジトリにcommit
  └── Vercel Deploy Hook で API を再デプロイ

【自動収集②】Windowsタスクスケジューラ（毎日任意の時刻）
  └── 資源エネルギー庁 週次ガソリン・灯油価格を取得（海外IPからアクセス不可のため）
  └── run_collect.bat → python run_all.py → git push

Vercel（API）                    Vercel（フロントエンド）
  └── FastAPI サーバーレス          └── Next.js
  └── data/*.csv を読み込んで返す    └── API から取得してチャート表示
```

| レイヤー | 技術 |
|---------|------|
| フロントエンド | Next.js 16 / TypeScript / Tailwind CSS / Recharts |
| バックエンド | Python 3.12 / FastAPI / pandas |
| ホスティング | Vercel（フロント・API 両方） |
| データ更新（国際指標） | GitHub Actions（日次 cron） |
| データ更新（国内小売価格） | Windowsタスクスケジューラ + `run_collect.bat` |
| データ保存 | CSV ファイル（リポジトリ内 `data/`） |

---

## ローカル開発

### 前提条件

- Python 3.12+
- Node.js 18+
- 各種 API キー（`.env` ファイルに設定）

### セットアップ

```bash
# リポジトリをクローン
git clone https://github.com/kichima-400/energy-metrics.git
cd energy-metrics

# Python 依存ライブラリをインストール
pip install -r requirements.txt

# .env ファイルを作成（.env.example を参考に）
cp .env.example .env
# .env に各APIキーを記入

# データを手動取得
python run_all.py
```

### バックエンド起動

```bash
uvicorn api.main:app --port 8001
# → http://localhost:8001/docs でAPIドキュメント確認
```

### フロントエンド起動

```bash
cd frontend
NEXT_PUBLIC_API_URL=http://localhost:8001 npm run dev
# → http://localhost:3000 でダッシュボード確認
```

---

## データ更新の仕組み

### GitHub Actions（国際指標）

毎日 JST 6:00 と 18:00 の2回、以下を実行する:

1. `python run_all.py` — Yahoo Finance・FRED・EIA・e-Stat・JEPX からデータ取得
2. `data/` 以下の CSV に差分をcommit・push
3. Vercel Deploy Hook を叩いて API を再デプロイ

手動実行: GitHub リポジトリ → Actions → 「データ収集」→ Run workflow

### Windowsタスクスケジューラ（国内小売価格）

資源エネルギー庁サイトは海外IPからアクセスできないため、常時稼働のWindowsPC上でタスクスケジューラを使って自動収集する。

1. `run_collect.bat` を毎日実行
2. `python run_all.py` で全コレクター（エネ庁含む）を実行
3. `data/` に変更があれば自動でcommit・push
4. ログは `logs/collect_YYYYMMDD.log` に保存

セットアップ手順は [DEPLOY.md](DEPLOY.md) を参照。

---

## API エンドポイント

ベースURL: https://energy-metrics-beta.vercel.app

| エンドポイント | 説明 |
|--------------|------|
| `GET /health` | ヘルスチェック |
| `GET /api/indicators` | 指標一覧 |
| `GET /api/chart?ids=wti_crude&start=2024-01-01&end=2024-12-31` | 時系列データ |
| `GET /api/summary` | 最新値・前値比・前月比 |
