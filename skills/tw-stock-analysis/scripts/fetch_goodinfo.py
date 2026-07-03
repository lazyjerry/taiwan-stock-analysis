#!/usr/bin/env python3
"""
fetch_goodinfo.py
沿用既有檔名，但改由 MOPS 官方財報頁抓取台灣股票年度財報數據。
輸出最近三個可用年度的原始財報 JSON，含三層驗證機制（Provenance / Sanity / MOPS連結）。
用法：python fetch_goodinfo.py <股票代碼>
範例：python fetch_goodinfo.py 2317
"""

import requests
from bs4 import BeautifulSoup
import time
import json
import sys
import argparse
import urllib3
from datetime import date


MOPS_HOST = 'https://mopsov.twse.com.tw'
STATEMENT_PAGE_MAP = {
    'balance_sheet': 't164sb03',
    'income_statement': 't164sb04',
    'cash_flow': 't164sb05',
}
MARKET_LABELS = {
    'sii': '上市',
    'otc': '上櫃',
}
MAX_LOOKBACK_YEARS = 8


# ─── 抓取層 ───────────────────────────────────────────────

def make_session(verify_ssl=True):
    session = requests.Session()
    session.verify = verify_ssl
    session.headers.update(
        {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': f'{MOPS_HOST}/mops/web/index',
        }
    )
    return session


def normalize_text(text):
    return ' '.join(text.replace('\xa0', ' ').split())


def parse_amount(text, raw_unit=False):
    cleaned = text.replace(',', '').replace(' ', '').strip()
    if cleaned in {'', '--', '—', '-'}:
        return None
    negative = cleaned.startswith('(') and cleaned.endswith(')')
    if negative:
        cleaned = cleaned[1:-1]
    try:
        value = float(cleaned)
    except ValueError:
        return None
    if negative:
        value *= -1
    if raw_unit:
        return round(value, 2)
    return round(value / 100000, 2)


def build_payload(stock_id, roc_year, market):
    return {
        'step': '1',
        'firstin': '1',
        'off': '1',
        'queryName': 'co_id',
        'inpuType': 'co_id',
        'TYPEK': market,
        'isnew': 'false',
        'co_id': stock_id,
        'year': str(roc_year),
        'season': '04',
    }


def fetch_statement_html(session, stock_id, roc_year, market, page_id):
    url = f'{MOPS_HOST}/mops/web/ajax_{page_id}'
    response = session.post(
        url,
        data=build_payload(stock_id, roc_year, market),
        headers={'Referer': f'{MOPS_HOST}/mops/web/{page_id}'},
        timeout=20,
    )
    response.raise_for_status()
    response.encoding = 'utf-8'
    html = response.text
    if not html.strip():
        raise RuntimeError(
            f'MOPS 回傳空內容：stock_id={stock_id} year={roc_year} market={market} page={page_id}'
        )
    if '查詢無資料' in html or '查無所需資料' in html:
        return None
    return html


def parse_company_name(html):
    soup = BeautifulSoup(html, 'html.parser')
    heading = soup.find('h4')
    if heading:
        text = normalize_text(heading.get_text(' ', strip=True))
        marker = '本資料由'
        suffix = '公司提供'
        if marker in text and suffix in text:
            return text.split(marker, 1)[1].split(suffix, 1)[0]
    text = normalize_text(soup.get_text(' ', strip=True))
    if '上市公司)' in text:
        return text.split('上市公司)', 1)[1].split(' ', 1)[0]
    if '上櫃公司)' in text:
        return text.split('上櫃公司)', 1)[1].split(' ', 1)[0]
    return stock_id


def parse_statement_table(html):
    soup = BeautifulSoup(html, 'html.parser')
    tables = soup.find_all('table')
    if len(tables) < 2:
        raise ValueError(f'MOPS 頁面缺少財報表格，僅找到 {len(tables)} 個 table')

    result = {}
    for row in tables[1].find_all('tr')[4:]:
        cells = [normalize_text(cell.get_text(' ', strip=True)) for cell in row.find_all(['th', 'td'])]
        if len(cells) < 2:
            continue
        label = cells[0]
        if not label:
            continue
        value = parse_amount(cells[1], raw_unit='每股盈餘' in label or '每股虧損' in label)
        if value is None:
            continue
        result[label] = value

    if not result:
        raise ValueError('MOPS 財報表格解析失敗，抓不到欄位資料')
    return result


