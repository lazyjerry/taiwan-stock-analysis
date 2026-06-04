# 🇹🇼 台灣股票分析 Skills

這個 repo 目前包含兩個以台股為核心的 skill：

- `taiwan-stock-analysis`：抓取 MOPS 官方財報頁資料，整理成三維財務分析結果
- `taiwan-stock-valuation-bands`：把既有分析結果轉成悲觀／中性／樂觀三種估值區間與 1–5 分評級

## Skills

### taiwan-stock-analysis

用途：輸入股票代號後，抓取公開財報數據，整理經營分析、獲利分析、財務健全度。

涵蓋面向：

| 分頁 | 分析內容 |
|------|---------|
| 經營分析 | 營收成長、毛利率趨勢、管銷研費結構、費用率、營業利益率 |
| 獲利分析 | 稅後淨利、EPS、ROE、ROA、三層利潤率比較、現金股利 |
| 財務健全度 | 現金部位、流動比率、負債比率、營業現金流、自由現金流 |

### taiwan-stock-valuation-bands

用途：把既有 `*_analysis.json` 轉成三種 EPS 情境的估值帶，並輸出 HTML 儀表板，內含 1–5 分價格區間、現價評分與分批建議。
若另外提供歷史股價 JSON，還會補上近年收盤價區間與百分位。

使用前提：

- 先和使用者確認股票代號、公司名稱、檔名是否為同一個標的
- 確認完成才分析
- 若只有股票代號、沒有 `*_analysis.json`，不要直接假設 repo 內有 `analyze_tw_stock.py`

## 資料流程

### 1. 財報抓取

從 repo 根目錄可執行：

```bash
python3 skills/taiwan-stock-analysis/scripts/fetch_goodinfo.py <stock_id>
```

這支腳本沿用舊檔名，但目前實際改由 MOPS 官方財報頁抓資料，會輸出 `<stock_id>_goodinfo_raw_data.json`。

若要把 raw JSON 轉成三分頁 HTML 儀表板：

```bash
python3 skills/taiwan-stock-analysis/scripts/build_analysis_dashboard.py \
    --raw-json <stock_id>_goodinfo_raw_data.json \
    --price-history-json <stock_id>_twse_price_history.json \
    --output <company>_<stock_id>_analysis.html
```

### 2. 估值計算

估值 skill 讀的是 `*_analysis.json`，不是 `*_goodinfo_raw_data.json`。

若要補歷史股價，可先抓上市股票的公開日價資料：

```bash
python3 skills/taiwan-stock-valuation-bands/scripts/fetch_price_history.py 2330 --months 36
```

預設會輸出 `<stock_id>_<market>_price_history.json`，例如 `2330_twse_price_history.json`。

```bash
python3 skills/taiwan-stock-valuation-bands/scripts/build_valuation_report.py \
    --analysis-json <company>_<stock_id>_analysis.json \
    --current-price 163.5
```

預設會輸出 `<company>_<stock_id>_valuation.html`。

若有歷史股價 JSON：

```bash
python3 skills/taiwan-stock-valuation-bands/scripts/build_valuation_report.py \
    --analysis-json <company>_<stock_id>_analysis.json \
    --current-price 163.5 \
    --price-history-json <stock_id>_<market>_price_history.json
```

若只提供股票代號，必須額外指定 `--analyze-script`。目前這個 repo 沒有內建預設的 `analyze_tw_stock.py`。
歷史股價抓取目前僅支援上市 `TWSE`，上櫃 `TPEx` 尚未接入官方日價 JSON。

## 專案結構

```text
taiwan-stock-analysis/
├── README.md
├── skills/
│   ├── taiwan-stock-analysis/
│   │   ├── SKILL.md
│   │   ├── references/
│   │   │   └── dashboard_template.md
│   │   └── scripts/
│   │       ├── build_analysis_dashboard.py
│   │       └── fetch_goodinfo.py
│   └── taiwan-stock-valuation-bands/
│       ├── SKILL.md
│       ├── references/
│       │   └── methodology.md
│       └── scripts/
│           ├── build_valuation_report.py
│           └── fetch_price_history.py
└── docs/
```

## 使用範例

財報分析：

```text
幫我分析 2330 台積電
```

估值分析：

```text
幫我用 2317 的 analysis JSON 算估值區間，現價 163.5
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

- 僅適用於台灣上市／上櫃公司（4 位數股票代碼）
- 財報資料來源為 MOPS 官方財報頁；歷史股價資料來源為 TWSE 公開日價 API
- 僅供財務學習與研究參考，不構成投資建議
- `fetch_goodinfo.py` 目前產出的是原始財報 JSON（`*_goodinfo_raw_data.json`）；估值 skill 需要的是分析後 JSON，兩者不要混用
