"""fetch_goodinfo.py 純函式測試（Data-Driven，無網路）。

涵蓋：parse_amount（金額解析/億元換算）、build_ttm（TTM EPS 計算與退回）、
      sanity_check（合理性門檻警示）、average_balance、build_year_dict（轉置）、
      extract_eps、build_payload（表單組裝）、normalize_text。
案例資料：tests/data/fetch_goodinfo/*.yaml。
"""
import pytest

import fetch_goodinfo as m
from conftest import assert_close, assert_subset, case_id, load_cases


@pytest.mark.parametrize("case", load_cases("fetch_goodinfo", "parse_amount"), ids=case_id)
def test_parse_amount(case):
    """parse_amount：逗號/括號負值/缺值符號/億元換算 vs raw_unit。"""
    got = m.parse_amount(*case["args"], **case.get("kwargs", {}))
    assert_close(got, case["expected"])


@pytest.mark.parametrize("case", load_cases("fetch_goodinfo", "build_ttm"), ids=case_id)
def test_build_ttm(case):
    """build_ttm：正常相加 vs 缺值退回年報 EPS。"""
    got = m.build_ttm(*case["args"])
    assert_close(got, case["expected"])


@pytest.mark.parametrize("case", load_cases("fetch_goodinfo", "sanity_check"), ids=case_id)
def test_sanity_check(case):
    """sanity_check：各財務門檻觸發對應 error/warn。"""
    got = m.sanity_check(*case["args"])
    assert_close(got, case["expected"])


@pytest.mark.parametrize("case", load_cases("fetch_goodinfo", "average_balance"), ids=case_id)
def test_average_balance(case):
    """average_balance：缺值分支與平均計算。"""
    got = m.average_balance(*case["args"])
    assert_close(got, case["expected"])


@pytest.mark.parametrize("case", load_cases("fetch_goodinfo", "build_year_dict"), ids=case_id)
def test_build_year_dict(case):
    """build_year_dict：年→欄位 轉置為 欄位→年。"""
    got = m.build_year_dict(*case["args"])
    assert_close(got, case["expected"])


@pytest.mark.parametrize("case", load_cases("fetch_goodinfo", "extract_eps"), ids=case_id)
def test_extract_eps(case):
    """extract_eps：關鍵字比對取 EPS。"""
    got = m.extract_eps(*case["args"])
    assert_close(got, case["expected"])


@pytest.mark.parametrize("case", load_cases("fetch_goodinfo", "build_payload"), ids=case_id)
def test_build_payload(case):
    """build_payload：MOPS 表單鍵值（含預設/指定季別）。"""
    got = m.build_payload(*case["args"])
    assert_subset(got, case["expected"])


@pytest.mark.parametrize("case", load_cases("fetch_goodinfo", "normalize_text"), ids=case_id)
def test_normalize_text(case):
    """normalize_text：不斷行空白轉換與空白壓縮。"""
    got = m.normalize_text(*case["args"])
    assert got == case["expected"]
