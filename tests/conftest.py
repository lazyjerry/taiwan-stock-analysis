"""測試共用設定：把各 skill 的 scripts/ 目錄注入 sys.path，並提供 DDT 案例載入器與比對工具。

- 產品腳本散落在 per-skill 的 scripts/ 目錄、無 __init__.py，這裡以 sys.path 注入讓
  `import build_analysis_json` 等可直接運作。
- load_cases()：讀 tests/data/<module>/<func>.yaml 的案例陣列，供 @pytest.mark.parametrize 使用。
- assert_close()：遞迴比對數值（浮點用 pytest.approx），供純計算函式驗證。
"""
from __future__ import annotations

import datetime
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
TESTS_DIR = Path(__file__).resolve().parent
DATA_DIR = TESTS_DIR / "data"
FIXTURES_DIR = TESTS_DIR / "fixtures"

# 產品腳本目錄（5 支 Python 分佈於兩個 skill）
SCRIPT_DIRS = [
    ROOT / "skills" / "tw-stock-analysis" / "scripts",
    ROOT / "skills" / "tw-stock-valuation-bands" / "scripts",
]
for _dir in SCRIPT_DIRS:
    path_str = str(_dir)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


def load_cases(module: str, func: str) -> list[dict]:
    """讀取 tests/data/<module>/<func>.yaml 的案例陣列。"""
    path = DATA_DIR / module / f"{func}.yaml"
    cases = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(cases, list), f"{path} 應為案例陣列"
    return cases


def case_id(case: dict) -> str:
    return str(case.get("id", "case"))


def assert_close(got, expected, rel: float = 1e-6, abs_: float = 1e-9) -> None:
    """遞迴比對：浮點用 approx，dict/list 逐項比對，其餘用 ==。"""
    if isinstance(expected, bool):
        assert got == expected
    elif isinstance(expected, float):
        assert got == pytest.approx(expected, rel=rel, abs=abs_)
    elif isinstance(expected, dict):
        assert isinstance(got, dict), f"型別不符：{type(got)} != dict"
        assert set(got.keys()) == set(expected.keys()), f"鍵不符：{set(got)} != {set(expected)}"
        for key in expected:
            assert_close(got[key], expected[key], rel, abs_)
    elif isinstance(expected, list):
        assert isinstance(got, list), f"型別不符：{type(got)} != list"
        assert len(got) == len(expected), f"長度不符：{len(got)} != {len(expected)}"
        for got_item, expected_item in zip(got, expected):
            assert_close(got_item, expected_item, rel, abs_)
    else:
        assert got == expected


def assert_subset(got, expected, rel: float = 1e-6, abs_: float = 1e-9) -> None:
    """只比對 expected 出現的鍵（遞迴）；用於 method_* 這類回傳含長 note 字串的大 dict。"""
    if isinstance(expected, bool):
        assert got == expected
    elif isinstance(expected, float):
        assert got == pytest.approx(expected, rel=rel, abs=abs_)
    elif isinstance(expected, dict):
        assert isinstance(got, dict), f"型別不符：{type(got)} != dict"
        for key in expected:
            assert key in got, f"缺少鍵：{key}"
            assert_subset(got[key], expected[key], rel, abs_)
    elif isinstance(expected, list):
        assert isinstance(got, list), f"型別不符：{type(got)} != list"
        assert len(got) == len(expected), f"長度不符：{len(got)} != {len(expected)}"
        for got_item, expected_item in zip(got, expected):
            assert_subset(got_item, expected_item, rel, abs_)
    else:
        assert got == expected


# 凍結「今天」為固定日期，讓依賴 date.today() 的函式（iter_recent_months、render_markdown）可確定性比對
FIXED_TODAY = datetime.date(2026, 7, 5)


class _FixedDate(datetime.date):
    @classmethod
    def today(cls) -> datetime.date:  # type: ignore[override]
        return datetime.date(FIXED_TODAY.year, FIXED_TODAY.month, FIXED_TODAY.day)


@pytest.fixture
def frozen_today(monkeypatch: pytest.MonkeyPatch) -> datetime.date:
    """把 fetch_price_history 與 build_valuation_report 用到的 date.today() 固定為 FIXED_TODAY。"""
    import build_valuation_report
    import fetch_price_history

    monkeypatch.setattr(fetch_price_history, "date", _FixedDate)
    monkeypatch.setattr(build_valuation_report.datetime, "date", _FixedDate)
    return FIXED_TODAY
