#!/usr/bin/env bash
# ==============================================================================
# 门户按钮冒烟测试
#
# 逐个调用门户里每个按钮背后的端点，走【成功路径】而不只是验错误路径。
# 用法（在被测服务器上以 root 运行）:
#   bash tests/portal-buttons-smoke.sh
#
# ⚠️ 这是针对【测试机】的冒烟脚本：它会真的安装 AmneziaWG、创建/删除测试用户与
#    代理账号。不要在生产节点上跑。默认跳过 reboot-server 这类破坏性按钮。
# ==============================================================================
set -uo pipefail

HY2=/etc/hysteria
PORTAL_JSON="$HY2/portal.json"
ACCESS_JSON="$HY2/portal-access.json"

[[ -f "$PORTAL_JSON" && -f "$ACCESS_JSON" ]] || { echo "找不到门户配置，本机未安装？"; exit 2; }

PORT=$(jq -r '.port' "$PORTAL_JSON")
TOKEN=$(jq -r '.token' "$PORTAL_JSON")
USER=$(jq -r '.username' "$ACCESS_JSON")
PASS=$(jq -r '.password' "$ACCESS_JSON")
BASE="http://127.0.0.1:${PORT}/${TOKEN}/"
PUBLIC_IP=$(curl -4 -s --max-time 8 https://api.ipify.org || echo 127.0.0.1)

PASS_CNT=0; FAIL_CNT=0
ok()   { PASS_CNT=$((PASS_CNT+1)); echo "  [PASS] $*"; }
bad()  { FAIL_CNT=$((FAIL_CNT+1)); echo "  [FAIL] $*"; }
chk()  { if [[ "$2" == "$3" ]]; then ok "$1 = $3"; else bad "$1 期望[$3] 实际[$2]"; fi; }
step() { echo; echo "===== $* ====="; }

# 只打印状态码，响应体留在 /tmp/pb.out
get()  { curl -sS -u "$USER:$PASS" -o /tmp/pb.out -w '%{http_code}' "$BASE$1"; }
post() { curl -sS -u "$USER:$PASS" -o /tmp/pb.out -w '%{http_code}' -X POST -d "$2" "$BASE$1"; }
jqv()  { jq -r "$1" /tmp/pb.out 2>/dev/null; }

echo "被测门户: http://127.0.0.1:${PORT}  公网IP: ${PUBLIC_IP}"
echo "Hysteria2: $(systemctl is-active hysteria-server 2>/dev/null)  门户: $(systemctl is-active hysteria-portal 2>/dev/null)"

# ==============================================================================
step "第 1 轮：只读端点（页面加载时会自动调用）"
# ==============================================================================
for ep in check-version awg-state proxy-services warp-status bbr-status reality-status; do
    code=$(get "$ep")
    if [[ "$code" == "200" ]] && jq -e '.ok == true' /tmp/pb.out >/dev/null 2>&1; then
        ok "GET $ep → 200 ok=true"
    else
        bad "GET $ep → $code  $(head -c 120 /tmp/pb.out)"
    fi
done
code=$(get "traffic-speed")
chk "GET traffic-speed → 200" "$code" "200"

# ==============================================================================
step "第 2 轮：AWG 卡片按钮 —— 一键安装"
# ==============================================================================
# 先确保干净起点
if [[ -x /usr/local/bin/hy2-awgctl ]]; then
    /usr/local/bin/hy2-awgctl uninstall >/dev/null 2>&1 || true
    sleep 3
fi

code=$(post install-amneziawg "line=3&endpoint=${PUBLIC_IP}")
if [[ "$code" == "200" ]] && jq -e '.ok == true' /tmp/pb.out >/dev/null 2>&1; then
    ok "POST install-amneziawg → 200  $(jqv '.message')"
else
    bad "POST install-amneziawg → $code  $(head -c 200 /tmp/pb.out)"
fi
sleep 2
chk "安装后服务 active" "$(systemctl is-active amneziawg-server 2>/dev/null)" "active"
chk "awg0 接口存在" "$(ip link show awg0 >/dev/null 2>&1 && echo yes || echo no)" "yes"

# ==============================================================================
step "第 3 轮：AWG 卡片按钮 —— 状态与客户端管理"
# ==============================================================================
code=$(get awg-state)
chk "GET awg-state → 200" "$code" "200"
chk "  installed" "$(jqv '.installed')" "true"
chk "  active"    "$(jqv '.active')"    "true"
chk "  协议线"    "$(jqv '.line')"      "3"
AWG_PORT=$(jqv '.port')
echo "  监听端口: ${AWG_PORT}"
if [[ "$AWG_PORT" =~ ^[0-9]+$ ]] && (( AWG_PORT < 20000 || AWG_PORT > 40000 )); then
    ok "端口在跳跃区间之外"
else
    bad "端口 $AWG_PORT 落在 20000-40000 内"
fi
# 私钥绝不能下发
if grep -q 'private_key' /tmp/pb.out; then bad "awg-state 泄露了 private_key"; else ok "awg-state 未泄露私钥"; fi

# 新增客户端
# 注意：门户的「一键安装」不带 --client，awgctl 会按默认名建一个 client1，
# 所以这里基线是 1 个客户端而不是 0。
code=$(post manage-amneziawg "action=peer_add&name=webtest&endpoint=${PUBLIC_IP}")
chk "POST peer_add → 200" "$code" "200"
chk "  客户端数变为 2（含安装时的默认 client1）" "$(get awg-state >/dev/null; jqv '.peer_count')" "2"

# 下载配置
code=$(get "awg-conf?name=webtest")
chk "GET awg-conf → 200" "$code" "200"
if grep -q '\[Interface\]' /tmp/pb.out && grep -q 'PrivateKey' /tmp/pb.out && grep -q 'Endpoint' /tmp/pb.out; then
    ok "  .conf 内容完整（Interface / PrivateKey / Endpoint）"
else
    bad "  .conf 内容异常: $(head -c 200 /tmp/pb.out)"
fi
# 与 CLI 导出的一致性（两端参数必须一致，这里顺便交叉验证）
if command -v hy2-awgctl >/dev/null 2>&1; then
    hy2-awgctl client-conf webtest --endpoint "$PUBLIC_IP" > /tmp/pb.cli 2>/dev/null
    if diff -q <(grep -v '^#' /tmp/pb.out) <(grep -v '^#' /tmp/pb.cli) >/dev/null 2>&1; then
        ok "  门户导出与 CLI 导出完全一致"
    else
        bad "  门户导出与 CLI 导出不一致"
    fi
fi

# 二维码
code=$(get "awg-qr.svg?name=webtest")
chk "GET awg-qr.svg → 200" "$code" "200"
if head -c 200 /tmp/pb.out | grep -q '<svg'; then ok "  返回了 SVG"; else bad "  不是 SVG: $(head -c 120 /tmp/pb.out)"; fi

# ==============================================================================
step "第 4 轮：AWG 卡片按钮 —— 更新二进制 / 切换协议线"
# ==============================================================================
code=$(post manage-amneziawg "action=update")
chk "POST action=update → 200" "$code" "200"

code=$(post manage-amneziawg "action=set_line&line=2")
chk "POST action=set_line line=2 → 200" "$code" "200"
sleep 2
chk "  协议线已切到 2" "$(get awg-state >/dev/null; jqv '.line')" "2"
chk "  2.x 配置不含 HeaderProtectionKey" "$(grep -c '^HeaderProtectionKey' /etc/amnezia/amneziawg/awg0.conf)" "0"
chk "  切换后服务仍 active" "$(systemctl is-active amneziawg-server 2>/dev/null)" "active"

# ==============================================================================
step "第 5 轮：AWG 卡片按钮 —— 删除客户端"
# ==============================================================================
code=$(post manage-amneziawg "action=peer_del&name=webtest")
chk "POST action=peer_del → 200" "$code" "200"
chk "  客户端数回到 1" "$(get awg-state >/dev/null; jqv '.peer_count')" "1"
code=$(get "awg-conf?name=webtest")
chk "已删除的客户端导出 → 404" "$code" "404"

# ==============================================================================
step "第 6 轮：更新面板 —— 版本检测与目标校验"
# ==============================================================================
code=$(get check-version)
chk "GET check-version → 200" "$code" "200"
for k in core_current portal_current portal_latest portal_has_update awg_installed awg_current awg_latest awg_has_update; do
    if jq -e "has(\"$k\")" /tmp/pb.out >/dev/null 2>&1; then ok "  含字段 $k = $(jqv ".$k")"; else bad "  缺少字段 $k"; fi
done
if [[ "$(jqv '.portal_current')" == "未安装" || -z "$(jqv '.portal_current')" ]]; then
    bad "  portal_current 取值异常: $(jqv '.portal_current')"
else
    ok "  portal_current 是内容哈希前缀（不再是写死的日期）"
fi

code=$(post do-upgrade "target=invalid")
chk "POST do-upgrade 非法目标 → 400" "$code" "400"

code=$(post do-upgrade "target=awg")
chk "POST do-upgrade target=awg → 200" "$code" "200"

# ==============================================================================
step "第 7 轮：其它既有按钮抽查（可逆的走成功路径，不可逆的只做接线校验）"
# ==============================================================================
# 用户管理走的是表单 POST→302 重定向（Location: <prefix>#users），302 即成功
code=$(post manage-user "action=create&user_id=smoketest&duration_days=1&ip_limit=0&traffic_gb=0")
chk "POST manage-user create → 302" "$code" "302"
code=$(get "user-config?user_id=smoketest")
chk "GET user-config → 200" "$code" "200"
code=$(post manage-user "action=delete&user_id=smoketest")
chk "POST manage-user delete → 302" "$code" "302"

# 入站代理：建一个再删掉（自成一体的可逆操作）
code=$(post manage-proxy "action=create&type=socks5")
if [[ "$code" == "200" ]]; then
    ok "POST manage-proxy create → 200"
    PX_ID=$(jqv '.id // .port // ""')
    if [[ -n "$PX_ID" ]]; then
        code=$(post manage-proxy "action=delete&id=${PX_ID}")
        chk "POST manage-proxy delete → 200" "$code" "200"
    else
        bad "  创建返回里没有 id/port，无法删除"
    fi
else
    bad "POST manage-proxy create → $code $(head -c 150 /tmp/pb.out)"
fi

# WARP 规则：加一条探针域名再删掉（净零）。
code=$(post manage-warp "action=add_rule&domain=probe-smoketest.example")
if [[ "$code" == "200" ]]; then
    ok "POST manage-warp add_rule → 200"
    sleep 3
    chk "  加规则后 Hysteria 仍 active" "$(systemctl is-active hysteria-server 2>/dev/null)" "active"
    code=$(post manage-warp "action=del_rule&domain=probe-smoketest.example")
    chk "POST manage-warp del_rule → 200" "$code" "200"
    sleep 3
    get warp-status >/dev/null
    if jq -e '.rules | index("probe-smoketest.example")' /tmp/pb.out >/dev/null 2>&1; then
        bad "  探针域名未被清理干净"
    else
        ok "  探针域名已清理，规则恢复原状"
    fi
else
    bad "POST manage-warp add_rule → $code $(head -c 150 /tmp/pb.out)"
fi

# WARP 开关本身：这条路径会【真的重写 config.yaml 并重启 hysteria】，
# 也正是历史上把 Hysteria 打成 failed 的那条路径 ——
# 门户曾无条件往 ACL 里写 direct_ipv4(all)，而该出站可能已被
# toggle_warp.sh 连 outbounds 段一起删掉，于是 hysteria 启动即 FATAL：
#   invalid config: acl.inline: error at line N: outbound direct_ipv4 not found
# 所以必须真的点一次，并确认 hysteria 活着。
WARP_BEFORE=$(get warp-status >/dev/null; jqv '.enabled')
WARP_FLIP=$([[ "$WARP_BEFORE" == "true" ]] && echo false || echo true)
code=$(post manage-warp "action=toggle")
chk "POST manage-warp toggle → 200" "$code" "200"
sleep 6
chk "  ★ 切换后 Hysteria 仍 active（防「开关打挂服务」回归）" \
    "$(systemctl is-active hysteria-server 2>/dev/null)" "active"
chk "  WARP 状态已翻转" "$(get warp-status >/dev/null; jqv '.enabled')" "$WARP_FLIP"

# 切回原状态
code=$(post manage-warp "action=toggle")
sleep 6
chk "  ★ 再切回后 Hysteria 仍 active" "$(systemctl is-active hysteria-server 2>/dev/null)" "active"
chk "  WARP 状态已还原" "$(get warp-status >/dev/null; jqv '.enabled')" "$WARP_BEFORE"
if [[ "$(systemctl is-active hysteria-server 2>/dev/null)" != "active" ]]; then
    echo "      ⚠️ Hysteria 未恢复，尝试 reset-failed 后重启"
    systemctl reset-failed hysteria-server 2>/dev/null || true
    systemctl restart hysteria-server 2>/dev/null || true
fi

# Reality：本机没装 xray，用非法 action 做接线校验（期望 400 而非 500）
code=$(post manage-reality "action=__probe__")
chk "POST manage-reality 非法 action → 400" "$code" "400"

# 明确跳过（破坏性或重型，不在冒烟范围）
echo "  [SKIP] reboot-server（会重启整台机器）"
echo "  [SKIP] install-warp / install-xray / install-gost（重型安装，会扰动本机现有服务）"
echo "  [SKIP] set-bbr（会把本机从 cubic 切成 BBR，而界面没有「还原为 cubic」入口 —— 属真实配置变更）"

# ==============================================================================
step "第 8 轮：一键安装类按钮（重型，但必须真的能用）"
# ==============================================================================
# install-gost 曾经【必然失败】：处理函数里用了 os.chmod，而 `import os` 只出现在
# do_POST 的另一个分支（do-upgrade）里 —— Python 把 os 视为整个函数的局部名，
# 于是 gost 分支执行到 os.chmod 时抛 UnboundLocalError。更坑的是报错被后续
# 下载源的错误覆盖，界面上只显示一个无关的 DNS 失败。
# 现在所有 import 都提到模块级，这里做真实安装验证。
#
# 注意：这一步会真的下载 ~17MB 并安装 gost，属于重型操作。
code=$(post install-gost "")
chk "POST install-gost → 200" "$code" "200"
if [[ "$code" == "200" ]]; then
    chk "  gost 二进制已就位" "$([[ -x /usr/local/bin/gost ]] && echo yes || echo no)" "yes"
    sleep 2
    chk "  gost 服务 active" "$(systemctl is-active gost 2>/dev/null)" "active"
    chk "  gost 可执行" "$(/usr/local/bin/gost -V >/dev/null 2>&1 && echo ok || echo fail)" "ok"
else
    echo "      响应: $(head -c 300 /tmp/pb.out)"
fi

# install-xray：报成功时服务必须真的起来；报失败则必须说明原因。
# 修复前它会无条件回"安装成功，已在 TCP 443 就绪"，而 443 被 Caddy 占用时
# xray 根本起不来 —— 用户看到成功却怎么都用不了，也无从排查。
code=$(post install-xray "")
sleep 3
xr=$(systemctl is-active xray 2>/dev/null)
if [[ "$code" == "200" ]]; then
    chk "install-xray 报成功时 xray 必须真的 active" "$xr" "active"
else
    if grep -qE '未能启动|占用' /tmp/pb.out; then
        ok "install-xray 如实报错并说明了原因（xray 当前状态: $xr）"
    else
        bad "install-xray 失败但未说明原因: $(head -c 200 /tmp/pb.out)"
    fi
fi

# ==============================================================================
echo
echo "================ 结果 ================"
echo "  通过: ${PASS_CNT}   失败: ${FAIL_CNT}"
rm -f /tmp/pb.out /tmp/pb.cli
[[ $FAIL_CNT -eq 0 ]] && echo "  全部通过" || echo "  存在问题，见上方 [FAIL]"
exit $(( FAIL_CNT > 0 ? 1 : 0 ))
