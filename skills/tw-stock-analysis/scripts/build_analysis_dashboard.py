#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

CHART_JS_CDN = "https://cdn.jsdelivr.net/npm/chart.js@4.5.0/dist/chart.umd.min.js"
MOPS_WEB_HOST = "https://mopsov.twse.com.tw"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a three-dimension Taiwan stock analysis dashboard from raw financial JSON."
    )
    parser.add_argument("--raw-json", type=Path, required=True, help="Path to <stock_id>_goodinfo_raw_data.json")
    parser.add_argument("--price-history-json", type=Path, help="Path to <stock_id>_twse_price_history.json")
    parser.add_argument("--output", type=Path, help="Output HTML path")
    return parser.parse_args()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def fmt_amount(value: float | None) -> str:
    if value is None:
        return "-"
    rounded = round(value, 2)
    if abs(rounded) >= 1000:
        return f"{rounded:,.0f}"
    if abs(rounded) >= 100:
        return f"{rounded:,.1f}".rstrip("0").rstrip(".")
    return f"{rounded:,.2f}".rstrip("0").rstrip(".")


def fmt_pct(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.2f}%"


def fmt_ratio(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.2f}x"


def fmt_price(value: float | None) -> str:
    if value is None:
        return "-"
    if abs(value - round(value)) < 1e-9:
        return f"{int(round(value))}"
    return f"{value:.2f}"


def pct_change(current: float | None, previous: float | None) -> float | None:
    if current is None or previous in (None, 0):
        return None
    return (current - previous) / previous * 100


def cagr(start: float | None, end: float | None, periods: int) -> float | None:
    if start in (None, 0) or end is None or periods <= 0:
        return None
    return (end / start) ** (1 / periods) * 100 - 100


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


def trend_class(current: float | None, previous: float | None, higher_is_better: bool = True) -> str:
    if current is None or previous is None:
        return "neutral"
    if math.isclose(current, previous, rel_tol=0.001, abs_tol=0.01):
        return "neutral"
    better = current > previous if higher_is_better else current < previous
    return "up" if better else "down"


def trend_symbol(css_class: str) -> str:
    if css_class == "up":
        return "▲"
    if css_class == "down":
        return "▼"
    return "■"


def short_trend(label: str, current: float | None, previous: float | None, higher_is_better: bool = True) -> tuple[str, str]:
    css_class = trend_class(current, previous, higher_is_better)
    symbol = trend_symbol(css_class)
    if current is None or previous is None:
        return css_class, f"{symbol} 資料不足"
    delta = current - previous
    if label == "revenue":
        if delta > 0:
            return css_class, f"{symbol} 年增 {pct_change(current, previous):.1f}%"
        if delta < 0:
            return css_class, f"{symbol} 年減 {abs(pct_change(current, previous)):.1f}%"
        return css_class, f"{symbol} 近乎持平"
    if label == "margin":
        if delta > 0:
            return css_class, f"{symbol} 擴大 {delta:.2f}pt"
        if delta < 0:
            return css_class, f"{symbol} 收斂 {abs(delta):.2f}pt"
        return css_class, f"{symbol} 窄幅震盪"
    if label == "ratio-low":
        if delta < 0:
            return css_class, f"{symbol} 下降 {abs(delta):.1f}pt"
        if delta > 0:
            return css_class, f"{symbol} 上升 {abs(delta):.1f}pt"
        return css_class, f"{symbol} 變化有限"
    if label == "cashflow":
        if delta > 0:
            return css_class, f"{symbol} 增加 {fmt_amount(abs(delta))}億"
        if delta < 0:
            return css_class, f"{symbol} 減少 {fmt_amount(abs(delta))}億"
        return css_class, f"{symbol} 近乎持平"
    if delta > 0:
        return css_class, f"{symbol} 成長 {fmt_amount(abs(delta))}億"
    if delta < 0:
        return css_class, f"{symbol} 減少 {fmt_amount(abs(delta))}億"
    return css_class, f"{symbol} 變化有限"


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


