---
name: taiwan-stock-valuation-bands
description: (Lazyjery 版本)當使用者要把台股財報分析接到股價、計算合理價、拆成悲觀/中性/樂觀三種價格區間、輸出 1-5 分估值評級，或建立估值報告檔案時使用。優先讀取 `*_analysis.json`，並用 `scripts/build_valuation_report.py` 產出 HTML 或 JSON 報告。
---

# Taiwan Stock Valuation Bands

## Overview

這個 skill 會把既有的 `*_analysis.json` 轉成估值報告，內容包含：

- 三種 EPS 情境
- `1-5 分` 價格區間與對應 PER
- 指定現價時的評分
- 若有歷史股價 JSON，補上近年收盤區間、區間位置、百分位
- 從財報分析 JSON 整理出的三年財報摘要

分析前先確認股票代號、公司名稱、`*_analysis.json` 是否指向同一個標的。未確認前不要分析。

本 repo 目前沒有預設的 `analyze_tw_stock.py`。若使用者只有股票代號、沒有 `*_analysis.json`，先停下來要求明確資料來源，或改走 `taiwan-stock-analysis` skill 產出分析 JSON。

## Quick Start

1. 確認股票代號、公司名、`*_analysis.json` 檔名一致
2. 問使用者報告要放預設位置還是自訂位置
3. 用 `scripts/build_valuation_report.py` 建立報告
4. 若有現價，帶 `--current-price`
5. 若要補歷史股價，先用 `scripts/fetch_price_history.py` 產生 JSON，再帶 `--price-history-json`
6. 若使用者指定悲觀 / 中性 / 樂觀 EPS，改用覆寫參數

## Workflow

### 1. 確認資料來源

- 已有 `*_analysis.json`
  檢查檔名或內容中的股票代號是否和使用者提供的一致；一致才執行腳本
- 需要歷史股價
  先用 `fetch_price_history.py` 產出 `<stock_id>_<market>_price_history.json`
  目前只支援上市 `TWSE`
- 只有股票代號
  先明講 repo 沒有預設 `analyze_tw_stock.py`
  請使用者提供 `*_analysis.json`，或改走財報分析 skill
- 只有口頭假設
  可用自訂 EPS 參數產出估值表，但要先標明這不是從既有財報 JSON 推導

### 2. 確認報告位置

執行前一定要處理報告位置：

- 預設位置：和 `*_analysis.json` 同資料夾
- 自訂資料夾：帶 `--output-dir <dir>`
- 自訂完整檔名：帶 `--output-file <path>`

若使用者沒指定，回覆中要明講報告會建立在 `*_analysis.json` 同資料夾。

報告檔名規則看 [references/report_blueprint.md](references/report_blueprint.md)。

### 3. 執行估值腳本

估值邏輯看 [references/methodology.md](references/methodology.md)。
報告段落與整理方式看 [references/report_blueprint.md](references/report_blueprint.md)。

常用指令：

```bash
python3 skills/taiwan-stock-valuation-bands/scripts/build_valuation_report.py \
  --analysis-json 雄獅_2731_analysis.json \
  --current-price 163.5
```

```bash
python3 skills/taiwan-stock-valuation-bands/scripts/build_valuation_report.py \
  --analysis-json 台積電_2330_analysis.json \
  --current-price 950 \
  --price-history-json 2330_twse_price_history.json \
  --output-dir docs/report
```

```bash
python3 skills/taiwan-stock-valuation-bands/scripts/build_valuation_report.py \
  --analysis-json 雄獅_2731_analysis.json \
  --pessimistic-eps 15 \
  --base-eps 17.5 \
  --optimistic-eps 20 \
  --output-file docs/report/雄獅_2731_custom_valuation.html
```

腳本行為：

- 讀取 `*_analysis.json`
- 預設寫出報告檔
- HTML 報告會先整理三年財報，再列三種估值情境
- 可帶現價與歷史股價 JSON
- 可改輸出 `html` 或 `json`

### 4. 回覆使用者

至少交代四件事：

- 報告建立位置
- 基準 EPS 與中性情境區間
- 現價評分與偏便宜 / 合理 / 偏貴判讀
- 若有歷史股價，補近年區間位置與百分位

若使用者只要摘要，不要整份貼滿，摘出：

- 中性情境的 `1-5 分` 區間
- 現價對應分數
- 一句可執行判讀，例如 `149 以下才回到 2 分帶`

## Report Content Rules

報告不是只列估值帶，還要整理財報分析 JSON 內的原始指標。

- 直接使用 `metrics_by_year`
- 重新整理成三段，不直接複製 `taiwan-stock-analysis` skill 的原標題
- 優先用整理式詞彙，例如：
  - `營運規模與成本結構`
  - `獲利與股東報酬`
  - `資產負債與現金流`

每段至少要讓使用者看得到三年數列與變化方向，不只留下估值結論。

## Validation

至少做一個實跑驗證：

```bash
python3 skills/taiwan-stock-valuation-bands/scripts/build_valuation_report.py \
  --analysis-json 雄獅_2731_analysis.json \
  --current-price 163.5 \
  --output-file docs/report/雄獅_2731_valuation_test.html
```

確認：

- 報告檔有建立成功
- 檔案是完整 HTML，包含 `<!DOCTYPE html>` 與分頁區塊
- 財報整理三段都有輸出
- 三個情境都有 `1-5 分`
- 現價評分合理
- 沒有缺 EPS 的錯誤

## Resources

### `scripts/build_valuation_report.py`

- 讀取 `*_analysis.json`
- 依最新年度 EPS 產出三情境估值帶
- 預設把報告寫到 `*_analysis.json` 同資料夾
- 支援 `--output-dir` 與 `--output-file`
- 可帶入現價
- 可讀入歷史股價 JSON
- 可覆寫 EPS 情境
- 支援 `html` / `json`

### `scripts/fetch_price_history.py`

- 透過 TWSE 公開 `STOCK_DAY` 端點抓上市股票日價資料
- 預設輸出 `<stock_id>_<market>_price_history.json`
- 內含 `summary` 與逐日 `records`
- 目前僅支援上市 `TWSE`

### `references/methodology.md`

- 說明估值規則
- 說明 `1-5 分` 對應的 PER 帶
- 說明何時應改用自訂 EPS

### `references/report_blueprint.md`

- 說明報告建立位置規則
- 說明報告段落
- 說明財報整理用語與建議欄位
