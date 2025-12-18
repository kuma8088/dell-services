# 統合管理ポータル 運用設計

**技術スタック**: FastAPI, React, Docker Compose, pytest, Vitest

---

## 1. 運用方針

### 1.1 運用原則

| 原則 | 内容 |
|------|------|
| 自動化優先 | 定型作業はスクリプト化 |
| 監視と通知 | 異常検知→即時対応 |
| ドキュメント化 | 手順書整備、変更履歴記録 |
| 最小権限 | 運用に必要な権限のみ付与 |

### 1.2 運用担当範囲

| カテゴリ | 担当 | 頻度 |
|---------|------|------|
| 日常監視 | 自動/手動 | 毎日 |
| セキュリティ更新 | 手動 | 月次 |
| 機能追加 | 手動 | 随時 |
| 障害対応 | 手動 | 随時 |

---

## 2. 監視設計

### 2.1 監視項目

| カテゴリ | 監視項目 | 閾値 | 通知 |
|---------|---------|------|------|
| サービス | Backend状態 | unhealthy | 緊急 |
| サービス | Frontend応答 | 5秒以上 | 警告 |
| サービス | Nginx状態 | unhealthy | 緊急 |
| API | レスポンスタイム | 1秒以上 | 警告 |
| API | エラー率 | 1%以上 | 警告 |
| リソース | CPU使用率 | 80%以上 | 警告 |
| リソース | メモリ使用率 | 80%以上 | 警告 |

### 2.2 ヘルスチェック

```bash
# Docker Compose サービス状態確認
cd /opt/onprem-infra-system/project-root-infra/services/unified-portal
docker compose ps

# Backend ヘルスチェック
curl http://localhost:8000/api/health

# 期待出力
# {"status":"healthy","version":"0.1.0"}

# Nginx ヘルスチェック
curl http://localhost:8080/health

# Frontend確認
curl -I http://localhost:8080/
```

### 2.3 ログ監視

| ログ | 確認方法 | 確認ポイント |
|------|---------|-------------|
| Backend | `docker logs unified-portal-backend` | API エラー、例外 |
| Frontend | `docker logs unified-portal-frontend` | ビルドエラー |
| Nginx | `docker logs unified-portal-nginx` | 5xx エラー、アクセス異常 |

---

## 3. 開発ガイド

### 3.1 Backend開発環境セットアップ

```bash
# 1. ディレクトリ移動
cd /opt/onprem-infra-system/project-root-infra/services/unified-portal/backend

# 2. 仮想環境作成（初回のみ）
python3 -m venv venv

# 3. 仮想環境有効化
source venv/bin/activate

# 4. 依存関係インストール
pip install --upgrade pip
pip install -r requirements.txt

# 5. 環境変数設定
cp .env.local-setup .env
# .env を編集（DB接続情報等）

# 6. 開発サーバー起動
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3.2 Frontend開発環境セットアップ

```bash
# 1. ディレクトリ移動
cd /opt/onprem-infra-system/project-root-infra/services/unified-portal/frontend

# 2. 依存関係インストール
npm install

# 3. 環境変数設定
cp .env.example .env.local
# .env.local を編集

# 4. 開発サーバー起動
npm run dev
```

### 3.3 データベース接続確認

```bash
cd /opt/onprem-infra-system/project-root-infra/services/unified-portal/backend
source venv/bin/activate

python -c "
from app.database import mailserver_engine
from sqlalchemy import text

try:
    with mailserver_engine.connect() as conn:
        result = conn.execute(text('SELECT COUNT(*) FROM users'))
        print(f'✅ DB接続成功: {result.scalar()} users')
except Exception as e:
    print(f'❌ エラー: {e}')
"
```

---

## 4. テスト実行

### 4.1 Backend テスト

```bash
cd /opt/onprem-infra-system/project-root-infra/services/unified-portal/backend
source venv/bin/activate

# 全テスト実行
pytest

# 詳細出力
pytest -v

# カバレッジ付きテスト
pytest --cov=app --cov-report=html

# 特定のテストのみ
pytest tests/test_auth.py -v

# カバレッジレポート確認
open htmlcov/index.html
```

### 4.2 Frontend テスト

```bash
cd /opt/onprem-infra-system/project-root-infra/services/unified-portal/frontend

# Unit テスト
npm run test

# カバレッジ付きテスト
npm run test:coverage

# 型チェック
npm run type-check

# Lint
npm run lint
```

---

## 5. 障害対応

### 5.1 障害レベル定義

| レベル | 定義 | 目標復旧時間 | 例 |
|--------|------|-------------|-----|
| Critical | ポータル全体停止 | 1時間 | 全コンテナ停止 |
| High | 主要機能停止 | 2時間 | API応答なし |
| Medium | 一部機能停止 | 4時間 | 特定ページエラー |
| Low | 軽微な問題 | 24時間 | 表示崩れ |

### 5.2 障害対応フロー

```
障害検知
    │
    ▼
┌─────────────────────┐
│ 1. 影響範囲確認     │
│    docker compose ps│
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│ 2. ログ確認         │
│    docker logs ...  │
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│ 3. 原因特定         │
│    設定/リソース/外部│
└─────────────────────┘
    │
    ├── Backend問題 → サービス再起動
    ├── Frontend問題 → 再ビルド
    └── Nginx問題 → 設定確認/reload
    │
    ▼
┌─────────────────────┐
│ 4. 復旧確認         │
│    ヘルスチェック    │
└─────────────────────┘
```

### 5.3 よくある障害と対処

#### Backend起動失敗

```bash
# 1. ログ確認
docker compose logs backend | tail -50

