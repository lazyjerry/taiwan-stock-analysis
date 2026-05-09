# AI 工具 資安掃描報告

```
╔══════════════════════════════════════════════════════╗
║           AI 工具 資安掃描報告                        ║
╠══════════════════════════════════════════════════════╣
║  掃描時間：2026-05-09                                 ║
║  掃描範圍：當前工作區                                  ║
║            taiwan-stock-analysis/                    ║
║  掃描項目：1 skill, 1 script, 2 reference/docs        ║
╚══════════════════════════════════════════════════════╝
```

## 風險摘要

| 嚴重性 | 數量 |
|--------|------|
| Critical | 0 |
| High | 0 |
| Medium | 0 |
| Low | 1 |

---

## 各項目掃描結果

### ✅ SKILL.md（無問題）

- **A 提示注入**：無覆寫系統指令、無身份偽冒、無隱藏觸發條件、無零寬字符
- **E 社交工程**：description 與實際流程高度一致，清楚說明三步驟（抓取 → 驗證 → 生成 HTML），無隱藏意圖
- **D 範圍蔓延**：僅存取 Goodinfo.tw 公開財報，無 `find /` 廣域掃描，未要求存取 `~/.ssh/` 等敏感路徑

### ✅ references/dashboard_template.md（無問題）

- 純 CSS / JS 模板，無動態執行指令
- Chart.js 來源：`cdn.jsdelivr.net`（主流 CDN，已知可信）
- `event.target.classList.add('active')` 使用全域 `event` 物件（屬前端慣用寫法，非安全問題）

### ✅ README.md（無問題）

- 純說明文件，無可執行邏輯

### ⚠️ scripts/fetch_goodinfo.py（發現 1 項低風險）

**[Low] 輸入驗證缺失 — 路徑穿越（Path Traversal）理論風險**

- 位置：第 206 行、第 259–261 行
- 內容：
  ```python
  stock_id = sys.argv[1] if len(sys.argv) > 1 else '2330'
  # ...
  out_file = f'{stock_id}_raw_data.json'
  with open(out_file, 'w', encoding='utf-8') as f:
  ```
- 說明：`stock_id` 直接來自 `sys.argv[1]`，若傳入 `../../etc/something` 之類的值，`open()` 呼叫會寫入非預期路徑。在 Skill 情境下 Claude 會傳入 4 位數股票代碼，實際觸發機率極低；但若腳本直接暴露給不可信使用者，建議加入格式驗證。

#### 問題根源

`stock_id` 從命令列輸入到 `open()` 之間沒有任何過濾，形成完整的攻擊鏈：

```
sys.argv[1]  →  stock_id  →  f'{stock_id}_raw_data.json'  →  open(out_file, 'w')
```

#### 攻擊情境

**情境一：覆寫 SSH 授權金鑰**

```bash
python fetch_goodinfo.py "../../.ssh/authorized_keys"
```

實際執行的 `open()` 路徑變成 `<工作目錄>/../../.ssh/authorized_keys_raw_data.json`。若工作目錄夠深，可覆寫 `~/.ssh/authorized_keys`，攻擊者植入自己的公鑰後即可取得 SSH 登入權限。

**情境二：覆寫專案設定檔**

```bash
python fetch_goodinfo.py "../.env"
```

將格式錯誤的 JSON 寫入 `../.env`，破壞上層專案的環境設定。

**情境三：URL 參數注入（次要）**

```python
# 第 32 行
url = f"...&STOCK_ID={stock_id}&REINIT=..."
```

若傳入 `2317&HACK=value`，URL 變成 `...&STOCK_ID=2317&HACK=value&REINIT=...`。對 Goodinfo.tw 影響有限，但若程式碼複用於其他場景風險會升高。

#### 為何在 Skill 情境下風險低

透過 Claude Skill 觸發時，`stock_id` 由 Claude 根據使用者說的股票代碼決定（例如「分析 2317」→ Claude 傳入 `2317`），Claude 本身不會傳入惡意路徑。**但前提是沒有人繞過 Skill 直接呼叫此腳本。**

#### 修補建議

**Option A：格式驗證（最少改動，推薦）**

```python
if __name__ == '__main__':
    import re
    raw = sys.argv[1] if len(sys.argv) > 1 else '2330'
    if not re.fullmatch(r'\d{4,6}', raw):
        sys.exit(f"錯誤：stock_id 必須為 4–6 位數字，收到：{raw!r}")
    stock_id = raw
```

**Option B：路徑正規化（防禦縱深）**

```python
import os, re

raw = sys.argv[1] if len(sys.argv) > 1 else '2330'
if not re.fullmatch(r'\d{4,6}', raw):
    sys.exit(f"錯誤：stock_id 必須為 4–6 位數字")
stock_id = raw

# 確保輸出檔只寫在當前目錄，即使正規表達式有漏洞也阻止跨目錄寫入
out_file = os.path.join(os.getcwd(), f'{stock_id}_raw_data.json')
```

---

## 遙測與追蹤分析

| 項目 | 結果 |
|------|------|
| 本地行為紀錄 | 無 |
| 遠端上傳 | 無（僅向 Goodinfo.tw 發送 GET 請求讀取公開數據） |
| 持久追蹤 ID | 無 |
| Opt-out 設計問題 | 不適用 |

---

## 總結建議

1. **整體安全性良好** — 無 Critical / High / Medium 問題，skill 行為與說明完全吻合
2. **Low 風險可選擇修補** — `fetch_goodinfo.py` 加入 4 位數字驗證可消除路徑穿越理論風險（約 2 行程式碼）
3. **資料流透明** — 只讀取 Goodinfo.tw 公開財報，輸出至本地 HTML/JSON，無任何外傳行為

---

> ⚠️ 本報告由 AI 自動產生，結果可能存在誤判（false positive）或遺漏（false negative）。所有發現皆需經人工核實與驗證，不應作為唯一的安全評估依據。