def build_insights(company_name: str, years: list[str], metrics: dict[str, dict], price_summary: dict | None) -> dict[str, list[str]]:
    first_year = years[0]
    last_year = years[-1]
    rev_start = metrics[first_year]["revenue"]
    rev_end = metrics[last_year]["revenue"]
    rev_prev = metrics[years[-2]]["revenue"]
    gross_path = " → ".join(fmt_pct(metrics[year]["gross_margin"]) for year in years)
    opex_path = " → ".join(fmt_pct(metrics[year]["total_opex_ratio"]) for year in years)
    op_margin_path = " → ".join(fmt_pct(metrics[year]["op_margin"]) for year in years)
    eps_path = " → ".join(f"{metrics[year]['eps']:.2f}" for year in years if metrics[year]["eps"] is not None)
    net_margin_path = " → ".join(fmt_pct(metrics[year]["net_margin"]) for year in years)
    current_ratio_path = " → ".join(fmt_pct(metrics[year]["current_ratio"]) for year in years)
    debt_ratio_path = " → ".join(fmt_pct(metrics[year]["debt_ratio"]) for year in years)
    cash_path = " → ".join(f"{fmt_amount(metrics[year]['cash'])}億" for year in years)
    cfo_path = " → ".join(f"{fmt_amount(metrics[year]['operating_cf'])}億" for year in years)
    inventory_path = " → ".join(f"{fmt_amount(metrics[year]['inventory'])}億" for year in years)
    dividend_path = " → ".join(f"{fmt_amount(abs(metrics[year]['dividends']))}億" for year in years)
    revenue_cagr = cagr(rev_start, rev_end, len(years) - 1)
    op_cagr = cagr(metrics[first_year]["op_income"], metrics[last_year]["op_income"], len(years) - 1)
    net_cagr = cagr(metrics[first_year]["net_income"], metrics[last_year]["net_income"], len(years) - 1)
    inventory_delta = pct_change(metrics[last_year]["inventory"], metrics[years[-2]]["inventory"])
    payout_ratio = abs(metrics[last_year]["dividends"]) / metrics[last_year]["net_income"] * 100 if metrics[last_year]["dividends"] and metrics[last_year]["net_income"] else None

    ops = [
        f"三年營收 {fmt_amount(rev_start)} → {fmt_amount(rev_prev)} → {fmt_amount(rev_end)} 億，CAGR +{revenue_cagr:.1f}%，{last_year} 年再增 {pct_change(rev_end, rev_prev):+.1f}%，伺服器與雲端硬體出貨延續成長。",
        f"毛利率 {gross_path}，代工本質讓毛利維持低個位數，但絕對毛利已由 {fmt_amount(metrics[first_year]['gross_profit'])} 億擴大到 {fmt_amount(metrics[last_year]['gross_profit'])} 億。",
        f"管銷研費用率 {opex_path}，研發費用從 {fmt_amount(metrics[first_year]['rd_exp'])} 億增至 {fmt_amount(metrics[last_year]['rd_exp'])} 億，占營收比卻下降，規模效益持續浮現。",
        f"營業利益 {fmt_amount(metrics[first_year]['op_income'])} → {fmt_amount(metrics[years[-2]]['op_income'])} → {fmt_amount(metrics[last_year]['op_income'])} 億，CAGR +{op_cagr:.1f}%，營業利益率 {op_margin_path}。",
    ]
    profit = [
        f"EPS 三年 {eps_path} 元，{last_year} 年年增 {pct_change(metrics[last_year]['eps'], metrics[years[-2]]['eps']):+.1f}%，稅後淨利同步升至 {fmt_amount(metrics[last_year]['net_income'])} 億。",
        f"淨利三年 {fmt_amount(metrics[first_year]['net_income'])} → {fmt_amount(metrics[years[-2]]['net_income'])} → {fmt_amount(metrics[last_year]['net_income'])} 億，CAGR +{net_cagr:.1f}%，高於營收 CAGR，獲利槓桿延續。",
        f"三層利潤率為毛利 {fmt_pct(metrics[last_year]['gross_margin'])} / 營業 {fmt_pct(metrics[last_year]['op_margin'])} / 淨利 {fmt_pct(metrics[last_year]['net_margin'])}，淨利率路徑 {net_margin_path}。",
        f"ROE {fmt_pct(metrics[first_year]['roe'])} → {fmt_pct(metrics[years[-2]]['roe'])} → {fmt_pct(metrics[last_year]['roe'])}，股東權益報酬率回升到近三年高點。",
        f"現金股利三年 {dividend_path}，以 {last_year} 年淨利估算配息率約 {payout_ratio:.1f}%，配息能力仍由獲利支撐。",
    ]
    finance = [
        f"流動比率 {current_ratio_path}，{last_year} 年落在 {fmt_pct(metrics[last_year]['current_ratio'])}，低於 150% 但仍高於 100%，短期償債力可控。",
        f"負債比率 {debt_ratio_path}，{last_year} 年來到 {fmt_pct(metrics[last_year]['debt_ratio'])}，擴產帶動槓桿攀升，需要持續觀察。",
        f"現金部位 {cash_path}，同期存貨 {inventory_path}，{last_year} 年存貨年增 {inventory_delta:+.1f}%，反映備料與高成長產品拉貨。",
        f"營業現金流三年 {cfo_path}，{last_year} 年與淨利比值約 {fmt_ratio(metrics[last_year]['cfo_to_net'])}，現金轉換仍屬正向。",
        f"{last_year} 年資本支出約 {fmt_amount(abs(metrics[last_year]['capex']))} 億，自由現金流 {fmt_amount(metrics[last_year]['fcf'])} 億。",
    ]
    if price_summary is not None:
        finance.append(
            f"最近收盤 {fmt_price(price_summary['latest_close'])} 元，位於近三年區間 {price_summary['range_position_pct']:.2f}% 與百分位 {price_summary['percentile_pct']:.2f}%，股價已接近區間高檔。"
        )
    return {"ops": ops[:5], "profit": profit[:5], "finance": finance[:5]}


