# Claude Code Skills - 股票觀察日記

此資料夾包含用於股票觀察日記 Obsidian 庫的自訂 skill 和工具。

## 已安裝的 Skills

### ETF 成分股查詢 (`tw-stock-etf-constituent-lookup`)

輸入「任意」台灣上市 ETF 代號，即時抓取**完整成分股**，自動寫入 Obsidian 筆記。

**檔案：**
- `SKILL.md` — Skill 入口（Claude Code 載入用，含 name / description frontmatter）
- `tw-stock-etf-constituent-lookup.sh` — 主執行 script（v5.0）
- `tw-stock-etf-constituent-lookup.yaml` — 舊版設定備份（非 Claude Code 標準格式，僅供參考，可刪除）
- `README.md` — 本文件

**支援範圍：** 任意台灣上市 ETF 代號（4-8 位英數，如 `0050`、`0056`、`00878`、`006208`、`00919`、`00632R`）。

**資料來源：** 主來源為**口袋證券（pocket.tw）背後的 CMoney API**（`GetDtnoData.ashx`，DtNo=59449513／M722），回傳 JSON **完整成分股**（0050 全 52 檔、00919 全 135 檔…），全發行商通用。MoneyDJ 用於取基金全名，並在 CMoney 回空時退回其前十大。另依代號自動附上發行商官方查核連結。

## 快速開始

### 基本用法

```bash
# 進入 Vault 目錄
cd /Users/lazyjerry/Library/Mobile\ Documents/iCloud~md~obsidian/Documents/股票觀察日記

# 查詢 0050，寫入 Obsidian 當前開啟的檔案（預設）
./.claude/skills/tw-stock-etf-constituent-lookup/tw-stock-etf-constituent-lookup.sh 0050

# 附加到當前開啟的檔案（保留原內容）
./.claude/skills/tw-stock-etf-constituent-lookup/tw-stock-etf-constituent-lookup.sh 0050 "" append

# 指定筆記位置
./.claude/skills/tw-stock-etf-constituent-lookup/tw-stock-etf-constituent-lookup.sh 0050 "finances/0050.md"
```

> **寫入目標**：省略路徑時，預設寫入 Obsidian 當前開啟的檔案（讀 `.obsidian/workspace.json` 的 active leaf）。若目標檔已有內容，透過 skill 使用時代理會先問要「複寫（預設）或附加」；直接用 CLI 且為互動終端時腳本會自行詢問，非互動則預設複寫並印警告。

### 輸出內容

自動生成的 Markdown 筆記包含：
- YAML 元數據（ticker、name、type、source、top_holdings、last_updated）
- 基本資訊表格（代碼、基金名稱、顯示持股數、資料來源、更新日期）
- 完整成分股表格（排名、股票代碼、名稱、權重(%)、持有股數）；CMoney 不可用時退回前十大
- 事實查核引用連結（reference-style，樣式 `[來源 xxx]`）：查詢用的 `[來源 MoneyDJ]` 放在持股表後；證交所／Yahoo／玩股網放在「事實查核」段供核對完整清單，連結定義集中於檔尾
- 時間戳記和數據聲明

## 特性

✓ **任意代號** — 不再寫死清單，任何台灣上市 ETF 皆可查
✓ **完整成分股** — 自 CMoney（口袋證券後端）取得全部持股與權重（非僅前十大）
✓ **固定輸出格式** — 避免 AI 執行時跑版
✓ **純文本控制台輸出** — 移除 ANSI 色碼，使用統一格式
✓ **安全錯誤處理** — 查無資料時報錯離開，不覆蓋既有筆記
✓ **模板化 Markdown** — 一致的筆記結構
✓ **Bash 兼容性** — 相容 macOS 預設 Bash 3.2
✓ **自動目錄建立** — 若筆記路徑不存在則自動創建
✓ **元數據支持** — YAML frontmatter 便於 Dataview 查詢