def find_market_and_years(session, stock_id):
    current_roc_year = date.today().year - 1911
    for market in ('sii', 'otc'):
        found_years = []
        cached_html = {}
        for roc_year in range(current_roc_year, current_roc_year - MAX_LOOKBACK_YEARS, -1):
            html = fetch_statement_html(session, stock_id, roc_year, market, STATEMENT_PAGE_MAP['income_statement'])
            if html is None:
                continue
            found_years.append(roc_year)
            cached_html[('income_statement', roc_year)] = html
            if len(found_years) == 3:
                return market, found_years, cached_html
    raise RuntimeError(f'找不到 {stock_id} 最近三個可用年度的官方財報資料')


def build_year_dict(statement_by_year):
    merged = {}
    for year, fields in statement_by_year.items():
        for field_name, value in fields.items():
            merged.setdefault(field_name, {})[year] = value
    return merged


# ─── 驗證層 A：資料來源標注 ────────────────────────────────

def build_metadata(stock_id, company_name, years, market):
    return {
        'fetched_at': time.strftime('%Y-%m-%dT%H:%M:%S+08:00'),
        'source': 'MOPS 官方財報頁',
        'company_name': company_name,
        'market': market,
        'market_label': MARKET_LABELS.get(market, market),
        'source_urls': {
            'income_statement': f'{MOPS_HOST}/mops/web/{STATEMENT_PAGE_MAP["income_statement"]}',
            'balance_sheet': f'{MOPS_HOST}/mops/web/{STATEMENT_PAGE_MAP["balance_sheet"]}',
            'cash_flow': f'{MOPS_HOST}/mops/web/{STATEMENT_PAGE_MAP["cash_flow"]}',
        },
        'mops_url':     f'https://mops.twse.com.tw/mops/web/t05st01?step=1&co_id={stock_id}&TYPEK=sii',
        'mops_url_otc': f'https://mops.twse.com.tw/mops/web/t05st01?step=1&co_id={stock_id}&TYPEK=otc',
        'years_covered': years,
        'currency': 'TWD 億元',
    }


# ─── 驗證層 B：合理性檢查 ──────────────────────────────────

def sanity_check(metrics_by_year, years):
    """
    metrics_by_year: {year: {gross_margin, op_margin, net_margin,
                              current_ratio, debt_ratio, roe, roa}}
    回傳 warnings 列表，每項為 {'level': 'warn'|'error', 'field': str, 'msg': str}
    """
    warnings = []

    for yr in years:
        m = metrics_by_year.get(yr, {})

        gm = m.get('gross_margin')
        if gm is not None:
            if gm > 100:
                warnings.append({'level': 'error', 'field': f'{yr} 毛利率',
                    'msg': f'{gm:.1f}% 超過 100%，數據可能有誤'})
            elif gm < -50:
                warnings.append({'level': 'error', 'field': f'{yr} 毛利率',
                    'msg': f'{gm:.1f}% 低於 -50%，請確認是否為特殊損失年度'})

        cr = m.get('current_ratio')
        if cr is not None and cr < 0:
            warnings.append({'level': 'error', 'field': f'{yr} 流動比率',
                'msg': f'{cr:.1f}% 為負值，請檢查資產負債表數據'})

        dr = m.get('debt_ratio')
        if dr is not None and dr > 100:
            warnings.append({'level': 'warn', 'field': f'{yr} 負債比率',
                'msg': f'{dr:.1f}% 超過 100%，若非金融業則為警示訊號'})

        roe = m.get('roe')
        if roe is not None and roe > 100:
            warnings.append({'level': 'warn', 'field': f'{yr} ROE',
                'msg': f'{roe:.1f}% 超過 100%，可能為高槓桿，請確認股東權益是否偏低'})

    # 相鄰年度淨利率波動檢查
    nm_list = [(yr, metrics_by_year[yr].get('net_margin'))
               for yr in years if yr in metrics_by_year]
    for i in range(1, len(nm_list)):
        yr_prev, nm_prev = nm_list[i - 1]
        yr_curr, nm_curr = nm_list[i]
        if nm_prev is not None and nm_curr is not None:
            delta = nm_curr - nm_prev
            if abs(delta) > 30:
                warnings.append({'level': 'warn',
                    'field': f'{yr_prev}→{yr_curr} 淨利率',
                    'msg': f'波動 {delta:+.1f} 個百分點，建議確認是否有一次性損益'})

    return warnings


