---
name: tw-stock-valuation-bands
description: (Lazyjery 版本)當使用者要把台股財報分析接到股價、計算合理價、拆成悲觀/中性/樂觀三種價格區間、輸出 1-5 分估值評級，或建立估值報告時使用。優先讀取 `*_analysis.json`，用 `scripts/build_valuation_report.py` 產出報告；**預設寫入「Obsidian 當前開啟的檔案」**（Markdown，含 YAML frontmatter、基本資訊、三年財報摘要、估值帶、MOPS／證交所查核連結），亦可指定筆記路徑，或改輸出 HTML／JSON。
---

# Taiwan Stock Valuation Bands

## Overview

這個 skill 會把既有的 `*_analysis.json` 轉成估值報告，內容包含：

- 三種 EPS 情境
- `1-5 分` 價格區間與對應 PER
- 指定現價時的評分
- 若有歷史股價 JSON，補上近年收盤區間、區間位置、百分位
- 從財報分析 JSON 整理出的三年財報摘要

**預設輸出格式為 Markdown，並寫入「Obsidian 當前開啟的檔案」**（讀 `.obsidian/workspace.json` 的 active leaf），內容為固定格式：YAML frontmatter、基本資訊、三年財報摘要、估值情境（1–5 分帶）、官方／證交所查核連結。也可指定筆記路徑，或改用 `--output-format html｜json` 產出檔案。

分析前先確認股票代號、公司名稱、`*_analysis.json` 是否指向同一個標的。未確認前不要分析。

本 repo 目前沒有預設的 `analyze_tw_stock.py`。若使用者只有股票代號、沒有 `*_analysis.json`，先停下來要求明確資料來源，或改走 `tw-stock-analysis` skill 產出分析 JSON。

## Quick Start

1. 確認股票代號、公司名、`*_analysis.json` 檔名一致
2. 確認寫入目標：**預設寫入 Obsidian 當前開啟的檔案**；若該檔已有內容先問複寫或附加；使用者可改指定筆記路徑
3. 用 `scripts/build_valuation_report.py` 建立報告（預設 `--output-format md`）
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

### 2. 確認寫入目標與模式

執行前一定要處理寫入目標。**預設（`md` 格式）＝寫入 Obsidian 當前開啟的檔案**：

- 預設目標：Obsidian 當前開啟的檔案（腳本讀 `--vault-root/.obsidian/workspace.json` 的 `active` leaf，**不是** `lastOpenFiles[0]`）；偵測不到才建新筆記 `<代碼> <名稱> 估值.md`（如 `2330 台積電 估值.md`）
- 指定筆記路徑：帶 `--note-path <相對 vault 路徑>`
- 寫入模式：`--write-mode overwrite`（複寫，預設）｜ `append`（附加到檔尾，去重 frontmatter）｜ `newfile`（不動既有檔，改用 `<代碼> <名稱> 估值.md` 建立不重複的新筆記，自動改名）
- 新檔名帶「估值」後綴，與 `tw-stock-analysis` skill 的 `<代碼> <名稱>.md` 區隔，避免同一標的兩份報告撞名
- Vault 根目錄：`--vault-root <dir>`，預設當前目錄 `.`

**若當前開啟檔已有內容，先讓使用者三選一**，再傳對應 `--write-mode`：

1. 複寫（預設）→ `overwrite`
2. 附加到檔案尾端 → `append`
3. 建立新檔案（檔名自動改名，不覆蓋當前檔）→ `newfile`

原因：腳本非互動時遇非空檔預設複寫、不會停下來問；詢問由代理在呼叫前完成，以免覆蓋既有內容。

若要改輸出檔案（非 Obsidian）：

- HTML／JSON：帶 `--output-format html｜json`（此時不寫 Obsidian，改寫檔案）
- 自訂資料夾：帶 `--output-dir <dir>`（filename 由 analysis JSON 推導）
- 自訂完整檔名：帶 `--output-file <path>`

若使用者沒指定，回覆中要明講報告寫入了哪個檔案（當前開啟檔／指定路徑／新建檔）。

