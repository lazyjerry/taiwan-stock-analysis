#!/bin/bash
# 可重複執行的測試入口：首次自動建立 .venv 並安裝依賴，之後重用。
# 用法：
#   bash tests/run_tests.sh            # 跑全部測試
#   bash tests/run_tests.sh -k etf     # 傳給 pytest 的額外參數（篩選、單檔等）
# 相容 macOS 預設 Bash 3.2。
set -euo pipefail

TESTS_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="${TESTS_DIR}/.venv"
PYTHON_BIN="${PYTHON_BIN:-python3}"

if [ ! -d "${VENV_DIR}" ]; then
    echo "==> 建立虛擬環境 ${VENV_DIR}"
    "${PYTHON_BIN}" -m venv "${VENV_DIR}"
    "${VENV_DIR}/bin/pip" install --quiet --upgrade pip
    echo "==> 安裝測試依賴"
    "${VENV_DIR}/bin/pip" install --quiet -r "${TESTS_DIR}/requirements-test.txt"
fi

cd "${TESTS_DIR}"
exec "${VENV_DIR}/bin/python" -m pytest "$@"
