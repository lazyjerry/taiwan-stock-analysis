#!/usr/bin/env python3
"""四方法合理 PER 估算。

從 *_analysis.json（含 metrics_by_year 的 eps／roe）以固定公式推導四種主流方法的
合理 PER 與對應合理價，確保相同輸入必得相同輸出：

  ① 歷史分位數法  需 price_history_json；close ÷ 當年度 EPS 取 25/50/75 分位
  ② PEG 法        合理 PER = EPS 年均成長率(%)；PEG = 現 PER ÷ 成長率
  ③ ROE 驅動法    P/B = (ROE − g)/(r − g)；PER = P/B ÷ ROE（三組 r,g 情境）
  ④ Graham 公式    合理 PER = 8.5 + 2g（可選利率修正 × 4.4/公債殖利率）

輸出附各方法適用性評分與建議，供 SKILL 呈現、由使用者選定。
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path


# 方法三固定情境（label, r 必要報酬, g 長期成長）
DEFAULT_ROE_SCENARIOS = (
    ("conservative", 0.13, 0.07),
    ("neutral", 0.11, 0.08),
    ("aggressive", 0.105, 0.08),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="四方法合理 PER 估算")
    parser.add_argument("--analysis-json", type=Path, required=True, help="Path to *_analysis.json")
    parser.add_argument("--current-price", type=float, help="現價，用於算目前市場 PER 與 PEG")
    parser.add_argument(
        "--price-history-json",
        type=Path,
        help="fetch_price_history.py 產生的歷史股價 JSON（方法一需要）",
    )
    parser.add_argument("--roe", type=float, help="覆寫 ROE（小數，如 0.39）；預設取最新年度 roe")
    parser.add_argument("--growth", type=float, help="覆寫 EPS 成長率（小數，如 0.10）；預設自 EPS 序列算 CAGR")
    parser.add_argument("--bond-yield", type=float, help="公債殖利率(%)，帶入啟用 Graham 完整版利率修正")
    parser.add_argument(
        "--method",
        choices=("all", "historical", "peg", "roe", "graham"),
        default="all",
        help="輸出指定方法；all＝四法全出（預設）",
    )
    parser.add_argument(
        "--output-format",
        choices=("json", "md"),
        default="json",
        help="json（預設，供程式解析）｜md（比較報告）",
    )
    return parser.parse_args()


# ---------- 資料存取 ----------


def load_analysis(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"找不到分析 JSON：{path}")
    return json.loads(path.read_text(encoding="utf-8"))


def eps_by_year(data: dict) -> dict[int, float]:
    metrics = data.get("metrics_by_year") or {}
    result: dict[int, float] = {}
    for year, metric in metrics.items():
        eps = metric.get("eps")
        if eps is not None:
            result[int(year)] = float(eps)
    return result


def base_eps(data: dict) -> float:
    years = [int(y) for y in (data.get("years") or [])]
    eps_map = eps_by_year(data)
    for year in sorted(years, reverse=True):
        if year in eps_map and eps_map[year]:
            return eps_map[year]
    raise ValueError("找不到可用的最新年度 EPS")


def latest_roe_fraction(data: dict) -> float | None:
    years = [int(y) for y in (data.get("years") or [])]
    metrics = data.get("metrics_by_year") or {}
    for year in sorted(years, reverse=True):
        roe = metrics.get(str(year), {}).get("roe")
        if roe is not None:
            return float(roe) / 100.0
    return None


def eps_cagr(eps_map: dict[int, float]) -> float | None:
    positives = {y: e for y, e in eps_map.items() if e and e > 0}
    if len(positives) < 2:
        return None
    years = sorted(positives)
    first, last = positives[years[0]], positives[years[-1]]
    span = years[-1] - years[0]
    if span <= 0:
        return None
    return (last / first) ** (1 / span) - 1


# ---------- 數值工具 ----------


def percentile(values: list[float], q: float) -> float | None:
    """線性插值分位數，與 numpy 預設一致。"""
    if not values:
        return None
    s = sorted(values)
    if len(s) == 1:
        return s[0]
    rank = (q / 100) * (len(s) - 1)
    lo = math.floor(rank)
    hi = math.ceil(rank)
    if lo == hi:
        return s[lo]
    return s[lo] + (s[hi] - s[lo]) * (rank - lo)


def r2(value: float | None) -> float | None:
    return None if value is None else round(value, 2)


def band(per: float | None, base: float, assumption: str) -> dict:
    return {
        "per": r2(per),
        "price": r2(None if per is None else per * base),
        "assumption": assumption,
    }


# ---------- 四方法 ----------


def method_historical(price_history_path: Path | None, data: dict, base: float) -> dict:
    result = {
        "id": "historical",
        "name": "歷史 PER 分位數法",
        "available": False,
        "note": "需 price_history_json；以每日收盤 ÷ 當年度 EPS 取 25/50/75 分位（近似，用年度 EPS 而非季 TTM）",
        "bands": None,
    }
    if price_history_path is None:
        result["note"] += "。未提供歷史股價，改請至 Goodinfo 本益比河流手動核實。"
        return result
    if not price_history_path.exists():
        raise FileNotFoundError(f"找不到歷史股價 JSON：{price_history_path}")

    payload = json.loads(price_history_path.read_text(encoding="utf-8"))
    records = payload.get("records") or []
    eps_map = eps_by_year(data)
    if not eps_map:
        return result
    known_years = sorted(eps_map)

    def eps_for(year: int) -> float:
        if year in eps_map:
            return eps_map[year]
        if year < known_years[0]:
            return eps_map[known_years[0]]
        if year > known_years[-1]:
            return eps_map[known_years[-1]]
        lower = max(y for y in known_years if y <= year)
        return eps_map[lower]

    pers: list[float] = []
    for record in records:
        close = record.get("close")
        date_text = record.get("date")
        if close is None or not date_text:
            continue
        eps = eps_for(int(date_text[:4]))
        if eps and eps > 0:
            pers.append(close / eps)

    if len(pers) < 2:
        return result

    p25 = percentile(pers, 25)
    p50 = percentile(pers, 50)
    p75 = percentile(pers, 75)
    result.update(
        available=True,
        sample_size=len(pers),
        bands={
            "conservative": band(p25, base, "25th 分位（歷史相對低估）"),
            "neutral": band(p50, base, "50th 分位（歷史中位合理）"),
            "aggressive": band(p75, base, "75th 分位（歷史相對高估）"),
        },
    )
    return result


def method_peg(eps_map: dict[int, float], base: float, growth: float | None, current_price: float | None) -> dict:
    result = {
        "id": "peg",
        "name": "PEG 法（Peter Lynch）",
        "available": False,
        "note": "合理 PER = EPS 成長率(%)（PEG=1）；保守/積極為 ±20% 帶。假設成長是唯一價值來源，會系統性低估高 ROE 股。",
        "bands": None,
    }
    if growth is None:
        result["note"] += " 缺 EPS 成長率，無法估算。"
        return result

    g_pct = growth * 100
    fair = g_pct
    result.update(
        available=True,
        growth_pct=round(g_pct, 2),
        bands={
            "conservative": band(fair * 0.8, base, f"PEG 0.8（g={g_pct:.1f}%）"),
            "neutral": band(fair, base, f"PEG 1.0（g={g_pct:.1f}%）"),
            "aggressive": band(fair * 1.2, base, f"PEG 1.2（g={g_pct:.1f}%）"),
        },
    )
    if current_price is not None and base:
        current_per = current_price / base
        peg = current_per / g_pct if g_pct else None
        if peg is None:
            diagnosis = "成長率為 0，無法計算 PEG"
        elif peg < 1.0:
            diagnosis = "低估"
        elif peg <= 1.2:
            diagnosis = "合理"
        else:
            diagnosis = "高估"
        result["current"] = {
            "per": r2(current_per),
            "peg": r2(peg),
            "diagnosis": diagnosis,
        }
    return result


def method_roe(roe: float | None, base: float, scenarios=DEFAULT_ROE_SCENARIOS) -> dict:
    result = {
        "id": "roe",
        "name": "ROE 驅動法（Gordon Growth）",
        "available": False,
        "note": "P/B=(ROE−g)/(r−g)，PER=P/B÷ROE。r 與 g 利差對結果極敏感，利差縮小 1% PER 可能翻倍。",
        "bands": None,
    }
    if roe is None or roe <= 0:
        result["note"] += " 缺可用 ROE，無法估算。"
        return result

    bands: dict[str, dict] = {}
    for label, r, g in scenarios:
        if r <= g or roe <= g:
            bands[label] = band(None, base, f"r={r:.1%}, g={g:.1%}（利差非正，無解）")
            continue
        pb = (roe - g) / (r - g)
        per = pb / roe
        bands[label] = band(per, base, f"r={r:.1%}, g={g:.1%}, P/B={pb:.2f}")
    result.update(available=True, roe_pct=round(roe * 100, 2), bands=bands)
    return result


def method_graham(base: float, growth: float | None, bond_yield: float | None) -> dict:
    result = {
        "id": "graham",
        "name": "Benjamin Graham 成長公式",
        "available": False,
        "note": "合理 PER = 8.5 + 2g（g 為整數 %）；帶 --bond-yield 啟用完整版 ×(4.4/殖利率)。",
        "bands": None,
    }
    if growth is None:
        result["note"] += " 缺成長率，無法估算。"
        return result

    neutral_g = round(growth * 100)
    factor = (4.4 / bond_yield) if bond_yield else 1.0
    if bond_yield:
        result["note"] += f" 已套用利率修正 ×(4.4/{bond_yield})={factor:.3f}。"

    def graham_per(g: float) -> float:
        return (8.5 + 2 * g) * factor

    scenarios = (
        ("conservative", neutral_g - 3),
        ("neutral", neutral_g),
        ("aggressive", neutral_g + 3),
    )
    result.update(
        available=True,
        bands={
            label: band(graham_per(g), base, f"g={g}%")
            for label, g in scenarios
        },
    )
    return result


# ---------- 適用性評分與建議 ----------


def applicability(data: dict, roe: float | None, growth: float | None, has_history: bool) -> list[dict]:
    roe_pct = (roe or 0) * 100
    growth_pct = (growth or 0) * 100
    high_roe = roe_pct >= 20

    items: list[dict] = []

    items.append({
        "id": "historical",
        "stars": 5 if has_history else 2,
        "reason": "最客觀，反映市場歷史定價；" + ("已可由歷史股價自動計算。" if has_history else "但目前缺歷史股價 JSON，需手動核實。"),
    })

    if growth_pct <= 0:
        peg_stars, peg_reason = 1, "EPS 無正成長，PEG 不適用。"
    elif high_roe:
        peg_stars, peg_reason = 2, "系統性低估高 ROE 股，僅供估值下限參考。"
    else:
        peg_stars, peg_reason = 4, "一般成長股適用，成長為主要價值來源時可靠。"
    items.append({"id": "peg", "stars": peg_stars, "reason": peg_reason})

    if roe is None or roe_pct <= 0:
        roe_stars, roe_reason = 2, "缺可用 ROE。"
    elif high_roe:
        roe_stars, roe_reason = 5, f"最貼合高 ROE（{roe_pct:.0f}%）優質股特質；注意 r、g 假設敏感度。"
    else:
        roe_stars, roe_reason = 3, "ROE 一般，結果對利差假設敏感。"
    items.append({"id": "roe", "stars": roe_stars, "reason": roe_reason})

    if growth_pct <= 0:
        gr_stars, gr_reason = 2, "缺正成長率，Graham 成長項失效。"
    else:
        gr_stars, gr_reason = 4, "結果通常貼近市況；未修正利率環境（可帶公債殖利率補正）。"
    items.append({"id": "graham", "stars": gr_stars, "reason": gr_reason})

    priority = {"historical": 0, "roe": 1, "graham": 2, "peg": 3}
    best = max(items, key=lambda x: (x["stars"], -priority[x["id"]]))
    for item in items:
        item["recommended"] = item["id"] == best["id"]
    return items


# ---------- 組裝與輸出 ----------


def build_result(args: argparse.Namespace) -> dict:
    data = load_analysis(args.analysis_json)
    eps_map = eps_by_year(data)
    base = base_eps(data)
    roe = args.roe if args.roe is not None else latest_roe_fraction(data)
    growth = args.growth if args.growth is not None else eps_cagr(eps_map)
    has_history = args.price_history_json is not None and args.price_history_json.exists()

    methods = {
        "historical": method_historical(args.price_history_json, data, base),
        "peg": method_peg(eps_map, base, growth, args.current_price),
        "roe": method_roe(roe, base),
        "graham": method_graham(base, growth, args.bond_yield),
    }
    if args.method != "all":
        methods = {args.method: methods[args.method]}

    return {
        "stock_id": data.get("stock_id", ""),
        "company_name": data.get("company_name", ""),
        "latest_year": (data.get("years") or [None])[-1],
        "base_eps": r2(base),
        "roe_pct": None if roe is None else round(roe * 100, 2),
        "eps_growth_pct": None if growth is None else round(growth * 100, 2),
        "current_price": args.current_price,
        "current_market_per": r2(args.current_price / base) if args.current_price else None,
        "methods": methods,
        "applicability": applicability(data, roe, growth, has_history) if args.method == "all" else None,
    }


def render_md(result: dict) -> str:
    labels = {"conservative": "悲觀", "neutral": "中性", "aggressive": "樂觀"}
    star = lambda n: "★" * n + "☆" * (5 - n)
    lines: list[str] = []
    lines.append(f"# {result['company_name']}（{result['stock_id']}）四方法合理 PER")
    lines.append("")
    lines.append(
        f"基準 EPS {result['base_eps']} 元 ｜ ROE {result['roe_pct']}% ｜ "
        f"EPS 成長率 {result['eps_growth_pct']}%"
        + (f" ｜ 現價 {result['current_price']} 元（市場 PER {result['current_market_per']}x）" if result["current_price"] else "")
    )
    lines.append("")
    lines.append("## 各方法合理 PER 彙整")
    lines.append("")
    lines.append("| 方法 | 悲觀 PER | 中性 PER | 樂觀 PER |")
    lines.append("|------|----------|----------|----------|")
    for method in result["methods"].values():
        bands = method.get("bands")
        if not bands:
            cells = "資料不足 | 資料不足 | 資料不足"
        else:
            cells = " | ".join(
                f"{bands[k]['per']}x（{bands[k]['price']}元）" if bands[k]["per"] is not None else "無解"
                for k in ("conservative", "neutral", "aggressive")
            )
        lines.append(f"| {method['name']} | {cells} |")
    lines.append("")

    for method in result["methods"].values():
        lines.append(f"## {method['name']}")
        lines.append("")
        lines.append(f"> {method['note']}")
        lines.append("")
        bands = method.get("bands")
        if bands:
            lines.append("| 情境 | 合理 PER | 合理股價 | 依據 |")
            lines.append("|------|----------|----------|------|")
            for key in ("conservative", "neutral", "aggressive"):
                b = bands[key]
                per = f"{b['per']}x" if b["per"] is not None else "無解"
                price = f"{b['price']} 元" if b["price"] is not None else "-"
                lines.append(f"| {labels[key]} | {per} | {price} | {b['assumption']} |")
            lines.append("")
        current = method.get("current")
        if current:
            lines.append(f"> 目前 PER {current['per']}x，PEG {current['peg']} → **{current['diagnosis']}**")
            lines.append("")

    if result.get("applicability"):
        name_map = {m["id"]: m["name"] for m in result["methods"].values()} if False else {
            "historical": "歷史 PER 分位數法",
            "peg": "PEG 法",
            "roe": "ROE 驅動法",
            "graham": "Graham 成長公式",
        }
        lines.append("## 方法適用性與建議")
        lines.append("")
        lines.append("| 方法 | 適用性 | 說明 |")
        lines.append("|------|--------|------|")
        for item in result["applicability"]:
            mark = "（建議）" if item["recommended"] else ""
            lines.append(f"| {name_map[item['id']]}{mark} | {star(item['stars'])} | {item['reason']} |")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    try:
        result = build_result(args)
    except (FileNotFoundError, ValueError) as exc:
        print(f"錯誤：{exc}", file=sys.stderr)
        return 1

    if args.output_format == "md":
        print(render_md(result))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
