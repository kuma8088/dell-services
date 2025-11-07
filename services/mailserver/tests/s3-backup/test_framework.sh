#!/bin/bash
# test_framework.sh - Phase 11-B S3 Backup Test Framework

# カラー定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# テスト統計
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_SKIPPED=0

# 現在のテストスイート名
CURRENT_SUITE=""

# テストスイート開始
suite() {
    CURRENT_SUITE="$1"
    echo -e "\n${YELLOW}=== Test Suite: ${CURRENT_SUITE} ===${NC}"
}

# テスト実行
test() {
    local test_name="$1"
    local test_func="$2"

    TESTS_RUN=$((TESTS_RUN + 1))

    # テスト実行
    if $test_func; then
        TESTS_PASSED=$((TESTS_PASSED + 1))
        echo -e "${GREEN}✓${NC} ${test_name}"
        return 0
    else
        TESTS_FAILED=$((TESTS_FAILED + 1))
        echo -e "${RED}✗${NC} ${test_name}"
        return 1
    fi
}

# アサーション関数
assert_equals() {
    local expected="$1"
    local actual="$2"
    local message="${3:-Assertion failed}"

    if [ "$expected" = "$actual" ]; then
        return 0
    else
        echo -e "${RED}  Expected: ${expected}${NC}"
        echo -e "${RED}  Actual:   ${actual}${NC}"
        echo -e "${RED}  ${message}${NC}"
        return 1
    fi
}

assert_true() {
    local condition="$1"
    local message="${2:-Assertion failed}"

    if [ "$condition" = "true" ]; then
        return 0
    else
        echo -e "${RED}  ${message}${NC}"
        return 1
    fi
}

assert_false() {
    local condition="$1"
    local message="${2:-Assertion failed}"

    if [ "$condition" = "false" ]; then
        return 0
    else
        echo -e "${RED}  ${message}${NC}"
        return 1
    fi
}

assert_file_exists() {
    local file="$1"
    local message="${2:-File does not exist: $file}"

    if [ -f "$file" ]; then
        return 0
    else
        echo -e "${RED}  ${message}${NC}"
        return 1
    fi
}

assert_dir_exists() {
    local dir="$1"
    local message="${2:-Directory does not exist: $dir}"

    if [ -d "$dir" ]; then
        return 0
    else
        echo -e "${RED}  ${message}${NC}"
        return 1
    fi
}

assert_command_success() {
    local command="$1"
    local message="${2:-Command failed: $command}"

    if eval "$command" &> /dev/null; then
        return 0
    else
        echo -e "${RED}  ${message}${NC}"
        return 1
    fi
}

assert_command_fails() {
    local command="$1"
    local message="${2:-Command should fail: $command}"

    if ! eval "$command" &> /dev/null; then
        return 0
    else
        echo -e "${RED}  ${message}${NC}"
        return 1
    fi
}

assert_contains() {
    local haystack="$1"
    local needle="$2"
    local message="${3:-String does not contain: $needle}"

    if echo "$haystack" | grep -q "$needle"; then
        return 0
    else
        echo -e "${RED}  ${message}${NC}"
        return 1
    fi
}

assert_not_contains() {
    local haystack="$1"
    local needle="$2"
    local message="${3:-String should not contain: $needle}"

    if ! echo "$haystack" | grep -q "$needle"; then
        return 0
    else
        echo -e "${RED}  ${message}${NC}"
        return 1
    fi
}

# テスト環境セットアップ
setup_test_env() {
    export TEST_ROOT="/tmp/s3-backup-test-$$"
    export TEST_SCRIPTS_DIR="${TEST_ROOT}/scripts"
    export TEST_DATA_DIR="${TEST_ROOT}/data"
    export TEST_LOG_DIR="${TEST_ROOT}/logs"
    export TEST_CONFIG_DIR="${TEST_ROOT}/config"

    mkdir -p "$TEST_SCRIPTS_DIR"
    mkdir -p "$TEST_DATA_DIR"
    mkdir -p "$TEST_LOG_DIR"
    mkdir -p "$TEST_CONFIG_DIR"

    # モックAWS CLI
    export PATH="${TEST_SCRIPTS_DIR}:${PATH}"

    # テスト用設定ファイル
    cat > "${TEST_CONFIG_DIR}/mailserver-backup.conf" <<EOF
ADMIN_EMAIL="test@example.com"
AWS_PROFILE=test-profile
AWS_DEFAULT_REGION=ap-northeast-1
EOF
}

# テスト環境クリーンアップ
teardown_test_env() {
    if [ -n "$TEST_ROOT" ] && [ -d "$TEST_ROOT" ]; then
        rm -rf "$TEST_ROOT"
    fi
}

# モックAWS CLI作成
create_mock_aws() {
    cat > "${TEST_SCRIPTS_DIR}/aws" <<'EOF'
#!/bin/bash
# Mock AWS CLI

COMMAND="$1"
shift

case "$COMMAND" in
    s3)
        SUBCOMMAND="$1"
        shift
        case "$SUBCOMMAND" in
            ls)
                # S3バケット一覧
                echo "2025-11-01/ 2025-11-02/ 2025-11-07/"
                ;;
            sync)
                # S3同期
                echo "upload: test.txt to s3://bucket/test.txt"
                return 0
                ;;
            cp)
                # S3コピー
                echo "copy: test.txt to s3://bucket/test.txt"
                return 0
                ;;
            *)
                echo "Unknown s3 subcommand: $SUBCOMMAND" >&2
                return 1
                ;;
        esac
        ;;
    sts)
        SUBCOMMAND="$1"
        case "$SUBCOMMAND" in
            get-caller-identity)
                echo '{"Account": "123456789012"}'
                ;;
        esac
        ;;
    *)
        echo "Unknown command: $COMMAND" >&2
        return 1
        ;;
esac
EOF
    chmod +x "${TEST_SCRIPTS_DIR}/aws"
}

# テストサマリー表示
print_summary() {
    echo -e "\n${YELLOW}=== Test Summary ===${NC}"
    echo -e "Total:   ${TESTS_RUN}"
    echo -e "${GREEN}Passed:  ${TESTS_PASSED}${NC}"
    echo -e "${RED}Failed:  ${TESTS_FAILED}${NC}"
    echo -e "Skipped: ${TESTS_SKIPPED}"

    if [ $TESTS_FAILED -eq 0 ]; then
        echo -e "\n${GREEN}All tests passed!${NC}"
        return 0
    else
        echo -e "\n${RED}Some tests failed!${NC}"
        return 1
    fi
}

# テストスキップ
skip() {
    local reason="$1"
    TESTS_SKIPPED=$((TESTS_SKIPPED + 1))
    echo -e "${YELLOW}⊘${NC} ${reason}"
    return 0
}
