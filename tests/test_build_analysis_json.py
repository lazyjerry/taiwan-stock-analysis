"""build_analysis_json.py 純函式測試（Data-Driven）。

涵蓋：safe_div（安全除法）、find_key（欄位兩階段比對）、get_value（取年度值）、
      build_metrics（逐年財務指標，抽點核算）。
案例資料：tests/data/build_analysis_json/*.yaml；fixture：tests/fixtures/raw_sample.json。
"""
import json

import pytest

import build_analysis_json as m
from conftest import FIXTURES_DIR, assert_close, case_id, load_cases


@pytest.mark.parametrize("case", load_cases("build_analysis_json", "safe_div"), ids=case_id)
def test_safe_div(case):
    """safe_div：驗證除零/缺值防呆與 scale 換算。"""
    got = m.safe_div(*case["args"], **case.get("kwargs", {}))
    assert_close(got, case["expected"])


@pytest.mark.parametrize("case", load_cases("build_analysis_json", "find_key"), ids=case_id)
def test_find_key(case):
    """find_key：完全相等優先於子字串包含。"""
    got = m.find_key(*case["args"])
    assert got == case["expected"]


@pytest.mark.parametrize("case", load_cases("build_analysis_json", "get_value"), ids=case_id)
def test_get_value(case):
    """get_value：找不到欄位或無該年度皆回 None。"""
    got = m.get_value(*case["args"])
    assert_close(got, case["expected"])


@pytest.mark.parametrize("case", load_cases("build_analysis_json", "build_metrics"), ids=case_id)
def test_build_metrics(case):
    """build_metrics：以合成 raw 報表抽點核算逐年指標（毛利率、ROE、FCF…）。"""
    raw = json.loads((FIXTURES_DIR / "raw_sample.json").read_text(encoding="utf-8"))
    _years, metrics = m.build_metrics(raw)
    assert_close(metrics[case["year"]][case["field"]], case["expected"])