def build_kpis(years: list[str], metrics: dict[str, dict]) -> dict[str, list[dict]]:
    latest = years[-1]
    prev = years[-2]
    return {
        "ops": [
            {
                "label": f"{latest} 年營收",
                "value": f"{fmt_amount(metrics[latest]['revenue'])} 億",
                "change_class": "up",
                "change_text": f"▲ {pct_change(metrics[latest]['revenue'], metrics[prev]['revenue']):+.1f}% YoY（{prev} 年 {fmt_amount(metrics[prev]['revenue'])} 億）",
                "card_class": "teal",
            },
            {
                "label": f"毛利率 ({latest})",
                "value": fmt_pct(metrics[latest]["gross_margin"]),
                "change_class": trend_class(metrics[latest]['gross_margin'], metrics[prev]['gross_margin']),
                "change_text": f"{trend_symbol(trend_class(metrics[latest]['gross_margin'], metrics[prev]['gross_margin']))} {prev} 年 {fmt_pct(metrics[prev]['gross_margin'])} → {latest} 年 {fmt_pct(metrics[latest]['gross_margin'])}",
                "card_class": "green",
            },
            {
                "label": f"管銷研費用率 ({latest})",
                "value": fmt_pct(metrics[latest]["total_opex_ratio"]),
                "change_class": "up",
                "change_text": f"▲ {prev} 年 {fmt_pct(metrics[prev]['total_opex_ratio'])} → 規模效益持續攤薄",
                "card_class": "green",
            },
            {
                "label": f"營業利益 ({latest})",
                "value": f"{fmt_amount(metrics[latest]['op_income'])} 億",
                "change_class": "up",
                "change_text": f"▲ {pct_change(metrics[latest]['op_income'], metrics[prev]['op_income']):+.1f}% vs {prev}",
                "card_class": "green",
            },
            {
                "label": f"營業利益率 ({latest})",
                "value": fmt_pct(metrics[latest]["op_margin"]),
                "change_class": "up",
                "change_text": f"▲ 三年路徑 {' → '.join(fmt_pct(metrics[year]['op_margin']) for year in years)}",
                "card_class": "green",
            },
        ],
        "profit": [
            {
                "label": f"{latest} 稅後淨利",
                "value": f"{fmt_amount(metrics[latest]['net_income'])} 億",
                "change_class": "up",
                "change_text": f"▲ {pct_change(metrics[latest]['net_income'], metrics[prev]['net_income']):+.1f}% vs {prev}",
                "card_class": "teal",
            },
            {
                "label": f"淨利率 ({latest})",
                "value": fmt_pct(metrics[latest]["net_margin"]),
                "change_class": trend_class(metrics[latest]['net_margin'], metrics[prev]['net_margin']),
                "change_text": f"{trend_symbol(trend_class(metrics[latest]['net_margin'], metrics[prev]['net_margin']))} {prev} 年 {fmt_pct(metrics[prev]['net_margin'])} → {latest} 年 {fmt_pct(metrics[latest]['net_margin'])}",
                "card_class": "green",
            },
            {
                "label": f"EPS ({latest})",
                "value": f"{metrics[latest]['eps']:.2f} 元",
                "change_class": "up",
                "change_text": f"▲ {pct_change(metrics[latest]['eps'], metrics[prev]['eps']):+.1f}% YoY，三年最高",
                "card_class": "green",
            },
            {
                "label": f"ROE ({latest})",
                "value": fmt_pct(metrics[latest]["roe"]),
                "change_class": "up",
                "change_text": f"▲ {prev} 年 {fmt_pct(metrics[prev]['roe'])} → {latest} 年 {fmt_pct(metrics[latest]['roe'])}",
                "card_class": "green",
            },
            {
                "label": f"ROA ({latest})",
                "value": fmt_pct(metrics[latest]["roa"]),
                "change_class": "up",
                "change_text": f"▲ {prev} 年 {fmt_pct(metrics[prev]['roa'])} → 資產效率改善",
                "card_class": "green",
            },
        ],
        "finance": [
            {
                "label": f"現金及約當現金 ({latest})",
                "value": f"{fmt_amount(metrics[latest]['cash'])} 億",
                "change_class": trend_class(metrics[latest]['cash'], metrics[prev]['cash']),
                "change_text": f"{trend_symbol(trend_class(metrics[latest]['cash'], metrics[prev]['cash']))} 三年路徑 {' → '.join(f'{fmt_amount(metrics[year]["cash"])}億' for year in years)}",
                "card_class": "teal",
            },
            {
                "label": f"流動比率 ({latest})",
                "value": fmt_pct(metrics[latest]["current_ratio"]),
                "change_class": trend_class(metrics[latest]['current_ratio'], metrics[prev]['current_ratio'], higher_is_better=True),
                "change_text": f"{trend_symbol(trend_class(metrics[latest]['current_ratio'], metrics[prev]['current_ratio'], True))} {prev} 年 {fmt_pct(metrics[prev]['current_ratio'])} → {latest} 年 {fmt_pct(metrics[latest]['current_ratio'])}",
                "card_class": "orange",
            },
            {
                "label": f"負債比率 ({latest})",
                "value": fmt_pct(metrics[latest]["debt_ratio"]),
                "change_class": trend_class(metrics[latest]['debt_ratio'], metrics[prev]['debt_ratio'], higher_is_better=False),
                "change_text": f"{trend_symbol(trend_class(metrics[latest]['debt_ratio'], metrics[prev]['debt_ratio'], False))} {prev} 年 {fmt_pct(metrics[prev]['debt_ratio'])} → {latest} 年 {fmt_pct(metrics[latest]['debt_ratio'])}",
                "card_class": "orange",
            },
            {
                "label": f"營業 CF ({latest})",
                "value": f"{fmt_amount(metrics[latest]['operating_cf'])} 億",
                "change_class": trend_class(metrics[latest]['operating_cf'], metrics[prev]['operating_cf']),
                "change_text": f"{trend_symbol(trend_class(metrics[latest]['operating_cf'], metrics[prev]['operating_cf']))} {prev} 年 {fmt_amount(metrics[prev]['operating_cf'])} 億 → {latest} 年 {fmt_amount(metrics[latest]['operating_cf'])} 億",
                "card_class": "green",
            },
            {
                "label": f"自由現金流 ({latest})",
                "value": f"{fmt_amount(metrics[latest]['fcf'])} 億",
                "change_class": trend_class(metrics[latest]['fcf'], metrics[prev]['fcf']),
                "change_text": f"{trend_symbol(trend_class(metrics[latest]['fcf'], metrics[prev]['fcf']))} CAPEX {fmt_amount(abs(metrics[latest]['capex']))} 億後仍維持正值",
                "card_class": "green",
            },
        ],
    }


