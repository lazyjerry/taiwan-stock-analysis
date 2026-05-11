---
name: taiwan-stock-valuation-bands
description: (Lazyjery 版本)當使用者要把台股財報分析接到股價、計算合理價、拆成悲觀/中性/樂觀三種價格區間、或輸出 1-5 分估值評級與分批建議時使用。優先讀取 `*_analysis.json`，並用 `scripts/build_valuation_report.py` 產出可直接貼給使用者的估值表。
---

# Taiwan Stock Valuation Bands

## Overview

這個 skill 會把既有的台股財報分析 JSON 轉成估值帶，輸出三種 EPS 情境、`1–5 分` 價格區間、現價評分與分批建議。
若另外提供歷史股價 JSON，還會補上近年收盤價區間、最近收盤在區間中的相對位置，以及收盤價百分位。
分析前要先和使用者確認股票代號、公司名稱、檔名是否指向同一個標的；確認完成才繼續。
本 repo 目前找不到 `analyze_tw_stock.py`。若要確認相對位置，現有最接近的財報抓取腳本是 `../taiwan-stock-analysis/scripts/fetch_goodinfo.py`，但它輸出的是 `*_goodinfo_raw_data.json`，不能直接當成這個 skill 的 `*_analysis.json` 來源。

## Quick Start

1. 先和使用者確認股票代號、公司名稱、`*_analysis.json` 檔名是否一致
2. 只有確認同一個標的後，才使用 `*_analysis.json` 如果沒有相符的 `*_analysis.json`，先告知使用者，請使用者提供路徑或請他使用財報分析 taiwan-stock-analysis skill 產出 `*_analysis.json`
3. 用 `scripts/build_valuation_report.py` 產出估值報告
4. 若使用者提供現價，帶入 `--current-price`
5. 若使用者要納入歷史股價，先用 `scripts/fetch_price_history.py` 抓公開日價資料，再帶 `--price-history-json`
6. 若使用者明確指定悲觀/中性/樂觀 EPS，改用覆寫參數
7. 若只有股票代號、沒有 `*_analysis.json`，先停下來確認資料來源，不要直接假設 repo 內有 `analyze_tw_stock.py`

常用指令：

```bash
python3 skills/taiwan-stock-valuation-bands/scripts/build_valuation_report.py \
  --analysis-json 雄獅_2731_analysis.json \
  --current-price 163.5
```

```bash
python3 skills/taiwan-stock-valuation-bands/scripts/fetch_price_history.py 2330 --months 36

python3 skills/taiwan-stock-valuation-bands/scripts/build_valuation_report.py \
  --analysis-json 台積電_2330_analysis.json \
  --current-price 950 \
  --price-history-json 2330_twse_price_history.json
```

```bash
python3 skills/taiwan-stock-valuation-bands/scripts/build_valuation_report.py \
  --analysis-json 雄獅_2731_analysis.json \
  --pessimistic-eps 15 \
  --base-eps 17.5 \
  --optimistic-eps 20
```

## Workflow

### 1. 決定資料來源

- 先確認股票代號、公司名、檔名是否同一個標的
  未確認前不要分析
- 已有 `*_analysis.json`
  先檢查檔名或內容中的股票代號是否和使用者提供的一致；一致才餵給腳本
- 要補歷史股價
  先用 `fetch_price_history.py` 產出 `<stock_id>_<market>_price_history.json`
  目前只支援上市 `TWSE`，上櫃 `TPEx` 尚未接入官方日價 JSON
- 只有股票代碼
  先明確告知：repo 目前沒有 `analyze_tw_stock.py`
  若要找相對位置，現有腳本是 `../taiwan-stock-analysis/scripts/fetch_goodinfo.py`
  但它只會產出 `*_goodinfo_raw_data.json`，所以要先請使用者確認是否改走財報分析 skill，或直接提供 `*_analysis.json`
- 只有口頭假設
  直接用自訂 EPS 參數出估值表

### 2. 跑估值腳本

預設規則看 [references/methodology.md](references/methodology.md)。

優先用腳本，不要手算，避免不同回合出現不一致的區間。

如果使用者提供現價：

- 帶 `--current-price`
- 回報各情境下的 PER 與 `1–5 分`

如果使用者另外提供歷史股價 JSON：

- 帶 `--price-history-json`
- 回報近年收盤價區間
- 回報最近收盤在區間中的相對位置與百分位

如果使用者要求特定情境：

- 悲觀 EPS → `--pessimistic-eps`
- 中性 EPS → `--base-eps`
- 樂觀 EPS → `--optimistic-eps`

### 3. 回覆格式

預設輸出是 Markdown，可直接整理進最終回覆：

- 先給基準 EPS 與目前股價
- 若有歷史股價，再補近年區間與百分位
- 再列三種情境表
- 最後補一句總結：現價在不同情境下偏便宜、合理、或偏貴

若使用者只要結論，不要整份貼滿，摘出：

- 中性情境的 `1–5 分`
- 現價對應分數
- `140 以下 / 140–157 / 157–175 ...` 這類可執行區間

## Validation

至少做一個實跑驗證：

```bash
python3 skills/taiwan-stock-valuation-bands/scripts/build_valuation_report.py \
  --analysis-json 雄獅_2731_analysis.json \
  --current-price 163.5
```

確認：

- 三個情境都有輸出
- 每個情境都有 `1–5 分`
- 現價評分合理
- 沒有缺 EPS 的錯誤

## Resources

### `scripts/build_valuation_report.py`

- 讀取 `*_analysis.json`
- 僅在使用者已確認標的一致後才應執行
- 依最新年度 EPS 產出三情境估值帶
- 可帶入現價
- 可讀入 `fetch_price_history.py` 產出的歷史股價 JSON
- 可覆寫 EPS 情境
- 若只有 `--stock-id`，應要求明確提供 `--analyze-script`，不要假設 repo 內有 `analyze_tw_stock.py`
- 支援 `markdown` / `json`

### `scripts/fetch_price_history.py`

- 透過 TWSE 公開 `STOCK_DAY` 端點抓上市股票日價資料
- 預設輸出 `<stock_id>_<market>_price_history.json`
- 內含 `summary` 與逐日 `records`
- 目前僅支援上市 `TWSE`

### `references/methodology.md`

- 說明估值規則
- 說明 `1–5 分` 對應的 PER 帶
- 說明何時應改用自訂 EPS
