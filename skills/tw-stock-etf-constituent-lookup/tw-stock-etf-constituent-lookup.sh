#!/bin/bash

################################################################################
# ETF 成分股查詢 & 筆記生成工具 v5.0
#
# 用途：查詢「任意」台灣上市 ETF 的成分股，寫入 Obsidian 筆記
#
# 資料來源：
#   主：口袋證券背後的 CMoney API（GetDtnoData.ashx，DtNo=59449513／M722）
#       回傳「完整成分股」清單（JSON），任意代號皆可查
#   輔／備援：MoneyDJ 持股狀況頁（取基金全名；CMoney 失敗時退回其前十大）
#
# 使用方式：
#   ./tw-stock-etf-constituent-lookup.sh <ETF代碼> [<筆記路徑>] [<寫入模式>]
#
#   <筆記路徑>：省略＝寫入「Obsidian 當前開啟的檔案」（讀 .obsidian/workspace.json
#               的 active leaf）；偵測不到才建立新筆記 <代碼> <名稱>.md
#   <寫入模式>：overwrite（複寫，預設）｜ append（附加到檔尾）
#
# 範例：
#   ./tw-stock-etf-constituent-lookup.sh 0050
#   ./tw-stock-etf-constituent-lookup.sh 0050 "" append
#   ./tw-stock-etf-constituent-lookup.sh 006208 "finances/006208.md" overwrite
#
# 相容 macOS 預設 Bash 3.2；持股 JSON 解析需 python3
################################################################################

set -euo pipefail

# ============================================================================
# 配置區段
# ============================================================================

readonly VAULT_ROOT="${VAULT_ROOT:-.}"
readonly ETF_CODE="${1:-}"
readonly CUSTOM_NOTE_PATH="${2:-}"
readonly WRITE_MODE="${3:-}"
readonly TODAY="$(date +%Y-%m-%d)"

readonly USER_AGENT="Mozilla/5.0"
readonly CMONEY_API="https://www.cmoney.tw/MobileService/ashx/GetDtnoData.ashx"
readonly CMONEY_DTNO_HOLDINGS=59449513
readonly POCKET_URL="https://www.pocket.tw/etf/tw/${ETF_CODE}/fundholding"
readonly MONEYDJ_URL="https://www.moneydj.com/etf/x/basic/basic0007.xdjhtm?etfid=${ETF_CODE}.tw"

# 暫存檔（供 EXIT trap 清理；用預設值防護 set -u）
html_file=""
cmoney_json=""
tsv_moneydj=""
tsv_cmoney=""
cleanup() {
    local f
    for f in "${html_file:-}" "${cmoney_json:-}" "${tsv_moneydj:-}" "${tsv_cmoney:-}"; do
        [[ -n "$f" ]] && rm -f "$f"
    done
    return 0
}
trap cleanup EXIT

# ============================================================================
# 輸出工具函數（純文字、避免跑版）
# ============================================================================

print_header() {
    cat << 'EOF'
================================================================================
  ETF 成分股查詢工具
================================================================================

EOF
}

print_info()    { printf "[INFO] %s\n" "$1"; }
print_success() { printf "[OK]   %s\n" "$1"; }
print_error()   { printf "[ERR]  %s\n" "$1" >&2; }
print_warn()    { printf "[WARN] %s\n" "$1"; }

print_section() {
    cat << EOF

$1
$(printf '%.0s-' {1..80})
EOF
}

print_footer() {
    cat << 'EOF'

================================================================================
EOF
}

usage() {
    cat << 'EOF'

用法：./tw-stock-etf-constituent-lookup.sh <ETF代碼> [<筆記路徑>] [<寫入模式>]

  <ETF代碼>  台灣上市 ETF 代號（任意），如 0050、00878、006208、00919
  [筆記路徑] 選填；省略＝寫入 Obsidian 當前開啟的檔案，偵測不到才建新筆記
  [寫入模式] 選填；overwrite（複寫，預設）｜ append（附加到檔尾）

範例：
  ./tw-stock-etf-constituent-lookup.sh 0050                  # 寫入當前開啟檔案
  ./tw-stock-etf-constituent-lookup.sh 0050 "" append        # 附加到當前開啟檔案
  ./tw-stock-etf-constituent-lookup.sh 00878 "finances/00878.md"

EOF
}

# ============================================================================
# 資料抓取與解析
# ============================================================================

