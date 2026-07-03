---
name: tw-stock-etf-constituent-lookup
description: 查詢「任意」台灣上市 ETF（如 0050、0056、00878、006208、00919、00632R）的「完整成分股」，即時抓取口袋證券背後的 CMoney API，並在 Obsidian 庫中自動建立或更新標準化 Markdown 筆記。當使用者提到「查詢 ETF 成分股」、「ETF 成分股」、「某代號的成分股／持股」、「查詢 00XX」、「建立 ETF 筆記」時使用。
---

# ETF 成分股查詢

輸入任意台灣上市 ETF 代號，即時抓取**完整成分股**（0050 全 52 檔、00919 全 135 檔…），**預設寫入「Obsidian 當前開啟的檔案」**（而非另建新筆記），產生格式固定的內容（YAML frontmatter、基本資訊、完整持股表、官方／證交所查核連結）。

固定流程已封裝於本目錄的 `tw-stock-etf-constituent-lookup.sh`，**由腳本負責抓取、解析與寫檔**，代理負責解析代號、（必要時）詢問寫入方式、呼叫腳本、回報結果。

## 使用方式

在 Vault 根目錄執行（路徑含 skill 子目錄一層）：

```bash
./.claude/skills/tw-stock-etf-constituent-lookup/tw-stock-etf-constituent-lookup.sh <ETF代碼> [筆記路徑] [寫入模式]
```

- `<ETF代碼>`（必要）：任意台灣上市 ETF 代號，4-8 位英數，如 `0050`、`00878`、`006208`、`00632R`
- `[筆記路徑]`（選擇性）：自訂輸出位置（相對 `VAULT_ROOT`）。**省略＝寫入 Obsidian 當前開啟的檔案**（讀 `.obsidian/workspace.json` 的 active leaf）；偵測不到才建立新筆記 `<代碼> <名稱>.md`
- `[寫入模式]`（選擇性）：`overwrite`（複寫，預設）｜ `append`（附加到檔尾，會去除重複 frontmatter）
- 環境變數 `VAULT_ROOT`（選擇性）：Vault 根目錄，預設為當前目錄 `.`

範例：

```bash
# 寫入 Obsidian 當前開啟的檔案
./.claude/skills/tw-stock-etf-constituent-lookup/tw-stock-etf-constituent-lookup.sh 0050

# 附加到當前開啟的檔案（保留原內容）
./.claude/skills/tw-stock-etf-constituent-lookup/tw-stock-etf-constituent-lookup.sh 0050 "" append

# 指定路徑
./.claude/skills/tw-stock-etf-constituent-lookup/tw-stock-etf-constituent-lookup.sh 00878 "finances/00878.md"
```

## 寫入目標與模式（代理務必遵守）

1. 預設目標＝Obsidian 當前開啟的檔案（腳本自 `workspace.json` 偵測，取 `active` leaf，**不是** `lastOpenFiles[0]`）。
2. **若該檔已有內容，先詢問使用者**：複寫（預設）或附加到檔尾——再依回答傳入 `overwrite`／`append`。
   - 原因：腳本在非互動（被代理呼叫）情境下，遇到非空檔且未指定模式會**預設複寫**並僅印警告，不會停下來問。詢問這一步要由代理在呼叫前完成，以免覆蓋使用者既有內容。
   - 空白檔或新建檔可直接呼叫（預設複寫）。
3. 使用者若明確指定了某個檔案路徑，就用該路徑（第二參數），略過偵測。

## 資料來源與涵蓋範圍

- **主來源（完整成分股）**：口袋證券（pocket.tw）背後的 CMoney API `GetDtnoData.ashx`（`DtNo=59449513`、`MajorTable=M722`）。回傳 JSON 完整持股（日期、代碼、名稱、權重%、持有股數），任意代號皆可查，免特殊 header。
- **備援／名稱來源**：MoneyDJ 持股狀況頁（靜態 HTML）——用來取基金全名；當 CMoney 回空時退回其**前十大**。
- 事實查核用的引用連結（依基金名稱自動判斷發行商）：元大、國泰、富邦、群益、復華、中信投信官方頁 + 口袋證券 + MoneyDJ + 證交所國內成分股 ETF + Yahoo + 玩股網。
- 找不到資料（代碼有誤、非上市 ETF、來源改版）時回傳非零離開碼，並**不會覆蓋**既有筆記。

> pocket.tw 頁面本身是 Nuxt SPA、持股靜態抓不到；真正可用的是其前端呼叫的 CMoney `GetDtnoData.ashx` 端點（本 skill 即直接打此 API）。證交所 OpenAPI 無「單一 ETF 完整成分股」端點。

## 輸出

生成的 Markdown 筆記包含：

- YAML frontmatter（`ticker`、`name`、`type`、`source`、`holdings_count`、`last_updated`），便於 Dataview 查詢
- 基本資訊表格
- 完整成分股表格（排名、股票代碼、名稱、權重(%)、持有股數）；CMoney 不可用時退回前十大並於標題標明
- 事實查核用的引用連結（reference-style link，樣式 `[來源 xxx]`）：查詢所用的 `[來源 口袋證券]` 緊接在持股表後；「事實查核／其他來源」段放 `[來源 <發行商>投信官方]`（依代號判斷）+ 口袋證券／MoneyDJ／證交所／Yahoo／玩股網，連結定義集中於檔尾
- 時間戳與「資料以官網為準」聲明

## 依賴

- Bash 3.2+（相容 macOS 預設版本）
- `curl`（抓取 CMoney API 與 MoneyDJ）
- `python3`（解析 CMoney 持股 JSON；解析 `.obsidian/workspace.json` 偵測當前開啟檔案。缺少時完整持股與當前檔偵測會失效，退回 MoneyDJ 前十大／建立新筆記）
- 網路連線

## 備註

持股與權重為即時抓取，會隨市場調整；最新資料請以筆記內來源連結核對。若日後 CMoney API 改版，調整 `fetch_cmoney_holdings`／`parse_cmoney_holdings`；MoneyDJ 改版則調整 `parse_fund_name`／`parse_moneydj_holdings`。
