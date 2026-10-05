#!/usr/bin/env bash
# ==============================================================================
# AmneziaWG 端到端冒烟测试（在 se 测试机上跑）
#
# 目标：证明新代码在真实 Debian 12 上不仅能装起来，而且【隧道真的能通】。
# 只装起来不算验证 —— 阻塞点永远是"两端参数必须逐字节一致"，
# 只有真的握手成功、隧道里有流量，才说明配置生成是对的。
#
# ⚠️ 但本脚本【只测到隧道内互通为止】，证明不了"客户端能上网"。
#    「连上但没网」是另一类故障（服务端 FORWARD/NAT 的回程方向没放行等），
#    必须另跑 tests/awg-internet-netns.sh —— 它把客户端放进 network namespace，
#    测的是完整的公网访问路径。
#    历史教训：PostUp 曾漏了 `-o awg0 -j ACCEPT`，隧道内 ping 全通、
#    但客户端上不了网，本脚本完全测不出来。
#
# 做法：服务端装 awg0（走真实的 install.sh → hy2-awgctl 路径），
#       再在本机用导出的客户端配置起第二个实例 awgtest，从隧道内 ping 服务端。
#       两端都是同一台机器，但握手/加密/参数校验全都真实发生。
#
# 安全约束：
#   - 绝不修改 /etc/hysteria 或 hysteria-server（这是生产服务）
#   - 客户端配置强制把 AllowedIPs 改成 10.66.66.0/24，避免劫持默认路由掐断 SSH
#   - 用独立的接口名 awgtest，结束后彻底清理
# ==============================================================================
set -uo pipefail

# ⚠️ 不用 raw.githubusercontent.com 取 install.sh：它 push 后数分钟仍返回旧内容
# （且不把查询串算进缓存键，加 ?cb= 也没用 —— 见仓库内 awgctl.sh 的 awg_fetch_ctl 注释）。
# 本测试要验的是【当前代码】，所以走权威源；raw 仅作最后兜底。
REPO_SLUG="yys9253462-gif/hysteria2-installer"
fetch_install_sh() {
    local out="$1"
    curl -fsSL --max-time 30 -H "Accept: application/vnd.github.raw" \
        "https://api.github.com/repos/${REPO_SLUG}/contents/install.sh?ref=main" \
        -o "$out" 2>/dev/null && [[ -s "$out" ]] && grep -q 'Hysteria 2' "$out" && return 0
    curl -fsSL --max-time 30 \
        "https://cdn.jsdelivr.net/gh/${REPO_SLUG}@main/install.sh" \
        -o "$out" 2>/dev/null && [[ -s "$out" ]] && grep -q 'Hysteria 2' "$out" && return 0
    curl -fsSL --max-time 30 \
        "https://raw.githubusercontent.com/${REPO_SLUG}/main/install.sh" \
        -o "$out" 2>/dev/null && [[ -s "$out" ]] && grep -q 'Hysteria 2' "$out" && return 0
    return 1
}
CTL=/usr/local/bin/hy2-awgctl
TEST_IF=awgtest
TEST_CONF=/etc/amnezia/amneziawg/${TEST_IF}.conf
PASS=0; FAIL=0
ok()   { PASS=$((PASS+1)); echo "    [PASS] $*"; }
bad()  { FAIL=$((FAIL+1)); echo "    [FAIL] $*"; }
chk()  { if [[ "$2" == "$3" ]]; then ok "$1 = $3"; else bad "$1 期望[$3] 实际[$2]"; fi; }
step() { echo; echo "===== $* ====="; }

# 记录出口网卡（AWG 的 PostUp 加的是 -o <出口网卡> -j MASQUERADE）
WAN_IF=$(ip -4 route show default 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="dev"){print $(i+1); exit}}')
WAN_IF=${WAN_IF:-eth0}

