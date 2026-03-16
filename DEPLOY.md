# デプロイ手順

このアプリケーションは **Vercel 2プロジェクト構成** でデプロイする。
同一の GitHub リポジトリから、APIとフロントエンドをそれぞれ別プロジェクトとして展開する。

---

## 前提条件

- GitHub アカウント（リポジトリ: `kichima-400/energy-metrics`）
- Vercel アカウント（https://vercel.com — GitHub ログインで登録可、クレカ不要）
- 各種 API キー（FRED・EIA・e-Stat）

---

## 1. Vercel APIプロジェクトの作成

### 1-1. プロジェクト作成

1. https://vercel.com/dashboard → **Add New Project**
2. GitHub リポジトリ `energy-metrics` を選択
3. 以下の設定を行う:

| 項目 | 設定値 |
|------|--------|
| Root Directory | `/`（デフォルトのまま） |
| Framework Preset | **Other**（Next.js が自動検出されても変更する） |

4. **Deploy** をクリック

### 1-2. デプロイ後の確認

- プロジェクト URL（例: `https://energy-metrics-beta.vercel.app`）をメモする
- `https://<your-api-url>/health` にアクセスして `{"status":"ok"}` が返ることを確認

### 1-3. Deploy Hook の作成

1. プロジェクト → **Settings** → **Git** → **Deploy Hooks**
2. Hook名: `github-actions`、Branch: `main` → **Create Hook**
3. 生成された URL をコピーしておく（後で GitHub Secrets に登録）

---

## 2. Vercel フロントエンドプロジェクトの作成

### 2-1. プロジェクト作成

1. https://vercel.com/dashboard → **Add New Project**
2. 同じ GitHub リポジトリ `energy-metrics` を選択
3. 以下の設定を行う:

| 項目 | 設定値 |
|------|--------|
| Root Directory | `frontend` |
| Framework Preset | Next.js（自動検出される） |

4. **Environment Variables** に以下を追加:

| Name | Value |
|------|-------|
| `NEXT_PUBLIC_API_URL` | `https://<手順1でメモしたAPIのURL>` |

5. **Deploy** をクリック

---

## 3. GitHub Secrets の設定

GitHub リポジトリ → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

| Name | Value |
|------|-------|
| `FRED_API_KEY` | FRED の API キー（https://fred.stlouisfed.org/docs/api/api_key.html） |
| `EIA_API_KEY` | EIA の API キー（https://www.eia.gov/opendata/register.php） |
| `ESTAT_API_KEY` | e-Stat の API キー（https://api.e-stat.go.jp/） |
| `VERCEL_DEPLOY_HOOK_API` | 手順1-3でコピーした Deploy Hook URL |

---

## 4. 動作確認

### API

```bash
# ヘルスチェック
curl https://<your-api-url>/health

# 指標一覧
curl https://<your-api-url>/api/indicators

# サマリー
curl https://<your-api-url>/api/summary
```

### フロントエンド

ブラウザで `https://<your-frontend-url>/` を開き、チャートとサマリーパネルが表示されることを確認する。

### GitHub Actions の手動実行

1. GitHub リポジトリ → **Actions** タブ
2. 左側「データ収集」をクリック
3. **Run workflow** → **Run workflow** をクリック
4. 完了後、`data/` ディレクトリに新しいコミットが作成され、Vercel API が再デプロイされることを確認する

---

## 構成ファイルの役割

| ファイル | 役割 |
|---------|------|
| `vercel.json` | API プロジェクト用 Vercel 設定（Python サーバーレス関数） |
| `frontend/vercel.json` | フロントエンドプロジェクト用 Vercel 設定（Next.js） |
| `api/index.py` | Vercel サーバーレス関数のエントリーポイント |
| `.github/workflows/collect-data.yml` | データ収集・commit・Vercel 再デプロイの自動化 |
