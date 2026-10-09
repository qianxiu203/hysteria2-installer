#!/usr/bin/env bash
# 在干净机器上真跑 install.sh，验证「已有 Caddy 占 80/443」时的安装成功率。
# 这是 2026-10-09 修过的场景（原先会退回自签导致连不上）。
set -u
cd /tmp || exit 1

printf '1\n' > /tmp/ans
sleep 1
printf 'us5x.zy3a.com\n' >> /tmp/ans   # 1) 选安装 2) 填域名
sleep 2
for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do
    printf '\n' >> /tmp/ans
done
sleep 1
(cat /tmp/ans; sleep 2) | timeout 400 bash install.sh > /tmp/install.log 2>&1
echo "退出码=$?"
echo
echo "--- 关键输出 ---"
grep -nE 'ERROR|失败|成功|证书|端口|域名|服务|已就位|警告|WARN' /tmp/install.log | head -30
