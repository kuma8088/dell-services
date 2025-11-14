# テスト計画書（簡易版）

**プロジェクト**: Unified Portal - Mailserver統合

**テスト戦略**: ユニットテスト + 統合テスト + E2Eテスト

**目標カバレッジ**: 80%以上

**作成日**: 2025-11-14

---

## 📋 テストレベル

### 1. ユニットテスト（Unit Tests）
**対象**: 個別関数・メソッド
**ツール**: pytest（バックエンド）、Jest/Vitest（フロントエンド）
**実施環境**: Web側 + ローカル

#### バックエンド
```bash
# 実行コマンド
pytest tests/ -v --cov=app --cov-report=html

# テストファイル
- test_mail_user_service.py: UserService全メソッド
- test_mail_domain_service.py: DomainService全メソッド
- test_admin_user_service.py: AdminUserService全メソッド
- test_password_reset_service.py: パスワードリセットロジック
- test_email_service.py: メール送信機能

# テストケース例
def test_create_user_success():
    user = MailUserService.create_user(
        email="test@kuma8088.com",
        password="SecurePass123!",
        domain_id=1
    )
    assert user.email == "test@kuma8088.com"
    assert user.maildir == "/var/mail/vmail/kuma8088.com/test/"

def test_create_user_duplicate_email():
    with pytest.raises(ValueError, match="Email already exists"):
        MailUserService.create_user(...)
```

#### フロントエンド
```bash
# 実行コマンド
npm run test

# テストファイル
- src/components/mailserver/__tests__/UserTable.test.tsx
- src/components/mailserver/__tests__/UserForm.test.tsx
- src/lib/__tests__/mailserver-api.test.ts

# テストケース例（React Testing Library）
test('renders user table with data', () => {
  const users = [{id: 1, email: 'test@kuma8088.com', ...}];
  render(<UserTable users={users} />);
  expect(screen.getByText('test@kuma8088.com')).toBeInTheDocument();
});
```

---

### 2. 統合テスト（Integration Tests）
**対象**: API エンドポイント（DB接続含む）
**ツール**: pytest + TestClient（FastAPI）
**実施環境**: ローカル（実DBに接続）

```python
# test_mailserver_router.py
def test_list_users_endpoint(client, db_session):
    response = client.get(
        "/api/v1/mailserver/users",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert "users" in response.json()

def test_create_user_endpoint(client):
    response = client.post(
        "/api/v1/mailserver/users",
        json={"email": "test@kuma8088.com", "password": "Pass123!", "domain_id": 1},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 201
    assert response.json()["email"] == "test@kuma8088.com"
```

---

### 3. E2Eテスト（End-to-End Tests）
**対象**: ユーザーシナリオ全体
**ツール**: 手動テスト（ローカル環境）、将来的にPlaywright
**実施環境**: ローカル

#### テストシナリオ
1. **ユーザー管理フロー**:
   - ログイン → ユーザー一覧表示 → ユーザー作成 → 編集 → 削除
2. **パスワードリセットフロー**:
   - パスワード再設定リクエスト → メール受信 → リンククリック → 新パスワード設定
3. **管理者管理フロー**:
   - 管理者作成 → 権限設定 → ログイン確認
4. **DNS管理フロー**:
   - Cloudflareリンククリック → レコード編集 → DNS検証

---

## ✅ テストケース一覧

### メールユーザー管理（40ケース）
| ID | テストケース | 期待結果 |
|----|------------|----------|
| U001 | ユーザー一覧取得（正常） | 200 OK、ユーザー配列返却 |
| U002 | ユーザー一覧取得（ドメインフィルタ） | 指定ドメインのユーザーのみ返却 |
| U003 | ユーザー作成（正常） | 201 Created、maildir自動生成 |
| U004 | ユーザー作成（重複email） | 400 Bad Request |
| U005 | ユーザー作成（不正email形式） | 400 Bad Request |
| U006 | ユーザー作成（パスワード短すぎ） | 400 Bad Request |
| U007 | ユーザー更新（quota変更） | 200 OK |
| U008 | ユーザー削除（正常） | 204 No Content |
| U009 | パスワード変更（正常） | 200 OK、SHA512-CRYPTハッシュ |
| U010 | 有効/無効切替（正常） | 200 OK |
| ... | （以下30ケース） | ... |

### パスワードリセット（15ケース）
| ID | テストケース | 期待結果 |
|----|------------|----------|
| PR001 | リセットリクエスト（正常） | 200 OK、メール送信 |
| PR002 | リセットリクエスト（存在しないemail） | 200 OK（情報漏洩防止） |
| PR003 | リセットリクエスト（レート制限超過） | 429 Too Many Requests |
| PR004 | トークン検証（正常） | 200 OK、valid=true |
| PR005 | トークン検証（期限切れ） | 400 Bad Request |
| PR006 | トークン検証（使用済み） | 400 Bad Request |
| PR007 | パスワードリセット実行（正常） | 200 OK、成功メール送信 |
| ... | （以下8ケース） | ... |

### 管理者管理（10ケース）
| ID | テストケース | 期待結果 |
|----|------------|----------|
| A001 | 管理者一覧取得（正常） | 200 OK |
| A002 | 管理者作成（正常） | 201 Created |
| A003 | 管理者削除（正常） | 204 No Content |
| A004 | 権限レベル設定（正常） | 200 OK |
| ... | （以下6ケース） | ... |

### DNS管理（10ケース）
| ID | テストケース | 期待結果 |
|----|------------|----------|
| D001 | DNSレコード編集（正常） | 200 OK |
| D002 | DNS検証（正常） | 200 OK、dig結果返却 |
| ... | （以下8ケース） | ... |

---

## 🧪 テスト実施手順

### Step 1: Web側でテストコード生成（W-036 ~ W-038）
```bash
# pytest テストコード作成
# Jest/Vitest テストコード作成
```

### Step 2: ローカルでテスト実行
```bash
# バックエンドテスト
cd /opt/onprem-infra-system/project-root-infra/services/unified-portal/backend
source venv/bin/activate
pytest tests/ -v --cov=app --cov-report=html --cov-report=term

# フロントエンドテスト
cd /opt/onprem-infra-system/project-root-infra/services/unified-portal/frontend
npm run test

# E2Eテスト（手動）
# ブラウザでhttps://admin.kuma8088.comを開いて全シナリオ実行
```

### Step 3: 結果確認
- [ ] 全テストパス
- [ ] カバレッジ > 80%
- [ ] エラーログなし

---

## 📊 テストカバレッジ目標

| モジュール | 目標カバレッジ |
|-----------|--------------|
| models/ | 100% |
| services/ | 90% |
| routers/ | 85% |
| schemas/ | 100% |
| 全体 | 80%以上 |

---

## 🔄 継続的テスト

### CI/CD統合（将来実装）
```yaml
# .github/workflows/test.yml
name: Test
on: [push, pull_request]
jobs:
  backend-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run pytest
        run: |
          cd services/unified-portal/backend
          pip install -r requirements.txt
          pytest tests/ -v --cov=app
  frontend-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run npm test
        run: |
          cd services/unified-portal/frontend
          npm install
          npm run test
```

---

**参照**:
- [03_TASK_BREAKDOWN.md](03_TASK_BREAKDOWN.md) - テストタスク詳細（W-036 ~ W-038）
- [05_LOCAL_IMPLEMENTATION.md](05_LOCAL_IMPLEMENTATION.md) - ローカルテスト実行手順