# 主來源：CMoney（口袋證券）完整成分股，JSON 寫入指定檔
fetch_cmoney_holdings() {
    curl -s --max-time 15 -A "$USER_AGENT" \
        --data-urlencode "action=getdtnodata" \
        --data-urlencode "DtNo=${CMONEY_DTNO_HOLDINGS}" \
        --data-urlencode "ParamStr=AssignID=${ETF_CODE};MTPeriod=0;DTMode=0;DTRange=1;DTOrder=1;MajorTable=M722;" \
        --data-urlencode "FilterNo=0" \
        -G "$CMONEY_API" -o "$1"
}

# CMoney JSON → TSV：股票代碼 \t 名稱 \t 權重 \t 持有股數（千分位）
parse_cmoney_holdings() {
    command -v python3 &> /dev/null || return 0
    python3 - "$1" <<'PY' 2>/dev/null || true
import json, sys
try:
    d = json.load(open(sys.argv[1], encoding='utf-8'))
except Exception:
    sys.exit(0)
for r in (d.get("Data") or []):
    if len(r) >= 5:
        code, name, weight, shares = r[1], r[2], r[3], r[4]
        try:
            shares = "{:,}".format(int(float(shares)))
        except Exception:
            pass
        print("\t".join([str(code), str(name), str(weight), str(shares)]))
PY
}

# 備援來源：MoneyDJ 持股狀況頁（靜態 HTML）
fetch_moneydj() {
    curl -s --max-time 15 -A "$USER_AGENT" "$MONEYDJ_URL" -o "$1"
}

# 從 MoneyDJ HTML 取基金全名（<title>元大台灣50-ETF持股狀況 - MoneyDJ理財網</title>）
parse_fund_name() {
    grep -oE '<title>[^<]*' "$1" | head -1 \
        | sed -e 's/<title>//' -e 's/-ETF持股狀況.*//' -e 's/^ *//' -e 's/ *$//'
}

# 從 MoneyDJ HTML 解析前十大持股 → TSV：股票代碼 \t 名稱 \t 權重 \t 持有股數
parse_moneydj_holdings() {
    sed 's/<td/\n<td/g' "$1" \
        | grep -E "class=[\"']col0[567]" \
        | sed -E 's/<[^>]*>//g; s/^ *//; s/ *$//' \
        | paste - - - \
        | awk -F'\t' 'NF>=3{
            raw=$1; code="-"; name=raw;
            p=index(raw,"(");
            if(p>0){ name=substr(raw,1,p-1); rest=substr(raw,p+1); q=index(rest,"."); code=(q>0?substr(rest,1,q-1):rest) }
            printf "%s\t%s\t%s\t%s\n", code, name, $2, $3
        }'
}

# 解析 Obsidian 當前開啟的檔案（.obsidian/workspace.json 的 active leaf）
# 輸出相對 vault 的 .md 路徑；偵測不到則不輸出
resolve_active_file() {
    local ws="${VAULT_ROOT}/.obsidian/workspace.json"
    [[ -f "$ws" ]] || return 0
    command -v python3 &> /dev/null || return 0
    python3 - "$ws" <<'PY' 2>/dev/null || true
import json, sys
try:
    d = json.load(open(sys.argv[1], encoding='utf-8'))
except Exception:
    sys.exit(0)
active = d.get('active')
found = [None]
def walk(n):
    if isinstance(n, dict):
        if n.get('type') == 'leaf' and n.get('id') == active:
            st = n.get('state', {})
            if st.get('type') == 'markdown':
                found[0] = st.get('state', {}).get('file')
        for v in n.values():
            walk(v)
    elif isinstance(n, list):
        for v in n:
            walk(v)
for k in ('main', 'left', 'right'):
    walk(d.get(k, {}))
f = found[0]
if f and f.endswith('.md'):
    print(f)
PY
}

# 依基金名稱前綴判斷發行商，輸出「官方標籤<TAB>官方URL」；未知則不輸出
detect_issuer_link() {
    local name="$1" code="$2"
    case "$name" in
        元大*)          printf '元大投信官方\thttps://www.yuantaetfs.com/product/detail/%s/ratio' "$code" ;;
        國泰*)          printf '國泰投信官方\thttps://www.cathaysite.com.tw/funds/etf/list' ;;
        富邦*)          printf '富邦投信官方\thttps://www.fubon.com/asset-management/etf/' ;;
        群益*)          printf '群益投信官方\thttps://www.capitalfund.com.tw/CFWeb/apply/etf.aspx' ;;
        復華*)          printf '復華投信官方\thttps://www.fhtrust.com.tw/etf/' ;;
        中信*|中國信託*) printf '中信投信官方\thttps://www.ctbcinvestments.com.tw/ETF/' ;;
        *)              : ;;
    esac
}

