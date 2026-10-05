#!/usr/bin/env bash
# ==============================================================================
# 门户「更新面板」完整循环验证
#
# 验证用户的核心诉求：**推送更新后，Web 端能检测到并真的更新过去**。
#
# 步骤：
#   1. 确认起点：本地 portal.py 与 main 一致 → has_update 应为 false
#   2. 人为扰动本地文件（追加一行注释）→ has_update 应变 true
#   3. 调 do-upgrade target=portal → 应取回 main 的版本并原子替换
#   4. 确认收敛：本地内容与 main 逐字节一致、has_update 回到 false、服务仍 active
#
# 关键点：第 3 步必须拿到【新鲜】内容。raw.githubusercontent.com 有 CDN 缓存，
# 若走 raw 可能取回旧版，本测试就会在第 4 步失败 —— 这正是要防的回归。
# ==============================================================================
set -uo pipefail

HY2=/etc/hysteria
PORT=$(jq -r '.port' "$HY2/portal.json")
TOKEN=$(jq -r '.token' "$HY2/portal.json")
USER=$(jq -r '.username' "$HY2/portal-access.json")
PASS=$(jq -r '.password' "$HY2/portal-access.json")
BASE="http://127.0.0.1:${PORT}/${TOKEN}/"

PASS_CNT=0; FAIL_CNT=0
ok()  { PASS_CNT=$((PASS_CNT+1)); echo "  [PASS] $*"; }
bad() { FAIL_CNT=$((FAIL_CNT+1)); echo "  [FAIL] $*"; }
chk() { if [[ "$2" == "$3" ]]; then ok "$1 = $3"; else bad "$1 期望[$3] 实际[$2]"; fi; }
step(){ echo; echo "===== $* ====="; }

get()  { curl -sS -u "$USER:$PASS" -o /tmp/uc.out -w '%{http_code}' "$BASE$1"; }
post() { curl -sS -u "$USER:$PASS" -o /tmp/uc.out -w '%{http_code}' -X POST -d "$2" "$BASE$1"; }
jqv()  { jq -r "$1" /tmp/uc.out 2>/dev/null; }

# 直接问 GitHub 要 main 上 portal.py 的内容（权威源，不走 CDN 缓存）
fetch_remote_portal() {
    curl -fsSL --max-time 30 -H "Accept: application/vnd.github.raw" \
        "https://api.github.com/repos/yys9253462-gif/hysteria2-installer/contents/portal.py?ref=main" \
        -o "$1" 2>/dev/null && [[ -s "$1" ]]
}

echo "被测门户: ${BASE}"
echo "门户服务: $(systemctl is-active hysteria-portal)"

# ---------------------------------------------------------------- 1. 起点
step "1. 起点：本地应与 main 一致"
fetch_remote_portal /tmp/uc.remote || { echo "取不到远端 portal.py，无法测试"; exit 2; }
echo "  远端 main portal.py: $(stat -c%s /tmp/uc.remote) 字节, sha256=$(sha256sum /tmp/uc.remote | cut -c1-16)"
echo "  本地 portal.py     : $(stat -c%s "$HY2/portal.py") 字节, sha256=$(sha256sum "$HY2/portal.py" | cut -c1-16)"
if cmp -s /tmp/uc.remote "$HY2/portal.py"; then
    ok "起点一致（本地就是刚推送的版本）"
else
    bad "起点不一致 —— 请先把最新 portal.py 部署到本机再跑本测试"
fi
get check-version >/dev/null
chk "  起点 portal_has_update" "$(jqv '.portal_has_update')" "false"
START_SHA=$(jqv '.portal_current')
echo "  起点 portal_current: ${START_SHA}"

# ---------------------------------------------------------------- 2. 扰动
step "2. 人为扰动本地文件，模拟「本地落后于远端」"
printf '\n# __update_cycle_probe__\n' >> "$HY2/portal.py"
systemctl restart hysteria-portal >/dev/null 2>&1
sleep 2
chk "扰动后门户仍 active" "$(systemctl is-active hysteria-portal)" "active"
get check-version >/dev/null
chk "  扰动后 portal_has_update" "$(jqv '.portal_has_update')" "true"
echo "  portal_current=$(jqv '.portal_current')  portal_latest=$(jqv '.portal_latest')"
if [[ "$(jqv '.portal_current')" != "$(jqv '.portal_latest')" ]]; then
    ok "  本地与远端 sha 已不同（检测逻辑生效）"
