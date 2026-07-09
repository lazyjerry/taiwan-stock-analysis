"""fetch_price_history.py 純函式測試（Data-Driven，無網路）。

涵蓋：parse_number（價量字串）、to_iso_date（民國轉西元）、validate_stock_id（含 ValueError）、
      normalize_records（去重/排序/欄位過濾）、summarize_history（區間位置/百分位）、
      iter_recent_months（依 today 往回推月；用 frozen_today 凍結時間）。
案例資料：tests/data/fetch_price_history/*.yaml。
"""
import pytest

import fetch_price_history as m
from conftest import assert_close, case_id, load_cases


@pytest.mark.parametrize("case", load_cases("fetch_price_history", "parse_number"), ids=case_id)
def test_parse_number(case):
    """parse_number：逗號、缺值符號、除權息 → None。"""
    got = m.parse_number(*case["args"])
    assert_close(got, case["expected"])


@pytest.mark.parametrize("case", load_cases("fetch_price_history", "to_iso_date"), ids=case_id)
def test_to_iso_date(case):
    """to_iso_date：民國年 +1911 並補零。"""
    got = m.to_iso_date(*case["args"])
    assert got == case["expected"]


@pytest.mark.parametrize("case", load_cases("fetch_price_history", "validate_stock_id"), ids=case_id)
def test_validate_stock_id(case):
    """validate_stock_id：4 位數字合法，否則 ValueError。"""
    if case.get("raises"):
        with pytest.raises(ValueError):
            m.validate_stock_id(*case["args"])
    else:
        assert m.validate_stock_id(*case["args"]) == case["expected"]


@pytest.mark.parametrize("case", load_cases("fetch_price_history", "normalize_records"), ids=case_id)
def test_normalize_records(case):
    """normalize_records：欄位<9 跳過、日期去重、升冪排序。"""
    got = m.normalize_records(*case["args"])
    assert_close(got, case["expected"])


@pytest.mark.parametrize("case", load_cases("fetch_price_history", "summarize_history"), ids=case_id)
def test_summarize_history(case):
    """summarize_history：區間位置與百分位；無收盤 → ValueError。"""
    if case.get("raises"):
        with pytest.raises(ValueError):
            m.summarize_history(*case["args"])
    else:
        assert_close(m.summarize_history(*case["args"]), case["expected"])


def test_iter_recent_months(frozen_today):
    """iter_recent_months：以凍結的 2026-07-05 往回推 3 個月 → 2026/05、06、07（升冪）。"""
    months = m.iter_recent_months(3)
    assert [req.query_date for req in months] == ["20260501", "20260601", "20260701"]
    assert months[-1].tpex_query_date == "2026/07/01"


def test_iter_recent_months_invalid():
    """iter_recent_months：months<=0 → ValueError。"""
    with pytest.raises(ValueError):
        m.iter_recent_months(0)