# ─── 主流程 ───────────────────────────────────────────────

def fetch_all(stock_id, verify_ssl=True):
    result = {'stock_id': stock_id}

    if not verify_ssl:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        print('⚠️  本次已停用 SSL 憑證驗證，僅建議用於本機 CA 異常排查')

    session = make_session(verify_ssl=verify_ssl)
    market, roc_years, cached_html = find_market_and_years(session, stock_id)
    gregorian_years = [str(year + 1911) for year in roc_years]
    first_html = cached_html[('income_statement', roc_years[0])]
    company_name = parse_company_name(first_html)

    print(f'已鎖定 {stock_id} 為 {MARKET_LABELS.get(market, market)}公司，最近三年：{", ".join(gregorian_years)}')

    raw_by_statement = {
        'income_statement': {},
        'balance_sheet': {},
        'cash_flow': {},
    }

    for statement_name, page_id in STATEMENT_PAGE_MAP.items():
        print(f'正在抓取 {stock_id} {statement_name}...')
        for roc_year, gregorian_year in zip(roc_years, gregorian_years):
            html = cached_html.get((statement_name, roc_year))
            if html is None:
                html = fetch_statement_html(session, stock_id, roc_year, market, page_id)
            if html is None:
                raise RuntimeError(
                    f'找不到 {stock_id} {gregorian_year} 年 {statement_name} 官方財報資料'
                )
            raw_by_statement[statement_name][gregorian_year] = parse_statement_table(html)
            time.sleep(0.2)

    result['company_name'] = company_name
    result['market'] = market
    result['income_statement'] = build_year_dict(raw_by_statement['income_statement'])
    result['balance_sheet'] = build_year_dict(raw_by_statement['balance_sheet'])
    result['cash_flow'] = build_year_dict(raw_by_statement['cash_flow'])
    result['years'] = gregorian_years

    # 驗證層 A：資料標注
    result['metadata'] = build_metadata(stock_id, company_name, gregorian_years, market)

    return result


def run_verification(result, metrics_by_year):
    """在 fetch_all() 之後、建立儀表板之前呼叫。"""
    years = result['years'][:3]

    # 驗證層 B：合理性檢查
    warnings = sanity_check(metrics_by_year, years)
    sanity_pass = all(w['level'] != 'error' for w in warnings)

    result['verification'] = {
        'sanity': warnings,
        'sanity_pass': sanity_pass,
    }

    if warnings:
        print(f"\n⚠️  合理性檢查發現 {len(warnings)} 項警示：")
        for w in warnings:
            icon = '❌' if w['level'] == 'error' else '⚠️ '
            print(f"  {icon} [{w['field']}] {w['msg']}")
    else:
        print("✅ 合理性檢查通過，所有指標在合理範圍內")

    # 驗證層 C：MOPS 連結（已在 metadata 中）
    print(f"📋 MOPS 官方申報（上市）：{result['metadata']['mops_url']}")

    return result


def average_balance(current_value, previous_value):
    if current_value is None:
        return None
    if previous_value is None:
        return current_value
    return (current_value + previous_value) / 2


