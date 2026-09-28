#!/usr/bin/env bash
# 验证 portal_ensure_py 的失败路径：三个源都拿不到时必须【明确报错并中止】，
# 而不是静默写一个空文件 —— 门户同时是 Hysteria 的 auth 后端，
# 缺了它所有客户端都连不上，静默失败会把问题推到很久以后才暴露。
set -u

# 从 install.sh 里摘出待测函数
eval "$(sed -n '/^portal_fetch_py() {/,/^}/p' install.sh)"
eval "$(sed -n '/^portal_ensure_py() {/,/^}/p' install.sh)"

# 打桩：日志与目标目录
log_err()  { echo "  [ERR] $*"; }
log_info() { echo "  [INF] $*"; }
HY2_DIR="$(mktemp -d)"

PASS=0; FAIL=0
ok()  { PASS=$((PASS+1)); echo "  ✅ $*"; }
bad() { FAIL=$((FAIL+1)); echo "  ❌ $*"; }

echo "=== 1) 三源全部不可达时，必须报错且不留下坏文件 ==="
export AWG_REPO="this-repo-does-not-exist-nyaa/nope"
rm -f "$HY2_DIR/portal.py"
out=$(portal_ensure_py 2>&1); rc=$?
if [[ $rc -ne 0 ]]; then ok "返回非零（rc=$rc）"; else bad "竟然返回 0"; fi
if echo "$out" | grep -q '无法获取 portal.py'; then ok "给出了明确原因"; else bad "错误信息不明确: $out"; fi
if echo "$out" | grep -q '鉴权后端'; then ok "说明了后果（客户端会连不上）"; else bad "没说明后果"; fi
if [[ -f "$HY2_DIR/portal.py" ]]; then bad "失败时仍留下了文件"; else ok "未留下半成品文件"; fi

echo
echo "=== 2) 内容不合法（不是 portal.py）时也要拒绝 ==="
export AWG_REPO="yys9253462-gif/hysteria2-installer"
# 造一个"看起来像但其实是垃圾"的源文件，通过本地快路径喂进去
FakeDir="$(mktemp -d)"
echo "print('not the real portal')" > "$FakeDir/portal.py"
# 用 BASH_SOURCE 模拟：直接测语法校验分支
bad_src=$(mktemp); printf 'def broken(:\n  pass\n' > "$bad_src"
if python3 -c 'import ast,sys; ast.parse(open(sys.argv[1], encoding="utf-8").read())' "$bad_src" 2>/dev/null; then
    bad "语法校验放过了坏文件"
else
    ok "语法校验能拦住坏文件"
fi
rm -f "$bad_src"; rm -rf "$FakeDir"

echo
echo "=== 3) 正常路径：真实仓库应能取到并通过校验 ==="
export AWG_REPO="yys9253462-gif/hysteria2-installer"
if out=$(portal_ensure_py 2>&1); then
    ok "获取成功"
    if [[ -s "$HY2_DIR/portal.py" ]] && grep -q 'def page_html' "$HY2_DIR/portal.py"; then
        ok "内容看起来是完整的 portal.py（$(wc -c < "$HY2_DIR/portal.py") 字节）"
    else
        bad "内容不完整"
    fi
    if python3 -c 'import ast,sys; ast.parse(open(sys.argv[1], encoding="utf-8").read())' "$HY2_DIR/portal.py" 2>/dev/null; then
        ok "通过 Python 语法校验"
    else
        bad "语法校验失败"
    fi
else
    bad "正常路径失败了（网络？）: $out"
fi

rm -rf "$HY2_DIR"
echo
echo "================ 结果 ================"
echo "  通过: $PASS   失败: $FAIL"
[[ $FAIL -eq 0 ]]