## 範例

```bash
./.claude/skills/tw-stock-etf-constituent-lookup/tw-stock-etf-constituent-lookup.sh 00878
# → 於 Vault 建立 [[00878 國泰永續高股息]]，含完整成分股表（34 檔）
```

## 技術細節

### 依賴

- Bash 3.2+（已驗證 macOS 預設版本）
- curl（抓取 CMoney API 與 MoneyDJ）
- python3（解析 CMoney 持股 JSON；解析 `.obsidian/workspace.json` 偵測當前開啟檔案；缺少則退回 MoneyDJ 前十大／建新筆記）
- 網路連線

### 架構

```
tw-stock-etf-constituent-lookup.sh
├─ 設定區段（配置、變數、EXIT 清理 trap）
├─ 輸出工具函數（純文字格式）
├─ 資料抓取與解析（fetch_cmoney_holdings / parse_cmoney_holdings；fetch_moneydj / parse_fund_name / parse_moneydj_holdings）
├─ Markdown 模板生成（generate_markdown_template / build_holdings_table）
└─ 主程序（main）
```

### 維護方式

不再有寫死的 ETF 清單——任意代號皆即時抓取。若 CMoney API 改版導致完整持股失效，調整 `fetch_cmoney_holdings()`（DtNo／ParamStr）與 `parse_cmoney_holdings()`（JSON 欄位索引）；若 MoneyDJ 改版導致名稱或備援失效，調整 `parse_fund_name()`（取 `<title>`）與 `parse_moneydj_holdings()`（抓 `col05`/`col06`/`col07`）。

### 資料來源

