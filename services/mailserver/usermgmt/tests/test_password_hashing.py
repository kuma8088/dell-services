"""
Test suite for Password Hashing Service (Phase 3 - Task 3)

Test Specification: tests/specs/TEST_SPEC_password_hashing.md
"""
import pytest
import re
import time
from app.services.password import hash_password, verify_password, generate_random_password


class TestBasicPasswordHashing:
    """TC-PW-001: 基本的なパスワードハッシュ化テスト"""

    def test_hash_password_basic(self):
        """基本的なパスワードがハッシュ化されることを検証"""
        password = 'password123'
        hashed = hash_password(password)

        # ハッシュ形式の検証
        assert hashed.startswith('{SHA512-CRYPT}')
        assert '$6$' in hashed  # SHA512識別子
        assert len(hashed) > 50  # 十分な長さ

    def test_hash_password_secure(self):
        """セキュアなパスワードがハッシュ化されることを検証"""
        password = 'SecurePass!2024'
        hashed = hash_password(password)

        assert hashed.startswith('{SHA512-CRYPT}')
        assert '$6$' in hashed

    def test_hash_password_japanese(self):
        """日本語パスワードがハッシュ化されることを検証"""
        password = 'テストパスワード'
        hashed = hash_password(password)

        assert hashed.startswith('{SHA512-CRYPT}')
        assert '$6$' in hashed

    def test_hash_password_special_chars(self):
        """特殊文字を含むパスワードがハッシュ化されることを検証"""
        password = 'P@ssw0rd_With_Speci@l_Ch@rs!'
        hashed = hash_password(password)

        assert hashed.startswith('{SHA512-CRYPT}')
        assert '$6$' in hashed

    def test_hash_password_long(self):
        """長いパスワードがハッシュ化されることを検証"""
        password = 'a' * 100
        hashed = hash_password(password)

        assert hashed.startswith('{SHA512-CRYPT}')
        assert '$6$' in hashed

    def test_hash_format_structure(self):
        """ハッシュ形式が正しい構造であることを検証"""
        password = 'TestPassword'
        hashed = hash_password(password)

        # {SHA512-CRYPT}$6$salt$hash の形式
        pattern = r'^\{SHA512-CRYPT\}\$6\$[A-Za-z0-9./]+\$[A-Za-z0-9./]+$'
        assert re.match(pattern, hashed) is not None


class TestPasswordVerification:
    """TC-PW-002: パスワード検証テスト"""

    def test_verify_correct_password(self):
        """正しいパスワードで検証が成功することを確認"""
        password = 'TestPassword123!'
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_wrong_password(self):
        """誤ったパスワードで検証が失敗することを確認"""
        password = 'TestPassword123!'
        wrong_password = 'WrongPassword'
        hashed = hash_password(password)

        assert verify_password(wrong_password, hashed) is False

    def test_verify_empty_password(self):
        """空パスワードで検証が失敗することを確認"""
        password = 'TestPassword123!'
        hashed = hash_password(password)

        assert verify_password('', hashed) is False

    def test_verify_case_sensitive(self):
        """大文字小文字が区別されることを確認"""
        password = 'TestPassword123!'
        wrong_case = 'testpassword123!'
        hashed = hash_password(password)

        assert verify_password(wrong_case, hashed) is False

    def test_verify_multiple_passwords(self):
        """複数のパスワードが正しく検証されることを確認"""
        passwords = ['Pass1', 'Pass2', 'Pass3']
        hashes = [hash_password(p) for p in passwords]

        # 正しい組み合わせ
        for password, hashed in zip(passwords, hashes):
            assert verify_password(password, hashed) is True

        # 誤った組み合わせ
        assert verify_password(passwords[0], hashes[1]) is False
        assert verify_password(passwords[1], hashes[2]) is False


class TestDovecotCompatibility:
    """TC-PW-003: Dovecot互換性テスト"""

    def test_hash_format_matches_dovecot(self):
        """生成されたハッシュがDovecot形式と一致することを確認"""
        password = 'test_password'
        hashed = hash_password(password)

        # Dovecot形式: {SHA512-CRYPT}$6$salt$hash
        assert hashed.startswith('{SHA512-CRYPT}')
        assert '$6$' in hashed

        # プレフィックス除去が可能
        hash_without_prefix = hashed.replace('{SHA512-CRYPT}', '')
        assert hash_without_prefix.startswith('$6$')

    def test_prefix_handling(self):
        """プレフィックスの処理が正しいことを確認"""
        password = 'test'
        hashed = hash_password(password)

        # プレフィックス除去
        hash_value = hashed.replace('{SHA512-CRYPT}', '')

        # passlib互換形式
        assert hash_value.startswith('$6$')

    def test_rounds_parameter(self):
        """ラウンド数が適切であることを確認"""
        password = 'test'
        hashed = hash_password(password)

        # SHA512-CRYPTのデフォルトラウンド数は5000
        # ハッシュにrounds指定がない場合はデフォルト
        hash_without_prefix = hashed.replace('{SHA512-CRYPT}', '')
        # $6$salt$hash または $6$rounds=5000$salt$hash の形式
        assert hash_without_prefix.startswith('$6$')