else
    bad "  本地与远端 sha 相同，检测逻辑没生效"
fi

# ---------------------------------------------------------------- 3. 更新
step "3. 点击「一键更新面板」"
BEFORE_BAK=$([[ -f "$HY2/portal.py.bak" ]] && echo yes || echo no)
code=$(post do-upgrade "target=portal")
chk "POST do-upgrade target=portal → 200" "$code" "200"
echo "  响应: $(head -c 200 /tmp/uc.out)"
if jq -e '.ok == true' /tmp/uc.out >/dev/null 2>&1; then
    ok "  返回 ok=true（$(jqv '.message')）"
else
    bad "  返回异常"
fi

# 等服务重启完成
for i in $(seq 1 20); do
    sleep 1
    if systemctl is-active --quiet hysteria-portal; then
        # 再确认能真正响应请求（进程起来 ≠ 端口可用）
        if [[ "$(curl -sS -o /dev/null -w '%{http_code}' -u "$USER:$PASS" "${BASE}check-version")" == "200" ]]; then
            break
        fi
    fi
done
chk "更新后门户服务 active" "$(systemctl is-active hysteria-portal)" "active"

# ---------------------------------------------------------------- 4. 收敛
step "4. 确认收敛到已推送的版本"
if cmp -s /tmp/uc.remote "$HY2/portal.py"; then
    ok "本地 portal.py 与 main 逐字节一致（说明取到的是【新鲜】内容，没被 CDN 缓存挡住）"
else
    bad "本地 portal.py 与 main 不一致"
    echo "      本地 sha256: $(sha256sum "$HY2/portal.py" | cut -c1-16)"
    echo "      远端 sha256: $(sha256sum /tmp/uc.remote | cut -c1-16)"
    echo "      差异行数: $(diff /tmp/uc.remote "$HY2/portal.py" | wc -l)"
fi
if grep -q '__update_cycle_probe__' "$HY2/portal.py"; then
    bad "  扰动标记仍在，说明文件没被替换"
else
    ok "  扰动标记已被清除（文件确实被替换了）"
fi
if [[ -f "$HY2/portal.py.bak" ]]; then
    ok "  已留下 .bak 备份（可回滚）"
else
    bad "  未留下 .bak 备份"
fi
get check-version >/dev/null
chk "  收敛后 portal_has_update" "$(jqv '.portal_has_update')" "false"
echo "  portal_current=$(jqv '.portal_current')"

# 更新后功能仍正常
get awg-state >/dev/null
chk "  更新后 awg-state 仍 200" "$?" "0"

# ---------------------------------------------------------------- 5. AWG 引擎更新
step "5. 顺带验证 target=awg 的更新路径"
code=$(post do-upgrade "target=awg")
chk "POST do-upgrade target=awg → 200" "$code" "200"
if [[ -f /usr/local/bin/hy2-awgctl ]]; then
    REMOTE_AWG=/tmp/uc.awg
    if curl -fsSL --max-time 30 -H "Accept: application/vnd.github.raw" \
        "https://api.github.com/repos/yys9253462-gif/hysteria2-installer/contents/awgctl.sh?ref=main" \
        -o "$REMOTE_AWG" 2>/dev/null; then
        if cmp -s "$REMOTE_AWG" /usr/local/bin/hy2-awgctl; then
            ok "hy2-awgctl 与 main 逐字节一致"
        else
            bad "hy2-awgctl 与 main 不一致"
        fi
    fi
else
    bad "hy2-awgctl 不存在"
fi

rm -f /tmp/uc.out /tmp/uc.remote /tmp/uc.awg
echo
echo "================ 结果 ================"
echo "  通过: ${PASS_CNT}   失败: ${FAIL_CNT}"
[[ $FAIL_CNT -eq 0 ]] && echo "  全部通过" || echo "  存在问题，见上方 [FAIL]"
exit $(( FAIL_CNT > 0 ? 1 : 0 ))
