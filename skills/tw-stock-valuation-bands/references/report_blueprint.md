# 估值報告結構

## 用途

這份規格提供 `build_valuation_report.py` 的報告輸出結構，讓主 skill 只保留流程與決策點。

## 報告寫入位置

**預設（`md` 格式）＝寫入 Obsidian 當前開啟的檔案**（讀 `--vault-root/.obsidian/workspace.json` 的 `active` leaf）：

- 預設：Obsidian 當前開啟的檔案；偵測不到才建新筆記 `<公司>_<代碼>_valuation.md`
- 指定筆記路徑：帶 `--note-path <相對 vault 路徑>`
- 寫入模式：`--write-mode overwrite`（複寫，預設）｜ `append`（附加，去重 frontmatter）｜ `newfile`（建立新檔，自動改名）
- Vault 根目錄：`--vault-root <dir>`（預設 `.`）

改輸出檔案（非 Obsidian）：

- HTML／JSON：帶 `--output-format html｜json`，配合 `--output-dir` 或 `--output-file`
- 檔名推導：`鴻海_2317_analysis.json` -> `鴻海_2317_valuation.{md｜html｜json}`

## 報告段落

### Markdown 報告（預設，寫入 Obsidian）固定結構

1. YAML frontmatter：`ticker`、`name`、`type: 個股`、`report: 估值區間`、`latest_year`、`base_eps`、`current_price`、`current_score`、`last_updated`
2. 基本資訊表：股票代碼、公司名稱、最新年度、基準 EPS、中性 3 分帶、目前股價、現價評分、更新日期
3. 三年財報摘要（三張表，見下方用語）
4. 估值情境（1–5 分價格帶）：悲觀 / 中性 / 樂觀 三張表，每張含價格區間、對應 PER、判讀；有現價時附現價 PER 與分數
5. 近年股價位置（若帶歷史股價 JSON）
6. 官方／證交所查核連結：MOPS（上市/上櫃）、證交所、Yahoo、Goodinfo

### HTML 報告分頁（`--output-format html`）

1. 估值總覽：公司名稱、股票代號、最新年度、基準 EPS、現價、歷史股價、三情境 EPS 與中性價格帶圖表
2. 財報整理：整理 `metrics_by_year`，用重寫過的段名，拆三張表
3. 情境明細：悲觀 / 中性 / 樂觀，各列 `1-5 分` 區間、對應 PER、判讀

代理在最終回覆中摘出中性情境區間、現價分數、偏便宜或偏貴判讀；若使用者只要摘要，不必整份貼出。

## 財報整理用語

報告段名與列名要偏整理式，不直接照抄 `tw-stock-analysis` skill：

- 可用：`營運規模與成本結構`
- 可用：`獲利與股東報酬`
- 可用：`資產負債與現金流`
- 避免直接寫成：`經營分析`、`獲利分析`、`財務健全度` 三個原標題

## 建議欄位

### 營運規模與成本結構

- 營收
- 毛利率
- 營業費用率
- 營業利益率

### 獲利與股東報酬

- 稅後淨利
- EPS
- ROE
- 現金股利

### 資產負債與現金流

- 現金部位
- 流動比率
- 負債比率
- 營業現金流
- 自由現金流
- 現金流 / 淨利

## 代理執行提醒

- 預設寫入 Obsidian 當前開啟的檔案；**若該檔已有內容，先讓使用者三選一**（複寫 `overwrite`／附加 `append`／建立新檔 `newfile`），再傳 `--write-mode`
- 使用者若指定筆記路徑，帶 `--note-path`，略過偵測
- 回覆中要明講報告寫入了哪個檔案（當前開啟檔／指定路徑／新建檔）與寫入模式
- 若改用 HTML／JSON，帶 `--output-format` 並在回覆中明講完整檔案路徑
- 若只有 `*_analysis.json` 沒有現價，照樣建立報告，只是不做現價評分
