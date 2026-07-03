#!/bin/bash

################################################################################
# 台股分析報告 → Obsidian 筆記寫入工具 v1.0
#
# 用途：把「已產生好的 Markdown 報告內容」寫入 Obsidian 筆記。
#       報告內容由代理（Claude）依 SKILL.md 手寫並存成暫存檔，本腳本只負責
#       決定寫入目標（Obsidian 當前開啟檔）與寫入模式（複寫／附加）。
#
# 使用方式：
#   ./write_to_obsidian.sh <內容檔> [<筆記路徑>] [<寫入模式>] [<新建檔名>]
#
#   <內容檔>    必要；含完整 Markdown 報告的檔案（通常是暫存檔）
#   <筆記路徑>  選填；相對 VAULT_ROOT 的目標路徑。
#               省略＝寫入「Obsidian 當前開啟的檔案」（讀 .obsidian/workspace.json
#               的 active leaf）；偵測不到才建立新筆記 <新建檔名>
#   <寫入模式>  選填；overwrite（複寫，預設）｜ append（附加到檔尾，去重 frontmatter）
#               ｜ newfile（不動既有檔，改用新建檔名建立不重複的新筆記）
#   <新建檔名>  選填；未偵測到當前檔且未指定路徑時（或 newfile 時）的新筆記檔名，預設「台股分析報告.md」
#
#   環境變數 VAULT_ROOT：Vault 根目錄，預設當前目錄 .
#
# 範例：
#   ./write_to_obsidian.sh /tmp/report.md                       # 寫入當前開啟檔
#   ./write_to_obsidian.sh /tmp/report.md "" append             # 附加到當前開啟檔
#   ./write_to_obsidian.sh /tmp/report.md "finances/2330.md"    # 指定路徑
#
# 相容 macOS 預設 Bash 3.2；偵測當前開啟檔需 python3
################################################################################

set -euo pipefail

readonly VAULT_ROOT="${VAULT_ROOT:-.}"
readonly CONTENT_FILE="${1:-}"
readonly CUSTOM_NOTE_PATH="${2:-}"
readonly WRITE_MODE="${3:-}"
readonly FALLBACK_NAME="${4:-台股分析報告.md}"

print_info()    { printf "[INFO] %s\n" "$1"; }
print_success() { printf "[OK]   %s\n" "$1"; }
print_error()   { printf "[ERR]  %s\n" "$1" >&2; }
print_warn()    { printf "[WARN] %s\n" "$1"; }

usage() {
    cat << 'EOF'

用法：./write_to_obsidian.sh <內容檔> [<筆記路徑>] [<寫入模式>] [<新建檔名>]

  <內容檔>   含完整 Markdown 報告的檔案
  [筆記路徑] 選填；省略＝寫入 Obsidian 當前開啟的檔案，偵測不到才建新筆記
  [寫入模式] 選填；overwrite（複寫，預設）｜ append（附加到檔尾）｜ newfile（建立新檔，自動改名）
  [新建檔名] 選填；建新筆記時的檔名，預設「台股分析報告.md」

EOF
}

# 給定目標路徑，若已存在則在檔名尾端加「 (2)」「 (3)」…回傳不重複的新路徑
unique_path() {
    local base="$1" dir fname stem candidate n
    if [[ ! -e "$base" ]]; then
        printf '%s' "$base"
        return
    fi
    dir="$(dirname "$base")"
    fname="$(basename "$base")"
    stem="${fname%.md}"
    n=2
    while :; do
        candidate="${dir}/${stem} (${n}).md"
        if [[ ! -e "$candidate" ]]; then
            printf '%s' "$candidate"
            return
        fi
        n=$((n + 1))
    done
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

main() {
    if [[ -z "$CONTENT_FILE" ]]; then
        print_error "未提供內容檔"
        usage
        exit 1
    fi
    if [[ ! -f "$CONTENT_FILE" ]]; then
        print_error "內容檔不存在：$CONTENT_FILE"
        exit 1
    fi

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
            note_path="${VAULT_ROOT}/${FALLBACK_NAME}"
            print_info "筆記位置：${note_path}（未偵測到當前檔案，改建新筆記）"
        fi
    fi

    # ------- 決定寫入模式（複寫 / 附加 / 建立新檔）-------
    local mode="$WRITE_MODE" ans
    if [[ -z "$mode" ]]; then
        if [[ -s "$note_path" ]]; then
            if [[ -t 0 ]]; then
                printf '\n目標檔案已有內容：%s\n' "$note_path"
                printf '[o] 複寫（預設）  [a] 附加到檔尾  [n] 建立新檔案（自動改名）  [c] 取消 > '
                read -r ans || ans=""
                case "$ans" in
                    a|A) mode="append" ;;
                    n|N) mode="newfile" ;;
                    c|C) print_warn "已取消，未寫入"; exit 0 ;;
                    *)   mode="overwrite" ;;
                esac
            else
                mode="overwrite"
                print_warn "目標已有內容，非互動模式預設複寫（附加請傳 append，建立新檔請傳 newfile）"
            fi
        else
            mode="overwrite"
        fi
    fi

    # newfile：不動既有檔，改用新建檔名建立不重複的新筆記
    if [[ "$mode" == "newfile" ]]; then
        note_path="$(unique_path "${VAULT_ROOT}/${FALLBACK_NAME}")"
        print_info "改建立新檔案：${note_path}"
        mode="overwrite"
    fi

    local note_dir; note_dir="$(dirname "$note_path")"
    [[ "$note_dir" != "." ]] && mkdir -p "$note_dir"

    if [[ "$mode" == "append" ]]; then
        # 附加時去除 YAML frontmatter，避免與既有筆記重複
        {
            printf '\n'
            awk 'f>=2{print} /^---$/{f++}' "$CONTENT_FILE"
        } >> "$note_path"
        print_success "已附加報告到：$note_path"
    else
        cat "$CONTENT_FILE" > "$note_path"
        print_success "報告已複寫：$note_path"
    fi
}

main