報告結構與命名規則看 [references/report_blueprint.md](references/report_blueprint.md)。

### 3. 執行估值腳本

估值邏輯看 [references/methodology.md](references/methodology.md)。
報告段落與整理方式看 [references/report_blueprint.md](references/report_blueprint.md)。

常用指令：

```bash
# 預設：md 寫入 Obsidian 當前開啟的檔案（vault 根目錄為當前目錄）
python3 skills/tw-stock-valuation-bands/scripts/build_valuation_report.py \
  --analysis-json 雄獅_2731_analysis.json \
  --current-price 163.5
```

```bash
# 附加到當前開啟檔（保留原內容）
python3 skills/tw-stock-valuation-bands/scripts/build_valuation_report.py \
  --analysis-json 雄獅_2731_analysis.json \
  --current-price 163.5 \
  --write-mode append
```

```bash
# 指定 Obsidian 筆記路徑（相對 vault 根）
python3 skills/tw-stock-valuation-bands/scripts/build_valuation_report.py \
  --analysis-json 台積電_2330_analysis.json \
  --current-price 950 \
  --price-history-json 2330_twse_price_history.json \
  --note-path "finances/2330 估值.md"
```

```bash
# 改輸出 HTML 檔案（非 Obsidian）
python3 skills/tw-stock-valuation-bands/scripts/build_valuation_report.py \
  --analysis-json 雄獅_2731_analysis.json \
  --pessimistic-eps 15 \
  --base-eps 17.5 \
  --optimistic-eps 20 \
  --output-format html \
  --output-file docs/report/雄獅_2731_custom_valuation.html
```

腳本行為：

- 讀取 `*_analysis.json`
- 預設 `md` 格式：寫入 Obsidian 當前開啟的檔案（含 YAML frontmatter、基本資訊、三年財報摘要、估值帶、查核連結）
- 帶 `--note-path` 可指定筆記路徑；`--write-mode append` 附加
- 帶 `--output-format html｜json` 改寫成檔案（配合 `--output-file`／`--output-dir`）
- 可帶現價與歷史股價 JSON

### 4. 回覆使用者

至少交代四件事：

- 報告寫入位置（Obsidian 當前開啟檔／指定筆記路徑／新建檔）與寫入模式
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
- 重新整理成三段，不直接複製 `tw-stock-analysis` skill 的原標題
- 優先用整理式詞彙，例如：
  - `營運規模與成本結構`
  - `獲利與股東報酬`
  - `資產負債與現金流`

每段至少要讓使用者看得到三年數列與變化方向，不只留下估值結論。

## Validation

至少做一個實跑驗證（用 `--note-path` 寫到臨時筆記，避免動到當前開啟檔）：

```bash
python3 skills/tw-stock-valuation-bands/scripts/build_valuation_report.py \
  --analysis-json 雄獅_2731_analysis.json \
  --current-price 163.5 \
  --note-path _tmp/雄獅_2731_valuation_test.md
```

確認：

- 報告檔有建立成功
- 檔案含 YAML frontmatter（`ticker`／`name`／`last_updated` 等）
- 三年財報摘要三段都有輸出
- 三個情境都有 `1-5 分` 價格帶
- 現價評分合理
- 有「官方／證交所查核連結」段落
- 沒有缺 EPS 的錯誤

（如需驗證 HTML 輸出，改帶 `--output-format html --output-file <path>`，確認含 `<!DOCTYPE html>` 與三個分頁。）

## Resources

### `scripts/build_valuation_report.py`

- 讀取 `*_analysis.json`
- 依最新年度 EPS 產出三情境估值帶
- 預設 `md` 格式，寫入 Obsidian 當前開啟的檔案（讀 `--vault-root/.obsidian/workspace.json`）
- `--note-path` 指定筆記路徑；`--write-mode overwrite｜append`
- `--output-format html｜json` 改寫檔案，配合 `--output-dir`／`--output-file`
- 可帶入現價
- 可讀入歷史股價 JSON
- 可覆寫 EPS 情境

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