# ⚠️ 判定残留时【只比对 AWG 自己的规则】，不要比对整张 iptables 表。
# 本机跑着 Docker，它会在任意时刻动态增删自己的 br-* / docker0 MASQUERADE 规则
# —— 实测本测试就因此误报过两次（一次行数比较、一次全表比对），
# 而被怀疑的"残留"其实是 Docker 新建的容器网桥。
PRE_NAT_COUNT=$(iptables -t nat -S POSTROUTING 2>/dev/null | grep -c -- "-o ${WAN_IF} -j MASQUERADE" || true)
PRE_FWD_COUNT=$(iptables -S FORWARD 2>/dev/null | grep -c -- "-i awg0 -j ACCEPT" || true)
PRE_HY2=$(systemctl is-active hysteria-server 2>/dev/null)
PUBLIC_IP=$(curl -4 -s --max-time 8 https://api.ipify.org || echo 127.0.0.1)

echo "靶机: $(hostname) / $(. /etc/os-release; echo $PRETTY_NAME) / $(uname -r)"
echo "公网IP: ${PUBLIC_IP}"
echo "Hysteria2 测试前状态: ${PRE_HY2}"

# ---------------------------------------------------------------- 1. 装
step "1. 通过项目真实路径安装 AWG 3.x"
fetch_install_sh /tmp/hy2-install.sh || { echo "下载 install.sh 失败（三个源均不可用）"; exit 1; }
echo "    install.sh 大小: $(stat -c%s /tmp/hy2-install.sh) 字节"
echo "    含多源回退函数 awg_fetch_ctl: $(grep -c 'awg_fetch_ctl' /tmp/hy2-install.sh) 处"

bash /tmp/hy2-install.sh awg-install --line 3 --endpoint "$PUBLIC_IP" --client smoketest >/tmp/awginstall.log 2>&1
RC=$?
chk "安装命令退出码" "$RC" "0"
if [[ $RC -ne 0 ]]; then echo "--- 安装日志尾部 ---"; tail -30 /tmp/awginstall.log; exit 1; fi

chk "控制工具已就位" "$([[ -x $CTL ]] && echo yes || echo no)" "yes"
chk "服务 active"     "$(systemctl is-active amneziawg-server 2>/dev/null)" "active"
chk "awg0 接口存在"   "$(ip link show awg0 >/dev/null 2>&1 && echo yes || echo no)" "yes"

# ---------------------------------------------------------------- 2. 端口
step "2. 端口必须避开 20000-40000（本机该区间已被 Hysteria2 跳跃规则劫持）"
JUMP=$(iptables -t nat -S PREROUTING 2>/dev/null | grep -oE 'dport [0-9]+:[0-9]+' | head -1)
echo "    本机跳跃规则: ${JUMP:-<无>}"
AWG_PORT=$(jq -r '.port' /etc/amnezia/amneziawg/awg_meta.json)
echo "    AWG 监听端口: ${AWG_PORT}"
if [[ "$AWG_PORT" =~ ^[0-9]+$ ]] && (( AWG_PORT < 20000 || AWG_PORT > 40000 )); then
    ok "端口 $AWG_PORT 在跳跃区间之外"
else
    bad "端口 $AWG_PORT 落在 20000-40000 内，会被劫持"
fi
echo "    iptables 实际监听确认:"; ss -lunp 2>/dev/null | grep -E "amneziawg-go|:${AWG_PORT} " | sed 's/^/      /' || echo "      (未匹配到)"

step "3. 端口落入劫持区间时必须被拒绝"
bash /tmp/hy2-install.sh awg install --line 3 --port 25000 --endpoint "$PUBLIC_IP" >/tmp/awgreject.log 2>&1
chk "拒绝 25000 的退出码非 0" "$([[ $? -ne 0 ]] && echo yes || echo no)" "yes"
if grep -q "跳跃区间" /tmp/awgreject.log; then ok "报错信息点明了原因"; else bad "报错未说明原因"; fi

# ---------------------------------------------------------------- 4. 服务端状态
step "4. 服务端配置自检"
grep -cE '^(S[1-4]|H[1-4]) = ' /etc/amnezia/amneziawg/awg0.conf | { read n; chk "服务端含 8 个混淆参数" "$n" "8"; }
chk "3.x 含 HeaderProtectionKey" "$(grep -c '^HeaderProtectionKey = ' /etc/amnezia/amneziawg/awg0.conf)" "1"
chk "协议线记录为 3" "$(jq -r '.line' /etc/amnezia/amneziawg/awg_meta.json)" "3"
echo "    awg show awg0:"; awg show awg0 2>/dev/null | sed 's/^/      /'

# ---------------------------------------------------------------- 5. 隧道连通性
step "5. 用导出的客户端配置在本机起客户端，验证隧道真的能通"

run_tunnel_test() {
    local line="$1"
    rm -f "$TEST_CONF"

    $CTL client-conf smoketest --endpoint 127.0.0.1 > "$TEST_CONF" 2>/tmp/cc.log
    if [[ ! -s "$TEST_CONF" ]]; then bad "导出客户端配置失败"; cat /tmp/cc.log; return 1; fi

    # 🔴 安全 + 避免路由冲突：把 AllowedIPs 收窄成「只路由服务端隧道地址」的单主机路由。
    #   - 不能保留 0.0.0.0/0：那会劫持默认路由、直接掐断 SSH
    #   - 也不能用 10.66.66.0/24：服务端的 awg0 已经占了这条 /24 路由，
    #     再加一条会报 "RTNETLINK answers: File exists" 而中断
    #   - /32 是更具体的前缀，两者可以共存，且 ping 时按最长前缀匹配走隧道
    sed -i 's|^AllowedIPs = 0.0.0.0/0|AllowedIPs = 10.66.66.1/32|' "$TEST_CONF"
    # 去掉 DNS 行：awg-quick 会调 resolvconf，而本机（最小化 Debian 云镜像）没装它，
    # 会导致 set -e 中断、接口被拆，从而验不到隧道本身。
    # 真实客户端设备（手机/桌面）都有 resolvconf 等价物，不受影响。
    sed -i '/^DNS = /d' "$TEST_CONF"
    sed -i "s|^Endpoint = .*|Endpoint = 127.0.0.1:${AWG_PORT}|" "$TEST_CONF"
    chmod 600 "$TEST_CONF"

    if grep -q '^AllowedIPs = 0.0.0.0/0' "$TEST_CONF"; then
        bad "客户端 AllowedIPs 仍是 0.0.0.0/0，为安全起见中止测试"
        return 1
    fi
    ok "客户端 AllowedIPs 已收窄为隧道网段（防止劫持默认路由）"

    echo "    ---- 客户端配置（隐去私钥）----"
    sed -E 's/^(PrivateKey|PresharedKey) = .*/\1 = <已隐去>/' "$TEST_CONF" | sed 's/^/      /'

    # 两端必须逐字节一致的参数，逐项对比
    echo "    ---- 服务端 vs 客户端 参数一致性 ----"
    local mismatch=0
    for k in Jc Jmin Jmax S1 S2 S3 S4 H1 H2 H3 H4; do
        local sv cv
        sv=$(awk -v k="$k" '$1==k {print $3}' /etc/amnezia/amneziawg/awg0.conf)
        cv=$(awk -v k="$k" '$1==k {print $3}' "$TEST_CONF")
        if [[ "$sv" != "$cv" || -z "$sv" ]]; then
            bad "$k 两端不一致 (服务端[$sv] 客户端[$cv])"; mismatch=1
        fi
    done
    if [[ $mismatch -eq 0 ]]; then ok "11 个参数两端逐字节一致"; fi
    if [[ "$line" == "3" ]]; then
        local sh ch
        sh=$(awk '$1=="HeaderProtectionKey" {print $3}' /etc/amnezia/amneziawg/awg0.conf)
        ch=$(awk '$1=="HeaderProtectionKey" {print $3}' "$TEST_CONF")
        if [[ -n "$sh" && "$sh" == "$ch" ]]; then ok "HeaderProtectionKey 两端一致"; else bad "HeaderProtectionKey 不一致"; fi
    fi

    # 起客户端
    echo "    ---- 启动客户端接口 ${TEST_IF} ----"
    WG_QUICK_USERSPACE_IMPLEMENTATION=/usr/local/bin/amneziawg-go \
        timeout 40 awg-quick up "$TEST_IF" 2>&1 | sed 's/^/      /'
    if ! ip link show "$TEST_IF" >/dev/null 2>&1; then
        bad "客户端接口未能建立"; return 1
    fi
    ok "客户端接口已建立"

    sleep 3
    echo "    ---- 隧道内 ping 服务端 10.66.66.1 ----"
    local pout
    pout=$(ping -c 3 -W 3 10.66.66.1 2>&1)
    echo "$pout" | sed 's/^/      /'
    if echo "$pout" | grep -qE '[1-3] (packets )?received'; then
        ok "隧道内 ping 通（握手成功 + 参数一致 + 加密正常）"
    else
        bad "隧道内 ping 失败"
    fi

    echo "    ---- 客户端 awg show（应有握手时间与收发字节）----"
    awg show "$TEST_IF" 2>/dev/null | sed 's/^/      /'
    local hs xfer
    hs=$(awg show "$TEST_IF" latest-handshakes 2>/dev/null | awk '{print $2}')
    xfer=$(awg show "$TEST_IF" transfer 2>/dev/null | awk '{print $2+$3}')
    if [[ -n "${hs:-}" && "${hs:-0}" -gt 0 ]]; then ok "已建立握手（时间戳 ${hs}）"; else bad "无握手记录"; fi
    if [[ -n "${xfer:-}" && "${xfer:-0}" -gt 0 ]]; then ok "隧道内有真实流量（${xfer} 字节）"; else bad "隧道内无流量"; fi

    awg-quick down "$TEST_IF" >/dev/null 2>&1
    ip link show "$TEST_IF" >/dev/null 2>&1 && ip link delete "$TEST_IF" 2>/dev/null
    rm -f "$TEST_CONF"
    return 0
}

run_tunnel_test 3

# ---------------------------------------------------------------- 6. 切换协议线
step "6. 切换协议线 3.x -> 2.x 后再验一次隧道"
$CTL update --line 2 >/tmp/awgswitch.log 2>&1
chk "切换命令退出码" "$?" "0"
chk "协议线已变为 2" "$(jq -r '.line' /etc/amnezia/amneziawg/awg_meta.json)" "2"
chk "2.x 配置不含 HeaderProtectionKey" "$(grep -c '^HeaderProtectionKey = ' /etc/amnezia/amneziawg/awg0.conf)" "0"
chk "切换后服务仍 active" "$(systemctl is-active amneziawg-server 2>/dev/null)" "active"
run_tunnel_test 2

# ---------------------------------------------------------------- 7. 清理
step "7. 卸载并确认不留垃圾"
$CTL uninstall >/tmp/awguninstall.log 2>&1
chk "卸载退出码" "$?" "0"
chk "/etc/amnezia 已移除"    "$([[ -d /etc/amnezia ]] && echo no || echo yes)" "yes"
chk "服务单元已移除"        "$([[ -f /etc/systemd/system/amneziawg-server.service ]] && echo no || echo yes)" "yes"
chk "amneziawg-go 已移除"   "$([[ -f /usr/local/bin/amneziawg-go ]] && echo no || echo yes)" "yes"
chk "awg0 接口已消失"       "$(ip link show awg0 >/dev/null 2>&1 && echo no || echo yes)" "yes"
chk "测试接口已清理"        "$(ip link show $TEST_IF >/dev/null 2>&1 && echo no || echo yes)" "yes"
# 控制工具是延迟自删的（避免删掉正在被 bash 读取的脚本），等它一下
sleep 4
chk "控制工具已自移除"      "$([[ -f /usr/local/bin/hy2-awgctl ]] && echo no || echo yes)" "yes"

POST_NAT_COUNT=$(iptables -t nat -S POSTROUTING 2>/dev/null | grep -c -- "-o ${WAN_IF} -j MASQUERADE" || true)
POST_FWD_COUNT=$(iptables -S FORWARD 2>/dev/null | grep -c -- "-i awg0 -j ACCEPT" || true)

chk "AWG 的 MASQUERADE 规则已清理" "$POST_NAT_COUNT" "$PRE_NAT_COUNT"
chk "AWG 的 FORWARD 放行规则已清理" "$POST_FWD_COUNT" "$PRE_FWD_COUNT"

# 顺带确认没有残留的 AWG 专用规则（防御性）
if iptables -t nat -S POSTROUTING 2>/dev/null | grep -q -- "-i awg0"; then
    bad "POSTROUTING 仍含 awg0 相关规则"
else
    ok "POSTROUTING 无任何 awg0 相关规则"
fi

# 生产服务必须毫发无伤
chk "Hysteria2 仍在运行" "$(systemctl is-active hysteria-server 2>/dev/null)" "$PRE_HY2"
chk "Hysteria2 跳跃规则仍在" "$(iptables -t nat -S PREROUTING 2>/dev/null | grep -c 'dport 20000:40000')" "1"

# ---------------------------------------------------------------- 汇总
echo
echo "================ 结果 ================"
echo "  通过: ${PASS}   失败: ${FAIL}"
[[ -f /tmp/hy2-install.sh ]] && rm -f /tmp/hy2-install.sh
[[ $FAIL -eq 0 ]] && echo "  全部通过" || echo "  存在问题，见上方 [FAIL]"
exit $(( FAIL > 0 ? 1 : 0 ))