# 把 4 欄 TSV（代碼｜名稱｜權重｜股數）轉為 Markdown 表格列
build_holdings_table() {
    local f="$1" rank=1 code name weight shares
    while IFS=$'\t' read -r code name weight shares; do
        [[ -z "${code}${name}" ]] && continue
        printf '| %d | %s | %s | %s | %s |\n' "$rank" "$code" "$name" "$weight" "$shares"
        rank=$((rank + 1))
    done < "$f"
}

# ============================================================================
# Markdown 模板生成
# ============================================================================

# 參數：code name count scope_label table primary_ref source_tag factcheck_links extra_refs
generate_markdown_template() {
    local etf_code="$1" etf_name="$2" count="$3" scope_label="$4" table="$5"
    local primary_ref="$6" source_tag="$7" factcheck_links="$8" extra_refs="$9"

    cat << EOF
---
ticker: $etf_code
name: $etf_name
type: ETF
source: $source_tag
holdings_count: $count
last_updated: $TODAY
---

# $etf_code $etf_name

## 基本資訊

| 項目 | 內容 |
|------|------|
| **ETF 代碼** | $etf_code |
| **基金名稱** | $etf_name |
| **成分股** | ${count} 檔（${scope_label}） |
| **資料來源** | [來源 ${primary_ref}] |
| **更新日期** | $TODAY |

## ${scope_label}（${count} 檔）

| 排名 | 股票代碼 | 名稱 | 權重(%) | 持有股數 |
|------|---------|------|---------|---------|
$table

資料來源：[來源 ${primary_ref}]（${scope_label}，$TODAY 抓取）

## 事實查核 / 其他來源

依代號自動附上發行商官方頁與其他查核來源：
$factcheck_links

---

**最後更新：** $TODAY

**注**：本筆記由自動化工具即時抓取生成；持股與權重會隨市場調整，最新資料請點上方來源核對。

<!-- 引用連結定義（reference-style links） -->
[來源 口袋證券]: $POCKET_URL
[來源 MoneyDJ]: $MONEYDJ_URL
[來源 臺灣證券交易所]: https://www.twse.com.tw/zh/products/securities/etf/products/domestic.html
[來源 Yahoo 股市]: https://tw.stock.yahoo.com/quote/${etf_code}.TW
[來源 玩股網]: https://www.wantgoo.com/stock/etf/${etf_code}/constituent
$extra_refs
EOF
}

# ============================================================================
# 主程序
# ============================================================================