# 2. 環境変数確認
docker compose exec backend env | grep DATABASE

# 3. DB接続テスト
docker compose exec backend python -c "
from app.database import engine
print(engine.connect())
"

# 4. 再起動
docker compose restart backend
```

#### Frontend表示されない

```bash
# 1. ビルド状態確認
docker compose logs frontend | tail -50

# 2. 静的ファイル確認
docker compose exec nginx ls -la /usr/share/nginx/html/

# 3. 再ビルド
docker compose build frontend
docker compose up -d frontend nginx
```

#### API応答なし

```bash
# 1. Backend状態確認
curl http://localhost:8000/api/health

# 2. Nginxプロキシ確認
docker compose logs nginx | grep -i error

# 3. ネットワーク確認
docker network inspect unified-portal_portal_network
```

---

## 6. デバッグ方法

### 6.1 Backend デバッグ

```bash
# ログレベル変更
LOG_LEVEL=DEBUG uvicorn app.main:app --reload

# SQLクエリログ有効化
# app/database.py で SQLALCHEMY_ECHO = True
```

### 6.2 Frontend デバッグ

```tsx
// API リクエストログ追加（src/lib/api.ts）
axios.interceptors.request.use((config) => {
  console.log('Request:', config);
  return config;
});

axios.interceptors.response.use(
  (response) => {
    console.log('Response:', response);
    return response;
  },
  (error) => {
    console.error('Error:', error);
    return Promise.reject(error);
  }
);
```

### 6.3 VSCode デバッガー設定

**.vscode/launch.json**:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": ["app.main:app", "--reload"],
      "jinja": true
    },
    {
      "name": "Chrome: Frontend",
      "type": "chrome",
      "request": "launch",
      "url": "http://localhost:5173",
      "webRoot": "${workspaceFolder}/frontend/src"
    }
  ]
}
```

---

## 7. トラブルシューティング

### 7.1 Backend

| 問題 | 原因 | 解決策 |
|------|------|--------|
| `ModuleNotFoundError` | venv未有効化 | `source venv/bin/activate` |
| DB接続エラー | パスワード不一致 | `.env` 確認 |
| Docker APIエラー | 権限不足 | `usermod -aG docker $USER` |

### 7.2 Frontend

| 問題 | 原因 | 解決策 |
|------|------|--------|
| `ECONNREFUSED` | Backend未起動 | Backend起動確認 |
| `Module not found` | 依存関係不足 | `npm install` |
| ビルドエラー | TypeScriptエラー | `npm run type-check` |

### 7.3 Docker

| 問題 | 原因 | 解決策 |
|------|------|--------|
| コンテナ起動失敗 | ポート競合 | `docker compose config` で確認 |
| ネットワークエラー | IP競合 | サブネット変更 |
| ビルド失敗 | キャッシュ問題 | `docker compose build --no-cache` |

---

## 8. 定期メンテナンス

### 8.1 日次タスク

| タスク | 確認方法 |
|--------|---------|
| サービス状態確認 | `docker compose ps` |
| エラーログ確認 | `docker compose logs --since 24h | grep -i error` |

### 8.2 週次タスク

| タスク | 確認方法 |
|--------|---------|
| ディスク使用量確認 | `docker system df` |
| 未使用イメージ削除 | `docker image prune` |
| セキュリティ更新確認 | `pip list --outdated` |

### 8.3 月次タスク

| タスク | 手順 |
|--------|------|
| 依存関係更新 | `pip install --upgrade -r requirements.txt` |
| npm更新 | `npm update` |
| Dockerイメージ更新 | `docker compose pull` |
| セキュリティ監査 | `npm audit`, `pip audit` |

---

## 9. API仕様

### 9.1 自動生成ドキュメント

| URL | 説明 |
|-----|------|
| /docs | Swagger UI |
| /redoc | ReDoc |
| /openapi.json | OpenAPI仕様 |

### 9.2 認証フロー

```
1. POST /api/v1/auth/login
   Request: { "username": "...", "password": "..." }
   Response: { "access_token": "...", "token_type": "bearer" }

2. 認証が必要なエンドポイント
   Header: Authorization: Bearer <access_token>

3. POST /api/v1/auth/refresh
   トークン更新

4. POST /api/v1/auth/logout
   ログアウト
```

---

## 10. 運用チェックリスト

### 10.1 デプロイ時

```
□ 設定ファイルの検証（docker compose config）
□ バックアップ確認
□ 変更内容のレビュー
□ ロールバック手順の確認
□ デプロイの実行
□ ヘルスチェック
□ ログ確認
```

### 10.2 障害発生時

```
□ 影響範囲の確認
□ ログの確認
□ 原因の特定
□ 対処の実施
□ 復旧の確認
□ 事後分析・再発防止策
```

---

## 11. 推奨開発ツール

### 11.1 VSCode拡張機能

```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.vscode-pylance",
    "esbenp.prettier-vscode",
    "dbaeumer.vscode-eslint",
    "bradlc.vscode-tailwindcss",
    "ms-vscode.vscode-typescript-next"
  ]
}
```

### 11.2 ブラウザ拡張機能

- React Developer Tools
- JSON Viewer

---

## 12. 関連ドキュメント

| ドキュメント | 内容 |
|------------|------|
| [requirements.md](requirements.md) | 要件定義・トレードオフ分析 |
| [architecture.md](architecture.md) | システムアーキテクチャ・コンポーネント設計 |
| [deployment.md](deployment.md) | デプロイ戦略・Docker Compose設定 |
