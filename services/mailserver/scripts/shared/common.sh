#!/bin/bash
# shellcheck shell=bash
#
# Common helper utilities shared by operational scripts.

if [[ -n "${MAILSERVER_COMMON_SOURCED:-}" ]]; then
  return 0
fi
export MAILSERVER_COMMON_SOURCED=1

MAILSERVER_SHARED_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAILSERVER_SCRIPTS_DIR="$(cd "${MAILSERVER_SHARED_DIR}/.." && pwd)"
MAILSERVER_PROJECT_ROOT="$(cd "${MAILSERVER_SCRIPTS_DIR}/.." && pwd)"

readonly MAILSERVER_COLOR_RED='\033[0;31m'
readonly MAILSERVER_COLOR_GREEN='\033[0;32m'
readonly MAILSERVER_COLOR_YELLOW='\033[1;33m'
readonly MAILSERVER_COLOR_BLUE='\033[0;34m'
readonly MAILSERVER_COLOR_RESET='\033[0m'

mailserver_log_info() {
  echo -e "${MAILSERVER_COLOR_GREEN}[INFO]${MAILSERVER_COLOR_RESET} $*"
}

mailserver_log_warn() {
  echo -e "${MAILSERVER_COLOR_YELLOW}[WARN]${MAILSERVER_COLOR_RESET} $*"
}

mailserver_log_error() {
  echo -e "${MAILSERVER_COLOR_RED}[ERROR]${MAILSERVER_COLOR_RESET} $*"
}

mailserver_log_section() {
  echo -e "${MAILSERVER_COLOR_BLUE}=== $* ===${MAILSERVER_COLOR_RESET}"
}
