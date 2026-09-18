#!/usr/bin/env bash
# ==============================================================================
# Hysteria 2 全功能生产级一键部署与管理脚本
# GitHub: https://github.com/yys9253462-gif/hysteria2-installer
# Author: Yanshan (yys9253462-gif)
# ==============================================================================

set -eo pipefail
umask 077

# 终端色彩
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
PLAIN='\033[0m'

HY2_DIR="/etc/hysteria"
HY2_CONFIG="${HY2_DIR}/config.yaml"
HY2_BIN="/usr/local/bin/hysteria"
HY2_SERVICE="/etc/systemd/system/hysteria-server.service"
HY2_CERT_DIR="${HY2_DIR}/cert"
HY2_META_FILE="${HY2_DIR}/client_meta.json"
HY2_SUB_PORT="8443"

log_info() { echo -e "${GREEN}[INFO]${PLAIN} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${PLAIN} $1"; }
log_err()  { echo -e "${RED}[ERROR]${PLAIN} $1"; }
log_step() { echo -e "${CYAN}==>${PLAIN} ${BLUE}$1${PLAIN}"; }

# 1. 基础环境检查
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_err "本脚本必须以 root 权限运行！请使用 sudo 或切换至 root 用户。"
        exit 1
    fi
}

check_arch() {
    ARCH=$(uname -m)
    case "$ARCH" in
        x86_64|amd64)
            HY2_ARCH="amd64"
            ;;
        aarch64|arm64)
            HY2_ARCH="arm64"
            ;;
        armv7l|armhf)
            HY2_ARCH="armv7"
            ;;
        *)
            log_err "暂不支持的 CPU 架构: ${ARCH}"
            exit 1
            ;;
    esac
}

get_public_ip() {
    PUBLIC_IP=$(curl -4 -s --max-time 5 https://api.ipify.org || \
                curl -4 -s --max-time 5 https://icanhazip.com || \
                curl -4 -s --max-time 5 https://ipinfo.io/ip || \
                echo "127.0.0.1")
}

install_dependencies() {
    log_step "检查并安装基础依赖 (curl, wget, jq, openssl, iptables, tar)..."
    if command -v apt-get >/dev/null 2>&1; then
        apt-get update -qq && apt-get install -y -qq curl wget jq openssl iptables tar ca-certificates qrencode python3
    elif command -v dnf >/dev/null 2>&1; then
        dnf install -y curl wget jq openssl iptables tar ca-certificates qrencode python3
    elif command -v yum >/dev/null 2>&1; then
        yum install -y curl wget jq openssl iptables tar ca-certificates qrencode python3
    elif command -v apk >/dev/null 2>&1; then
        apk add --no-cache curl wget jq openssl iptables tar ca-certificates bash qrencode python3
    else
        log_warn "未识别的包管理器，请确认已安装 curl, wget, jq, openssl, iptables"
    fi
}

