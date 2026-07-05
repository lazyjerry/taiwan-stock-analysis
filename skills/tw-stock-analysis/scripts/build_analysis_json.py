#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build structured *_analysis.json (metrics_by_year) from raw financial JSON."
    )
    parser.add_argument("--raw-json", type=Path, required=True, help="Path to <stock_id>_goodinfo_raw_data.json")
    parser.add_argument("--output", type=Path, help="Output analysis JSON path（預設 <名稱>_<代碼>_analysis.json）")
    return parser.parse_args()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def safe_div(numerator: float | None, denominator: float | None, scale: float = 100.0) -> float | None:
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator * scale


def find_key(section: dict, patterns: list[str]) -> str | None:
    for pattern in patterns:
        for key in section.keys():
            if pattern == key:
                return key
    for pattern in patterns:
        for key in section.keys():
            if pattern in key:
                return key
    return None


def get_value(section: dict, patterns: list[str], year: str) -> float | None:
    key = find_key(section, patterns)
    if key is None:
        return None
    return section[key].get(year)


def build_metrics(raw: dict) -> tuple[list[str], dict[str, dict]]:
    years = sorted(raw["years"])
    income = raw["income_statement"]
    balance = raw["balance_sheet"]
    cash_flow = raw["cash_flow"]
    metrics: dict[str, dict] = {}

    for index, year in enumerate(years):
        previous_year = years[index - 1] if index > 0 else None
        revenue = get_value(income, ["營業收入合計", "營業收入"], year)
        gross_profit = get_value(income, ["營業毛利（毛損）淨額", "營業毛利（毛損）"], year)
        sell_exp = get_value(income, ["推銷費用"], year)
        admin_exp = get_value(income, ["管理費用"], year)
        rd_exp = get_value(income, ["研究發展費用"], year)
        op_income = get_value(income, ["營業利益（損失）"], year)
        net_income = get_value(income, ["本期淨利（淨損）", "繼續營業單位本期淨利（淨損）", "稅後淨利"], year)
        eps = get_value(income, ["基本每股盈餘", "每股盈餘"], year)
        cash = get_value(balance, ["現金及約當現金"], year)
        inventory = get_value(balance, ["存貨"], year)
        current_assets = get_value(balance, ["流動資產合計"], year)
        current_liabilities = get_value(balance, ["流動負債合計"], year)
        total_liabilities = get_value(balance, ["負債總額", "負債總計"], year)
        equity = get_value(balance, ["權益總額", "股東權益總額"], year)
        total_assets = get_value(balance, ["資產總額", "資產總計", "負債及權益總計"], year)
        operating_cf = get_value(cash_flow, ["營業活動之淨現金流入（流出）"], year)
        investing_cf = get_value(cash_flow, ["投資活動之淨現金流入（流出）"], year)
        financing_cf = get_value(cash_flow, ["籌資活動之淨現金流入（流出）"], year)
        dividends = get_value(cash_flow, ["發放現金股利"], year)
        capex = get_value(cash_flow, ["取得不動產、廠房及設備"], year)
        previous_assets = get_value(balance, ["資產總額", "資產總計", "負債及權益總計"], previous_year) if previous_year else None
        previous_equity = get_value(balance, ["權益總額", "股東權益總額"], previous_year) if previous_year else None
        average_assets = total_assets if previous_assets is None or total_assets is None else (total_assets + previous_assets) / 2
        average_equity = equity if previous_equity is None or equity is None else (equity + previous_equity) / 2
        total_opex = None if None in (sell_exp, admin_exp, rd_exp) else sell_exp + admin_exp + rd_exp
        fcf = None if operating_cf is None or capex is None else operating_cf + capex

        metrics[year] = {
            "revenue": revenue,
            "gross_profit": gross_profit,
            "sell_exp": sell_exp,
            "admin_exp": admin_exp,
            "rd_exp": rd_exp,
            "total_opex": total_opex,
            "gross_margin": safe_div(gross_profit, revenue),
            "sell_ratio": safe_div(sell_exp, revenue),
            "admin_ratio": safe_div(admin_exp, revenue),
            "rd_ratio": safe_div(rd_exp, revenue),
            "total_opex_ratio": safe_div(total_opex, revenue),
            "op_income": op_income,
            "op_margin": safe_div(op_income, revenue),
            "net_income": net_income,
            "net_margin": safe_div(net_income, revenue),
            "eps": eps,
            "cash": cash,
            "inventory": inventory,
            "current_assets": current_assets,
            "current_liabilities": current_liabilities,
            "current_ratio": safe_div(current_assets, current_liabilities),
            "total_liabilities": total_liabilities,
            "equity": equity,
            "total_assets": total_assets,
            "debt_ratio": safe_div(total_liabilities, total_assets),
            "roe": safe_div(net_income, average_equity),
            "roa": safe_div(net_income, average_assets),
            "operating_cf": operating_cf,
            "investing_cf": investing_cf,
            "financing_cf": financing_cf,
            "dividends": dividends,
            "capex": capex,
            "fcf": fcf,
            "cfo_to_net": safe_div(operating_cf, net_income, scale=1.0),
        }
    return years, metrics


def main() -> int:
    args = parse_args()
    raw = load_json(args.raw_json)
    company_name = raw.get("company_name") or raw.get("metadata", {}).get("company_name") or raw["stock_id"]
    years, metrics = build_metrics(raw)

    analysis = {
        "stock_id": raw["stock_id"],
        "company_name": company_name,
        "market": raw.get("market"),
        "years": years,
        "metrics_by_year": metrics,
        "latest_quarter": raw.get("latest_quarter"),
        "ttm": raw.get("ttm"),
        "metadata": raw.get("metadata"),
        "verification": raw.get("verification"),
    }

    output = args.output or Path(f"{company_name}_{raw['stock_id']}_analysis.json")
    output.write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
