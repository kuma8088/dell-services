# テスト仕様書: パスワードハッシュ化サービス

**対象フェーズ**: Phase 3 - 認証システム実装
**対象コンポーネント**: パスワードハッシュ化サービス (SHA512-CRYPT)
**作成日**: 2025-11-05
**優先度**: 🔴 高 (MVP必須)

---

## 1. テスト目的

パスワードハッシュ化サービスが正しく動作し、以下の機能を提供することを検証する：
- Dovecot互換のSHA512-CRYPTハッシュ生成
- パスワード検証機能
- セキュアなハッシュ強度
- エラーハンドリング

---

## 2. テスト対象機能

### 2.1 パスワードハッシュ化 (app/services/password.py)
- `hash_password(password: str) -> str`: パスワードをSHA512-CRYPTでハッシュ化
- `verify_password(password: str, hash: str) -> bool`: パスワード検証
- `generate_random_password(length: int) -> str`: ランダムパスワード生成

### 2.2 Dovecot互換性
- ハッシュ形式: `{SHA512-CRYPT}$6$...$...`
- 既存のDovecotユーザーと同じハッシュ方式
- ラウンド数: 5000 (デフォルト)

### 2.3 セキュリティ要件
- ソルト自動生成
- 十分なラウンド数
- タイミング攻撃対策

---

## 3. テストケース一覧

### TC-PW-001: 基本的なパスワードハッシュ化テスト
**目的**: hash_password が正しくハッシュを生成することを検証
**テストデータ**:
```python
test_passwords = [
    'password123',
    'SecurePass!2024',
    'テストパスワード',  # 日本語
    'P@ssw0rd_With_Speci@l_Ch@rs!',
    'a' * 100  # 長いパスワード
]
```

**テスト手順**:
1. 各テストパスワードをハッシュ化
2. ハッシュが `{SHA512-CRYPT}` で始まることを確認
3. ハッシュが `$6$` を含むことを確認 (SHA512識別子)
4. ハッシュの長さが適切であることを確認

**期待結果**:
- ✅ すべてのパスワードが正常にハッシュ化される
- ✅ ハッシュ形式が `{SHA512-CRYPT}$6$salt$hash` に一致
- ✅ 同じパスワードでも異なるハッシュが生成される (ソルト)

---

### TC-PW-002: パスワード検証テスト
**目的**: verify_password が正しくパスワードを検証することを検証
**テストデータ**:
```python
password = 'TestPassword123!'
correct_hash = hash_password(password)
wrong_password = 'WrongPassword'
```

**テスト手順**:
1. 正しいパスワードとハッシュで検証
2. 誤ったパスワードとハッシュで検証
3. 空文字列パスワードで検証
4. 大文字小文字が異なるパスワードで検証

**期待結果**:
- ✅ `verify_password(password, correct_hash)` == True
- ✅ `verify_password(wrong_password, correct_hash)` == False
- ✅ `verify_password('', correct_hash)` == False
- ✅ `verify_password('testpassword123!', correct_hash)` == False (大文字小文字区別)

---

### TC-PW-003: Dovecot互換性テスト
**目的**: 既存のDovecotハッシュと互換性があることを検証
**テストデータ**:
```python
# 既存の /etc/dovecot/users からのハッシュ
dovecot_hash = '{SHA512-CRYPT}$6$AsaBrRHlvZiiCa1q$PML7EaM2PvWhUOXXb2VwLlYnjBEbfqQcnd4zmuKjPlzmng7Q5M774u.JAFF4NFT1YYvkroIOG5FHnZSODGK5J1'
dovecot_password = 'test_password'  # 実際のパスワードは不明のためモック
```

**テスト手順**:
1. Dovecot形式のハッシュを読み込む
2. ハッシュから `{SHA512-CRYPT}` プレフィックスを除去できることを確認
3. 生成したハッシュが同じ形式であることを確認

**期待結果**:
- ✅ ハッシュ形式が Dovecot と同一
- ✅ プレフィックス `{SHA512-CRYPT}` の処理が正しい
- ✅ passlib の sha512_crypt が Dovecot 互換

---

### TC-PW-004: ソルトのランダム性テスト
**目的**: 同じパスワードでも異なるハッシュが生成されることを検証
**テストデータ**:
```python
password = 'SamePassword123'
iterations = 10
```

