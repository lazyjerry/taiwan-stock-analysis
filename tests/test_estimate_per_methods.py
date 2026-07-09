"""estimate_per_methods.py 純函式測試（Data-Driven，無網路）。

涵蓋：percentile（分位數）、eps_cagr（複合成長率）、method_peg/roe/graham（三方法合理 PER/價）、
      applicability（星等與唯一建議）、resolve_base_eps（TTM 優先，退回年報）。
案例資料：tests/data/estimate_per_methods/*.yaml。method_* 回傳含長 note，用 assert_subset 只驗關注鍵。
"""
import pytest

import estimate_per_methods as m
from conftest import assert_close, assert_subset, case_id, load_cases


@pytest.mark.parametrize("case", load_cases("estimate_per_methods", "percentile"), ids=case_id)
def test_percentile(case):
    """percentile：空/單值/線性插值分位。"""
    assert_close(m.percentile(*case["args"]), case["expected"])


@pytest.mark.parametrize("case", load_cases("estimate_per_methods", "eps_cagr"), ids=case_id)
def test_eps_cagr(case):
    """eps_cagr：僅取正值、跨度計算 CAGR，<2 筆 → None。"""
    assert_close(m.eps_cagr(*case["args"]), case["expected"])


@pytest.mark.parametrize("case", load_cases("estimate_per_methods", "method_peg"), ids=case_id)
def test_method_peg(case):
    """method_peg：合理 PER=成長率%、±20% 帶、PEG 診斷。"""
    assert_subset(m.method_peg(*case["args"]), case["expected"])


@pytest.mark.parametrize("case", load_cases("estimate_per_methods", "method_roe"), ids=case_id)
def test_method_roe(case):
    """method_roe：Gordon Growth 三情境；利差非正 → 無解。"""
    assert_subset(m.method_roe(*case["args"]), case["expected"])


@pytest.mark.parametrize("case", load_cases("estimate_per_methods", "method_graham"), ids=case_id)
def test_method_graham(case):
    """method_graham：8.5+2g、利率修正、g±3 三情境。"""
    assert_subset(m.method_graham(*case["args"]), case["expected"])


@pytest.mark.parametrize("case", load_cases("estimate_per_methods", "applicability"), ids=case_id)
def test_applicability(case):
    """applicability：星等與唯一 recommended 選取。"""
    assert_subset(m.applicability(*case["args"]), case["expected"])


@pytest.mark.parametrize("case", load_cases("estimate_per_methods", "resolve_base_eps"), ids=case_id)
def test_resolve_base_eps(case):
    """resolve_base_eps：TTM 優先、退回最新年報、皆無則 ValueError。"""
    if case.get("raises"):
        with pytest.raises(ValueError):
            m.resolve_base_eps(*case["args"])
    else:
        assert_close(list(m.resolve_base_eps(*case["args"])), case["expected"])