main() {
    print_header

    # 驗證輸入
    if [[ -z "$ETF_CODE" ]]; then
        print_error "未提供 ETF 代碼"
        usage
        print_footer
        exit 1
    fi
    if ! [[ "$ETF_CODE" =~ ^[0-9A-Za-z]{4,8}$ ]]; then
        print_error "ETF 代碼格式不正確：${ETF_CODE}（預期 4-8 位英數，如 0050、00878、00632R）"
        print_footer
        exit 1
    fi

    print_info "ETF 代碼：$ETF_CODE"

    # 檢查 curl
    print_section "檢查環境"
    if ! command -v curl &> /dev/null; then
        print_error "缺少 curl 工具"
        print_footer
        exit 1
    fi
    print_success "curl 可用"

    # ------- 抓取資料 -------
    print_section "抓取持股資料"

    # 名稱（與備援前十大）取自 MoneyDJ
    html_file="$(mktemp -t etf_moneydj.XXXXXX)"
    fetch_moneydj "$html_file" || true
    local etf_name; etf_name="$(parse_fund_name "$html_file" || true)"
    tsv_moneydj="$(mktemp -t etf_mdj.XXXXXX)"
    parse_moneydj_holdings "$html_file" > "$tsv_moneydj" || true
    local moneydj_count; moneydj_count="$(grep -c . "$tsv_moneydj" || true)"

    # 完整成分股取自 CMoney（口袋證券）
    cmoney_json="$(mktemp -t etf_cm.XXXXXX)"
    fetch_cmoney_holdings "$cmoney_json" || true
    tsv_cmoney="$(mktemp -t etf_cmtsv.XXXXXX)"
    parse_cmoney_holdings "$cmoney_json" > "$tsv_cmoney" || true
    local cmoney_count; cmoney_count="$(grep -c . "$tsv_cmoney" || true)"

    # 決定使用來源：CMoney 完整優先，否則退回 MoneyDJ 前十大
    local data_tsv count scope_label primary_ref source_tag
    if [[ "$cmoney_count" -gt 0 ]]; then
        data_tsv="$tsv_cmoney"; count="$cmoney_count"
        scope_label="完整成分股"; primary_ref="口袋證券"; source_tag="pocket.tw/CMoney"
    else
        data_tsv="$tsv_moneydj"; count="$moneydj_count"
        scope_label="前十大持股"; primary_ref="MoneyDJ"; source_tag="MoneyDJ"
    fi
    [[ -z "$etf_name" ]] && etf_name="$ETF_CODE"

    if [[ "$count" -eq 0 ]]; then
        print_error "查無 $ETF_CODE 的成分股（可能非上市 ETF、代碼有誤，或來源改版）"
        print_info "可先於瀏覽器確認：$POCKET_URL"
        print_footer
        exit 1
    fi
    print_success "已取得：${etf_name}（${count} 檔，${scope_label}，來源 ${primary_ref}）"

    # ------- 決定筆記路徑：明確路徑 > Obsidian 當前開啟檔案 > 新建 -------
    local note_path active_rel
    if [[ -n "$CUSTOM_NOTE_PATH" ]]; then
        note_path="${VAULT_ROOT}/${CUSTOM_NOTE_PATH}"
        print_info "筆記位置：${note_path}（指定路徑）"
    else
        active_rel="$(resolve_active_file)"
        if [[ -n "$active_rel" ]]; then
            note_path="${VAULT_ROOT}/${active_rel}"
            print_info "筆記位置：${note_path}（Obsidian 當前開啟檔案）"
        else
            note_path="${VAULT_ROOT}/${ETF_CODE} ${etf_name}.md"
            print_info "筆記位置：${note_path}（未偵測到當前檔案，改建新筆記）"
        fi
    fi

    # ------- 事實查核連結（reference-style）-------
    local issuer_line issuer_label issuer_url factcheck_links extra_refs
    issuer_line="$(detect_issuer_link "$etf_name" "$ETF_CODE")"
    factcheck_links="[來源 口袋證券] · [來源 MoneyDJ] · [來源 臺灣證券交易所] · [來源 Yahoo 股市] · [來源 玩股網]"
    extra_refs=""
    if [[ -n "$issuer_line" ]]; then
        issuer_label="${issuer_line%%$'\t'*}"
        issuer_url="${issuer_line##*$'\t'}"
        factcheck_links="[來源 ${issuer_label}] · ${factcheck_links}"
        extra_refs="[來源 ${issuer_label}]: ${issuer_url}"
    fi

    # ------- 生成筆記內容 -------
    print_section "生成筆記"
    local table; table="$(build_holdings_table "$data_tsv")"
    local content
    content="$(generate_markdown_template \
        "$ETF_CODE" "$etf_name" "$count" "$scope_label" "$table" \
        "$primary_ref" "$source_tag" "$factcheck_links" "$extra_refs")"

    # ------- 決定寫入模式（複寫 / 附加）-------
    local mode="$WRITE_MODE" ans
    if [[ -z "$mode" ]]; then
        if [[ -s "$note_path" ]]; then
            if [[ -t 0 ]]; then
                printf '\n目標檔案已有內容：%s\n' "$note_path"
                printf '[o] 複寫（預設）  [a] 附加到檔尾  [c] 取消 > '
                read -r ans || ans=""
                case "$ans" in
                    a|A) mode="append" ;;
                    c|C) print_warn "已取消，未寫入"; print_footer; exit 0 ;;
                    *)   mode="overwrite" ;;
                esac
            else
                mode="overwrite"
                print_warn "目標已有內容，非互動模式預設複寫（要附加請傳第三參數 append）"
            fi
        else
            mode="overwrite"
        fi
    fi

    local note_dir; note_dir="$(dirname "$note_path")"
    [[ "$note_dir" != "." ]] && mkdir -p "$note_dir"

    if [[ "$mode" == "append" ]]; then
        # 附加時去除 YAML frontmatter，避免與既有筆記重複
        {
            printf '\n'
            printf '%s\n' "$content" | awk 'f>=2{print} /^---$/{f++}'
        } >> "$note_path"
        print_success "已附加 ETF 區塊到：$note_path"
    else
        printf '%s\n' "$content" > "$note_path"
        print_success "筆記已複寫：$note_path"
    fi

    print_section "操作完成"
    cat << EOF

筆記已建立/更新：
  $note_path

後續步驟：
  1. 於 Obsidian 開啟：[[$ETF_CODE $etf_name]]
  2. 核對來源最新資料：$POCKET_URL

EOF
    print_footer
}

main
