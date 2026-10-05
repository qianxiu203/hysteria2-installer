#!/usr/bin/env bash
# ==============================================================================
# AmneziaWG 上网能力验证（客户端放在网络命名空间里）
#
# 为什么不用"客户端也跑在本机"的测法：
#   导出的客户端配置地址是 10.66.66.2，如果客户端就在同一台机器上，
#   这个地址就成了【本机地址】；服务端收到 src=本机地址 的包时，
#   在 accept_local=0（默认）下会按 martian source 丢掉 ——
#   于是"连上没网"，但这是测试假象，不是真实故障。
#   实测：把 accept_local 打开后 FORWARD 计数立刻从 0 涨到 189，
#   证明转发链路本身是通的。
#
# 正确做法：把客户端放进 network namespace —— 独立网络栈，等价于真实设备。
#   且默认路由的改动只发生在 netns 内，**绝不会影响本机 SSH**。
# ==============================================================================
set -uo pipefail

NS=awgcli
VETH_H=veth-awgh
VETH_C=veth-awgc
HOST_IP=10.200.200.1
CLI_IP=10.200.200.2
CONF_NAME=awgns
PEER=${1:-client1}

PASS=0; FAIL=0
ok()  { PASS=$((PASS+1)); echo "  [PASS] $*"; }
bad() { FAIL=$((FAIL+1)); echo "  [FAIL] $*"; }
info(){ echo "  [INFO] $*"; }
step(){ echo; echo "===== $* ====="; }

AWG_PORT=$(jq -r '.port' /etc/amnezia/amneziawg/awg_meta.json 2>/dev/null || echo "")

# 前置条件：本机必须已装好 AmneziaWG。
# ⚠️ 注意 tests/awg-e2e-smoke.sh 结尾会卸载 AWG（且 hy2-awgctl 会自删），
#    所以两个脚本连着跑时，请先跑本脚本、再跑 e2e 脚本。
if [[ -z "$AWG_PORT" ]]; then
    echo "❌ 本机尚未安装 AmneziaWG，无法测试上网。请先执行："
    echo "     bash install.sh awg-install --line 3 --endpoint <域名或公网IP>"
    echo "   然后重跑本脚本。"
    echo "   （提示：tests/awg-e2e-smoke.sh 结尾会卸载 AWG，两个脚本连着跑时请先跑本脚本）"
    exit 2
fi

cleanup() {
    ip netns exec $NS awg-quick down "$CONF_NAME" >/dev/null 2>&1 || true
    ip netns del $NS >/dev/null 2>&1 || true
    ip link del $VETH_H >/dev/null 2>&1 || true
    rm -f /etc/amnezia/amneziawg/${CONF_NAME}.conf
}
trap cleanup EXIT
cleanup

echo "服务端 AWG 端口: $AWG_PORT"

# ---------------------------------------------------------------- 1. 建 netns
step "1. 创建客户端网络命名空间"
ip netns add $NS
ip link add $VETH_H type veth peer name $VETH_C
ip link set $VETH_C netns $NS
ip addr add ${HOST_IP}/24 dev $VETH_H
ip link set $VETH_H up
ip netns exec $NS ip addr add ${CLI_IP}/24 dev $VETH_C
ip netns exec $NS ip link set $VETH_C up
ip netns exec $NS ip link set lo up
ok "netns $NS 已建立（$HOST_IP <-> $CLI_IP）"

# 确认 netns 能到服务端的 UDP 端口（外层隧道要能通）
if ip netns exec $NS ping -c 2 -W 2 $HOST_IP >/dev/null 2>&1; then
    ok "netns 能到宿主 $HOST_IP"
else
    bad "netns 到不了宿主"
fi

# ---------------------------------------------------------------- 2. 客户端配置
step "2. 在 netns 内配置客户端（完整隧道，AllowedIPs=0.0.0.0/0）"
CONF=/etc/amnezia/amneziawg/${CONF_NAME}.conf
hy2-awgctl client-conf "$PEER" --endpoint "${HOST_IP}" > "$CONF" 2>/dev/null || {
    bad "导出客户端配置失败"; exit 2; }
sed -i "s|^Endpoint = .*|Endpoint = ${HOST_IP}:${AWG_PORT}|" "$CONF"
sed -i '/^DNS = /d' "$CONF"
chmod 600 "$CONF"
info "AllowedIPs = $(grep '^AllowedIPs' "$CONF" | head -1 | cut -d= -f2- | xargs)"
info "Address    = $(grep '^Address' "$CONF" | head -1 | cut -d= -f2- | xargs)"
info "MTU        = $(grep '^MTU' "$CONF" | head -1 | cut -d= -f2- | xargs)"

# 在 netns 内起客户端（默认路由只改 netns 内部，不影响宿主）
if ip netns exec $NS env WG_QUICK_USERSPACE_IMPLEMENTATION=/usr/local/bin/amneziawg-go \
     timeout 40 awg-quick up "$CONF_NAME" >/tmp/nsup.log 2>&1; then
    ok "netns 内客户端接口已建立"
else
    bad "netns 内建立客户端接口失败"; tail -6 /tmp/nsup.log | sed 's/^/      /'; exit 2
fi
sleep 3

step "3. 隧道状态"
ip netns exec $NS awg show "$CONF_NAME" 2>/dev/null | grep -E "handshake|transfer|endpoint|allowed" | sed 's/^/  /'
info "netns 内路由:"; ip netns exec $NS ip -4 route | sed 's/^/    /'

# ---------------------------------------------------------------- 4. 关键测试
step "4. 🔴 经隧道访问公网（这才是「有没有网」）"
for ip in 1.1.1.1 8.8.8.8; do
    out=$(ip netns exec $NS ping -c 3 -W 4 "$ip" 2>&1)
    if echo "$out" | grep -qE '[1-3] received'; then
        ok "ping $ip 通 —— $(echo "$out" | grep -oE '[0-9]+ received')"
    else
        bad "ping $ip 不通"
        echo "$out" | tail -3 | sed 's/^/        /'
    fi
done

step "5. DNS 解析（经隧道查域名）"
if command -v dig >/dev/null 2>&1; then
    r=$(ip netns exec $NS dig +short +time=4 +tries=1 @1.1.1.1 example.com 2>&1 | head -2)
    if [[ -n "$r" ]]; then ok "经隧道 DNS 解析成功: $(echo $r | head -c 60)"; else bad "经隧道 DNS 解析失败"; fi
else
    info "无 dig，跳过"
fi

step "6. 服务端侧证据"
info "FORWARD -i awg0 计数（应 >0，说明包真的被转发了）:"
iptables -L FORWARD -v -n 2>/dev/null | grep "awg0" | sed 's/^/    /'
info "nat POSTROUTING -o $(ip -4 route show default | awk '{for(i=1;i<=NF;i++) if($i=="dev"){print $(i+1); exit}}') 计数:"
WAN=$(ip -4 route show default | awk '{for(i=1;i<=NF;i++) if($i=="dev"){print $(i+1); exit}}')
iptables -t nat -L POSTROUTING -v -n 2>/dev/null | grep -- "-o $WAN" | sed 's/^/    /'

echo
echo "================ 结果 ================"
echo "  通过: ${PASS}   失败: ${FAIL}"
