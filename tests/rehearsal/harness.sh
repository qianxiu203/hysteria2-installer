#!/usr/bin/env bash
# ==============================================================================
# 小白安装演练 harness（在干净容器里真跑 install.sh）
# ------------------------------------------------------------------------------
# 目标不是「跑通就算」，而是把**每一步的输出、耗时、以及新手会卡住的地方**
# 全部记录下来。所以：
#   * 每步单独计时（慢的步骤本身就是体验问题）
#   * 每步的 stdout/stderr 全部落盘，事后逐份翻
#   * 任何一步非 0 退出都记录但**不中断**整个流程 —— 真实安装里用户看到的是
#     「装到一半停了」，我们要把那个「一半」精确还原出来
# ==============================================================================
set -u

LOG_DIR="${LOG_DIR:-/tmp/hy2-rehearsal}"
mkdir -p "$LOG_DIR"
STEP_LOG="$LOG_DIR/steps.tsv"
: > "$STEP_LOG"

REPO_DIR="${REPO_DIR:-/repo}"     # 容器内挂载仓库的位置

_pass=0; _fail=0; _warn=0

step() {
    # step <名称> <命令...>
    local name="$1"; shift
    local t0 t1 rc out
    t0=$(date +%s.%N)
    out="$LOG_DIR/$(printf '%02d' $(( $(wc -l < "$STEP_LOG") + 1 )))-${name}.log"
    # shellcheck disable=SC2068
    "$@" >"$out" 2>&1
    rc=$?
    t1=$(date +%s.%N)
    local dt
    dt=$(awk -v a="$t0" -v b="$t1" 'BEGIN{printf "%.1f", b-a}')
    printf '%s\t%s\t%s\t%s\n' "$name" "$rc" "$dt" "$out" >> "$STEP_LOG"
    if [[ $rc -eq 0 ]]; then
        _pass=$((_pass+1)); printf '  ✅ %-38s %6ss\n' "$name" "$dt"
    else
        _fail=$((_fail+1)); printf '  ❌ %-38s %6ss  (rc=$rc, 日志: %s)\n' "$name" "$dt" "$out"
    fi
    return $rc
}

note() { printf '  \033[33m→\033[0m %s\n' "$*"; }
head2() { printf '\n\033[36m=== %s ===\033[0m\n' "$*"; }

: "${HY2_DIR:=/etc/hysteria}"

summary() {
    head2 "演练结果汇总"
    printf '  通过 %d / 失败 %d\n' "$_pass" "$_fail"
    echo
    printf '%-38s %-4s %-8s %s\n' "步骤" "rc" "耗时" "日志"
    while IFS=$'\t' read -r name rc dt out; do
        local mark="  "
        [[ "$rc" == "0" ]] || mark="❌"
        printf '%s %-36s %-4s %-8s %s\n' "$mark" "$name" "$rc" "${dt}s" "$out"
    done < "$STEP_LOG"
}

banner() {
    printf '\n\033[1;36m%s\033[0m\n' "############################################################"
    printf '\033[1;36m# %s\033[0m\n' "$1"
    printf '\033[1;36m%s\033[0m\n' "############################################################"
}