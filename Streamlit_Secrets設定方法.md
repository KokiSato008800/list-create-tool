# Streamlit Secrets 設定方法

GitHubにサービスアカウントの認証情報をプッシュできないため、Streamlit Cloudの「Secrets」機能を使用して認証情報を安全に管理します。

---

## 📋 Streamlit Cloudでの設定手順

### ステップ1: アプリをデプロイ

まず、認証情報なしでアプリをデプロイします。

1. GitHubに以下のファイルをプッシュ：
   - `streamlit_app.py`
   - `scraper.py`
   - `sheets_handler.py`
   - `config.py`（修正版）
   - `requirements.txt`
   - `packages.txt`
   - `.streamlit/config.toml`
   - `.gitignore`

2. Streamlit Cloudで「New app」を作成
3. リポジトリを選択して「Deploy」

**この時点ではエラーが出ますが、それで正常です。**

---

### ステップ2: Secrets を設定

1. Streamlit Cloudのダッシュボードを開く
2. デプロイしたアプリを選択
3. 右上の「⋮」メニュー → 「Settings」をクリック
4. 左サイドバーから「Secrets」を選択

---

### ステップ3: 認証情報を追加

「Secrets」の入力欄に、以下のように**TOML形式**で認証情報を貼り付けます：

```toml
[gcp_service_account]
type = "service_account"
project_id = "YOUR_PROJECT_ID"
private_key_id = "YOUR_PRIVATE_KEY_ID"
private_key = """-----BEGIN PRIVATE KEY-----
YOUR_PRIVATE_KEY_CONTENT_HERE
-----END PRIVATE KEY-----"""
client_email = "YOUR_SERVICE_ACCOUNT@YOUR_PROJECT_ID.iam.gserviceaccount.com"
client_id = "YOUR_CLIENT_ID"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/YOUR_SERVICE_ACCOUNT%40YOUR_PROJECT_ID.iam.gserviceaccount.com"
universe_domain = "googleapis.com"
```

**重要**: 上記の `YOUR_PROJECT_ID`, `YOUR_PRIVATE_KEY_ID`, `YOUR_PRIVATE_KEY_CONTENT_HERE` などの部分を、実際のGCPサービスアカウントの認証情報に置き換えてください。

**重要**:
- `private_key`の部分は**三重引用符 `"""`** で囲んでください
- インデントに注意してください
- 改行をそのまま保持してください

---

### ステップ4: 保存して再起動

1. 「Save」ボタンをクリック
2. アプリが自動的に再起動されます
3. 数分待つと、アプリが正常に動作するようになります

---

## ✅ 動作確認

アプリのURLを開いて、以下を確認：

1. エラーが表示されないこと
2. スプレッドシートURLを入力できること
3. 「データ取得開始」ボタンが押せること

---

## 🔧 トラブルシューティング

### エラー: 「認証情報が見つかりません」

**原因**: Secretsの設定が正しくありません

**対処法**:
1. Secretsの内容を再確認
2. TOML形式が正しいか確認
3. `[gcp_service_account]`というセクション名が正しいか確認

---

### エラー: 「TOML parse error」

**原因**: TOML形式が間違っています

**対処法**:
1. `private_key`が三重引用符で囲まれているか確認
2. インデントが正しいか確認
3. 上記の例をそのままコピー&ペーストしてみてください

---

## 📝 ローカル開発の場合

ローカルで開発・テストする場合は、以下の方法で認証情報を設定できます：

### 方法1: credentials.json ファイル

プロジェクトルートに`credentials.json`ファイルを作成：

```json
{
  "type": "service_account",
  "project_id": "YOUR_PROJECT_ID",
  "private_key_id": "YOUR_PRIVATE_KEY_ID",
  "private_key": "-----BEGIN PRIVATE KEY-----\nYOUR_PRIVATE_KEY_CONTENT_HERE\n-----END PRIVATE KEY-----\n",
  "client_email": "YOUR_SERVICE_ACCOUNT@YOUR_PROJECT_ID.iam.gserviceaccount.com",
  "client_id": "YOUR_CLIENT_ID",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/YOUR_SERVICE_ACCOUNT%40YOUR_PROJECT_ID.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}
```

**重要**: 実際のサービスアカウントの認証情報に置き換えてください。GCP Console > IAM > サービスアカウント からダウンロードできます。

**⚠️ 注意**: このファイルは`.gitignore`に含まれているため、GitHubにプッシュされません。

---

## 🔐 セキュリティのベストプラクティス

1. **絶対にGitHubにプッシュしない**: 認証情報は`.gitignore`で除外
2. **Streamlit Secretsを使用**: 本番環境では必ずSecretsを使用
3. **定期的にキーをローテーション**: 定期的に新しいサービスアカウントキーを作成
4. **最小権限の原則**: 必要最小限の権限のみ付与

---

これで安全にStreamlit Cloudにデプロイできます！
