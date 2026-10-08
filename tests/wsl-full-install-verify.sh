#!/usr/bin/env bash
# 全流程真实安装验证（在干净 Linux 上真跑 install.sh）
set -u
cd /root/hytest || exit 1
printf '1\n1\n' > /tmp/ans
for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16; do printf '\n' >> /tmp/ans; done
(cat /tmp/ans; sleep 1) | timeout 240 bash install.sh > run.log 2>&1
echo "退出码=$?"
echo "--- 关键输出 ---"
grep -nE "ERROR|失败|安装成功|服务启动|证书|门户|已就位" run.log | head -22
echo
echo "--- 产物验收 ---"
if [ -f /etc/hysteria/config.yaml ]; then
    CF=$(grep -E '^ +cert:' /etc/hysteria/config.yaml | head -1 | sed 's/.*cert: *//')
    KF=$(grep -E '^ +key:' /etc/hysteria/config.yaml | head -1 | sed 's/.*key: *//')
    echo "cert=$CF"
    if [ -s "$CF" ]; then
        echo "  字节=$(wc -c < "$CF")  CN=$(openssl x509 -in "$CF" -noout -subject 2>/dev/null | sed 's/.*CN *= *//;s/,.*//')  链=$(grep -c 'BEGIN CERTIFICATE' "$CF")"
        a=$(openssl x509 -in "$CF" -noout -pubkey 2>/dev/null | openssl sha256 | awk '{print $NF}')
        b=$(openssl pkey -in "$KF" -pubout 2>/dev/null | openssl sha256 | awk '{print $NF}')
        if [ -n "$a" ] && [ "$a" = "$b" ]; then echo "  公私钥配对: 是"; else echo "  公私钥配对: 否"; fi
    else
        echo "  证书文件缺失!"
    fi
else
    echo "config.yaml 未生成!"
fi
echo
echo "--- 门户文件 ---"
for f in portal.py portal_assets.py; do
    if [ -s "/etc/hysteria/$f" ]; then echo "  $f $(wc -c < "/etc/hysteria/$f") 字节"; else echo "  $f 缺失!"; fi
done
echo
echo "--- 端口监听 ---"
ss -ulpn 2>/dev/null | grep hysteria || echo "  无 UDP 监听"
echo
echo "--- 关键依赖 ---"
for b in curl jq openssl python3; do
    if command -v $b >/dev/null 2>&1; then echo "  $b OK"; else echo "  $b 缺失!"; fi
done