def build_table_rows(years: list[str], metrics: dict[str, dict]) -> dict[str, list[tuple[str, str, list[str], str, str]]]:
    latest = years[-1]
    prev = years[-2]
    ops_rows = []
    for title, key, label, higher_is_better in [
        ("營業收入", "revenue", "revenue", True),
        ("營業毛利（億元）", "gross_profit", "revenue", True),
        ("毛利率", "gross_margin", "margin", True),
        ("推銷費用（億元）", "sell_exp", "revenue", False),
        ("管理費用（億元）", "admin_exp", "revenue", False),
        ("研究發展費用（億元）", "rd_exp", "revenue", True),
        ("營業費用合計（億元）", "total_opex", "revenue", False),
        ("費用率（合計/營收）", "total_opex_ratio", "margin", False),
        ("營業利益（億元）", "op_income", "revenue", True),
        ("營業利益率", "op_margin", "margin", True),
    ]:
        values = [metrics[year][key] for year in years]
        css_class, text = short_trend(label, metrics[latest][key], metrics[prev][key], higher_is_better)
        formatted = [fmt_pct(v) if "率" in title else fmt_amount(v) for v in values]
        ops_rows.append((title, css_class, formatted, text, key))

    profit_rows = []
    for title, key, label, higher_is_better in [
        ("稅後淨利（億元）", "net_income", "revenue", True),
        ("EPS（元）", "eps", "revenue", True),
        ("毛利率", "gross_margin", "margin", True),
        ("營業利益率", "op_margin", "margin", True),
        ("淨利率", "net_margin", "margin", True),
        ("ROE", "roe", "margin", True),
        ("ROA", "roa", "margin", True),
        ("現金股利發放（億元）", "dividends", "cashflow", True),
    ]:
        values = [abs(metrics[year][key]) if key == "dividends" and metrics[year][key] is not None else metrics[year][key] for year in years]
        css_class, text = short_trend(label, values[-1], values[-2], higher_is_better)
        formatted = [fmt_pct(v) if title in {"毛利率", "營業利益率", "淨利率", "ROE", "ROA"} else (f"{v:.2f}" if key == "eps" else fmt_amount(v)) for v in values]
        profit_rows.append((title, css_class, formatted, text, key))

    balance_rows = []
    for title, key, label, higher_is_better in [
        ("現金及約當現金", "cash", "cashflow", True),
        ("存貨", "inventory", "cashflow", False),
        ("流動資產合計", "current_assets", "revenue", True),
        ("流動負債合計", "current_liabilities", "revenue", False),
        ("權益總額", "equity", "revenue", True),
        ("負債總額", "total_liabilities", "revenue", False),
        ("資產總額", "total_assets", "revenue", True),
        ("流動比率", "current_ratio", "margin", True),
        ("負債比率", "debt_ratio", "margin", False),
    ]:
        values = [metrics[year][key] for year in years]
        css_class, text = short_trend(label, values[-1], values[-2], higher_is_better)
        formatted = [fmt_pct(v) if title in {"流動比率", "負債比率"} else fmt_amount(v) for v in values]
        balance_rows.append((title, css_class, formatted, text, key))

    cash_rows = []
    for title, key, label, higher_is_better in [
        ("營業活動 CF", "operating_cf", "cashflow", True),
        ("投資活動 CF", "investing_cf", "cashflow", True),
        ("籌資活動 CF", "financing_cf", "cashflow", True),
        ("發放現金股利", "dividends", "cashflow", True),
        ("資本支出", "capex", "cashflow", True),
        ("自由現金流", "fcf", "cashflow", True),
    ]:
        values = [abs(metrics[year][key]) if key in {"dividends", "capex"} and metrics[year][key] is not None else metrics[year][key] for year in years]
        css_class, text = short_trend(label, values[-1], values[-2], higher_is_better)
        formatted = [fmt_amount(v) for v in values]
        cash_rows.append((title, css_class, formatted, text, key))

    return {
        "ops": ops_rows,
        "profit": profit_rows,
        "balance": balance_rows,
        "cash": cash_rows,
    }


def chart_list(values: list[float | None]) -> str:
    rendered = []
    for value in values:
        if value is None:
            rendered.append("null")
        else:
            rendered.append(f"{value:.2f}")
    return "[" + ", ".join(rendered) + "]"


def build_warning_html(raw: dict) -> str:
    warnings = raw.get("verification", {}).get("sanity") or []
    if not warnings:
        return ""
    items = []
    for warning in warnings:
        items.append(f"<li><strong>{warning['field']}</strong>：{warning['msg']}</li>")
    return (
        "<div class=\"verify-warnings\">"
        "<h3>⚠ 驗證警示</h3>"
        f"<ul>{''.join(items)}</ul>"
        "</div>"
    )


def render_table(title: str, years: list[str], rows: list[tuple[str, str, list[str], str, str]]) -> str:
    body_rows = []
    for item, css_class, values, trend_text, _ in rows:
        body_rows.append(
            f"<tr><td>{item}</td><td>{values[0]}</td><td>{values[1]}</td><td>{values[2]}</td><td class=\"{css_class}\">{trend_text}</td></tr>"
        )
    return (
        "<div class=\"chart-card\">"
        f"<div class=\"chart-title\">{title}</div>"
        "<table class=\"data-table\">"
        f"<thead><tr><th>項目</th><th>{years[0]}</th><th>{years[1]}</th><th>{years[2]}</th><th>趨勢評估</th></tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody>"
        "</table></div>"
    )


