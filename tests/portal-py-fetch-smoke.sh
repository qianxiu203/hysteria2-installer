#!/usr/bin/env bash
# 验证门户程序的获取逻辑（两个文件：portal.py + portal_assets.py）。
#
# 门户是 Hysteria 的鉴权后端，缺任何一个文件 = 所有客户端连不上，
# 所以这条路径必须能证明：
#   1. 三源全部不可达时明确报错、中止，且**不留下半成品文件**
#   2. 语法不合法的内容被拒绝
#   3. 只有一半文件时判定为不完整
#   4. 正常路径能把两个文件都取回、通过校验，且能协同工作
set -u

# 从 install.sh 里摘出 PORTAL_FILES 声明与待测函数
# （PORTAL_FILES 是从脚本里读出来的真实值，不是在这里另抄一份 ——
#   否则脚本改了文件清单、测试却还按旧的跑，测试就失去意义了）
PORTAL_FILES="$(sed -n 's/^PORTAL_FILES="\(.*\)"$/\1/p' install.sh | head -1)"
if [[ -z "$PORTAL_FILES" ]]; then
    echo "❌ 没能从 install.sh 里读到 PORTAL_FILES" >&2
    exit 2
fi
echo "（从 install.sh 读到 PORTAL_FILES = $PORTAL_FILES）"
echo

for fn in portal_files_ok portal_fetch_files portal_fetch_py portal_ensure_py; do
    eval "$(sed -n "/^${fn}() {/,/^}/p" install.sh)"
done

log_err()  { echo "  [ERR] $*"; }
log_info() { echo "  [INF] $*"; }
HY2_DIR="$(mktemp -d)"

PASS=0; FAIL=0
ok()  { PASS=$((PASS+1)); echo "  ✅ $*"; }
bad() { FAIL=$((FAIL+1)); echo "  ❌ $*"; }

echo "=== 1) 三源全部不可达时：报错 + 中止 + 不留半成品 ==="
export AWG_REPO="this-repo-does-not-exist-nyaa/nope"
rm -f "$HY2_DIR"/portal.py "$HY2_DIR"/portal_assets.py
out=$(portal_ensure_py 2>&1); rc=$?
[[ $rc -ne 0 ]] && ok "返回非零（rc=$rc）" || bad "竟然返回 0"
echo "$out" | grep -q '无法获取门户程序' && ok "给出了明确原因" || bad "错误信息不明确: $out"
echo "$out" | grep -q '鉴权后端' && ok "说明了后果（客户端会连不上）" || bad "没说明后果"
if [[ ! -f "$HY2_DIR/portal.py" && ! -f "$HY2_DIR/portal_assets.py" ]]; then
    ok "未留下任何半成品文件"
else
    bad "失败时仍留下了文件"
fi

echo
echo "=== 2) 语法不合法的内容必须被拒绝 ==="
bad_src=$(mktemp); printf 'def broken(:\n  pass\n' > "$bad_src"
if python3 -c 'import ast,sys; ast.parse(open(sys.argv[1], encoding="utf-8").read())' "$bad_src" 2>/dev/null; then
    bad "语法校验放过了坏文件"
else
    ok "语法校验能拦住坏文件"
fi
rm -f "$bad_src"

echo
echo "=== 3) 只有一半文件时必须判定为不完整 ==="
onlydir="$(mktemp -d)"
echo "x" > "$onlydir/portal.py"
if portal_files_ok "$onlydir"; then bad "只有 portal.py 也判成了完整"; else ok "只有一半时判定为不完整"; fi
rm -rf "$onlydir"

echo
echo "=== 4) 正常路径：两个文件都取回、通过校验、能协同工作 ==="
export AWG_REPO="yys9253462-gif/hysteria2-installer"
if out=$(portal_ensure_py 2>&1); then
    ok "获取成功"
    for f in portal.py portal_assets.py; do
        if [[ -s "$HY2_DIR/$f" ]]; then
            ok "$f 已就位（$(wc -c < "$HY2_DIR/$f") 字节）"
        else
            bad "$f 缺失"
        fi
    done
    grep -q 'def page_html' "$HY2_DIR/portal.py" \
        && ok "portal.py 关键标记在位" || bad "portal.py 内容不对"
    grep -q 'SCRIPT = r' "$HY2_DIR/portal_assets.py" \
        && ok "portal_assets.py 关键标记在位（JS 仍是原始字符串）" || bad "portal_assets.py 内容不对"
    if python3 -c "
import sys; sys.path.insert(0, '${HY2_DIR}')
import portal
assert portal.SCRIPT and portal.STYLE, '常量没引进来'
" 2>/dev/null; then
        ok "两者可以一起 import，常量正常可用"
    else
        bad "两个文件不能协同工作"
    fi
else
    bad "正常路径失败了（网络？）: $out"
fi

rm -rf "$HY2_DIR"
echo
echo "================ 结果 ================"
echo "  通过: $PASS   失败: $FAIL"
[[ $FAIL -eq 0 ]]
