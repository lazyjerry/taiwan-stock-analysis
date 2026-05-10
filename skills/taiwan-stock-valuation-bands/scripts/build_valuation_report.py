#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


DEFAULT_PER_BANDS = {
    5: (None, 8.0),
    4: (8.0, 9.0),
    3: (9.0, 10.0),
    2: (10.0, 11.0),
    1: (11.0, None),
}


@dataclass(frozen=True)
class Scenario:
    label: str
    eps: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate Taiwan stock valuation bands and 1-5 score ranges from an analysis JSON."
    )
    parser.add_argument("--analysis-json", type=Path, help="Path to *_analysis.json")
    parser.add_argument(
        "--stock-id",
        help="Stock ID used to run an explicit analyze script before valuation",
    )
    parser.add_argument(
        "--analyze-script",
        type=Path,
        help="Path to analyze_tw_stock.py; no default because this repo does not include it",
    )
    parser.add_argument(
        "--current-price",
        type=float,
        help="Current market price for scenario scoring",
    )
    parser.add_argument(
        "--output-format",
        choices=("markdown", "json"),
        default="markdown",
        help="Report format",
    )
    parser.add_argument("--pessimistic-eps", type=float, help="Override pessimistic EPS")
    parser.add_argument("--base-eps", type=float, help="Override base EPS")
    parser.add_argument("--optimistic-eps", type=float, help="Override optimistic EPS")
    parser.add_argument(
        "--scenario-downside",
        type=float,
        default=0.15,
        help="Default downside ratio vs base EPS",
    )
    parser.add_argument(
        "--scenario-upside",
        type=float,
        default=0.15,
        help="Default upside ratio vs base EPS",
    )
    parser.add_argument(
        "--precision",
        type=int,
        default=2,
        help="Decimal precision for EPS",
    )
    return parser.parse_args()


def run_analysis(stock_id: str, analyze_script: Path) -> Path:
    if not analyze_script.exists():
        raise FileNotFoundError(f"找不到分析腳本：{analyze_script}")

    result = subprocess.run(
        [sys.executable, str(analyze_script), stock_id],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    return Path(payload["json_path"])


def load_analysis_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"找不到分析 JSON：{path}")
    return json.loads(path.read_text(encoding="utf-8"))


def latest_year_payload(data: dict) -> tuple[str, dict]:
    years = data.get("years") or []
    if not years:
        raise ValueError("analysis JSON 缺少 years")
    year = years[-1]
    return year, data["metrics_by_year"][year]


def round_price(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 2)


def build_scenarios(args: argparse.Namespace, latest_eps: float) -> list[Scenario]:
    precision = max(args.precision, 0)
    base_eps = args.base_eps if args.base_eps is not None else latest_eps
    pessimistic = (
        args.pessimistic_eps
        if args.pessimistic_eps is not None
        else round(base_eps * (1 - args.scenario_downside), precision)
    )
    optimistic = (
        args.optimistic_eps
        if args.optimistic_eps is not None
        else round(base_eps * (1 + args.scenario_upside), precision)
    )
    return [
        Scenario("悲觀", round(pessimistic, precision)),
        Scenario("中性", round(base_eps, precision)),
        Scenario("樂觀", round(optimistic, precision)),
    ]


def build_price_bands(eps: float) -> list[dict]:
    bands: list[dict] = []
    for score, (lower_per, upper_per) in DEFAULT_PER_BANDS.items():
        lower_price = None if lower_per is None else round_price(lower_per * eps)
        upper_price = None if upper_per is None else round_price(upper_per * eps)
        if score == 5:
            price_range = f"{fmt_price(upper_price)} 以下"
        elif score == 1:
            price_range = f"{fmt_price(lower_price)} 以上"
        else:
            price_range = f"{fmt_price(lower_price)}–{fmt_price(upper_price)}"
        bands.append(
            {
                "score": score,
                "per_low": lower_per,
                "per_high": upper_per,
                "price_low": lower_price,
                "price_high": upper_price,
                "price_range": price_range,
            }
        )
    return bands


