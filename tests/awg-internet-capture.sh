#!/usr/bin/env bash
# ==============================================================================
# AWG「连上没网」逐跳抓包定位
#
# 同时抓四个位置，一眼看出包在哪一段消失：
#   awgtest  —— 客户端 TUN，内层 ICMP 请求（应出现）
#   lo:55804 —— 客户端加密后的外层 UDP（应出现）
#   awg0     —— 服务端 TUN，解密后的内层 ICMP（应出现）
#   ens5     —— 出口网卡，NAT 后的 ICMP（应出现）
#
# 🔴 安全：客户端 AllowedIPs=0.0.0.0/0 + Table=off，只给 1.1.1.1 加 /32 路由，
#    不装默认路由（否则掐断 SSH）。
# ==============================================================================
set -uo pipefail

TEST_IF=awgtest
TEST_CONF=/etc/amnezia/amneziawg/${TEST_IF}.conf
PEER=${1:-client1}
AWG_PORT=$(jq -r '.port' /etc/amnezia/amneziawg/awg_meta.json)
WAN=$(ip -4 route show default | awk '{for(i=1;i<=NF;i++) if($i=="dev"){print $(i+1); exit}}')

command -v tcpdump >/dev/null 2>&1 || { echo "缺 tcpdump，尝试安装..."; apt-get install -y -qq tcpdump >/dev/null 2>&1 || { echo "装不上 tcpdump"; exit 2; }; }

cleanup() {
    [[ -n "${P1:-}" ]] && kill "$P1" 2>/dev/null
    [[ -n "${P2:-}" ]] && kill "$P2" 2>/dev/null
    [[ -n "${P3:-}" ]] && kill "$P3" 2>/dev/null
    [[ -n "${P4:-}" ]] && kill "$P4" 2>/dev/null
    ip route del 1.1.1.1/32 dev "$TEST_IF" 2>/dev/null || true
    awg-quick down "$TEST_IF" >/dev/null 2>&1 || true
    ip link delete "$TEST_IF" 2>/dev/null || true
    rm -f "$TEST_CONF"
}
trap cleanup EXIT

# 起客户端
rm -f "$TEST_CONF"
hy2-awgctl client-conf "$PEER" --endpoint 127.0.0.1 > "$TEST_CONF" 2>/dev/null || exit 2
sed -i 's|^AllowedIPs = .*|AllowedIPs = 0.0.0.0/0|' "$TEST_CONF"
sed -i '/^DNS = /d' "$TEST_CONF"
sed -i "s|^Endpoint = .*|Endpoint = 127.0.0.1:${AWG_PORT}|" "$TEST_CONF"
sed -i '/^\[Interface\]/a Table = off' "$TEST_CONF"
chmod 600 "$TEST_CONF"

WG_QUICK_USERSPACE_IMPLEMENTATION=/usr/local/bin/amneziawg-go \
    timeout 40 awg-quick up "$TEST_IF" >/dev/null 2>&1
ip link show "$TEST_IF" >/dev/null 2>&1 || { echo "客户端接口未建立"; exit 2; }
sleep 2
ip route add 1.1.1.1/32 dev "$TEST_IF"

echo "接口就绪，开始抓包..."
echo

# 起四个抓包点
tcpdump -i "$TEST_IF" -n -c 6 icmp > /tmp/cap_client.txt 2>&1 & P1=$!
tcpdump -i lo -n -c 6 "udp port ${AWG_PORT}" > /tmp/cap_udp.txt 2>&1 & P2=$!
tcpdump -i awg0 -n -c 6 icmp > /tmp/cap_awg0.txt 2>&1 & P3=$!
tcpdump -i "$WAN" -n -c 6 icmp > /tmp/cap_wan.txt 2>&1 & P4=$!
sleep 2

echo "=== 发 3 个 ping 到 1.1.1.1 ==="
ping -c 3 -W 3 1.1.1.1 2>&1 | tail -3

sleep 3
kill $P1 $P2 $P3 $P4 2>/dev/null
wait 2>/dev/null

for pair in "awgtest(客户端TUN):/tmp/cap_client.txt" "lo(加密UDP):/tmp/cap_udp.txt" "awg0(服务端TUN):/tmp/cap_awg0.txt" "$WAN(出口):/tmp/cap_wan.txt"; do
    name=${pair%%:*}; f=${pair#*:}
    n=$(grep -c "ICMP\|UDP" "$f" 2>/dev/null || echo 0)
    echo
    echo "--- $name  抓到 $n 个包 ---"
    grep -vE "^tcpdump:|^listening|^\s*$" "$f" 2>/dev/null | head -6 | sed 's/^/    /' || echo "    (空)"
done

echo
echo "=== 客户端/服务端计数器 ==="
awg show "$TEST_IF" transfer 2>/dev/null | sed 's/^/  客户端 transfer: /'
awg show awg0 transfer 2>/dev/null | sed 's/^/  服务端 peer transfer: /'
iptables -L FORWARD -v -n 2>/dev/null | grep "awg0" | sed 's/^/  FORWARD -i awg0: /'
