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

    cat >> "$HY2_CONFIG" <<EOF
auth:
  type: password
  password: $(jq -Rn --arg value "$AUTH_PASSWORD" '$value')

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
    log_info "请在云安全组放行信息页 URL 中的 TCP 端口。"
    log_warn "自签证书模式需核对证书指纹后信任；推荐使用有效域名证书。"
}

setup_portal() {
    cat > "$HY2_DIR/portal.py" <<'PYPORTAL'
"""仅监听回环地址；公网 TLS 由 Hysteria 的 masquerade proxy 提供。"""
import base64
import hashlib
import hmac
import html
import json
import secrets
import subprocess
import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import quote, urlencode


def artifacts(m):
    host = m['public_ip'] if m['is_insecure'] else m['server_name']
    name = 'Hy2-' + host
    params = {'sni': m['server_name']}
    if m['is_insecure']:
        params['insecure'] = '1'
    if m['obfs_password']:
        params.update({'obfs': 'salamander', 'obfs-password': m['obfs_password']})
    if m['hop_port_range']:
        params['mport'] = m['hop_port_range']
    uri = f"hysteria2://{quote(m['auth_password'], safe='')}@{host}:{m['listen_port']}?{urlencode(params)}#{quote(name)}"
    proxy = dict(name=name, type='hysteria2', server=host, port=m['listen_port'],
                 password=m['auth_password'], sni=m['server_name'], **{'skip-cert-verify': m['is_insecure']})
    sing = dict(type='hysteria2', tag=name, server=host, server_port=m['listen_port'],
                password=m['auth_password'], tls=dict(enabled=True, server_name=m['server_name'], insecure=m['is_insecure']))
    if m['hop_port_range']:
        proxy['ports'] = str(m['listen_port']) + ',' + m['hop_port_range']
        sing['server_ports'] = [str(m['listen_port']), m['hop_port_range'].replace('-', ':')]
        del sing['server_port']
    if m['obfs_password']:
        proxy.update({'obfs': 'salamander', 'obfs-password': m['obfs_password']})
        sing['obfs'] = dict(type='salamander', password=m['obfs_password'])
    # JSON 是 YAML 的子集，避免手拼 YAML 破坏密码中的特殊字符。
    clash = {'mixed-port': 7890, 'allow-lan': False, 'mode': 'rule', 'proxies': [proxy],
             'proxy-groups': [{'name': 'PROXY', 'type': 'select', 'proxies': [name, 'DIRECT']}],
             'rules': ['MATCH,PROXY']}
    return uri, json.dumps(clash, ensure_ascii=False, indent=2), json.dumps({'outbounds': [sing]}, ensure_ascii=False, indent=2)


def prepare(meta_path, port):
    m = json.loads(Path(meta_path).read_text())
    uri, clash, sing = artifacts(m)
    qr = subprocess.run(['qrencode', '-t', 'SVG', '-o', '-'], input=uri.encode(), capture_output=True, check=True).stdout
    user, password, token = secrets.token_hex(8), secrets.token_urlsafe(32), secrets.token_hex(32)
    host = m['public_ip'] if m['is_insecure'] else m['server_name']
    base = f"https://{host}:{m['subscription_port']}/{token}/"
    subscription = f"https://{user}:{password}@{host}:{m['subscription_port']}/{token}/clash.yaml"
    sections = [('v2rayN / HY2 节点链接', uri), ('Clash / Mihomo 订阅地址', subscription),
                ('Clash / Mihomo 完整配置', clash), ('Sing-box 出站配置片段', sing)]
    page = '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>节点信息</title><body><h1>HY2 节点信息</h1>'
    page += '<p>订阅地址包含登录凭据，请私密保存。客户端若不支持带账号密码的订阅 URL，可下载配置导入。</p>'
    page += '<img width="320" alt="HY2 二维码" src="qr.svg">'
    for title, value in sections:
        page += '<h2>' + title + '</h2><textarea readonly rows="8" cols="80">' + html.escape(value) + '</textarea>'
    page += '<p><a href="clash.yaml">下载 Clash 配置</a> · <a href="sing-box.json">下载 Sing-box 片段</a></p></body></html>'
    auth = base64.b64encode(f'{user}:{password}'.encode())
    data = dict(port=int(port), token=token, auth_hash=hashlib.sha256(auth).hexdigest(), page=page,
                qr=qr.decode(), clash=clash, sing=sing)
    root = Path(meta_path).parent
    for filename, value in [('portal.json', data), ('portal-access.json', dict(url=base, username=user, password=password))]:
        path = root / filename
        path.write_text(json.dumps(value, ensure_ascii=False))
        path.chmod(0o600)


def serve(path):
    data = json.loads(Path(path).read_text())
    class Handler(BaseHTTPRequestHandler):
        server_version = 'Gateway'
        sys_version = ''
        def setup(self):
            super().setup()
            self.connection.settimeout(5)
        def log_message(self, *args):
            pass  # 不把路径、凭据及订阅请求写入日志。
        def do_GET(self):
            now = time.monotonic()
            # 全局限速不信任客户端 X-Forwarded-For；限制所有请求及失败认证。
            self.server.requests[:] = [t for t in self.server.requests if now-t < 1]
            self.server.failures[:] = [t for t in self.server.failures if now-t < 60]
            if len(self.server.requests) >= 20 or len(self.server.failures) >= 30:
                return self.reply(429, b'Too many requests')
            self.server.requests.append(now)
            prefix = '/' + data['token'] + '/'
            if not self.path.startswith(prefix):
                return self.reply(404, b'Not found')
            auth = self.headers.get('Authorization', '')
            digest = hashlib.sha256(auth.removeprefix('Basic ').encode()).hexdigest()
            if not auth.startswith('Basic ') or not hmac.compare_digest(digest, data['auth_hash']):
                self.server.failures.append(now)
                return self.reply(401, b'Authentication required')
            routes = {'': ('page', 'text/html; charset=utf-8'), 'qr.svg': ('qr', 'image/svg+xml'),
                      'clash.yaml': ('clash', 'application/yaml'), 'sing-box.json': ('sing', 'application/json')}
            route = routes.get(self.path[len(prefix):])
            if route is None:
                return self.reply(404, b'Not found')
            key, mime = route
            self.reply(200, data[key].encode(), mime)
        def reply(self, code, body, mime='text/plain'):
            self.send_response(code)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('X-Frame-Options', 'DENY')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('X-Robots-Tag', 'noindex, nofollow, noarchive')
            self.send_header('Content-Security-Policy', "default-src 'none'; img-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
            if code == 401:
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
        prepare(sys.argv[2], sys.argv[3])
    else:
        serve(sys.argv[2])
PYPORTAL
    python3 "$HY2_DIR/portal.py" prepare "$HY2_META_FILE" "$PORTAL_LOCAL_PORT"
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