# 2. 安装与更新官方核心二进制
install_binary() {
    log_step "获取 Hysteria 2 官方最新版本..."
    LATEST_TAG=$(curl -s --max-time 10 https://api.github.com/repos/apernet/hysteria/releases/latest | jq -r '.tag_name // empty')
    
    if [[ -z "$LATEST_TAG" || "$LATEST_TAG" == "null" ]]; then
        log_warn "从 GitHub API 获取版本失败，尝试直接下载官方最新发布版..."
        DOWNLOAD_URL="https://download.hysteria.network/app/latest/hysteria-linux-${HY2_ARCH}"
        LATEST_TAG="latest"
    else
        DOWNLOAD_URL="https://github.com/apernet/hysteria/releases/download/${LATEST_TAG}/hysteria-linux-${HY2_ARCH}"
    fi

    log_info "目标版本: ${LATEST_TAG} (${HY2_ARCH})"
    log_step "下载二进制文件至 ${HY2_BIN}..."
    
    if curl -fL --progress-bar "$DOWNLOAD_URL" -o "${HY2_BIN}.tmp"; then
        mv "${HY2_BIN}.tmp" "$HY2_BIN"
        chmod +x "$HY2_BIN"
        log_info "Hysteria 2 二进制安装成功！版本信息: $($HY2_BIN version | head -n 1)"
    else
        rm -f "${HY2_BIN}.tmp"
        log_err "下载失败，请检查网络连接。"
        exit 1
    fi
}

# 3. 证书处理模块（自签名 / 自有证书 / ACME 域名证书）
setup_certificates() {
    mkdir -p "$HY2_CERT_DIR"
    
    echo -e "\n${CYAN}------------------------------------------------------------${PLAIN}"
    echo -e "${GREEN}TLS 证书配置方式：${PLAIN}"
    echo -e "  ${YELLOW}1.${PLAIN} 使用自动生成的自签名证书 (最简单快捷，客户端需开启 skip-cert-verify / insecure)"
    echo -e "  ${YELLOW}2.${PLAIN} 自定义已有证书文件路径 (例如 acme.sh / certbot 已签发的 fullchain.pem 与 privkey.pem)"
    echo -e "  ${YELLOW}3.${PLAIN} 绑定域名并自动申请 Let's Encrypt 证书 (推荐)"
    echo -e "  ${YELLOW}4.${PLAIN} 自动扫描并使用本机已有证书 (Let's Encrypt / acme.sh)"
    echo -e "${CYAN}------------------------------------------------------------${PLAIN}"
    read -rp "请选择证书类型 [默认: 1]: " cert_choice
    cert_choice=${cert_choice:-1}

    if [[ "$cert_choice" == "2" ]]; then
        read -rp "请输入证书公钥文件完整路径 (fullchain.pem/cert.crt): " input_cert
        read -rp "请输入证书私钥文件完整路径 (privkey.pem/private.key): " input_key
        if [[ ! -f "$input_cert" || ! -f "$input_key" ]]; then
            log_err "指定的文件不存在，将回退为自签名证书！"
            generate_self_signed_cert
        else
            CERT_TYPE="custom"
            CERT_FILE="$input_cert"
            KEY_FILE="$input_key"
            read -rp "请输入证书绑定的域名 (SNI): " SERVER_NAME
            SERVER_NAME=${SERVER_NAME:-$PUBLIC_IP}
            IS_INSECURE="false"
        fi
    elif [[ "$cert_choice" == "3" ]]; then
        setup_acme_certificate
    elif [[ "$cert_choice" == "4" ]]; then
        select_local_certificate
    else
        generate_self_signed_cert
    fi
}

select_local_certificate() {
    local certs=() cert key i choice
    while IFS= read -r cert; do
        if [[ "$(basename "$cert")" == "fullchain.pem" ]]; then
            key="$(dirname "$cert")/privkey.pem"
        else
            key="${cert%.cer}.key"
        fi
        [[ -f "$key" ]] && certs+=("$cert|$key")
    done < <(find /etc/letsencrypt/live /root/.acme.sh /home -type f \( -name fullchain.pem -o -name '*.cer' \) 2>/dev/null)
    if [[ ${#certs[@]} -eq 0 ]]; then
        log_err "未发现可配对的证书和私钥，请选择其他证书方式。"
        return 1
    fi
    echo -e "${GREEN}发现以下本机证书：${PLAIN}"
    for i in "${!certs[@]}"; do echo -e "  ${YELLOW}$((i+1)).${PLAIN} ${certs[$i]%%|*}"; done
    read -rp "请选择证书编号: " choice
    [[ "$choice" =~ ^[0-9]+$ ]] && (( choice >= 1 && choice <= ${#certs[@]} )) || { log_err "无效选择。"; return 1; }
    cert="${certs[$((choice-1))]%%|*}"; key="${certs[$((choice-1))]#*|}"
    CERT_TYPE="custom"; CERT_FILE="$cert"; KEY_FILE="$key"; IS_INSECURE="false"
    read -rp "请输入证书绑定的域名 (SNI): " SERVER_NAME
    [[ -n "$SERVER_NAME" ]] || { log_err "域名不能为空。"; return 1; }
}

setup_acme_certificate() {
    echo -e "${YELLOW}申请 ACME 证书前，请确认域名 A/AAAA 记录已指向本机，且云安全组与本机防火墙允许 TCP 80。${PLAIN}"
    read -rp "请输入要绑定的域名 (例如 hy2.example.com): " SERVER_NAME
    if [[ -z "$SERVER_NAME" || "$SERVER_NAME" == *"/"* || "$SERVER_NAME" == *":"* ]]; then
        log_err "域名不能为空，且不能包含协议、路径或端口。"
        return 1
    fi
    read -rp "请输入 ACME 通知邮箱: " ACME_EMAIL
    if [[ -z "$ACME_EMAIL" || "$ACME_EMAIL" != *"@"* ]]; then
        log_err "请输入有效的通知邮箱。"
        return 1
    fi

    CERT_TYPE="acme"
    IS_INSECURE="false"
    log_info "将为 ${SERVER_NAME} 自动申请 Let's Encrypt 证书。"
}

generate_self_signed_cert() {
    CERT_TYPE="self_signed"
    SERVER_NAME="www.bing.com"
    CERT_FILE="${HY2_CERT_DIR}/server.crt"
    KEY_FILE="${HY2_CERT_DIR}/server.key"
    IS_INSECURE="true"

    log_step "正在生成高拟真自签名 ECC 证书 (伪装 SNI: ${SERVER_NAME})..."
    openssl ecparam -genkey -name prime256v1 -out "$KEY_FILE"
    openssl req -new -x509 -days 3650 -key "$KEY_FILE" -out "$CERT_FILE" -subj "/CN=${SERVER_NAME}" >/dev/null 2>&1
    chmod 600 "$KEY_FILE"
    log_info "自签名证书生成成功。"
}

# 4. 端口与网络配置 (支持端口跳跃)
setup_ports_and_obfs() {
    echo -e "\n${CYAN}------------------------------------------------------------${PLAIN}"
    echo -e "${GREEN}服务端口与端口跳跃配置：${PLAIN}"
    echo -e "${CYAN}------------------------------------------------------------${PLAIN}"
    
    DEFAULT_PORT=$((RANDOM % 40000 + 10000))
    read -rp "请输入主监听 UDP 端口 [1-65535, 默认: ${DEFAULT_PORT}]: " LISTEN_PORT
    LISTEN_PORT=${LISTEN_PORT:-$DEFAULT_PORT}

    # 密码生成
    RANDOM_PASS=$(openssl rand -hex 16)
    read -rsp "请输入连接认证密码 [回车自动生成]: " AUTH_PASSWORD; echo
    AUTH_PASSWORD=${AUTH_PASSWORD:-$RANDOM_PASS}

    # 运行模式选择 (单机私密 vs 商城集群 Agent 模式)
    echo -e "\n请选择当前 Hysteria 2 节点的运行模式："
    echo -e "  ${GREEN}1.${PLAIN} 单机私密模式 (默认：单用户/自用，提供 Web 信息中心)"
    echo -e "  ${GREEN}2.${PLAIN} 商城集群 Agent 模式 (开启 REST API 接口，支持动态开户/续费，对接商城)"
    read -rp "请输入选项 [1-2, 默认 1]: " node_mode_choice
    node_mode_choice=${node_mode_choice:-1}

    if [[ "$node_mode_choice" == "2" ]]; then
        NODE_MODE="agent"
        RANDOM_API_KEY="hy2_sec_$(openssl rand -hex 16)"
        read -rsp "请设置节点通信 API Key [回车自动生成]: " NODE_API_KEY; echo
        NODE_API_KEY=${NODE_API_KEY:-$RANDOM_API_KEY}
        log_info "当前已选：商城集群 Agent 模式 (Node API Key 已生成)"
    else
        NODE_MODE="standalone"
        NODE_API_KEY=""
    fi

    # 端口跳跃
    echo -e "\n是否启用端口跳跃 (Port Hopping)? 可有效防止运营商对单 UDP 端口的 QoS 限速与阻断。"
    read -rp "是否开启端口跳跃? [y/N, 默认 N]: " enable_hop
    enable_hop=${enable_hop:-n}

    clear_all_hopping_rules
    HOP_PORT_RANGE=""
    if [[ "$enable_hop" =~ ^[Yy]$ ]]; then
        DEFAULT_HOP_START=20000
        DEFAULT_HOP_END=40000
        read -rp "请输入端口跳跃起始范围 [默认: ${DEFAULT_HOP_START}]: " HOP_START
        HOP_START=${HOP_START:-$DEFAULT_HOP_START}
        read -rp "请输入端口跳跃结束范围 [默认: ${DEFAULT_HOP_END}]: " HOP_END
        HOP_END=${HOP_END:-$DEFAULT_HOP_END}
        HOP_PORT_RANGE="${HOP_START}-${HOP_END}"
        setup_iptables_port_hopping "$LISTEN_PORT" "$HOP_START" "$HOP_END"
    fi

    # Salamander 混淆配置
    echo -e "\n是否启用 Salamander 混淆? (将整个 UDP 数据包伪装为随机高熵杂波，防止 GFW 特征识别)"
    read -rp "是否开启混淆? [y/N, 默认 N]: " enable_obfs
    enable_obfs=${enable_obfs:-n}

    OBFS_PASSWORD=""
    if [[ "$enable_obfs" =~ ^[Yy]$ ]]; then
        RANDOM_OBFS=$(openssl rand -hex 16)
        read -rsp "请输入混淆密码 [回车自动生成]: " OBFS_PASSWORD; echo
        OBFS_PASSWORD=${OBFS_PASSWORD:-$RANDOM_OBFS}
    fi
}

setup_system_firewall() {
    local port="$1"
    local s_port="$2"
    local e_port="$3"
    
    log_step "自动放行系统内部防火墙 (ufw / firewalld / iptables)..."
    if command -v ufw >/dev/null 2>&1 && ufw status | grep -q '^Status: active'; then
        ufw allow "${HY2_SUB_PORT}/tcp" >/dev/null 2>&1 || true
        ufw allow "${port}/udp" >/dev/null 2>&1 || true
        if [[ "$CERT_TYPE" == "acme" ]]; then
            ufw allow 80/tcp >/dev/null 2>&1 || true
            ufw allow "${HY2_SUB_PORT}/tcp" >/dev/null 2>&1 || true
        fi
        if [[ -n "$s_port" && -n "$e_port" ]]; then
            ufw allow "${s_port}:${e_port}/udp" >/dev/null 2>&1 || true
        fi
        log_info "已放行 UFW 防火墙端口。"
    fi
    if command -v firewall-cmd >/dev/null 2>&1 && systemctl is-active firewalld >/dev/null 2>&1; then
        firewall-cmd --zone=public --add-port="${HY2_SUB_PORT}/tcp" --permanent >/dev/null 2>&1 || true
        firewall-cmd --zone=public --add-port="${port}/udp" --permanent >/dev/null 2>&1 || true
        if [[ "$CERT_TYPE" == "acme" ]]; then
            firewall-cmd --zone=public --add-port="80/tcp" --permanent >/dev/null 2>&1 || true
            firewall-cmd --zone=public --add-port="${HY2_SUB_PORT}/tcp" --permanent >/dev/null 2>&1 || true
        fi
        if [[ -n "$s_port" && -n "$e_port" ]]; then
            firewall-cmd --zone=public --add-port="${s_port}-${e_port}/udp" --permanent >/dev/null 2>&1 || true
        fi
        firewall-cmd --reload >/dev/null 2>&1 || true
        log_info "已放行 firewalld 端口。"
    fi
}

select_subscription_port() {
    # bind 实际验证 IPv4 TCP 端口；不解析 ss 标题，不进行无限循环。
    HY2_SUB_PORT=$(python3 - <<'PYPORT'
import socket, secrets
for i in range(100):
    port = 8443 if i == 0 else 10000 + secrets.randbelow(50000)
    with socket.socket() as sock:
        try:
            sock.bind(('0.0.0.0', port))
        except OSError:
            continue
        print(port)
        break
else:
    raise SystemExit('无法找到可用 TCP 端口')
PYPORT
)
    PORTAL_LOCAL_PORT=$(python3 - <<'PYPORT'
import socket
with socket.socket() as sock:
    sock.bind(('127.0.0.1', 0))
    print(sock.getsockname()[1])
PYPORT
)
}

clear_all_hopping_rules() {
    # 彻底扫描并清理所有历史残留的 REDIRECT 到 hysteria 端口的 iptables 规则，防止旧端口重定向死循环
    while iptables -t nat -L PREROUTING -n --line-numbers 2>/dev/null | grep -q "REDIRECT.*udp"; do
        local line_num=$(iptables -t nat -L PREROUTING -n --line-numbers | grep "REDIRECT.*udp" | head -n 1 | awk '{print $1}')
        [ -n "$line_num" ] && iptables -t nat -D PREROUTING "$line_num" 2>/dev/null || break
    done
    if command -v ip6tables >/dev/null 2>&1; then
        while ip6tables -t nat -L PREROUTING -n --line-numbers 2>/dev/null | grep -q "REDIRECT.*udp"; do
            local line_num=$(ip6tables -t nat -L PREROUTING -n --line-numbers | grep "REDIRECT.*udp" | head -n 1 | awk '{print $1}')
            [ -n "$line_num" ] && ip6tables -t nat -D PREROUTING "$line_num" 2>/dev/null || break
        done
    fi
}

setup_iptables_port_hopping() {
    local l_port="$1"
    local s_port="$2"
    local e_port="$3"
    
    log_step "配置 iptables 端口跳跃转发规则 (${s_port}-${e_port} -> ${l_port})..."
    
    clear_all_hopping_rules
    
    # 注入新规则 (IPv4 + IPv6)
    iptables -t nat -A PREROUTING -p udp --dport "${s_port}:${e_port}" -j REDIRECT --to-ports "${l_port}"
    if command -v ip6tables >/dev/null 2>&1; then
        ip6tables -t nat -A PREROUTING -p udp --dport "${s_port}:${e_port}" -j REDIRECT --to-ports "${l_port}" 2>/dev/null || true
    fi

    # 保存规则持久化
    if command -v netfilter-persistent >/dev/null 2>&1; then
        netfilter-persistent save >/dev/null 2>&1 || true
    elif command -v service >/dev/null 2>&1 && service iptables status >/dev/null 2>&1; then
        service iptables save >/dev/null 2>&1 || true
    fi
    log_info "端口跳跃 iptables 规则已生效。"
}

# 5. 生成服务端配置文件与 Systemd 服务
generate_server_config() {
    log_step "生成 Hysteria 2 服务端配置: ${HY2_CONFIG}..."
    mkdir -p "$HY2_DIR"
    command -v python3 >/dev/null && command -v qrencode >/dev/null || install_dependencies
    python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else "需要 Python 3.9+")'
    local systemd_version
    systemd_version=$(systemctl --version | awk 'NR==1 {print $2}')
    if [[ ! "$systemd_version" =~ ^[0-9]+$ ]] || (( systemd_version < 247 )); then
        log_err "私密网页需要 systemd 247+ 的凭据隔离功能。"
        return 1
    fi
    select_subscription_port

    cat > "$HY2_CONFIG" <<EOF
# Hysteria 2 Server Configuration
# Generated by hysteria2-installer
listen: :${LISTEN_PORT}
EOF

    if [[ "$CERT_TYPE" == "acme" ]]; then
        cat >> "$HY2_CONFIG" <<EOF
acme:
  domains:
    - ${SERVER_NAME}
  email: ${ACME_EMAIL}
  type: http
EOF
    else
        cat >> "$HY2_CONFIG" <<EOF
tls:
  cert: ${CERT_FILE}
  key: ${KEY_FILE}
EOF
    fi

    if [[ "$NODE_MODE" == "agent" ]]; then
        cat >> "$HY2_CONFIG" <<EOF
auth:
  type: http
  http:
    url: http://127.0.0.1:${PORTAL_LOCAL_PORT}/auth
EOF
    else
        cat >> "$HY2_CONFIG" <<EOF
auth:
  type: password
  password: $(jq -Rn --arg value "$AUTH_PASSWORD" '$value')
EOF
    fi

    cat >> "$HY2_CONFIG" <<EOF

masquerade:
  type: proxy
  proxy:
    url: http://127.0.0.1:${PORTAL_LOCAL_PORT}/
    rewriteHost: false
  listenHTTPS: :${HY2_SUB_PORT}

ignoreClientBandwidth: false
disableUDP: false

bandwidth:
  up: 1 gbps
  down: 1 gbps

# Some IPv4-only VPS instances still receive IPv6 DNS answers but have no IPv6
# default route. Use the default direct outbound over IPv4 so those answers do
# not break requests to dual-stack sites such as YouTube.
outbounds:
  - name: direct-ipv4
    type: direct
    direct:
      mode: "4"
EOF

    # 写入混淆（如果有）
    if [[ -n "$OBFS_PASSWORD" ]]; then
        cat >> "$HY2_CONFIG" <<EOF

obfs:
  type: salamander
  salamander:
    password: $(jq -Rn --arg value "$OBFS_PASSWORD" '$value')
EOF
    fi

    jq -n --arg public_ip "$PUBLIC_IP" --arg server_name "$SERVER_NAME" \
        --arg auth_password "$AUTH_PASSWORD" --arg obfs_password "$OBFS_PASSWORD" \
        --arg hop_port_range "$HOP_PORT_RANGE" --arg cert_type "$CERT_TYPE" \
        --argjson listen_port "$LISTEN_PORT" --argjson is_insecure "$IS_INSECURE" \
        --argjson subscription_port "$HY2_SUB_PORT" \
        '$ARGS.named' > "$HY2_META_FILE"
    setup_portal
    log_info "配置文件写入完成。"
}

setup_systemd() {
    log_step "配置 systemd 系统守护服务: ${HY2_SERVICE}..."
    
    # 系统内核网络与 UDP 缓冲优化
    sysctl -w net.core.rmem_max=8388608 >/dev/null 2>&1 || true
    sysctl -w net.core.wmem_max=8388608 >/dev/null 2>&1 || true
    
    cat > "$HY2_SERVICE" <<EOF
[Unit]
Description=Hysteria 2 Server Service
Documentation=https://v2.hysteria.network/
After=network.target network-online.target
Wants=network-online.target
After=hysteria-portal.service
Wants=hysteria-portal.service

[Service]
Type=simple
User=root
WorkingDirectory=${HY2_DIR}
ExecStart=${HY2_BIN} server -c ${HY2_CONFIG}
Restart=always
RestartSec=3
LimitNOFILE=65535
LimitNPROC=65535
AmbientCapabilities=CAP_NET_BIND_SERVICE CAP_NET_RAW

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable hysteria-server >/dev/null 2>&1
    systemctl restart hysteria-server
    
    sleep 2
    if systemctl is-active hysteria-server >/dev/null 2>&1; then
        log_info "Hysteria 2 服务启动成功！"
    else
        log_err "Hysteria 2 服务启动异常，请运行 'journalctl -u hysteria-server -e' 查看日志！"
        return 1
    fi
}

# 6. 显示私密信息页的访问凭据，节点数据只在认证后提供。
show_client_configs() {
    if [[ ! -f "$HY2_DIR/portal-access.json" ]]; then
        log_err "尚未生成信息页，请重新配置。"
        return 1
    fi
    jq -r '"私密信息页: " + .url, "用户名: " + .username, "密码: " + .password' "$HY2_DIR/portal-access.json"
    local key=$(jq -r '.api_key // empty' "$HY2_DIR/portal-access.json")
    if [[ -n "$key" ]]; then
        echo -e "${YELLOW}节点通信 API Key (供商城集群对接): ${GREEN}${key}${PLAIN}"
    fi
    log_info "请在云安全组放行信息页 URL 中的 TCP 端口。"
    log_warn "自签证书模式需核对证书指纹后信任；推荐使用有效域名证书。"
}

write_portal_program() {
    cat > "$HY2_DIR/portal.py" <<'PYPORTAL'
"""仅监听回环地址；公网 TLS 由 Hysteria 的 masquerade proxy 提供。
集成多租户 REST API、同时在线 IP 限制引擎与可视化多用户管理控制台。
"""
import base64
import hashlib
import hmac
import html
import json
import secrets
import subprocess
import sys
import time
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlencode


STYLE = """
:root{color-scheme:light;--ink:#122b31;--muted:#667c81;--line:#dce7e6;--accent:#087f74;--accent-hover:#066960;--danger:#cf3c3c;--danger-bg:#fdf2f2;--brand-bg:#eaf5ef}
*{box-sizing:border-box}body{margin:0;background:#f3f7f6;color:var(--ink);font:15px/1.6 system-ui,-apple-system,"Segoe UI","Microsoft YaHei",sans-serif}
main{max-width:1160px;margin:auto;padding:32px 28px 48px}.topbar{display:flex;justify-content:space-between;align-items:center;padding-bottom:32px}
.brand{font-weight:800;letter-spacing:.04em;display:flex;gap:10px;align-items:center}.logo{background:var(--ink);color:white;border-radius:12px;padding:7px 12px;font-size:17px}.private{font-size:12px;color:var(--accent);border:1px solid #c3ddd5;border-radius:30px;padding:5px 12px;background:#eaf5ef}
.eyebrow{font-size:11px;letter-spacing:.16em;font-weight:750;color:var(--accent)}h1{font-size:34px;letter-spacing:-.04em;margin:6px 0}h2{font-size:18px;margin:0 0 4px}p{margin:0;color:var(--muted)}.hero{margin-bottom:26px}.hero p{font-size:14px}
.layout{display:grid;grid-template-columns:320px minmax(0,1fr);gap:22px;align-items:start}.card{background:#fff;border:1px solid var(--line);border-radius:20px;padding:24px;box-shadow:0 5px 22px #183f3505}.qr-card{text-align:center}.qr-frame{background:#fff;border:1px solid var(--line);border-radius:16px;padding:14px;margin:20px 0}.qr-frame img{display:block;width:100%;height:auto}.hint{font-size:12px}.tags{display:flex;gap:6px;justify-content:center;flex-wrap:wrap;margin-top:18px}.tag{background:#f0f5f4;color:#526a70;border-radius:6px;padding:3px 8px;font-size:11px}
.stack{display:grid;gap:18px}.card-head{display:flex;gap:14px;align-items:center;margin-bottom:16px}.step{display:grid;place-items:center;flex:0 0 38px;height:38px;border-radius:11px;background:#e8f4f0;color:var(--accent);font-weight:750}.card-head p{font-size:12px}textarea{display:block;width:100%;min-width:0;border:1px solid var(--line);background:#f7faf9;border-radius:12px;padding:14px;color:#35545c;font:12px/1.7 ui-monospace,SFMono-Regular,Consolas,monospace;resize:vertical;overflow-wrap:anywhere}textarea.link{height:92px}textarea.config{height:290px;margin-top:18px}textarea:focus{outline:2px solid #65b3a5;outline-offset:2px}.actions{display:flex;gap:10px;align-items:center;margin-top:14px;flex-wrap:wrap}.button{display:inline-flex;align-items:center;justify-content:center;gap:6px;border:1px solid var(--line);background:white;border-radius:9px;padding:9px 15px;color:var(--ink);text-decoration:none;font:600 12px/1.5 inherit;cursor:pointer}.button.primary{background:var(--accent);color:white;border-color:var(--accent)}.button.danger{background:var(--danger);color:white;border-color:var(--danger)}.button:hover{filter:brightness(.94)}button:focus-visible,a:focus-visible,summary:focus-visible{outline:3px solid #65b3a5;outline-offset:3px}.note{font-size:12px;margin-top:12px}.advanced{margin-top:24px}.advanced-title{display:flex;align-items:center;justify-content:space-between;margin-bottom:12px}.advanced-title p{font-size:12px}.config-grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}summary{cursor:pointer;font-weight:650;list-style-position:inside}summary span{font-size:11px;font-weight:400;color:var(--muted);margin-left:10px}.security{margin-top:24px;padding:15px 18px;border:1px solid #d8e6df;border-radius:12px;background:#eaf2ed;color:#4f6a60;font-size:12px}footer{display:flex;justify-content:space-between;margin-top:22px;color:#879996;font-size:11px}.status{font-size:12px;color:var(--accent)}

/* 登录与多用户控制台样式 */
.login-wrap{min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px 16px;background:radial-gradient(ellipse at top,#eef5f3 0%,#f3f7f6 100%)}
.login-card{width:100%;max-width:420px;background:#fff;border:1px solid var(--line);border-radius:24px;padding:36px 30px;box-shadow:0 12px 36px rgba(18,43,49,0.06)}
.login-brand{text-align:center;margin-bottom:28px}
.login-logo{display:inline-flex;align-items:center;justify-content:center;width:60px;height:60px;background:var(--accent);color:#fff;border-radius:18px;font-size:26px;font-weight:800;box-shadow:0 6px 16px rgba(8,127,116,0.22);margin-bottom:14px}
.login-badge{display:inline-block;font-size:11px;letter-spacing:.14em;font-weight:750;color:var(--accent);text-transform:uppercase;margin-bottom:6px}
.login-title{font-size:24px;letter-spacing:-.03em;color:var(--ink);margin:0 0 6px;font-weight:700}
.login-sub{font-size:13px;color:var(--muted);margin:0}
.login-form{display:grid;gap:18px}
.field-group{display:grid;gap:7px}
.field-label{font-size:13px;font-weight:650;color:var(--ink);display:flex;justify-content:space-between;align-items:center}
.field-input{width:100%;height:44px;padding:0 14px;border:1px solid var(--line);border-radius:11px;background:#f7faf9;color:var(--ink);font-size:14px;transition:all .15s ease}
.field-input:focus{outline:none;border-color:var(--accent);background:#fff;box-shadow:0 0 0 3px rgba(8,127,116,0.12)}
.field-pwd{position:relative}
.field-pwd input{padding-right:68px}
.toggle-pwd{position:absolute;right:8px;top:50%;transform:translateY(-50%);background:none;border:none;color:var(--muted);font-size:12px;font-weight:600;padding:6px 8px;cursor:pointer;border-radius:6px}
.toggle-pwd:hover{color:var(--accent);background:#eef5f3}
.remember-row{display:flex;align-items:center;gap:8px;margin-top:2px}
.remember-row input{accent-color:var(--accent);cursor:pointer;width:15px;height:15px}
.remember-row label{font-size:13px;color:var(--muted);cursor:pointer;user-select:none}
.btn-submit{width:100%;height:46px;background:var(--accent);color:#fff;border:none;border-radius:12px;font-size:14px;font-weight:700;cursor:pointer;transition:all .15s;margin-top:6px;display:flex;align-items:center;justify-content:center}
.btn-submit:hover{background:var(--accent-hover);box-shadow:0 4px 12px rgba(8,127,116,0.2)}
.btn-submit:active{transform:scale(0.99)}
.error-tip{padding:10px 14px;border-radius:10px;background:var(--danger-bg);color:var(--danger);font-size:13px;font-weight:550;display:flex;align-items:center;gap:8px;border:1px solid #f6cfcf}
.login-footer{margin-top:24px;padding-top:18px;border-top:1px solid #edf2f1;font-size:12px;color:var(--muted);line-height:1.6;text-align:center}
.login-footer code{background:#eef4f2;color:#33565f;padding:2px 6px;border-radius:4px;font-family:ui-monospace,SFMono-Regular,Consolas,monospace}

/* 多用户与集群控制台卡片 */
.user-panel{margin-top:28px}
.user-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;flex-wrap:wrap;gap:12px}
.user-stats{display:flex;gap:12px;flex-wrap:wrap}
.badge-count{background:var(--brand-bg);color:var(--accent);border:1px solid #c3ddd5;border-radius:20px;padding:4px 10px;font-size:12px;font-weight:700}
.user-table-wrap{width:100%;overflow-x:auto;border:1px solid var(--line);border-radius:14px;background:#fff}
.user-table{width:100%;border-collapse:collapse;text-align:left;font-size:13px}
.user-table th{background:#f8fbfb;padding:12px 14px;color:var(--muted);font-weight:700;border-bottom:1px solid var(--line);white-space:nowrap}
.user-table td{padding:12px 14px;border-bottom:1px solid var(--line);vertical-align:middle;white-space:nowrap}
.user-table tr:last-child td{border-bottom:none}
.status-pill{display:inline-block;padding:2px 8px;border-radius:20px;font-size:11px;font-weight:700}
.status-pill.active{background:#eafaf3;color:#0b8650}
.status-pill.expired{background:#fff1f0;color:#cf3c3c}
.status-pill.limit{background:#fff7e6;color:#d46b08}
.api-box{background:#f7faf9;border:1px solid var(--line);border-radius:12px;padding:14px;margin-bottom:16px;display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}
.api-key-code{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:12px;color:#35545c;word-break:break-all}
.modal-form{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;background:#f9fbfb;border:1px solid var(--line);border-radius:12px;padding:16px;margin-bottom:16px}
.modal-form input{height:38px;padding:0 10px;border:1px solid var(--line);border-radius:8px;font-size:13px;background:#fff}

@media(max-width:760px){
  main{padding:20px 16px 32px}.topbar{padding-bottom:24px}.layout,.config-grid{grid-template-columns:1fr}.qr-frame{max-width:248px;margin:18px auto}.card{padding:20px}h1{font-size:28px}.advanced-title{display:block}footer{gap:15px}.private{font-size:10px}.brand{font-size:13px}
  .login-card{padding:28px 20px;border-radius:20px}
}
"""

SCRIPT = """
document.querySelectorAll('[data-copy]').forEach(button => {
  button.addEventListener('click', async () => {
    const field = document.getElementById(button.dataset.copy);
    const status = document.getElementById('copy-status');
    try {
      const val = field.value || field.textContent || '';
      await navigator.clipboard.writeText(val);
      status.textContent = '已复制到剪贴板 ✓';
      button.textContent = '已复制 ✓';
      setTimeout(() => { button.textContent = '复制'; }, 1800);
    } catch (_) {
      if (field.select) { field.focus(); field.select(); }
      status.textContent = '已选中，请按 Ctrl+C 复制';
    }
  });
});
"""

LOGIN_SCRIPT = """
function toggleSecret(id, btn) {
  const el = document.getElementById(id);
  if (el.type === 'password') {
    el.type = 'text';
    btn.textContent = '隐藏';
  } else {
    el.type = 'password';
    btn.textContent = '显示';
  }
}
"""


def page_html(m, uri, subscription, clash, sing, users=None, api_key=None, token=""):
    def field(identifier, value, kind='link'):
        return f'<textarea id="{identifier}" class="{kind}" aria-label="{identifier}" readonly spellcheck="false">{html.escape(value)}</textarea>'
    def copy(identifier):
        return f'<button class="button primary" type="button" data-copy="{identifier}">复制</button>'
    
    is_insecure = m.get('is_insecure', False)
    server_name = m.get('server_name') or m.get('public_ip', 'localhost')
    public_ip = m.get('public_ip', server_name)
    host = public_ip if is_insecure else server_name
    sub_port = m.get('subscription_port', 8443)
    listen_port = m.get('listen_port', 19984)
    obfs_pw = m.get('obfs_password', '')
    users = users or {}
    now_ts = int(time.time())
    
    # 渲染多用户表格行
    user_rows = []
    active_count = 0
    for uid, u in sorted(users.items(), key=lambda x: x[1].get('created_at', 0), reverse=True):
        is_active = u.get('status') == 'active' and u.get('expires_at', 0) >= now_ts
        if is_active:
            active_count += 1
        status_html = '<span class="status-pill active">正常</span>' if is_active else '<span class="status-pill expired">已到期/停用</span>'
        expires_str = time.strftime('%Y-%m-%d %H:%M', time.localtime(u.get('expires_at', 0))) if u.get('expires_at', 0) < 2000000000 else '永久有效'
        ip_limit = u.get('ip_limit', 0)
        ip_limit_str = f"{ip_limit} IP" if ip_limit > 0 else '不限'
        online_ips = len(u.get('online_ips', {}))
        online_str = f'<span class="badge-count" style="font-size:11px;">{online_ips} 在线</span>' if online_ips > 0 else '<span style="color:var(--muted)">0</span>'
        note = u.get('note') or '-'
        
        # 用户专属直链弹窗触发
        user_rows.append(f'''<tr>
          <td><strong>{html.escape(uid)}</strong><div style="font-size:11px;color:var(--muted)">{html.escape(note)}</div></td>
          <td>{status_html}</td>
          <td>{ip_limit_str} ({online_str})</td>
          <td>{expires_str}</td>
          <td><code style="font-size:11px">{html.escape(u.get("password","")[:4] + "****" + u.get("password","")[-4:])}</code></td>
          <td>
            <form method="POST" action="/{token}/manage-user" style="display:inline" onsubmit="return confirm('确定注销此用户？')">
              <input type="hidden" name="action" value="delete">
              <input type="hidden" name="user_id" value="{html.escape(uid)}">
              <button class="button danger" style="padding:4px 10px;font-size:11px" type="submit">删除</button>
            </form>
          </td>
        </tr>''')

    users_table_html = "".join(user_rows) or '<tr><td colspan="6" style="text-align:center;color:var(--muted);padding:20px">暂无多用户数据</td></tr>'

    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>HY2 · 节点与多用户控制中心</title><style>{STYLE}</style></head><body><main>
<nav class="topbar" aria-label="页面标识"><div class="brand"><span class="logo">H₂</span> HYSTERIA <span> / 节点与集群控制中心</span></div><span class="private">● 集群运行中</span></nav>
<header class="hero"><div class="eyebrow">CLUSTER AGENT & MULTI-TENANT</div><h1>节点配置与多用户管理</h1><p>支持原生 Hysteria 2 客户端订阅，同时提供 REST API 自动开户与同时在线 IP 限制。</p></header>

<!-- API 对接控制台卡片 -->
<section class="card" style="margin-bottom:24px;border-left:4px solid var(--accent)">
  <div class="card-head"><span class="step">API</span><div><h2>集群通信与商城对接凭据</h2><p>可直接填入 pay.isoziyuan.com / admin / node-panels</p></div></div>
  <div class="api-box">
    <div><div style="font-size:11px;color:var(--muted);font-weight:700">API 基础地址 (Base URL)</div><div class="api-key-code" id="api-base-val">https://{host}:{sub_port}</div></div>
    <button class="button" type="button" data-copy="api-base-val">复制地址</button>
  </div>
  <div class="api-box">
    <div><div style="font-size:11px;color:var(--muted);font-weight:700">通信密钥 (Bearer API Key)</div><div class="api-key-code" id="api-key-val">{html.escape(api_key or "")}</div></div>
    <button class="button primary" type="button" data-copy="api-key-val">复制 Key</button>
  </div>
</section>

<!-- 多租户与在线 IP 管理中心 -->
<section class="card user-panel" style="margin-bottom:24px">
  <div class="user-header">
    <div><h2>多用户与 IP 限制管理</h2><p style="font-size:13px">实时监控当前节点有效用户、到期状态与在线客户端 IP 限制</p></div>
    <div class="user-stats">
      <span class="badge-count">有效用户: {active_count} / {len(users)}</span>
    </div>
  </div>

  <!-- 手动添加用户表单 -->
  <details style="margin-bottom:18px"><summary class="button" style="margin-bottom:12px;list-style:none">＋ 手动添加/开通新用户</summary>
    <form class="modal-form" method="POST" action="/{token}/manage-user">
      <input type="hidden" name="action" value="create">
      <input name="user_id" placeholder="用户标识 (如: user_01)" required>
      <input name="password" placeholder="连接密码 (留空随机生成)">
      <input name="duration_days" type="number" value="30" placeholder="有效天数 (默认30)">
      <input name="ip_limit" type="number" value="0" placeholder="限制同时在线 IP 数 (0为不限)">
      <input name="note" placeholder="备注说明 (如: 客户小明)">
      <button class="button primary" type="submit">立即创建用户</button>
    </form>
  </details>

  <div class="user-table-wrap">
    <table class="user-table">
      <thead><tr><th>用户标识</th><th>状态</th><th>IP 限制 (实时)</th><th>到期时间</th><th>连接密码</th><th>操作</th></tr></thead>
      <tbody>{users_table_html}</tbody>
    </table>
  </div>
</section>

<!-- 默认节点导入卡片 -->
<div class="layout"><section class="card qr-card"><div class="eyebrow">QUICK CONNECT</div><h2>主管理员节点扫码</h2><p class="hint">适用于支持 Hysteria 2 的客户端</p><div class="qr-frame"><img src="qr.svg" alt="HY2 节点导入二维码" width="260" height="260"></div><p class="hint">打开客户端的「扫描二维码」功能</p><div class="tags"><span class="tag">Hysteria 2</span><span class="tag">TLS</span><span class="tag">''' + ('Salamander' if obfs_pw else 'QUIC') + '''</span></div></section>
<div class="stack"><section class="card"><div class="card-head"><span class="step">01</span><div><h2>主节点链接</h2><p>v2rayN / Nekobox / Shadowrocket</p></div></div>''' + field('hy2-link', uri) + '<div class="actions">' + copy('hy2-link') + '</div><p class="note">' + html.escape(host) + ' · UDP ' + str(int(listen_port)) + '''</p></section>
<section class="card"><div class="card-head"><span class="step">02</span><div><h2>Clash 订阅</h2><p>适用于 Clash Meta / Mihomo 内核</p></div></div>''' + field('clash-subscription', subscription) + '<div class="actions">' + copy('clash-subscription') + '''<a class="button" href="clash.yaml" download="clash.yaml">下载配置 ↓</a></div><p class="note">在客户端添加订阅；若不支持带账号密码的 URL，可下载后导入。</p></section></div></div>

<section class="advanced"><div class="advanced-title"><h2>配置文件</h2><p>需要手动调整？展开查看完整内容。</p></div><div class="config-grid">
<details class="card"><summary>Clash / Mihomo <span>完整配置</span></summary>''' + field('clash-config', clash, 'config') + '<div class="actions">' + copy('clash-config') + '''<a class="button" href="clash.yaml" download="clash.yaml">下载 ↓</a></div></details>
<details class="card"><summary>Sing-box <span>出站配置片段</span></summary>''' + field('sing-config', sing, 'config') + '<div class="actions">' + copy('sing-config') + '''<a class="button" href="sing-box.json" download="sing-box.json">下载 ↓</a></div></details></div></section>
<div class="security">私密提示 · 链接和二维码包含连接凭据，请勿公开分享或发送截图给他人。</div><p id="copy-status" class="status" role="status" aria-live="polite"></p><footer><span>HYSTERIA 2 / PRIVATE CLUSTER PORTAL</span><span>配置由你的服务器动态生成</span></footer></main><script>''' + SCRIPT + '</script></body></html>'


def login_html(token, error_msg=None):
    error_banner = f'<div class="error-tip" role="alert"><span>⚠</span><span>{html.escape(error_msg)}</span></div>' if error_msg else ''
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>验证访问 · Hysteria 2 节点中心</title><style>{STYLE}</style></head><body>
<div class="login-wrap"><div class="login-card">
<div class="login-brand"><div class="login-logo">H₂</div><div class="login-badge">HYSTERIA 2 GATEWAY</div><h1 class="login-title">私密身份认证</h1><p class="login-sub">请输入服务器生成的专属凭据以进入节点中心</p></div>
<form class="login-form" method="POST" action="/{token}/login">
{error_banner}
<div class="field-group"><label class="field-label" for="username">用户名 (Username)</label><input class="field-input" id="username" name="username" type="text" autocomplete="username" required autofocus placeholder="输入随机生成的用户名"></div>
<div class="field-group"><div class="field-label"><label for="password">密码 (Password)</label></div><div class="field-pwd"><input class="field-input" id="password" name="password" type="password" autocomplete="current-password" required placeholder="输入访问密钥"><button type="button" class="toggle-pwd" onclick="toggleSecret('password', this)">显示</button></div></div>
<div class="remember-row"><input type="checkbox" id="remember" name="remember" value="1" checked><label for="remember">在此浏览器保持登录（30天）</label></div>
<button class="btn-submit" type="submit">立即进入私密中心 →</button>
</form>
<div class="login-footer">如果遗忘凭据，随时在服务器终端执行<br><code>bash install.sh info</code> 找回账号密码</div>
</div></div>
<script>{LOGIN_SCRIPT}</script></body></html>'''


def content_policy(extra_script=None):
    def digest(value):
        return base64.b64encode(hashlib.sha256(value.encode()).digest()).decode()
    scripts = ["'sha256-" + digest(SCRIPT) + "'", "'sha256-" + digest(LOGIN_SCRIPT) + "'"]
    if extra_script:
        scripts.append("'sha256-" + digest(extra_script) + "'")
    return ("default-src 'none'; img-src 'self'; style-src 'sha256-" + digest(STYLE)
            + "'; script-src " + " ".join(scripts)
            + "; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")


def artifacts(m, auth_override=None, name_override=None):
    is_insecure = m.get('is_insecure', False)
    server_name = m.get('server_name') or m.get('public_ip', 'localhost')
    public_ip = m.get('public_ip', server_name)
    host = public_ip if is_insecure else server_name
    name = name_override or ('Hy2-' + host)
    password = auth_override or m.get('auth_password', '')
    listen_port = m.get('listen_port', 19984)
    obfs_password = m.get('obfs_password', '')
    hop_port_range = m.get('hop_port_range', '')

    params = {'sni': server_name}
    if is_insecure:
        params['insecure'] = '1'
    if obfs_password:
        params.update({'obfs': 'salamander', 'obfs-password': obfs_password})
    if hop_port_range:
        params['mport'] = hop_port_range
    uri = f"hysteria2://{quote(password, safe='')}@{host}:{listen_port}?{urlencode(params)}#{quote(name)}"
    proxy = dict(name=name, type='hysteria2', server=host, port=listen_port,
                 password=password, sni=server_name, **{'skip-cert-verify': is_insecure})
    sing = dict(type='hysteria2', tag=name, server=host, server_port=listen_port,
                password=password, tls=dict(enabled=True, server_name=server_name, insecure=is_insecure))
    if hop_port_range:
        proxy['ports'] = str(listen_port) + ',' + hop_port_range
        sing['server_ports'] = [str(listen_port), hop_port_range.replace('-', ':')]
        del sing['server_port']
    if obfs_password:
        proxy.update({'obfs': 'salamander', 'obfs-password': obfs_password})
        sing['obfs'] = dict(type='salamander', password=obfs_password)
    clash = {'mixed-port': 7890, 'allow-lan': False, 'mode': 'rule', 'proxies': [proxy],
             'proxy-groups': [{'name': 'PROXY', 'type': 'select', 'proxies': [name, 'DIRECT']}],
             'rules': ['MATCH,PROXY']}
    return uri, json.dumps(clash, ensure_ascii=False, indent=2), json.dumps({'outbounds': [sing]}, ensure_ascii=False, indent=2)


def prepare(meta_path, port, node_api_key=None):
    m = json.loads(Path(meta_path).read_text())
    uri, clash, sing = artifacts(m)
    qr = subprocess.run(['qrencode', '-t', 'SVG', '-o', '-'], input=uri.encode(), capture_output=True, check=True).stdout
    user, password, token = secrets.token_hex(8), secrets.token_urlsafe(32), secrets.token_hex(32)
    host = m['public_ip'] if m['is_insecure'] else m['server_name']
    base = f"https://{host}:{m['subscription_port']}/{token}/"
    subscription = f"https://{user}:{password}@{host}:{m['subscription_port']}/{token}/clash.yaml"
    session_secret = secrets.token_hex(32)
    api_key = node_api_key or secrets.token_hex(24)

    users = {
        'admin_master': {
            'password': m['auth_password'],
            'expires_at': 2085974400,
            'ip_limit': 0,  # 0 为不限制
            'status': 'active',
            'created_at': int(time.time()),
            'note': 'Master Admin'
        }
    }
    page = page_html(m, uri, subscription, clash, sing, users=users, api_key=api_key, token=token)
    auth = base64.b64encode(f'{user}:{password}'.encode())

    data = dict(port=int(port), token=token, auth_hash=hashlib.sha256(auth).hexdigest(),
                session_secret=session_secret, api_key=api_key, users=users,
                page=page, qr=qr.decode(), clash=clash, sing=sing)
    root = Path(meta_path).parent
    for filename, value in [('portal.json', data), ('portal-access.json', dict(url=base, username=user, password=password, api_key=api_key))]:
        path = root / filename
        path.write_text(json.dumps(value, ensure_ascii=False))
        path.chmod(0o600)


def refresh(meta_path):
    root = Path(meta_path).parent
    m = json.loads(Path(meta_path).read_text())
    access = json.loads((root / 'portal-access.json').read_text())
    path = root / 'portal.json'
    data = json.loads(path.read_text())
    uri, clash, sing = artifacts(m)
    host = m['public_ip'] if m['is_insecure'] else m['server_name']
    subscription = f"https://{access['username']}:{access['password']}@{host}:{m['subscription_port']}/{data['token']}/clash.yaml"
    
    if 'session_secret' not in data:
        data['session_secret'] = secrets.token_hex(32)
    if 'api_key' not in data:
        data['api_key'] = access.get('api_key') or secrets.token_hex(24)
        access['api_key'] = data['api_key']
        (root / 'portal-access.json').write_text(json.dumps(access, ensure_ascii=False))
    if 'users' not in data:
        data['users'] = {
            'admin_master': {
                'password': m['auth_password'],
                'expires_at': 2085974400,
                'ip_limit': 0,
                'status': 'active',
                'created_at': int(time.time()),
                'note': 'Master Admin'
            }
        }
    data['page'] = page_html(m, uri, subscription, clash, sing, users=data['users'], api_key=data['api_key'], token=data['token'])
    
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False))
    temporary.chmod(0o600)
    temporary.replace(path)


def serve(path):
    portal_path = Path(path)
    data = json.loads(portal_path.read_text())
    session_secret = data.get('session_secret', data['auth_hash'])
    meta_path = portal_path.parent / 'client_meta.json'

    # 在线客户端 IP 滑动窗口跟踪器: { uid: { "ip_str": last_seen_ts } }
    ip_tracker = {}
    IP_TIMEOUT_SECONDS = 180  # 3 分钟内有鉴权活动视为同一个在线 IP

    def save_data():
        try:
            temp = portal_path.with_suffix('.tmp')
            temp.write_text(json.dumps(data, ensure_ascii=False))
            temp.chmod(0o600)
            temp.replace(portal_path)
        except OSError:
            disk_path = Path('/etc/hysteria/portal.json')
            if disk_path.exists():
                disk_temp = disk_path.with_suffix('.tmp')
                disk_temp.write_text(json.dumps(data, ensure_ascii=False))
                disk_temp.chmod(0o600)
                disk_temp.replace(disk_path)

    def regenerate_page():
        m = json.loads(meta_path.read_text()) if meta_path.exists() else {}
        uri, clash, sing = artifacts(m)
        root = portal_path.parent
        access_file = root / 'portal-access.json'
        access = json.loads(access_file.read_text()) if access_file.exists() else {}
        host = m.get('public_ip', '127.0.0.1') if m.get('is_insecure') else m.get('server_name', 'localhost')
        subscription = f"https://{access.get('username','')}:{access.get('password','')}@{host}:{m.get('subscription_port',8443)}/{data['token']}/clash.yaml"
        
        # 附加在线 IP 统计到展示字典
        now_ts = int(time.time())
        display_users = {}
        for uid, uinfo in data.get('users', {}).items():
            u_copy = dict(uinfo)
            user_ips = {ip: t for ip, t in ip_tracker.get(uid, {}).items() if now_ts - t < IP_TIMEOUT_SECONDS}
            u_copy['online_ips'] = user_ips
            display_users[uid] = u_copy

        data['page'] = page_html(m, uri, subscription, clash, sing, users=display_users, api_key=data.get('api_key'), token=data['token'])
        save_data()

    def sign_session(token):
        sig = hmac.new(session_secret.encode(), f'sess:{token}'.encode(), hashlib.sha256).hexdigest()
        return f'{token}.{sig}'

    def verify_session(cookie_header):
        if not cookie_header:
            return False
        cookies = SimpleCookie()
        try:
            cookies.load(cookie_header)
        except Exception:
            return False
        if 'hy2_session' not in cookies:
            return False
        raw = cookies['hy2_session'].value
        if '.' not in raw:
            return False
        t, sig = raw.split('.', 1)
        expected = hmac.new(session_secret.encode(), f'sess:{t}'.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(t, data['token']) and hmac.compare_digest(sig, expected)

    class Handler(BaseHTTPRequestHandler):
        server_version = 'Gateway'
        sys_version = ''
        def setup(self):
            super().setup()
            self.connection.settimeout(5)
        def log_message(self, *args):
            pass

        def verify_api_key(self):
            auth_header = self.headers.get('Authorization', '')
            expected = 'Bearer ' + data.get('api_key', '')
            return hmac.compare_digest(auth_header, expected)

        def is_authenticated(self):
            auth = self.headers.get('Authorization', '')
            if auth.startswith('Basic '):
                digest = hashlib.sha256(auth.removeprefix('Basic ').encode()).hexdigest()
                if hmac.compare_digest(digest, data['auth_hash']):
                    return True
            return verify_session(self.headers.get('Cookie', ''))

        def reply_json(self, code, payload):
            body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
            self.send_response(code)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            now = time.monotonic()
            self.server.requests[:] = [t for t in self.server.requests if now-t < 1]
            self.server.failures[:] = [t for t in self.server.failures if now-t < 60]
            if len(self.server.requests) >= 50 or len(self.server.failures) >= 60:
                return self.reply(429, b'Too many requests')
            self.server.requests.append(now)

            # 1. Hysteria 2 本地 HTTP 动态鉴权与 IP 限额拦截端点
            if self.path == '/auth':
                try:
                    length = int(self.headers.get('Content-Length', 0))
                    body = self.rfile.read(length).decode('utf-8')
                    req_data = json.loads(body)
                    client_auth = req_data.get('auth', '').strip()
                    client_addr = req_data.get('addr', '')
                    # 解析客户端 IPv4 / IPv6 地址（去掉端口）
                    client_ip = client_addr.rsplit(':', 1)[0].strip('[]') if client_addr else ''
                except Exception:
                    return self.reply_json(200, {'ok': False, 'msg': 'Bad auth request'})

                now_ts = int(time.time())
                users = data.get('users', {})
                matched_uid, matched_user = None, None
                for uid, uinfo in users.items():
                    if uinfo.get('password') == client_auth:
                        matched_uid, matched_user = uid, uinfo
                        break

                if not matched_user:
                    return self.reply_json(200, {'ok': False, 'msg': 'User not found'})

                if matched_user.get('status') != 'active':
                    return self.reply_json(200, {'ok': False, 'msg': 'User account inactive'})

                if matched_user.get('expires_at', 0) < now_ts:
                    return self.reply_json(200, {'ok': False, 'msg': 'User account expired'})

                # -------- 同时在线 IP 限制检查 -------- #
                ip_limit = int(matched_user.get('ip_limit', 0))
                if ip_limit > 0 and client_ip:
                    tracker = ip_tracker.setdefault(matched_uid, {})
                    # 清理超时 IP
                    active_ips = {ip: t for ip, t in tracker.items() if now_ts - t < IP_TIMEOUT_SECONDS}
                    ip_tracker[matched_uid] = active_ips

                    if client_ip not in active_ips and len(active_ips) >= ip_limit:
                        # 超过允许的最大 IP 数，拒绝本次连接
                        return self.reply_json(200, {'ok': False, 'msg': f'Concurrent IP limit exceeded ({ip_limit} max)'})
                    # 记录活跃 IP 活动时间戳
                    active_ips[client_ip] = now_ts
                elif client_ip:
                    # 不限制 IP 时依然记录供控制台展示
                    tracker = ip_tracker.setdefault(matched_uid, {})
                    tracker[client_ip] = now_ts

                return self.reply_json(200, {'ok': True, 'id': matched_uid})

            # 2. REST API 接口通道（供商城 pay.isoziyuan.com 调度）
            if self.path.startswith('/api/v1/'):
                if not self.verify_api_key():
                    return self.reply_json(401, {'ok': False, 'error': 'Unauthorized API key'})

                try:
                    length = int(self.headers.get('Content-Length', 0))
                    body = self.rfile.read(length).decode('utf-8') if length > 0 else '{}'
                    params = json.loads(body)
                except Exception:
                    return self.reply_json(400, {'ok': False, 'error': 'Invalid JSON body'})

                sub = self.path[len('/api/v1/'):]
                now_ts = int(time.time())

                # 动态开户: /api/v1/users/create (支持 ip_limit)
                if sub == 'users/create':
                    user_id = params.get('user_id') or ('hy2_' + secrets.token_hex(6))
                    pwd = params.get('password') or secrets.token_hex(16)
                    days = int(params.get('duration_days', 30))
                    ip_limit = int(params.get('ip_limit', 0))
                    expires = int(params.get('expires_at', now_ts + days * 86400))
                    note = params.get('note', '')

                    data.setdefault('users', {})[user_id] = {
                        'password': pwd,
                        'expires_at': expires,
                        'ip_limit': ip_limit,
                        'status': 'active',
                        'created_at': now_ts,
                        'note': note
                    }
                    regenerate_page()

                    m = json.loads(meta_path.read_text()) if meta_path.exists() else {}
                    uri, clash_yaml, sing_json = artifacts(m, auth_override=pwd, name_override=f"Hy2-{user_id}")
                    return self.reply_json(200, {
                        'ok': True,
                        'user_id': user_id,
                        'password': pwd,
                        'ip_limit': ip_limit,
                        'expires_at': expires,
                        'uri': uri,
                        'clash': clash_yaml,
                        'sing_box': sing_json
                    })

                elif sub == 'users/renew':
                    user_id = params.get('user_id')
                    days = int(params.get('extend_days', 30))
                    u = data.get('users', {}).get(user_id)
                    if not u:
                        return self.reply_json(404, {'ok': False, 'error': 'User not found'})
                    base_time = max(u.get('expires_at', 0), now_ts)
                    u['expires_at'] = base_time + days * 86400
                    u['status'] = 'active'
                    regenerate_page()
                    return self.reply_json(200, {'ok': True, 'user_id': user_id, 'expires_at': u['expires_at']})

                elif sub == 'users/delete':
                    user_id = params.get('user_id')
                    if user_id in data.get('users', {}):
                        del data['users'][user_id]
                        if user_id in ip_tracker:
                            del ip_tracker[user_id]
                        regenerate_page()
                        return self.reply_json(200, {'ok': True, 'message': 'User deleted'})
                    return self.reply_json(404, {'ok': False, 'error': 'User not found'})

                return self.reply_json(404, {'ok': False, 'error': 'API endpoint not found'})

            # 3. Web 网页版直接增删用户通道 (需已登录 Session)
            prefix = '/' + data['token'] + '/'
            if self.path == prefix + 'manage-user':
                if not self.is_authenticated():
                    return self.reply(401, b'Unauthorized')
                try:
                    length = int(self.headers.get('Content-Length', 0))
                    body = self.rfile.read(length).decode('utf-8')
                    form = parse_qs(body)
                    action = form.get('action', [''])[0]
                    user_id = form.get('user_id', [''])[0].strip()
                    now_ts = int(time.time())

                    if action == 'create' and user_id:
                        pwd = form.get('password', [''])[0].strip() or secrets.token_hex(16)
                        days = int(form.get('duration_days', ['30'])[0] or 30)
                        ip_limit = int(form.get('ip_limit', ['0'])[0] or 0)
                        note = form.get('note', [''])[0].strip()
                        data.setdefault('users', {})[user_id] = {
                            'password': pwd,
                            'expires_at': now_ts + days * 86400,
                            'ip_limit': ip_limit,
                            'status': 'active',
                            'created_at': now_ts,
                            'note': note
                        }
                    elif action == 'delete' and user_id:
                        if user_id in data.get('users', {}):
                            del data['users'][user_id]
                            if user_id in ip_tracker:
                                del ip_tracker[user_id]

                    regenerate_page()
                    self.send_response(302)
                    self.send_header('Location', prefix)
                    self.end_headers()
                    return
                except Exception:
                    return self.reply(400, b'Bad request')

            # 4. Web 表单登录
            if self.path == prefix + 'login':
                try:
                    length = int(self.headers.get('Content-Length', 0))
                    if length > 4096:
                        return self.reply(400, b'Bad request')
                    body = self.rfile.read(length).decode('utf-8', errors='ignore')
                    params = parse_qs(body)
                    user = params.get('username', [''])[0]
                    pwd = params.get('password', [''])[0]
                    remember = params.get('remember', ['0'])[0] == '1'
                except Exception:
                    return self.reply(400, b'Bad request')

                submitted_auth = base64.b64encode(f'{user}:{pwd}'.encode())
                submitted_digest = hashlib.sha256(submitted_auth).hexdigest()

                if not hmac.compare_digest(submitted_digest, data['auth_hash']):
                    self.server.failures.append(now)
                    page = login_html(data['token'], error_msg='用户名或密码不正确，请重新输入')
                    return self.reply(200, page.encode('utf-8'), 'text/html; charset=utf-8')

                sess_val = sign_session(data['token'])
                max_age = '; Max-Age=2592000' if remember else ''
                cookie = f'hy2_session={sess_val}; Path=/{data["token"]}/; HttpOnly; SameSite=Strict; Secure{max_age}'
                self.send_response(302)
                self.send_header('Location', prefix)
                self.send_header('Set-Cookie', cookie)
                self.send_header('Cache-Control', 'no-store')
                self.end_headers()
                return

            return self.reply(404, b'Not found')

        def do_GET(self):
            now = time.monotonic()
            self.server.requests[:] = [t for t in self.server.requests if now-t < 1]
            self.server.failures[:] = [t for t in self.server.failures if now-t < 60]
            if len(self.server.requests) >= 50 or len(self.server.failures) >= 60:
                return self.reply(429, b'Too many requests')
            self.server.requests.append(now)

            # REST API 心跳与元数据监控
            if self.path.startswith('/api/v1/'):
                if not self.verify_api_key():
                    return self.reply_json(401, {'ok': False, 'error': 'Unauthorized API key'})
                sub = self.path[len('/api/v1/'):]
                if sub == 'node/meta':
                    m = json.loads(meta_path.read_text()) if meta_path.exists() else {}
                    users_count = len(data.get('users', {}))
                    return self.reply_json(200, {'ok': True, 'meta': m, 'users_count': users_count, 'time': int(time.time())})
                return self.reply_json(404, {'ok': False, 'error': 'API endpoint not found'})

            prefix = '/' + data['token'] + '/'
            if not self.path.startswith(prefix):
                return self.reply(404, b'Not found')

            subpath = self.path[len(prefix):]
            auth_header = self.headers.get('Authorization', '')
            is_client_api = subpath in ('clash.yaml', 'sing-box.json') or auth_header.startswith('Basic ')

            if not self.is_authenticated():
                if is_client_api:
                    self.server.failures.append(now)
                    return self.reply(401, b'Authentication required', www_auth=True)
                page = login_html(data['token'])
                return self.reply(200, page.encode('utf-8'), 'text/html; charset=utf-8')

            # 每次访问主页刷新一次用户和 IP 在线统计
            if subpath == '':
                regenerate_page()

            routes = {'': ('page', 'text/html; charset=utf-8'), 'qr.svg': ('qr', 'image/svg+xml'),
                      'clash.yaml': ('clash', 'application/yaml'), 'sing-box.json': ('sing', 'application/json')}
            route = routes.get(subpath)
            if route is None:
                return self.reply(404, b'Not found')
            key, mime = route
            self.reply(200, data[key].encode(), mime)

        def reply(self, code, body, mime='text/plain', www_auth=False):
            self.send_response(code)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('X-Frame-Options', 'DENY')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('X-Robots-Tag', 'noindex, nofollow, noarchive')
            self.send_header('Content-Security-Policy', content_policy())
            if www_auth:
                self.send_header('WWW-Authenticate', 'Basic realm="Private", charset="UTF-8"')
            if code == 429:
                self.send_header('Retry-After', '60')
            self.end_headers()
            self.wfile.write(body)

    server = HTTPServer(('127.0.0.1', data['port']), Handler)
    server.requests, server.failures = [], []
    server.serve_forever()


if __name__ == '__main__':
    if sys.argv[1] == 'prepare':
        api_key = sys.argv[4] if len(sys.argv) > 4 else None
        prepare(sys.argv[2], sys.argv[3], api_key)
    elif sys.argv[1] == 'refresh':
        refresh(sys.argv[2])
    else:
        serve(sys.argv[2])
PYPORTAL
}

refresh_portal() {
    [[ -f "$HY2_DIR/portal.json" && -f "$HY2_DIR/portal-access.json" ]] || { log_err "未找到已有网页配置，请先安装。"; return 1; }
    write_portal_program
    chmod 644 "$HY2_DIR/portal.py"
    python3 "$HY2_DIR/portal.py" refresh "$HY2_META_FILE"
    systemctl restart hysteria-portal
    log_info "网页已更新，节点参数和登录凭据保持不变。"
}

setup_portal() {
    write_portal_program
    python3 "$HY2_DIR/portal.py" prepare "$HY2_META_FILE" "$PORTAL_LOCAL_PORT" "$NODE_API_KEY"
    cat > /etc/systemd/system/hysteria-portal.service <<EOF
[Unit]
Description=Private HY2 information page (loopback only)
After=network.target
[Service]
Type=simple
DynamicUser=yes
LoadCredential=portal.json:${HY2_DIR}/portal.json
ExecStart=/usr/bin/python3 ${HY2_DIR}/portal.py serve %d/portal.json
Restart=on-failure
UMask=0077
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
PrivateDevices=yes
RestrictAddressFamilies=AF_INET
[Install]
WantedBy=multi-user.target
EOF
    # 程序可读，包含节点密码的数据仅通过 systemd credential 交给动态用户。
    chmod 755 "$HY2_DIR"
    chmod 644 "$HY2_DIR/portal.py"
    chmod 600 "$HY2_DIR/portal.json" "$HY2_DIR/portal-access.json" "$HY2_META_FILE" "$HY2_CONFIG"
    systemctl daemon-reload
    systemctl enable hysteria-portal >/dev/null
    systemctl restart hysteria-portal
    sleep 1
    systemctl is-active --quiet hysteria-portal || { log_err "信息页服务启动失败"; return 1; }
}

# 7. 服务状态与管理命令
status_service() {
    if [[ ! -f "$HY2_BIN" ]]; then
        log_err "Hysteria 2 未安装！"
        return
    fi
    echo -e "\n${CYAN}--- Hysteria 2 运行状态 ---${PLAIN}"
    systemctl status hysteria-server --no-pager || true
}

start_service() {
    log_step "启动 Hysteria 2 服务..."
    systemctl start hysteria-server
    log_info "已执行启动命令。"
}

stop_service() {
    log_step "停止 Hysteria 2 服务..."
    systemctl stop hysteria-server
    log_info "已执行停止命令。"
}

restart_service() {
    log_step "重启 Hysteria 2 服务..."
    systemctl restart hysteria-server
    log_info "已执行重启命令。"
}

view_logs() {
    echo -e "${CYAN}正在查看 Hysteria 2 实时日志 (Ctrl+C 退出)...${PLAIN}"
    journalctl -u hysteria-server -f -n 50
}

uninstall_all() {
    read -rp "确定要彻底卸载 Hysteria 2 服务及所有配置文件吗？[y/N]: " confirm
    if [[ "$confirm" =~ ^[Yy]$ ]]; then
        log_step "正在停止并删除系统服务..."
        systemctl stop hysteria-server 2>/dev/null || true
        systemctl disable hysteria-server 2>/dev/null || true
        systemctl disable --now hysteria-portal 2>/dev/null || true
        rm -f /etc/systemd/system/hysteria-portal.service
        clear_all_hopping_rules
        rm -f "$HY2_SERVICE"
        systemctl daemon-reload

        log_step "清理二进制与配置目录..."
        rm -f "$HY2_BIN"
        rm -rf "$HY2_DIR"
        
        log_info "Hysteria 2 已彻底卸载完成！"
    else
        log_info "已取消卸载。"
    fi
}

# 主控制台菜单
menu() {
    clear 2>/dev/null || true
    echo -e "${CYAN}================================================================${PLAIN}"
    echo -e "${GREEN}       Hysteria 2 全功能生产级管理脚本 (${HY2_ARCH:-$(uname -m)})         ${PLAIN}"
    echo -e "${BLUE}       GitHub: https://github.com/yys9253462-gif/hysteria2-installer    ${PLAIN}"
    echo -e "${CYAN}================================================================${PLAIN}"
    
    if [[ -f "$HY2_BIN" ]] && systemctl is-active hysteria-server >/dev/null 2>&1; then
        echo -e "核心状态: ${GREEN}运行中 (Active)${PLAIN} | 版本: $($HY2_BIN version | head -n 1 2>/dev/null || echo '未知')"
    elif [[ -f "$HY2_BIN" ]]; then
        echo -e "核心状态: ${RED}已停止 (Inactive)${PLAIN} | 版本: $($HY2_BIN version | head -n 1 2>/dev/null || echo '未知')"
    else
        echo -e "核心状态: ${YELLOW}未安装 (Not Installed)${PLAIN}"
    fi
    echo -e "${CYAN}----------------------------------------------------------------${PLAIN}"
    echo -e "  ${GREEN}1.${PLAIN} 全新安装 Hysteria 2"
    echo -e "  ${GREEN}2.${PLAIN} 更新 Hysteria 2 核心至最新版"
    echo -e "  ${GREEN}3.${PLAIN} 查看私密信息页地址和登录凭据"
    echo -e "  ${GREEN}4.${PLAIN} 重新修改配置 (端口/密码/证书/域名/混淆)"
    echo -e "${CYAN}----------------------------------------------------------------${PLAIN}"
    echo -e "  ${GREEN}5.${PLAIN} 启动服务"
    echo -e "  ${GREEN}6.${PLAIN} 停止服务"
    echo -e "  ${GREEN}7.${PLAIN} 重启服务"
    echo -e "  ${GREEN}8.${PLAIN} 查看实时运行日志"
    echo -e "  ${GREEN}9.${PLAIN} 彻底卸载 Hysteria 2"
    echo -e "  ${GREEN}0.${PLAIN} 退出脚本"
    echo -e "${CYAN}================================================================${PLAIN}"
    read -rp "请输入选项 [0-9]: " choice

    case "$choice" in
        1)
            check_root
            check_arch
            get_public_ip
            install_dependencies
            install_binary
            setup_certificates
            setup_ports_and_obfs
            generate_server_config
            setup_system_firewall "$LISTEN_PORT" "$HOP_START" "$HOP_END"
            setup_systemd
            show_client_configs
            ;;
        2)
            check_root
            check_arch
            install_binary
            restart_service
            ;;
        3)
            show_client_configs
            ;;
        4)
            check_root
            get_public_ip
            setup_certificates
            setup_ports_and_obfs
            generate_server_config
            setup_system_firewall "$LISTEN_PORT" "$HOP_START" "$HOP_END"
            setup_systemd
            show_client_configs
            ;;
        5)
            start_service
            ;;
        6)
            stop_service
            ;;
        7)
            restart_service
            ;;
        8)
            view_logs
            ;;
        9)
            check_root
            uninstall_all
            ;;
        0)
            exit 0
            ;;
        *)
            log_err "无效选项，请重新选择！"
            sleep 1
            menu
            ;;
    esac
}

# 命令行直通参数 (如: ./install.sh install / update / status / info)
check_root
check_arch

if [[ $# -gt 0 ]]; then
    case "$1" in
        install)
            get_public_ip
            install_dependencies
            install_binary
            setup_certificates
            setup_ports_and_obfs
            generate_server_config
            setup_system_firewall "$LISTEN_PORT" "$HOP_START" "$HOP_END"
            setup_systemd
            show_client_configs
            ;;
        update)
            install_binary
            restart_service
            ;;
        info)
            show_client_configs
            ;;
        refresh-page)
            refresh_portal
            ;;
        status)
            status_service
            ;;
        restart)
            restart_service
            ;;
        uninstall)
            uninstall_all
            ;;
        *)
            menu
            ;;
    esac
else
    menu
fi
