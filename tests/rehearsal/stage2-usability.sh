#!/usr/bin/env bash
# 演练第 2 阶段：装完之后「这东西到底能不能用」
# ——安装脚本返回 0 不等于可用。这一阶段专门验证真实可用性。
set -u
export LOG_DIR=/tmp/rehearsal2
mkdir -p "$LOG_DIR"
source /repo/harness.sh

banner "阶段 2：安装后可用性验证"

step 'b01-服务状态'      bash -c 'systemctl is-active hysteria-server hysteria-portal'
step 'b02-监听端口'      bash -c "ss -tlnp 2>/dev/null | grep -E 'python3|hysteria' | head -5; echo '--- UDP ---'; ss -ulnp 2>/dev/null | grep hysteria | head -3"
step 'b03-config语法'    bash -c 'python3 -c "import yaml,sys; yaml.safe_load(open(\"/etc/hysteria/config.yaml\")); print(\"YAML OK\")" 2>/dev/null || echo "python3-yaml 未装，改用 hysteria 自检"'
step 'b04-hysteria自检'  bash -c '/usr/local/bin/hysteria server --config /etc/hysteria/config.yaml --test 2>&1 | tail -5 || true'
step 'b05-关键文件'      bash -c 'for f in config.yaml client_meta.json portal.json portal-access.json usage-meter-config.json cert/server.crt cert/server.key; do printf "%-28s %s\n" "$f" "$([ -f /etc/hysteria/$f ] && stat -c%s /etc/hysteria/$f || echo MISSING)"; done'
step 'b06-meta内容'      bash -c 'jq -c "{public_ip,server_name,cert_type,is_insecure,listen_port,subscription_port,hop_port_range}" /etc/hysteria/client_meta.json'
step 'b07-trafficStats'  bash -c 'grep -A3 "^trafficStats:" /etc/hysteria/config.yaml'
step 'b08-计量secret一致' bash -c 'Y=$(grep -A3 "^trafficStats:" /etc/hysteria/config.yaml | grep "secret:" | tr -d " " | cut -d: -f2); J=$(jq -r ".hysteria.secret" /etc/hysteria/usage-meter-config.json 2>/dev/null); echo "yaml=$Y"; echo "json=$J"; [ "$Y" = "$J" ] && echo "MATCH ✅" || echo "MISMATCH ❌"'
step 'b09-门户HTTP'      bash -c 'P=$(jq -r .port /etc/hysteria/portal.json); U=$(jq -r .username /etc/hysteria/portal-access.json); W=$(jq -r .password /etc/hysteria/portal-access.json); T=$(jq -r .token /etc/hysteria/portal.json); curl -sS -o /dev/null -w "root=%{http_code} " -u "$U:$W" "http://127.0.0.1:$P/$T/"; curl -sS -o /dev/null -w "cert-status=%{http_code}\n" -u "$U:$W" "http://127.0.0.1:$P/$T/cert-status"'
step 'b10-cert-status'  bash -c 'P=$(jq -r .port /etc/hysteria/portal.json); U=$(jq -r .username /etc/hysteria/portal-access.json); W=$(jq -r .password /etc/hysteria/portal-access.json); T=$(jq -r .token /etc/hysteria/portal.json); curl -sS -u "$U:$W" "http://127.0.0.1:$P/$T/cert-status" | jq -c "{ok,common_name,issuer,expires_in_days,warn_level,server_name,meta_matches_cert}"'
step 'b11-客户端直链'    bash -c 'P=$(jq -r .port /etc/hysteria/portal.json); U=$(jq -r .username /etc/hysteria/portal-access.json); W=$(jq -r .password /etc/hysteria/portal-access.json); T=$(jq -r .token /etc/hysteria/portal.json); curl -sS -u "$U:$W" "http://127.0.0.1:$P/$T/" | grep -o "hysteria2://[^\"<]*" | head -1'
step 'b12-clash订阅'    bash -c 'P=$(jq -r .port /etc/hysteria/portal.json); U=$(jq -r .username /etc/hysteria/portal-access.json); W=$(jq -r .password /etc/hysteria/portal-access.json); T=$(jq -r .token /etc/hysteria/portal.json); curl -sS -u "$U:$W" "http://127.0.0.1:$P/$T/clash.yaml" | head -c 200'
step 'b13-qr.svg'       bash -c 'P=$(jq -r .port /etc/hysteria/portal.json); U=$(jq -r .username /etc/hysteria/portal-access.json); W=$(jq -r .password /etc/hysteria/portal-access.json); T=$(jq -r .token /etc/hysteria/portal.json); curl -sS -o /dev/null -w "qr.svg=%{http_code} size=%{size_download}\n" -u "$U:$W" "http://127.0.0.1:$P/$T/qr.svg"'
step 'b14-自愈单元'      bash -c 'for u in hy2-cert-selfheal.timer hy2-cert-selfheal.path hy2-cert-selfheal.service; do printf "%-32s %s\n" "$u" "$(systemctl is-active $u 2>/dev/null || echo inactive)"; done; echo "--- timer ---"; systemctl list-timers hy2-cert-selfheal.timer --no-pager 2>/dev/null | head -2'
step 'b15-iptables跳跃'  bash -c 'iptables -t nat -L PREROUTING -n 2>/dev/null | grep REDIRECT | head -3; echo "--- OUTPUT 链 ---"; iptables -t nat -L OUTPUT -n 2>/dev/null | grep REDIRECT | head -2'
step 'b16-journal错误'  bash -c 'journalctl -u hysteria-server --no-pager -p err 2>&1 | tail -8'
step 'b17-portal-journal' bash -c 'journalctl -u hysteria-portal --no-pager -p warning 2>&1 | tail -8'

summary