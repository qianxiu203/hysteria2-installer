#!/usr/bin/env bash
# 🔴🔴 五轮回归统一入口 —— 跑完即知有没有回归。
#
# 五轮各自盯不同的失败面，缺一轮就会漏一类问题（2026-10-09 实测：
# 静态全绿但真机并发照样能把服务搞挂）：
#
#   轮 1  静态与契约     CSP 哈希 / id 对应 / data-* / 无内联事件 / 闭包变量签名
#   轮 2  边界与异常输入  YAML 注入 / 名字与地址边界 / 幂等 / ACL 兜底
#   轮 3  真实配置校验用**真实 hysteria 二进制**起进程验生成的 YAML（8 场景）
#   轮 4  并发与连续操作  连存/连切/连删后配置与服务是否仍一致（需服务器）
#   轮 5  真实流量闭环    真实客户端经节点访问标记服务，证明出站真的生效
#
# 🔴 轮 3/4/5 需要一台**已装 Hysteria 的 Linux**（改config.yaml + 重启服务）。
#    传HOST=se用 ssh 别名；不传则自动跳过并明确说明（不拿"跳过"当"通过"）。
#
# 用法：
#   bash tests/regression-all.sh                 # 本地能跑的就跑
#   HOST=se bash tests/regression-all.sh         # 连服务器跑全部五轮
set -u
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 2

HOST="${HOST:-}"
PY="$(command -v python3 || command -v python)"
TOTAL_PASS=0
TOTAL_FAIL=0
SKIPPED=""

hdr() { echo; echo "══════════════════════════════════════"; echo " $1"; echo "══════════════════════════════════════"; }
tally() {
    # 从测试输出里取"通过: N   失败: M"
    local out="$1"
    local p f
    p="$(grep -oE '通过: [0-9]+' <<<"$out" | tail -1 | grep -oE '[0-9]+' || echo 0)"
    f="$(grep -oE '失败: [0-9]+' <<<"$out" | tail -1 | grep -oE '[0-9]+' || echo 0)"
    TOTAL_PASS=$((TOTAL_PASS + ${p:-0}))
    TOTAL_FAIL=$((TOTAL_FAIL + ${f:-0}))
    echo "$out"
}

hdr "第 1 轮 · 静态与契约"
tally "$(bash tests/regression-round1-static.sh 2>&1)"

hdr "第 2 轮 · 边界与异常输入"
tally "$("$PY" tests/regression-round3-boundary.py 2>&1)"

if [[ -n "$HOST" ]]; then
    hdr "第 3 轮 · 真实 hysteria 校验生成的 YAML"
    scp -q install.sh "$HOST:/tmp/_reg_install.sh" 2>/dev/null
    scp -q tests/outbound-verify-on-server.py "$HOST:/tmp/" 2>/dev/null
    tally "$(ssh -o StrictHostKeyChecking=no "$HOST" \
        'mkdir -p /tmp/ymlcheck && cp /etc/hysteria/config.yaml /tmp/ymlcheck/base.yaml && cp /tmp/_reg_install.sh /tmp/ymlcheck/portal.py && cd /tmp && python3 outbound-verify-on-server.py 2>&1' | tail -25)"

    hdr "第 4 轮 · 并发与连续操作"
    scp -q tests/regression-round4-concurrency.py "$HOST:/tmp/" 2>/dev/null
    tally "$(ssh -o StrictHostKeyChecking=no "$HOST" \
        'cd /tmp && python3 regression-round4-concurrency.py 2>&1' | tail -40)"

    hdr "第 5 轮 · 真实流量闭环（证明出站真的生效）"
    scp -q tests/regression-round5-traffic.py tests/regression-round5b-traffic-proof.py "$HOST:/tmp/" 2>/dev/null
    tally "$(ssh -o StrictHostKeyChecking=no "$HOST" \
        'cd /tmp && python3 regression-round5-traffic.py 2>&1' | tail -32)"
    tally "$(ssh -o StrictHostKeyChecking=no "$HOST" \
        'cd /tmp && python3 regression-round5b-traffic-proof.py 2>&1' | tail -26)"
else
    SKIPPED="第 3/4/5 轮（需 HOST=<ssh别名> 才能跑真实 hysteria 与真实流量验证）"
fi

hdr "总计"
echo "  通过: $TOTAL_PASS"
echo "  失败: $TOTAL_FAIL"
if [[ -n "$SKIPPED" ]]; then
    echo "  ⚠️未跑：$SKIPPED"
    echo "   （未跑不等于通过 —— 真实服务相关的缺陷只有真跑才暴露）"
fi
[[ $TOTAL_FAIL -eq 0 ]] || exit 1
[[ -z "$SKIPPED" ]] || exit 2
exit 0