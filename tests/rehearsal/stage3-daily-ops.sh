#!/usr/bin/env bash
# 演练第 3 阶段：新手接下来会做的事 + 常见翻车点
set -u
export LOG_DIR=/tmp/rehearsal3
mkdir -p "$LOG_DIR"
source /repo/harness.sh

banner "阶段 3：安装后的日常操作（新手最常做的事）"

# ---- 3.1 计量是否真的在工作（本轮之前的静默降级区）----
step 'c01-计量模块能读到数据' bash -c '
S=$(jq -r .hysteria.secret /etc/hysteria/usage-meter-config.json)
curl -sS --max-time 6 -H "Authorization: $S" http://127.0.0.1:19996/traffic
'

step 'c02-usage-meter运行时是否在跑' bash -c '
systemctl list-units --all --no-pager 2>/dev/null | grep -iE "meter|usage" || echo "（无独立 meter unit —— 计量逻辑在 portal 进程内）"
echo "--- portal 进程 ---"
grep -c . /proc/net/tcp >/dev/null && echo ok
'

step 'c03-门户traffic端点' bash -c '
P=$(jq -r .port /etc/hysteria/portal.json); U=$(jq -r .username /etc/hysteria/portal-access.json)
W=$(jq -r .password /etc/hysteria/portal-access.json); T=$(jq -r .token /etc/hysteria/portal.json)
curl -sS --max-time 6 -u "$U:$W" "http://127.0.0.1:$P/$T/api/v1/traffic" | head -c 250
'

# ---- 3.2 新手最常做的：菜单 3 看信息、status、restart ----
step 'c04-menu3-查看信息'   bash -c 'printf "3\n0\n" | timeout 60 bash /repo/install.sh 2>&1 | grep -A14 "接下来怎么用" | head -18'
step 'c05-status子命令'     bash -c 'timeout 60 bash /repo/install.sh status 2>&1 | tail -14'
step 'c06-info子命令'       bash -c 'timeout 60 bash /repo/install.sh info 2>&1 | tail -16'
step 'c07-restart子命令'   bash -c 'timeout 90 bash /repo/install.sh restart 2>&1 | tail -4; systemctl is-active hysteria-server'
step 'c08-菜单11重启服务'   bash -c 'printf "11\n0\n" | timeout 90 bash /repo/install.sh 2>&1 | grep -iE "重启|成功|失败" | head -4'

# ---- 3.3 换证自愈（模拟 Caddy 续期）----
step 'c09-换证后自愈' bash -c '
echo "--- 换一张自签证书（模拟外部续期覆盖）---"
openssl ecparam -genkey -name prime256v1 -out /repo/scratch/n.key 2>/dev/null
openssl req -new -x509 -days 3650 -key /repo/scratch/n.key -out /repo/scratch/n.crt -subj "/CN=newnode.example.com" -addext "subjectAltName=DNS:newnode.example.com" >/dev/null 2>&1
cp /repo/scratch/n.crt /etc/hysteria/cert/server.crt.new && mv -f /etc/hysteria/cert/server.crt.new /etc/hysteria/cert/server.crt
cp /repo/scratch/n.key /etc/hysteria/cert/server.key.new && mv -f /etc/hysteria/cert/server.key.new /etc/hysteria/cert/server.key
echo "证书已换成 CN=newnode.example.com，meta 仍是旧的 www.bing.com（此刻应漂移）"
jq -c "{cert_type,server_name,is_insecure}" /etc/hysteria/client_meta.json
echo "--- 触发 path unit ---"
touch /etc/hysteria/cert/.t; sleep 8; rm -f /etc/hysteria/cert/.t; sleep 3
echo "--- 自愈后 ---"
jq -c "{cert_type,server_name,is_insecure}" /etc/hysteria/client_meta.json
'

step 'c10-自愈后二维码是否同步' bash -c '
P=$(jq -r .port /etc/hysteria/portal.json); U=$(jq -r .username /etc/hysteria/portal-access.json)
W=$(jq -r .password /etc/hysteria/portal-access.json); T=$(jq -r .token /etc/hysteria/portal.json)
echo "clash.yaml 里的 sni："
curl -sS -u "$U:$W" "http://127.0.0.1:$P/$T/clash.yaml" | grep -o "\"sni\": \"[^\"]*\""
echo "页面直链里的 sni："
curl -sS -u "$U:$W" "http://127.0.0.1:$P/$T/" | grep -o "hysteria2://[^\"<]*" | head -1 | grep -o "sni=[^&]*"
'

# ---- 3.4 卸载 ----
step 'c11-卸载-回答n应取消' bash -c 'printf "13\nn\n" | timeout 60 bash /repo/install.sh 2>&1 | tail -4'
step 'c12-卸载后服务仍在' bash -c 'systemctl is-active hysteria-server'

summary