- **CMoney `GetDtnoData.ashx`（口袋證券後端）— 主來源／完整成分股**：`https://www.cmoney.tw/MobileService/ashx/GetDtnoData.ashx?action=getdtnodata&DtNo=59449513&ParamStr=AssignID=<代號>;MTPeriod=0;DTMode=0;DTRange=1;DTOrder=1;MajorTable=M722;&FilterNo=0` → JSON `{"Title":[...],"Data":[[日期,代碼,名稱,權重%,持有數,單位],...]}`。免特殊 header，壞代號回 `Data:[]`。
- [MoneyDJ 持股狀況](https://www.moneydj.com/etf/x/basic/basic0007.xdjhtm?etfid=0050.tw)：取**基金全名**；CMoney 回空時退回其**前十大**。
- 發行商官方（事實查核，`detect_issuer_link()` 依基金名稱判斷）：元大（per-code ratio）、國泰、富邦、群益、復華、中信投信
- [臺灣證券交易所 - 國內成分股ETF](https://www.twse.com.tw/zh/products/securities/etf/products/domestic.html)、[Yahoo 股市](https://tw.stock.yahoo.com/)、[玩股網](https://www.wantgoo.com/)（查核）

**逆向說明：** pocket.tw 的 ETF 區是獨立 Nuxt app（`/etf/_nuxt/`），持股由前端 `$stockFundholding` 服務打 CMoney `GetDtnoData.ashx`（`action=getdtnodata`）。頁面靜態 HTML 抓不到持股，但**直接打此 API 即可**取得完整成分股。CMoney 的 ETF「基本資料」表（DtNo=50826570）無法用 `AssignSPID` 依代號選取（固定回 0050），故名稱仍取自 MoneyDJ。證交所 OpenAPI／`mis all_etf.txt` 只有報價、無單一 ETF 完整成分股端點。

## 版本歷史

### v5.0 (2026-07-03)
- 重大：主來源改為口袋證券背後的 CMoney API（`GetDtnoData.ashx`），取得**完整成分股**（0050 全 52 檔、00919 全 135 檔），取代 MoneyDJ 前十大
- MoneyDJ 降為基金名稱來源＋CMoney 回空時的前十大備援；持股 JSON 以 python3 解析
- 筆記標題／基本資訊依實際來源標「完整成分股」或「前十大持股」；來源引用連結新增 `[來源 口袋證券]`
- 逆向記錄寫入 README（pocket.tw `/etf/_nuxt/` → CMoney 端點與參數）

### v4.0 (2026-07-03)
- 重大：預設寫入「Obsidian 當前開啟的檔案」（解析 `.obsidian/workspace.json` 的 active leaf；不是 `lastOpenFiles[0]`），偵測不到才建新筆記
- 新增：第三參數寫入模式 `overwrite`（複寫，預設）／ `append`（附加到檔尾，去除重複 frontmatter）
- 新增：目標檔已有內容時，互動 CLI 會詢問；非互動預設複寫並警告；SKILL.md 要求代理呼叫前先問使用者
- 依賴新增 `python3`（僅解析 workspace.json，缺少則退回建新筆記）

### v3.1 (2026-07-03)
- 新增：依基金名稱自動判斷發行商，於「事實查核」段附上發行商官方查核連結（`detect_issuer_link()`）
- 元大 ETF 官方連結指向 per-code ratio 頁（本身即含完整成分股）
- 評估並記錄 pocket.tw／證交所 API／Goodinfo 為何不採用

### v3.0 (2026-07-03)
- 重大：改為支援「任意」台灣上市 ETF 代號，移除寫死的 0050/0056 清單
- 新增：即時自 MoneyDJ 抓取並解析前十大持股（`fetch_html`/`parse_holdings`/`parse_fund_name`）
- 新增：查無資料時回傳非零離開碼，且不覆蓋既有筆記
- 修正：全形字元緊貼變數導致 bash 3.2 `unbound variable`（改用 `${var}`）
- 修正：`local` 暫存檔在 EXIT trap 中不可見的清理錯誤（改全域 + `cleanup` 防護）
- 修正：`pipefail` 下 `grep` 無匹配使錯誤路徑被 `set -e` 提前中止（加 `|| true`）

### v2.0 (2026-07-03)
- 改進：移除 ANSI 色碼，使用純文字格式
- 改進：統一控制台輸出風格
- 改進：完整的 Markdown 模板系統
- 改進：自動環境檢查和錯誤處理
- 優化：相容舊版 Bash（macOS 預設版本）

### v1.0.0 (2026-07-03)
- 首次發布
- 支持 0050、0056
- 自動筆記生成
- 基本網路驗證

## 問題排除

| 問題 | 解決方案 |
|------|--------|
| `command not found` | 確認 script 有執行權限：`chmod +x tw-stock-etf-constituent-lookup.sh` |
| `declare: -A: invalid option` | Bash 版本過舊，已在 v2.0 修復 |
| 網路連接失敗 | v3 無本地備援，會報錯並離開（不覆蓋既有筆記）；請檢查網路後重試 |
| 查無持股 / 代碼有誤 | 先於瀏覽器開啟 MoneyDJ 頁確認該代號存在；非上市 ETF 可能無資料 |
| 筆記未創建 | 檢查 Vault 路徑和寫入權限 |
| 輸出跑版 | 已在 v2.0 移除 ANSI 色碼和 emoji |

## 開發筆記

### 設計原則

1. **可重複性** — 同樣的輸入永遠產生相同的輸出
2. **健壯性** — 環境檢查、錯誤處理
3. **相容性** — 支援舊版 Bash 和 macOS
4. **可維護性** — 清晰的函數分層和註釋
5. **安全性** — 避免注入漏洞，嚴格輸入驗證

### 未來改進方向

- [x] 取得「完整」成分股清單（v5.0 已改接 CMoney／口袋證券後端）
- [ ] 成分股變化追蹤（比對前次筆記）
- [ ] 配息歷史統計
- [ ] 與 Dataview 的進階查詢範本

---

**最後更新：** 2026-07-03  
**維護者：** Claude Code  
**授權：** MIT