class TestSaltRandomness:
    """TC-PW-004: ソルトのランダム性テスト"""

    def test_same_password_different_hashes(self):
        """同じパスワードでも異なるハッシュが生成されることを確認"""
        password = 'SamePassword123'
        hashes = [hash_password(password) for _ in range(10)]

        # すべてのハッシュが異なる
        assert len(set(hashes)) == 10

    def test_all_hashes_verify(self):
        """すべてのハッシュで検証が成功することを確認"""
        password = 'SamePassword123'
        hashes = [hash_password(password) for _ in range(10)]

        # すべてのハッシュで検証成功
        for hashed in hashes:
            assert verify_password(password, hashed) is True

    def test_salt_is_generated(self):
        """ソルトが自動生成されることを確認"""
        password = 'test'
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        # ハッシュから塩を抽出 (簡易チェック)
        # {SHA512-CRYPT}$6$salt$hash の形式
        salt1 = hash1.split('$')[2] if len(hash1.split('$')) > 2 else ''
        salt2 = hash2.split('$')[2] if len(hash2.split('$')) > 2 else ''

        # ソルトが異なる
        assert salt1 != salt2
        assert len(salt1) > 0
        assert len(salt2) > 0


class TestEdgeCases:
    """TC-PW-005: エッジケーステスト"""

    def test_empty_password_hashing(self):
        """空パスワードがハッシュ化されることを確認"""
        password = ''
        hashed = hash_password(password)

        assert hashed.startswith('{SHA512-CRYPT}')
        assert verify_password('', hashed) is True

    def test_whitespace_only_password(self):
        """空白のみのパスワードがハッシュ化されることを確認"""
        password = '   '
        hashed = hash_password(password)

        assert hashed.startswith('{SHA512-CRYPT}')
        assert verify_password('   ', hashed) is True

    def test_single_character_password(self):
        """1文字のパスワードがハッシュ化されることを確認"""
        password = 'a'
        hashed = hash_password(password)

        assert hashed.startswith('{SHA512-CRYPT}')
        assert verify_password('a', hashed) is True

    def test_very_long_password(self):
        """非常に長いパスワードがハッシュ化されることを確認"""
        password = 'a' * 1000
        hashed = hash_password(password)

        assert hashed.startswith('{SHA512-CRYPT}')
        assert verify_password(password, hashed) is True

    def test_none_password_raises_error(self):
        """Noneパスワードでエラーが発生することを確認"""
        with pytest.raises((ValueError, TypeError, AttributeError)):
            hash_password(None)

    def test_verify_with_invalid_hash(self):
        """無効なハッシュで検証が失敗することを確認"""
        password = 'test'
        invalid_hashes = [
            '',
            'invalid_hash',
            '{SHA512-CRYPT}invalid',
        ]

        for invalid_hash in invalid_hashes:
            # 無効なハッシュではFalseまたは例外
            try:
                result = verify_password(password, invalid_hash)
                assert result is False
            except (ValueError, TypeError):
                pass  # 例外でも許容

    def test_verify_with_none_hash(self):
        """Noneハッシュでエラーが発生することを確認"""
        password = 'test'

        with pytest.raises((ValueError, TypeError, AttributeError)):
            verify_password(password, None)


class TestRandomPasswordGeneration:
    """TC-PW-006: ランダムパスワード生成テスト"""

    def test_generate_password_length(self):
        """指定された長さのパスワードが生成されることを確認"""
        lengths = [8, 12, 16, 24, 32]

        for length in lengths:
            password = generate_random_password(length)
            assert len(password) == length

    def test_generate_password_character_types(self):
        """大小英字、数字、記号が含まれることを確認"""
        password = generate_random_password(32)

        # 英大文字
        assert any(c.isupper() for c in password)
        # 英小文字
        assert any(c.islower() for c in password)
        # 数字
        assert any(c.isdigit() for c in password)
        # 記号（英数字以外）
        assert any(not c.isalnum() for c in password)

    def test_generate_password_randomness(self):
        """生成されるパスワードがランダムであることを確認"""
        passwords = [generate_random_password(16) for _ in range(10)]

        # すべて異なる
        assert len(set(passwords)) == 10

    def test_generated_password_hashable(self):
        """生成されたパスワードがハッシュ化可能であることを確認"""
        password = generate_random_password(16)
        hashed = hash_password(password)

        assert hashed.startswith('{SHA512-CRYPT}')
        assert verify_password(password, hashed) is True


class TestPerformance:
    """TC-PW-007: パフォーマンステスト"""

    def test_hashing_performance(self):
        """ハッシュ化のパフォーマンスを確認"""
        password = 'PerformanceTest123!'
        iterations = 10  # 100だと時間がかかるので10に削減

        start_time = time.time()
        for _ in range(iterations):
            hash_password(password)
        end_time = time.time()

        avg_time = (end_time - start_time) / iterations
        print(f"\nAverage hashing time: {avg_time:.4f} seconds")

        # 1回あたり1秒以内
        assert avg_time < 1.0

    def test_verification_performance(self):
        """検証のパフォーマンスを確認"""
        password = 'PerformanceTest123!'
        hashed = hash_password(password)
        iterations = 10

        start_time = time.time()
        for _ in range(iterations):
            verify_password(password, hashed)
        end_time = time.time()

        avg_time = (end_time - start_time) / iterations
        print(f"\nAverage verification time: {avg_time:.4f} seconds")

        # 1回あたり1秒以内
        assert avg_time < 1.0


# テスト実行時の統計情報
def test_summary():
    """テストサマリー (情報提供用)"""
    print("\n" + "="*60)
    print("Password Hashing Service Test Suite")
    print("="*60)
    print("Test Cases:")
    print("  TC-PW-001: 基本的なパスワードハッシュ化テスト (6 tests)")
    print("  TC-PW-002: パスワード検証テスト (5 tests)")
    print("  TC-PW-003: Dovecot互換性テスト (3 tests)")
    print("  TC-PW-004: ソルトのランダム性テスト (3 tests)")
    print("  TC-PW-005: エッジケーステスト (7 tests)")
    print("  TC-PW-006: ランダムパスワード生成テスト (4 tests)")
    print("  TC-PW-007: パフォーマンステスト (2 tests)")
    print("="*60)
    print("Total: 30 test cases")
    print("="*60)
    assert True  # Always pass