**テスト手順**:
1. 同じパスワードを10回ハッシュ化
2. すべてのハッシュが異なることを確認
3. すべてのハッシュで検証が成功することを確認

**期待結果**:
- ✅ 10個のハッシュがすべて異なる
- ✅ すべてのハッシュで `verify_password` が True を返す
- ✅ ソルトが自動生成されている

---

### TC-PW-005: エッジケーステスト
**目的**: 異常系・境界値でのエラーハンドリングを検証
**テストデータ**:
```python
test_cases = [
    ('', 'empty password'),           # 空パスワード
    (' ', 'whitespace only'),         # 空白のみ
    ('a', 'single character'),        # 1文字
    ('a' * 1000, 'very long'),        # 非常に長い
    (None, 'None value'),             # None
]

invalid_hashes = [
    '',                               # 空ハッシュ
    'invalid_hash',                   # 不正な形式
    '{SHA512-CRYPT}invalid',          # プレフィックスのみ
    None,                             # None
]
```

**テスト手順**:
1. 各エッジケースでハッシュ化を試行
2. エラーハンドリングが適切か確認
3. 無効なハッシュで検証を試行
4. 適切な例外が発生するか確認

**期待結果**:
- ✅ None パスワードで ValueError 発生
- ✅ 空パスワードは正常にハッシュ化される
- ✅ 無効なハッシュで verify_password が False を返す
- ✅ None ハッシュで適切なエラー処理

---

### TC-PW-006: ランダムパスワード生成テスト
**目的**: generate_random_password が安全なパスワードを生成することを検証
**テストデータ**:
```python
lengths = [8, 12, 16, 24, 32]
```

**テスト手順**:
1. 各長さでランダムパスワードを生成
2. 指定された長さであることを確認
3. 文字種が含まれることを確認 (大小英字、数字、記号)
4. 10回生成してすべて異なることを確認

**期待結果**:
- ✅ 指定された長さのパスワードが生成される
- ✅ 英大文字、英小文字、数字、記号を含む
- ✅ 10回生成してすべて異なる (ランダム性)
- ✅ 生成されたパスワードがハッシュ化可能

---

### TC-PW-007: パフォーマンステスト
**目的**: ハッシュ化と検証のパフォーマンスを検証
**テストデータ**:
```python
password = 'PerformanceTest123!'
iterations = 100
```

**テスト手順**:
1. 100回のハッシュ化時間を計測
2. 100回の検証時間を計測
3. 平均実行時間を算出

**期待結果**:
- ✅ ハッシュ化: 1回あたり < 1秒
- ✅ 検証: 1回あたり < 1秒
- ✅ SHA512-CRYPT の適切なラウンド数 (5000)

---

## 4. テスト環境

### 4.1 ライブラリ
- **passlib**: パスワードハッシュ化ライブラリ
- **sha512_crypt**: Dovecot互換ハッシュアルゴリズム

### 4.2 セキュリティ設定
- ラウンド数: 5000 (デフォルト)
- ソルト: 自動生成 (16文字)

---

## 5. 成功基準

すべてのテストケース (TC-PW-001 ~ TC-PW-007) が成功すること:
- ✅ 基本的なハッシュ化が動作する
- ✅ パスワード検証が正確
- ✅ Dovecot互換性が確保されている
- ✅ ソルトが適切にランダム生成される
- ✅ エッジケースが正しく処理される
- ✅ ランダムパスワード生成が動作する
- ✅ パフォーマンスが許容範囲内

---

## 6. テスト実行方法

```bash
# テストディレクトリに移動
cd /opt/onprem-infra-system/project-root-infra/services/mailserver/usermgmt

# テスト実行
python -m pytest tests/test_password_hashing.py -v

# カバレッジ付きテスト実行
python -m pytest tests/test_password_hashing.py --cov=app/services --cov-report=html
```

---

## 7. ロールバック基準

以下の場合、実装をロールバックする:
- ❌ TC-PW-002 (パスワード検証) が失敗
- ❌ TC-PW-003 (Dovecot互換性) が失敗
- ❌ TC-PW-005 (エッジケース) で重大なエラー

---

## 8. 次ステップ

テスト合格後:
1. Task 4: 認証ルート実装へ進む
2. login/logout エンドポイント実装
3. 統合テスト実施