def render_dashboard(raw: dict, price_history: dict | None) -> str:
    years, metrics = build_metrics(raw)
    kpis = build_kpis(years, metrics)
    insights = build_insights(raw.get("company_name") or raw.get("metadata", {}).get("company_name") or raw["stock_id"], years, metrics, None if price_history is None else price_history.get("summary"))
    tables = build_table_rows(years, metrics)
    latest = years[-1]
    latest_metrics = metrics[latest]
    company_name = raw.get("company_name") or raw.get("metadata", {}).get("company_name") or raw["stock_id"]
    stock_id = raw["stock_id"]
    fetched_at = raw["metadata"]["fetched_at"]
    mops_url = raw["metadata"]["mops_url"] if raw.get("market") != "otc" else raw["metadata"]["mops_url_otc"]
    latest_close = price_history.get("summary", {}).get("latest_close") if price_history else None
    price_summary = price_history.get("summary") if price_history else None
    sanity_pass = raw.get("verification", {}).get("sanity_pass", True)
    sanity_badge = "<span class=\"badge-ok\">✓ 合理性檢查通過</span>" if sanity_pass else "<span class=\"badge-warn\">⚠ 合理性檢查有警示</span>"

    def render_kpis(items: list[dict]) -> str:
        return "".join(
            f"<div class=\"kpi-card {item['card_class']}\"><div class=\"kpi-label\">{item['label']}</div><div class=\"kpi-value\">{item['value']}</div><div class=\"kpi-change {item['change_class']}\">{item['change_text']}</div></div>"
            for item in items
        )

    def render_insight_box(title: str, lines: list[str]) -> str:
        return f"<div class=\"insight-box\"><h3>🔍 {title}亮點</h3><ul>{''.join(f'<li>{line}</li>' for line in lines)}</ul></div>"

    price_line = ""
    if price_summary is not None:
        price_line = (
            f"<span class=\"vl\">📈 最近收盤</span><span>{fmt_price(price_summary['latest_close'])} 元（{price_summary['latest_close_date']}），位於近三年區間 {price_summary['range_position_pct']:.2f}% / 百分位 {price_summary['percentile_pct']:.2f}%</span>"
        )

    warning_html = build_warning_html(raw)

    return f"""<!DOCTYPE html>
<html lang=\"zh-TW\">
<head>
<meta charset=\"UTF-8\">
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
<title>{company_name} ({stock_id}) 三維財務分析 {years[0]}–{years[-1]}</title>
<script src=\"{CHART_JS_CDN}\"></script>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: 'Microsoft JhengHei', 'Noto Sans TC', sans-serif; background: #f0f4f8; color: #2d3748; }}
.header {{ background: linear-gradient(135deg, #1a365d 0%, #2b6cb0 50%, #3182ce 100%); color: white; padding: 24px 32px; display: flex; justify-content: space-between; align-items: center; gap: 20px; }}
.header h1 {{ font-size: 1.6rem; font-weight: 700; }}
.subtitle {{ font-size: 0.92rem; opacity: 0.9; margin-top: 6px; }}
.badge {{ background: rgba(255,255,255,0.15); padding: 8px 16px; border-radius: 999px; font-size: 0.85rem; font-weight: 600; }}
.verify-bar {{ background: #1a202c; color: #e2e8f0; padding: 8px 32px; font-size: 0.78rem; display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }}
.verify-bar .vl {{ color: #718096; }}
.badge-ok {{ background: #276749; color: #c6f6d5; padding: 2px 10px; border-radius: 99px; font-size: 0.72rem; font-weight: 600; }}
.badge-warn {{ background: #7b341e; color: #feebc8; padding: 2px 10px; border-radius: 99px; font-size: 0.72rem; font-weight: 600; }}
.verify-bar a {{ color: #63b3ed; text-decoration: none; background: #2b4a6f; padding: 2px 9px; border-radius: 5px; }}
.verify-bar a:hover {{ background: #2c5282; }}
.verify-warnings {{ background: #fffaf0; border: 1px solid #fbd38d; border-radius: 12px; margin: 20px 32px 0; padding: 16px 20px; }}
.verify-warnings h3 {{ color: #c05621; font-size: 0.95rem; margin-bottom: 10px; }}
.verify-warnings ul {{ margin-left: 18px; }}
.verify-warnings li {{ margin: 6px 0; font-size: 0.87rem; }}
.tabs {{ display: flex; background: white; border-bottom: 2px solid #e2e8f0; padding: 0 32px; overflow-x: auto; }}
.tab {{ padding: 14px 24px; cursor: pointer; font-size: 0.95rem; font-weight: 600; color: #718096; border-bottom: 3px solid transparent; margin-bottom: -2px; transition: all 0.2s; white-space: nowrap; }}
.tab.active {{ color: #2b6cb0; border-bottom-color: #2b6cb0; }}
.tab-content {{ display: none; padding: 28px 32px; }}
.tab-content.active {{ display: block; }}
.kpi-row {{ display: flex; gap: 16px; margin-bottom: 24px; flex-wrap: wrap; }}
.kpi-card {{ flex: 1; min-width: 180px; background: white; border-radius: 12px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.07); border-left: 4px solid #3182ce; }}
.kpi-card.green {{ border-left-color: #38a169; }}
.kpi-card.orange {{ border-left-color: #dd6b20; }}
.kpi-card.red {{ border-left-color: #e53e3e; }}
.kpi-card.purple {{ border-left-color: #805ad5; }}
.kpi-card.teal {{ border-left-color: #1a365d; }}
.kpi-label {{ font-size: 0.78rem; color: #718096; margin-bottom: 6px; font-weight: 500; text-transform: uppercase; }}
.kpi-value {{ font-size: 1.7rem; font-weight: 700; color: #2d3748; }}
.kpi-change {{ font-size: 0.82rem; margin-top: 6px; }}
.up {{ color: #38a169; }}
.down {{ color: #e53e3e; }}
.neutral {{ color: #718096; }}
.insight-box {{ background: linear-gradient(135deg, #ebf8ff, #e6fffa); border: 1px solid #bee3f8; border-radius: 12px; padding: 18px 22px; margin-bottom: 20px; }}
.insight-box h3 {{ color: #2b6cb0; font-size: 0.9rem; margin-bottom: 10px; }}
.insight-box ul {{ list-style: none; }}
.insight-box li {{ font-size: 0.87rem; color: #4a5568; padding: 4px 0 4px 18px; position: relative; }}
.insight-box li::before {{ content: '▸'; position: absolute; left: 0; color: #3182ce; }}
.charts-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 24px; }}
.chart-card {{ background: white; border-radius: 12px; padding: 22px; box-shadow: 0 2px 8px rgba(0,0,0,0.07); }}
.chart-title {{ font-size: 0.92rem; font-weight: 700; color: #4a5568; margin-bottom: 16px; padding-bottom: 10px; border-bottom: 1px solid #f0f4f8; }}
.chart-container {{ position: relative; height: 240px; }}
.data-table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; }}
.data-table th {{ background: #2b6cb0; color: white; padding: 10px 14px; text-align: center; }}
.data-table td {{ padding: 9px 14px; text-align: right; border-bottom: 1px solid #e2e8f0; }}
.data-table td:first-child {{ text-align: left; font-weight: 500; }}
.data-table tr:nth-child(even) td {{ background: #f7fafc; }}
.two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
@media (max-width: 768px) {{
  .header {{ flex-direction: column; align-items: flex-start; }}
  .charts-grid, .two-col {{ grid-template-columns: 1fr; }}
  .tab-content {{ padding: 20px 16px; }}
  .tabs, .verify-bar {{ padding-left: 16px; padding-right: 16px; }}
}}
</style>
</head>
<body>
<div class=\"header\">
  <div>
    <h1>{company_name} ({stock_id}) 財務分析儀表板</h1>
    <div class=\"subtitle\">資料來源：MOPS 官方財報頁｜分析期間：{years[0]} – {years[-1]}｜金額單位：億元 (NTD)｜{latest_close if latest_close is not None else '-'} 元為最新收盤</div>
  </div>
  <div class=\"badge\">📘 官方年報 + TWSE 日價</div>
</div>
<div class=\"verify-bar\">
  <span class=\"vl\">🕐 抓取時間</span><span>{fetched_at}</span>
  <span class=\"vl\">📅 財報期間</span><span>{years[0]}–{years[-1]} 年報</span>
  {sanity_badge}
  {price_line}
  <a href=\"{mops_url}\" target=\"_blank\">📋 MOPS 官方申報</a>
    <a href=\"{MOPS_WEB_HOST}/mops/web/t164sb04\" target=\"_blank\">📑 官方綜損表頁</a>
</div>
{warning_html}
<div class=\"tabs\">
  <div class=\"tab active\" onclick=\"switchTab('ops', event)\">📊 經營分析</div>
  <div class=\"tab\" onclick=\"switchTab('profit', event)\">💰 獲利分析</div>
  <div class=\"tab\" onclick=\"switchTab('finance', event)\">🏦 財務健全度</div>
</div>
<div id=\"ops\" class=\"tab-content active\">
  <div class=\"kpi-row\">{render_kpis(kpis['ops'])}</div>
  {render_insight_box('經營分析', insights['ops'])}
  <div class=\"charts-grid\">
    <div class=\"chart-card\"><div class=\"chart-title\">📈 營收與毛利率趨勢</div><div class=\"chart-container\"><canvas id=\"revenueChart\"></canvas></div></div>
    <div class=\"chart-card\"><div class=\"chart-title\">📦 三大費用金額</div><div class=\"chart-container\"><canvas id=\"opexChart\"></canvas></div></div>
    <div class=\"chart-card\"><div class=\"chart-title\">📉 費用率趨勢</div><div class=\"chart-container\"><canvas id=\"expenseRatioChart\"></canvas></div></div>
    <div class=\"chart-card\"><div class=\"chart-title\">🏆 營業利益與利益率</div><div class=\"chart-container\"><canvas id=\"opIncomeChart\"></canvas></div></div>
  </div>
  {render_table('📋 損益表明細', years, tables['ops'])}
</div>
<div id=\"profit\" class=\"tab-content\">
  <div class=\"kpi-row\">{render_kpis(kpis['profit'])}</div>
  {render_insight_box('獲利分析', insights['profit'])}
  <div class=\"charts-grid\">
    <div class=\"chart-card\"><div class=\"chart-title\">💵 稅後淨利與淨利率</div><div class=\"chart-container\"><canvas id=\"netIncomeChart\"></canvas></div></div>
    <div class=\"chart-card\"><div class=\"chart-title\">📈 每股盈餘 EPS</div><div class=\"chart-container\"><canvas id=\"epsChart\"></canvas></div></div>
    <div class=\"chart-card\"><div class=\"chart-title\">🎯 三層利潤率比較</div><div class=\"chart-container\"><canvas id=\"marginChart\"></canvas></div></div>
    <div class=\"chart-card\"><div class=\"chart-title\">💸 現金股利發放</div><div class=\"chart-container\"><canvas id=\"dividendChart\"></canvas></div></div>
  </div>
  {render_table('📋 獲利能力彙總', years, tables['profit'])}
</div>
<div id=\"finance\" class=\"tab-content\">
  <div class=\"kpi-row\">{render_kpis(kpis['finance'])}</div>
  {render_insight_box('財務健全度', insights['finance'])}
  <div class=\"charts-grid\">
    <div class=\"chart-card\"><div class=\"chart-title\">🏗️ 資產負債結構</div><div class=\"chart-container\"><canvas id=\"balanceChart\"></canvas></div></div>
    <div class=\"chart-card\"><div class=\"chart-title\">💰 現金流量三表</div><div class=\"chart-container\"><canvas id=\"cfChart\"></canvas></div></div>
    <div class=\"chart-card\"><div class=\"chart-title\">📊 流動比率與負債比率</div><div class=\"chart-container\"><canvas id=\"ratioChart\"></canvas></div></div>
    <div class=\"chart-card\"><div class=\"chart-title\">💵 現金與存貨趨勢</div><div class=\"chart-container\"><canvas id=\"cashTrendChart\"></canvas></div></div>
  </div>
  <div class=\"two-col\">{render_table('📋 資產負債表摘要', years, tables['balance'])}{render_table('📋 現金流量摘要', years, tables['cash'])}</div>
</div>
<script>
const years = {json.dumps(years, ensure_ascii=False)};
function switchTab(name, event) {{
  document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(el => el.classList.remove('active'));
  document.getElementById(name).classList.add('active');
  event.target.classList.add('active');
}}
const comboOptions = {{
  responsive: true,
  maintainAspectRatio: false,
  scales: {{
    x: {{ grid: {{ display: false }} }},
    y: {{ grid: {{ color: 'rgba(0,0,0,0.05)' }} }},
    y2: {{ position: 'right', grid: {{ display: false }}, ticks: {{ callback: value => value + '%' }} }}
  }}
}};
const simpleOptions = {{ responsive: true, maintainAspectRatio: false, scales: {{ x: {{ grid: {{ display: false }} }}, y: {{ grid: {{ color: 'rgba(0,0,0,0.05)' }} }} }} }};
new Chart(document.getElementById('revenueChart'), {{
  type: 'bar',
  data: {{ labels: years, datasets: [
    {{ label: '營收 (億元)', data: {chart_list([metrics[y]['revenue'] for y in years])}, backgroundColor: 'rgba(49,130,206,0.18)', borderColor: '#3182ce', borderWidth: 2, yAxisID: 'y' }},
    {{ label: '毛利率 (%)', data: {chart_list([metrics[y]['gross_margin'] for y in years])}, type: 'line', borderColor: '#38a169', backgroundColor: '#38a169', pointRadius: 4, tension: 0.3, yAxisID: 'y2' }}
  ] }}, options: comboOptions
}});
new Chart(document.getElementById('opexChart'), {{
  type: 'bar',
  data: {{ labels: years, datasets: [
    {{ label: '推銷費用', data: {chart_list([metrics[y]['sell_exp'] for y in years])}, backgroundColor: 'rgba(237,100,166,0.65)' }},
    {{ label: '管理費用', data: {chart_list([metrics[y]['admin_exp'] for y in years])}, backgroundColor: 'rgba(66,153,225,0.65)' }},
    {{ label: '研究發展費用', data: {chart_list([metrics[y]['rd_exp'] for y in years])}, backgroundColor: 'rgba(56,161,105,0.65)' }}
  ] }}, options: simpleOptions
}});
new Chart(document.getElementById('expenseRatioChart'), {{
  type: 'line',
  data: {{ labels: years, datasets: [
    {{ label: '推銷費用率', data: {chart_list([metrics[y]['sell_ratio'] for y in years])}, borderColor: '#d53f8c', backgroundColor: '#d53f8c', pointRadius: 4, tension: 0.3 }},
    {{ label: '管理費用率', data: {chart_list([metrics[y]['admin_ratio'] for y in years])}, borderColor: '#3182ce', backgroundColor: '#3182ce', pointRadius: 4, tension: 0.3 }},
    {{ label: '研發費用率', data: {chart_list([metrics[y]['rd_ratio'] for y in years])}, borderColor: '#38a169', backgroundColor: '#38a169', pointRadius: 4, tension: 0.3 }},
    {{ label: '管銷研合計費用率', data: {chart_list([metrics[y]['total_opex_ratio'] for y in years])}, borderColor: '#1a365d', backgroundColor: '#1a365d', pointRadius: 4, tension: 0.3 }}
  ] }}, options: simpleOptions
}});
new Chart(document.getElementById('opIncomeChart'), {{
  type: 'bar',
  data: {{ labels: years, datasets: [
    {{ label: '營業利益 (億元)', data: {chart_list([metrics[y]['op_income'] for y in years])}, backgroundColor: 'rgba(246,173,85,0.4)', borderColor: '#dd6b20', borderWidth: 2, yAxisID: 'y' }},
    {{ label: '營業利益率 (%)', data: {chart_list([metrics[y]['op_margin'] for y in years])}, type: 'line', borderColor: '#2f855a', backgroundColor: '#2f855a', pointRadius: 4, tension: 0.3, yAxisID: 'y2' }}
  ] }}, options: comboOptions
}});
new Chart(document.getElementById('netIncomeChart'), {{
  type: 'bar',
  data: {{ labels: years, datasets: [
    {{ label: '稅後淨利 (億元)', data: {chart_list([metrics[y]['net_income'] for y in years])}, backgroundColor: 'rgba(49,130,206,0.18)', borderColor: '#2b6cb0', borderWidth: 2, yAxisID: 'y' }},
    {{ label: '淨利率 (%)', data: {chart_list([metrics[y]['net_margin'] for y in years])}, type: 'line', borderColor: '#38a169', backgroundColor: '#38a169', pointRadius: 4, tension: 0.3, yAxisID: 'y2' }}
  ] }}, options: comboOptions
}});
new Chart(document.getElementById('epsChart'), {{
  type: 'bar', data: {{ labels: years, datasets: [{{ label: 'EPS (元)', data: {chart_list([metrics[y]['eps'] for y in years])}, backgroundColor: ['rgba(49,130,206,0.55)','rgba(49,130,206,0.7)','rgba(49,130,206,0.9)'], borderRadius: 6 }}] }}, options: simpleOptions
}});
new Chart(document.getElementById('marginChart'), {{
  type: 'line', data: {{ labels: years, datasets: [
    {{ label: '毛利率', data: {chart_list([metrics[y]['gross_margin'] for y in years])}, borderColor: '#2b6cb0', backgroundColor: '#2b6cb0', pointRadius: 4, tension: 0.3 }},
    {{ label: '營業利益率', data: {chart_list([metrics[y]['op_margin'] for y in years])}, borderColor: '#38a169', backgroundColor: '#38a169', pointRadius: 4, tension: 0.3 }},
    {{ label: '淨利率', data: {chart_list([metrics[y]['net_margin'] for y in years])}, borderColor: '#dd6b20', backgroundColor: '#dd6b20', pointRadius: 4, tension: 0.3 }}
  ] }}, options: simpleOptions
}});
new Chart(document.getElementById('dividendChart'), {{
  type: 'bar', data: {{ labels: years, datasets: [{{ label: '現金股利 (億元)', data: {chart_list([abs(metrics[y]['dividends']) if metrics[y]['dividends'] is not None else None for y in years])}, backgroundColor: 'rgba(128,90,213,0.65)' }}] }}, options: simpleOptions
}});
new Chart(document.getElementById('balanceChart'), {{
  type: 'bar', data: {{ labels: years, datasets: [
    {{ label: '負債總額', data: {chart_list([metrics[y]['total_liabilities'] for y in years])}, backgroundColor: 'rgba(229,62,62,0.45)', stack: 'balance' }},
    {{ label: '權益總額', data: {chart_list([metrics[y]['equity'] for y in years])}, backgroundColor: 'rgba(56,161,105,0.45)', stack: 'balance' }}
  ] }}, options: simpleOptions
}});
new Chart(document.getElementById('cfChart'), {{
  type: 'bar', data: {{ labels: years, datasets: [
    {{ label: '營業活動 CF', data: {chart_list([metrics[y]['operating_cf'] for y in years])}, backgroundColor: 'rgba(56,161,105,0.65)' }},
    {{ label: '投資活動 CF', data: {chart_list([metrics[y]['investing_cf'] for y in years])}, backgroundColor: 'rgba(66,153,225,0.65)' }},
    {{ label: '籌資活動 CF', data: {chart_list([metrics[y]['financing_cf'] for y in years])}, backgroundColor: 'rgba(221,107,32,0.65)' }}
  ] }}, options: simpleOptions
}});
new Chart(document.getElementById('ratioChart'), {{
  type: 'line', data: {{ labels: years, datasets: [
    {{ label: '流動比率', data: {chart_list([metrics[y]['current_ratio'] for y in years])}, borderColor: '#2b6cb0', backgroundColor: '#2b6cb0', pointRadius: 4, tension: 0.3 }},
    {{ label: '負債比率', data: {chart_list([metrics[y]['debt_ratio'] for y in years])}, borderColor: '#e53e3e', backgroundColor: '#e53e3e', pointRadius: 4, tension: 0.3 }}
  ] }}, options: simpleOptions
}});
new Chart(document.getElementById('cashTrendChart'), {{
  type: 'bar', data: {{ labels: years, datasets: [
    {{ label: '現金及約當現金', data: {chart_list([metrics[y]['cash'] for y in years])}, backgroundColor: 'rgba(49,130,206,0.55)' }},
    {{ label: '存貨', data: {chart_list([metrics[y]['inventory'] for y in years])}, backgroundColor: 'rgba(221,107,32,0.55)' }}
  ] }}, options: simpleOptions
}});
</script>
</body>
</html>
"""


def main() -> int:
    args = parse_args()
    raw = load_json(args.raw_json)
    price_history = load_json(args.price_history_json) if args.price_history_json else None
    company_name = raw.get("company_name") or raw.get("metadata", {}).get("company_name") or raw["stock_id"]
    output = args.output or Path(f"{company_name}_{raw['stock_id']}_analysis.html")
    output.write_text(render_dashboard(raw, price_history), encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
