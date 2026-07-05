# 🇹🇼 台灣股票分析 Skills

這個 repo 目前包含三個以台股為核心的 skill：

- `tw-stock-analysis`：抓取 MOPS 官方財報，整理三維財務分析與結構化 JSON
- `tw-stock-valuation-bands`：把分析 JSON 轉成估值區間、1–5 分評級與合理 PER 比較
- `tw-stock-etf-constituent-lookup`：查詢台灣上市 ETF 的完整成分股並寫入 Obsidian

## Skills

### tw-stock-analysis

從 MOPS 取得最近 8 個可用年報與最新季報，整理經營分析、獲利分析、財務健全度，並提供後續估值所需的結構化資料。

涵蓋面向：

| 分頁 | 分析內容 |
|------|---------|
| 經營分析 | 營收成長、毛利率趨勢、管銷研費結構、費用率、營業利益率 |
| 獲利分析 | 稅後淨利、EPS、ROE、ROA、三層利潤率比較、現金股利 |
| 財務健全度 | 現金部位、流動比率、負債比率、營業現金流、自由現金流 |

### tw-stock-valuation-bands

接續財報分析結果，依 TTM（Trailing Twelve Months，最近十二個月）EPS 或最新年報 EPS 建立悲觀／中性／樂觀估值區間、1–5 分評級與分批建議。

可加入歷史股價區間與百分位，並比較歷史 PER 分位數、PEG、ROE 驅動與 Graham 成長公式。預設輸出至 Obsidian，也可保留結構化 JSON。

### tw-stock-etf-constituent-lookup

查詢任意台灣上市 ETF 的完整成分股，並產生標準化 Obsidian 筆記。CMoney API 為主要資料來源，MoneyDJ 提供基金名稱與備援資料。

## 使用範例

財報分析：

```text
幫我分析 2330 台積電
```

估值分析：

```text
幫我用 2317 的 analysis JSON 算估值區間，現價 163.5
```

ETF 成分股：

```text
幫我查 0050 的完整成分股
```

## 安裝 ai-global

若你要把這個 repo 的 skills 納入全域 AI 工具設定，建議先安裝你這個 fork 版本的 ai-global：

倉庫：<https://github.com/lazyjerry/ai-global>

前置需求：

- Node.js 14 以上可安裝 CLI
- 若要使用 tauri-gui，需 Node.js 18 以上與 Rust stable 1.75 以上

推薦安裝方式：

```bash
curl -fsSL https://raw.githubusercontent.com/lazyjerry/ai-global/main/install.sh | bash
```

也可用 npm：

```bash
npm install -g ai-global
```

其他套件管理器：

```bash
pnpm add -g ai-global
yarn global add ai-global
bun add -g ai-global
```

安裝後首次執行：

```bash
ai-global
```

這會掃描已安裝的 AI 工具、備份原始設定到 `~/.ai-global/backups/`，並建立共享設定的符號連結。

若要把 GitHub repo 加進全域 skills，可用：

```bash
ai-global add-skill lazyjerry/taiwan-stock-analysis
```

或：

```bash
ai-global add-skill https://github.com/lazyjerry/taiwan-stock-analysis
```

## 注意事項

- 財報與估值 skill 適用於台灣上市／上櫃公司
- ETF 成分股 skill 支援 4–8 位英數的台灣上市 ETF 代號
- 財報資料來源為 MOPS 官方財報頁；歷史股價資料來源為 TWSE／TPEx 公開日價 API
- ETF 成分股主來源為 CMoney API，MoneyDJ 提供基金名稱與備援資料
- 僅供財務學習與研究參考，不構成投資建議
