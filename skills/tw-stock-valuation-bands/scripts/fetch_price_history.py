#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import requests


TWSE_STOCK_DAY_URL = "https://www.twse.com.tw/exchangeReport/STOCK_DAY"


@dataclass(frozen=True)
class MonthlyRequest:
    year: int
    month: int

    @property
    def query_date(self) -> str:
        return f"{self.year:04d}{self.month:02d}01"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch Taiwan listed stock daily price history from public TWSE data."
    )
    parser.add_argument("stock_id", help="4-digit listed stock ID")
    parser.add_argument(
        "--months",
        type=int,
        default=36,
        help="How many recent months to fetch, default 36",
    )
    parser.add_argument(
        "--market",
        choices=("twse", "tpex"),
        default="twse",
        help="Market code. Only twse is currently supported.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output path, default <stock_id>_<market>_price_history.json",
    )
    return parser.parse_args()


def validate_stock_id(stock_id: str) -> str:
    if not re.fullmatch(r"\d{4}", stock_id):
        raise ValueError(f"stock_id 必須為 4 位數字，收到：{stock_id!r}")
    return stock_id


def iter_recent_months(months: int) -> list[MonthlyRequest]:
    if months <= 0:
        raise ValueError("months 必須大於 0")
    today = date.today()
    year = today.year
    month = today.month
    items: list[MonthlyRequest] = []
    for _ in range(months):
        items.append(MonthlyRequest(year=year, month=month))
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    items.reverse()
    return items


def fetch_month(stock_id: str, request_month: MonthlyRequest, session: requests.Session) -> dict:
    response = session.get(
        TWSE_STOCK_DAY_URL,
        params={
            "response": "json",
            "date": request_month.query_date,
            "stockNo": stock_id,
        },
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    stat = payload.get("stat")
    if stat and stat != "OK":
        raise RuntimeError(
            f"TWSE 回傳失敗：{request_month.query_date} {stock_id} -> {stat}"
        )
    return payload


def parse_number(value: str) -> float | None:
    cleaned = value.replace(",", "").strip()
    if cleaned in {"", "--", "X", "除權息", "除息", "除權"}:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def to_iso_date(roc_date: str) -> str:
    year_text, month_text, day_text = roc_date.split("/")
    return f"{int(year_text) + 1911:04d}-{int(month_text):02d}-{int(day_text):02d}"


def normalize_records(payloads: list[dict]) -> list[dict]:
    records: list[dict] = []
    seen_dates: set[str] = set()
    for payload in payloads:
        for row in payload.get("data", []):
            if len(row) < 9:
                continue
            trading_date = to_iso_date(row[0])
            if trading_date in seen_dates:
                continue
            seen_dates.add(trading_date)
            records.append(
                {
                    "date": trading_date,
                    "volume": parse_number(row[1]),
                    "amount": parse_number(row[2]),
                    "open": parse_number(row[3]),
                    "high": parse_number(row[4]),
                    "low": parse_number(row[5]),
                    "close": parse_number(row[6]),
                    "change": row[7].strip(),
                    "transactions": parse_number(row[8]),
                }
            )
    records.sort(key=lambda item: item["date"])
    return records


def summarize_history(records: list[dict]) -> dict:
    closes = [record["close"] for record in records if record.get("close") is not None]
    if not closes:
        raise ValueError("抓不到可用的收盤價資料")
    low = min(closes)
    high = max(closes)
    latest_close = closes[-1]
    latest_date = next(
        record["date"] for record in reversed(records) if record.get("close") is not None
    )
    range_position = 100.0 if high == low else ((latest_close - low) / (high - low) * 100)
    rank_count = sum(1 for value in closes if value <= latest_close)
    percentile = rank_count / len(closes) * 100
    return {
        "start_date": records[0]["date"],
        "end_date": records[-1]["date"],
        "trading_days": len(records),
        "close_low": round(low, 2),
        "close_high": round(high, 2),
        "latest_close": round(latest_close, 2),
        "latest_close_date": latest_date,
        "range_position_pct": round(range_position, 2),
        "percentile_pct": round(percentile, 2),
    }


def build_metadata(stock_id: str, months: int, market: str) -> dict:
    return {
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "source": "TWSE",
        "market": market,
        "months_requested": months,
        "source_url": f"{TWSE_STOCK_DAY_URL}?response=json&date=YYYYMM01&stockNo={stock_id}",
        "note": "目前僅支援上市 TWSE 歷史股價；上櫃 TPEx 尚未接入官方日價 JSON。",
    }


def fetch_history(stock_id: str, months: int, market: str) -> dict:
    if market != "twse":
        raise NotImplementedError("目前僅支援上市 TWSE 歷史股價；TPEx 請先自行提供資料")

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Referer": "https://www.twse.com.tw/",
        }
    )

    payloads = []
    for request_month in iter_recent_months(months):
        payloads.append(fetch_month(stock_id, request_month, session))
        time.sleep(0.2)

    records = normalize_records(payloads)
    return {
        "stock_id": stock_id,
        "metadata": build_metadata(stock_id, months, market),
        "summary": summarize_history(records),
        "records": records,
    }


def main() -> int:
    args = parse_args()
    stock_id = validate_stock_id(args.stock_id)
    data = fetch_history(stock_id, args.months, args.market)
    output_path = args.output or Path(f"{stock_id}_{args.market}_price_history.json")
    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())