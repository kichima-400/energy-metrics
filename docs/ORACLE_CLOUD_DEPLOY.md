# Oracle Cloud Free Tier デプロイ手順

資源エネルギー庁サイトは海外IPからアクセス不可のため、日本リージョンのVMでエネ庁コレクターを自動実行する手順。

---

## 前提

- Oracle Cloud Free Tier アカウント（東京リージョン）
- GitHub アカウント（リポジトリへのpush権限）
- ローカルの SSH クライアント

---

## 1. アカウント作成

1. https://www.oracle.com/cloud/free/ にアクセス
2. 「無料で始める」→ クレジットカード登録（課金されない）
3. **ホームリージョン: 日本東部（東京）** を選択 ← 作成後に変更不可

---

## 2. VM インスタンス作成

Oracle Cloud コンソール →「コンピュート」→「インスタンス」→「インスタンスの作成」

| 項目 | 設定値 |
|------|--------|
| イメージ | Ubuntu 22.04 |
| シェイプ | VM.Standard.E2.1.Micro（Always Free） |
| リージョン | 日本東部（東京） |
| SSH キー | 新規生成してダウンロード |

作成後、**パブリックIPアドレス**をメモ。

---

## 3. VM に SSH 接続

```bash
ssh -i ~/Downloads/ssh-key.key ubuntu@<パブリックIP>
```

---

## 4. 環境セットアップ

```bash
# パッケージ更新
sudo apt update && sudo apt upgrade -y

# Python・git インストール
sudo apt install -y python3-pip python3-venv git

# リポジトリをクローン
git clone https://github.com/kichima-400/energy-metrics.git
cd energy-metrics

# 仮想環境作成・依存ライブラリインストール
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## 5. .env ファイル作成

```bash
nano .env
```

以下を記入して保存（Ctrl+O → Enter → Ctrl+X）:

```
FRED_API_KEY=xxxx
EIA_API_KEY=xxxx
ESTAT_API_KEY=xxxx
```

---

## 6. GitHub SSH キー設定（push用）

```bash
ssh-keygen -t ed25519 -C "oracle-cloud"
cat ~/.ssh/id_ed25519.pub
```

表示された公開鍵を GitHub → Settings → SSH Keys に追加。

```bash
# リモートURLをHTTPSからSSHに変更
git remote set-url origin git@github.com:kichima-400/energy-metrics.git

# 接続確認
ssh -T git@github.com
```

---

## 7. 動作確認

```bash
cd ~/energy-metrics
source .venv/bin/activate
mkdir -p logs
python -m collectors.enecho
```

エネ庁データが取得・保存されれば OK。

---

## 8. cron 設定

```bash
crontab -e
```

以下を追記（毎日 JST 8:00 = UTC 23:00 に実行）:

```cron
0 23 * * * cd /home/ubuntu/energy-metrics && source .venv/bin/activate && python -m collectors.enecho >> logs/collect_$(date +\%Y\%m\%d).log 2>&1 && git diff --quiet data/enecho_weekly.csv data/enecho_monthly.csv || (git add data/enecho_weekly.csv data/enecho_monthly.csv && git commit -m "chore: エネ庁データ更新 $(date +\%Y-\%m-\%d)" && git push)
```

設定確認:

```bash
crontab -l
```

---

## 9. Windowsタスクスケジューラの無効化

Oracle Cloud が正常稼働したら、Windows 側のタスクスケジューラで `run_collect.bat` を無効化する。

---

## トラブルシューティング

### SSH 接続できない

Oracle Cloud コンソール →「ネットワーキング」→「セキュリティリスト」→ インバウンドルールに **ポート22（TCP）** が許可されているか確認。

### git push できない

```bash
# SSH エージェントに鍵を追加
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519
```

### cron が実行されない

```bash
# cron サービスの確認
sudo systemctl status cron

# ログ確認
grep CRON /var/log/syslog | tail -20
```

### エネ庁サイトにアクセスできない

VM のパブリックIPが日本リージョンであることを確認:

```bash
curl -s https://ipinfo.io/country
# → JP と表示されれば OK
```