def score_price(price: float, eps: float) -> dict:
    per = price / eps if eps else math.inf
    if per < 8:
        score = 5
    elif per < 9:
        score = 4
    elif per < 10:
        score = 3
    elif per < 11:
        score = 2
    else:
        score = 1
    return {
        "price": round_price(price),
        "per": round(per, 2),
        "score": score,
    }


def allocation_for_score(score: int) -> str:
    mapping = {
        5: "可積極看待",
        4: "可分批布局",
        3: "正常持有",
        2: "追價保守",
        1: "需更強成長支撐",
    }
    return mapping[score]


def fmt_price(value: float | None) -> str:
    if value is None:
        return "-"
    if abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    return f"{value:.2f}"


def fmt_per(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.2f}x"


def make_report(data: dict, scenarios: list[Scenario], current_price: float | None) -> dict:
    year, latest = latest_year_payload(data)
    company = data.get("company_name", data.get("stock_id", ""))
    stock_id = data.get("stock_id", "")
    latest_eps = latest.get("eps")
    if latest_eps in (None, 0):
        raise ValueError(f"{stock_id} 最新年度 EPS 不可用")

    scenario_rows = []
    for scenario in scenarios:
        bands = build_price_bands(scenario.eps)
        current = score_price(current_price, scenario.eps) if current_price is not None else None
        scenario_rows.append(
            {
                "label": scenario.label,
                "eps": scenario.eps,
                "bands": bands,
                "current_price_view": current,
            }
        )

    return {
        "company_name": company,
        "stock_id": stock_id,
        "latest_year": year,
        "latest_eps": latest_eps,
        "current_price": current_price,
        "scenario_rows": scenario_rows,
    }


def render_markdown(report: dict) -> str:
    company = report["company_name"]
    stock_id = report["stock_id"]
    year = report["latest_year"]
    latest_eps = report["latest_eps"]
    lines = [
        f"# {company} ({stock_id}) 估值區間",
        "",
        f"- 最新年度：`{year}`",
        f"- 基準 EPS：`{latest_eps:.2f}` 元",
    ]
    if report["current_price"] is not None:
        lines.append(f"- 目前股價：`{report['current_price']:.2f}` 元")
    lines.append("")

    for scenario in report["scenario_rows"]:
        lines.append(f"## {scenario['label']}情境")
        lines.append(f"- EPS：`{scenario['eps']:.2f}` 元")
        lines.append("")
        lines.append("| 分數 | 價格區間 | 對應 PER | 判讀 |")
        lines.append("|---|---:|---:|---|")
        for band in scenario["bands"]:
            low = fmt_per(band["per_low"])
            high = fmt_per(band["per_high"])
            if band["score"] == 5:
                per_range = f"{high} 以下"
            elif band["score"] == 1:
                per_range = f"{low} 以上"
            else:
                per_range = f"{low}–{high}"
            lines.append(
                f"| {band['score']} | `{band['price_range']}` | `{per_range}` | {allocation_for_score(band['score'])} |"
            )
        current = scenario["current_price_view"]
        if current:
            lines.append("")
            lines.append(
                f"- 目前股價對應：PER `{current['per']:.2f}x`，評分 `{current['score']} 分`"
            )
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def main() -> int:
    args = parse_args()
    analysis_json = args.analysis_json
    if args.stock_id:
        if args.analyze_script is None:
            print(
                "錯誤：提供 --stock-id 時，必須另外提供 --analyze-script。"
                " 目前 repo 沒有預設的 analyze_tw_stock.py，請先確認資料來源或直接提供 --analysis-json",
                file=sys.stderr,
            )
            return 1
        analysis_json = run_analysis(args.stock_id, args.analyze_script)
    if analysis_json is None:
        print("錯誤：請提供 --analysis-json 或 --stock-id", file=sys.stderr)
        return 1

    data = load_analysis_json(analysis_json)
    year, latest = latest_year_payload(data)
    latest_eps = latest.get("eps")
    if latest_eps in (None, 0):
        print(f"錯誤：{data.get('stock_id')} {year} EPS 不可用", file=sys.stderr)
        return 1

    scenarios = build_scenarios(args, float(latest_eps))
    report = make_report(data, scenarios, args.current_price)
    if args.output_format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
