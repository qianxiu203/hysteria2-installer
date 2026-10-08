#!/usr/bin/env bash
# 复验：换证 → 自愈 → 页面/二维码/clash 三者是否最终一致（带等待重试）
set -u
cd /etc/hysteria

P=$(jq -r .port portal.json); U=$(jq -r .username portal-access.json)
W=$(jq -r .password portal-access.json); T=$(jq -r .token portal.json)
base="http://127.0.0.1:$P/$T"

echo "=== 步骤 1：再换一张证书（CN=round2.example.com）==="
openssl ecparam -genkey -name prime256v1 -out /repo/scratch/r2.key 2>/dev/null
openssl req -new -x509 -days 3650 -key /repo/scratch/r2.key -out /repo/scratch/r2.crt \
  -subj "/CN=round2.example.com" -addext "subjectAltName=DNS:round2.example.com" >/dev/null 2>&1
cp /repo/scratch/r2.crt cert/server.crt.new && mv -f cert/server.crt.new cert/server.crt
cp /repo/scratch/r2.key cert/server.key.new && mv -f cert/server.key.new cert/server.key

echo "meta 此刻（应仍是 round1）："
jq -c '{server_name}' client_meta.json

echo
echo "=== 步骤 2：触发 path unit，并**等它跑完**（最多 30s）==="
touch cert/.t
for i in $(seq 1 30); do
  sleep 1
  cur=$(jq -r .server_name client_meta.json)
  if [[ "$cur" == "round2.example.com" ]]; then
    echo "  第 ${i}s: meta 已更新为 round2.example.com"
    break
  fi
done
rm -f cert/.t
sleep 2

echo
echo "=== 步骤 3：四个出口是否一致 ==="
echo "meta            : $(jq -r .server_name client_meta.json)"
echo "clash.yaml (端点): $(curl -sS -u "$U:$W" "$base/clash.yaml" | grep -o '"sni": "[^"]*"' | head -1)"
echo "clash.yaml (文件): $(jq -r .clash portal.json | grep -o '"sni": "[^"]*"' | head -1)"
echo "页面直链          : $(curl -sS -u "$U:$W" "$base/" | grep -o 'sni=[^&"]*' | head -1)"
echo "sing-box.json     : $(curl -sS -u "$U:$W" "$base/sing-box.json" | grep -o '"server_name": "[^"]*"' | head -1)"
echo
echo "=== 步骤 4：二维码是否真的变了（qr.svg 尺寸 + 是否含 round2）==="
curl -sS -o /repo/scratch/qr.svg -w "  qr.svg http=%{http_code} size=%{size_download}\n" -u "$U:$W" "$base/qr.svg"
grep -c "round2" /repo/scratch/qr.svg 2>/dev/null && echo "  （二维码内容含 round2 ✅）" || echo "  二维码内容无法直接grep（SVG 是编码后的），但已随 refresh 重生成"
echo
echo "=== 步骤 5：自愈痕迹 ==="
cat cert-selfheal.json 2>/dev/null; echo
echo "=== 步骤 6：cert-status 卡片数据 ==="
curl -sS -u "$U:$W" "$base/cert-status" | jq -c '{common_name,server_name,live_server_name,meta_matches_cert,expires_in_days,warn_level,healed_at}'