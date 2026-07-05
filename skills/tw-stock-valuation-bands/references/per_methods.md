# 四方法合理 PER

固定 `8–11x` PER 帶（見 [methodology.md](methodology.md)）對高 ROE、成長型或品質溢價股會系統性低估。此時改用 `scripts/estimate_per_methods.py`，用四種主流方法推導反映品質與成長的合理 PER。

四方法都寫成純公式，相同輸入必得相同輸出（`estimate_per_methods.py` 不連網、不含隨機或時間依賴的數值）。

## 資料來源

- 基準 EPS、各年度 EPS、ROE：`*_analysis.json` 的 `metrics_by_year`
- EPS 成長率：預設由 EPS 序列自動算 CAGR＝`(最新 EPS ÷ 最早 EPS)^(1/年差) − 1`
- 歷史 PER 序列（方法一）：`fetch_price_history.py` 的 `price_history_json`

## 四方法公式

### ① 歷史 PER 分位數法

以每日收盤 ÷ 當年度 EPS 得歷史 PER 序列，取 25th／50th／75th 分位（悲觀／中性／樂觀）。

- 需 `--price-history-json`；缺則標「資料不足」，請至 [Goodinfo 本益比河流](https://goodinfo.tw/tw/StockBzPerformance.asp?STOCK_ID=) 手動核實
- 近似：用年度 EPS，非季 TTM；分位數採線性插值（與 numpy 一致）

### ② PEG 法（Peter Lynch）

- 合理 PER = EPS 成長率（%），即 PEG=1.0
- 悲觀／樂觀＝PEG 0.8／1.2 帶
- `PEG = 現 PER ÷ 成長率`；<1 低估、≤1.2 合理、>1.2 高估
- **限制**：假設成長是唯一價值來源，對高 ROE 股（>20%）系統性低估，僅供估值下限

### ③ ROE 驅動法（Gordon Growth 衍生）

`P/B = (ROE − g) / (r − g)`，`PER = P/B ÷ ROE`

固定三情境（r 必要報酬、g 長期成長）：

| 情境 | r | g |
|------|---|---|
| 悲觀 | 13% | 7% |
| 中性 | 11% | 8% |
| 樂觀 | 10.5% | 8% |

- ROE 預設取最新年度；`--roe` 可覆寫（如文件用 0.39 進位值）
- **限制**：r 與 g 利差對結果極敏感，利差縮小 1% PER 可能翻倍；利差非正時該情境無解

### ④ Benjamin Graham 成長公式

- 合理 PER = `8.5 + 2g`（g 為整數 %）
- 中性 g＝四捨五入的 EPS CAGR；悲觀／樂觀＝中性 g ∓3
- `--bond-yield` 啟用完整版利率修正 `×(4.4 / 公債殖利率)`
- **限制**：簡化版未反映利率環境

## 方法選擇建議（SKILL 判斷依據）

腳本 `applicability` 依標的特質給 ★ 評分並標記建議方法；SKILL 據此建議、由使用者選定：

| 標的特質 | 優先方法 |
|----------|----------|
| 有歷史股價 JSON | ① 歷史分位數（最客觀） |
| 高 ROE（≥20%）、輕資產、品質溢價 | ③ ROE 驅動 |
| 一般成長股、ROE 10–20% | ② PEG 或 ④ Graham |
| 想要貼近市況的通用估計 | ④ Graham |
| 高 ROE 股 | ② PEG 僅供下限，不宜當中性依據 |

評分規則：

- 歷史分位數：有歷史股價 ★★★★★，否則 ★★（需手動核實）
- PEG：無正成長 ★，高 ROE ★★（僅下限），否則 ★★★★
- ROE 驅動：高 ROE ★★★★★，ROE 一般 ★★★，缺 ROE ★★
- Graham：有正成長 ★★★★，否則 ★★

## 套用流程

1. 跑 `estimate_per_methods.py`（`--output-format json` 供解析，或 `md` 給人看）
2. SKILL 呈現四方法彙整表與建議方法
3. 由使用者選定方法（建議用 AskUserQuestion）
4. 以選定方法的中性 PER × 基準 EPS 得合理價，樂觀／悲觀帶同理
5. 需寫回估值筆記時，用選定 PER 對應的合理價敘述；固定 1–5 分帶仍由 `build_valuation_report.py` 產出（兩者定位不同，可並列）