if __name__ == '__main__':
    import re
    parser = argparse.ArgumentParser(description='抓取 Goodinfo 財報數據')
    parser.add_argument('stock_id', nargs='?', default='2330', help='4 到 6 位數股票代碼')
    parser.add_argument(
        '--insecure',
        action='store_true',
        help='停用本次 HTTPS 憑證驗證，僅用於本機 CA 憑證異常時',
    )
    args, unknown = parser.parse_known_args()

    if unknown:
        if any(arg in {'--months', '--market', '--output'} for arg in unknown):
            parser.exit(
                2,
                '錯誤：fetch_goodinfo.py 只抓財報，不支援 --months / --market / --output。\n'
                '若要抓歷史股價，請改用：\n'
                'python3 skills/tw-stock-valuation-bands/scripts/fetch_price_history.py <stock_id> --months 36\n',
            )
        parser.error(f"unrecognized arguments: {' '.join(unknown)}")

    raw = args.stock_id
    if not re.fullmatch(r'\d{4,6}', raw):
        sys.exit(f"錯誤：stock_id 必須為 4–6 位數字，收到：{raw!r}")
    stock_id = raw
    try:
        data = fetch_all(stock_id, verify_ssl=not args.insecure)
    except Exception as exc:
        sys.exit(f"錯誤：{exc}")

    is_d = data['income_statement']
    bs_d = data['balance_sheet']
    cf_d = data['cash_flow']
    years = data['years'][:3]

    # 計算衍生指標（示範用）
    def g(table, key, yr):
        return table.get(key, {}).get(yr)
    def safe(a, b): return a / b * 100 if (a is not None and b) else None

    rev_key = next((k for k in is_d if '營業收入合計' in k or k == '營業收入'), None)
    gp_key = next((k for k in is_d if '營業毛利（毛損）淨額' in k or k == '營業毛利（毛損）'), None)
    op_key = next((k for k in is_d if '營業利益（損失）' in k), None)
    ni_key = next((k for k in is_d if '本期淨利' in k or '稅後淨利' in k), None)
    ca_key = next((k for k in bs_d if '流動資產合計' in k), None)
    cl_key = next((k for k in bs_d if '流動負債合計' in k), None)
    tl_key = next((k for k in bs_d if '負債總計' in k or '負債總額' in k), None)
    ta_key = next((k for k in bs_d if '資產總計' in k or '資產總額' in k), None)
    eq_key = next((k for k in bs_d if '權益總計' in k or '股東權益總額' in k), None)

    metrics_by_year = {}
    for index, yr in enumerate(years):
        prev_yr = years[index + 1] if index + 1 < len(years) else None

        rev = g(is_d, rev_key, yr) if rev_key else None
        gp  = g(is_d, gp_key,  yr) if gp_key  else None
        op  = g(is_d, op_key,  yr) if op_key  else None
        ni  = g(is_d, ni_key,  yr) if ni_key  else None
        ca  = g(bs_d, ca_key,  yr) if ca_key  else None
        cl  = g(bs_d, cl_key,  yr) if cl_key  else None
        tl  = g(bs_d, tl_key,  yr) if tl_key  else None
        ta  = g(bs_d, ta_key,  yr) if ta_key  else None
        eq  = g(bs_d, eq_key,  yr) if eq_key  else None
        prev_ta = g(bs_d, ta_key, prev_yr) if ta_key and prev_yr else None
        prev_eq = g(bs_d, eq_key, prev_yr) if eq_key and prev_yr else None
        avg_ta = average_balance(ta, prev_ta)
        avg_eq = average_balance(eq, prev_eq)

        metrics_by_year[yr] = {
            'gross_margin':  safe(gp, rev),
            'op_margin':     safe(op, rev),
            'net_margin':    safe(ni, rev),
            'current_ratio': safe(ca, cl),
            'debt_ratio':    safe(tl, ta),
            'roe':           safe(ni, avg_eq),
            'roa':           safe(ni, avg_ta),
        }

    data = run_verification(data, metrics_by_year)

    print(f"\n=== {stock_id} 財報摘要 ===")
    print(f"年度: {years}")
    for yr in years:
        rev_key = next((k for k in is_d if '營業收入合計' in k or k == '營業收入'), None)
        eps_key = next((k for k in is_d if '基本每股盈餘' in k or ('每股' in k and '盈餘' in k)), None)
        rev = g(is_d, rev_key, yr) if rev_key else None
        eps = g(is_d, eps_key, yr) if eps_key else None
        print(f"  {yr}: 營收={rev}億, EPS={eps}元")

    out_file = f'{stock_id}_goodinfo_raw_data.json'
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n原始數據（含驗證結果）已存至 {out_file}")
