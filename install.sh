#!/usr/bin/env bash
# ==============================================================================
# Hysteria 2 全功能生产级一键部署与管理脚本
# GitHub: https://github.com/yys9253462-gif/hysteria2-installer
# Author: Yanshan (yys9253462-gif)
# ==============================================================================

set -eo pipefail

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
        apt-get update -qq && apt-get install -y -qq curl wget jq openssl iptables tar ca-certificates
    elif command -v dnf >/dev/null 2>&1; then
        dnf install -y curl wget jq openssl iptables tar ca-certificates
    elif command -v yum >/dev/null 2>&1; then
        yum install -y curl wget jq openssl iptables tar ca-certificates
    elif command -v apk >/dev/null 2>&1; then
        apk add --no-cache curl wget jq openssl iptables tar ca-certificates bash
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

# 3. 证书处理模块 (自签名 / ACME 自带证书)
setup_certificates() {
    mkdir -p "$HY2_CERT_DIR"
    
    echo -e "\n${CYAN}------------------------------------------------------------${PLAIN}"
    echo -e "${GREEN}TLS 证书配置方式：${PLAIN}"
    echo -e "  ${YELLOW}1.${PLAIN} 使用自动生成的自签名证书 (最简单快捷，客户端需开启 skip-cert-verify / insecure)"
    echo -e "  ${YELLOW}2.${PLAIN} 自定义已有证书文件路径 (例如 acme.sh / certbot 已签发的 fullchain.pem 与 privkey.pem)"
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
    else
        generate_self_signed_cert
    fi
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
    RANDOM_PASS=$(tr -dc 'a-zA-Z0-9' </dev/urandom | head -c 16 || echo "hy2_$(date +%s)")
    read -rp "请输入连接认证密码 [默认随机: ${RANDOM_PASS}]: " AUTH_PASSWORD
    AUTH_PASSWORD=${AUTH_PASSWORD:-$RANDOM_PASS}

    # 端口跳跃
    echo -e "\n是否启用端口跳跃 (Port Hopping)? 可有效防止运营商对单 UDP 端口的 QoS 限速与阻断。"
    read -rp "是否开启端口跳跃? [y/N, 默认 N]: " enable_hop
    enable_hop=${enable_hop:-n}

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
        RANDOM_OBFS=$(tr -dc 'a-zA-Z0-9' </dev/urandom | head -c 12 || echo "obfs_$(date +%s)")
        read -rp "请输入混淆密码 [默认随机: ${RANDOM_OBFS}]: " OBFS_PASSWORD
        OBFS_PASSWORD=${OBFS_PASSWORD:-$RANDOM_OBFS}
    fi
}

setup_system_firewall() {
    local port="$1"
    local s_port="$2"
    local e_port="$3"
    
    log_step "自动放行系统内部防火墙 (ufw / firewalld / iptables)..."
    if command -v ufw >/dev/null 2>&1 && ufw status | grep -q "active"; then
        ufw allow "${port}/udp" >/dev/null 2>&1 || true
        if [[ -n "$s_port" && -n "$e_port" ]]; then
            ufw allow "${s_port}:${e_port}/udp" >/dev/null 2>&1 || true
        fi
        log_info "已放行 UFW 防火墙端口。"
    fi
    if command -v firewall-cmd >/dev/null 2>&1 && systemctl is-active firewalld >/dev/null 2>&1; then
        firewall-cmd --zone=public --add-port="${port}/udp" --permanent >/dev/null 2>&1 || true
        if [[ -n "$s_port" && -n "$e_port" ]]; then
            firewall-cmd --zone=public --add-port="${s_port}-${e_port}/udp" --permanent >/dev/null 2>&1 || true
        fi
        firewall-cmd --reload >/dev/null 2>&1 || true
        log_info "已放行 firewalld 端口。"
    fi
}

setup_iptables_port_hopping() {
    local l_port="$1"
    local s_port="$2"
    local e_port="$3"
    
    log_step "配置 iptables 端口跳跃转发规则 (${s_port}:${e_port} -> ${l_port})..."
    
    # 清除旧规则（如果存在）
    iptables -t nat -D PREROUTING -p udp --dport "${s_port}:${e_port}" -j REDIRECT --to-ports "${l_port}" 2>/dev/null || true
    # 注入新规则
    iptables -t nat -A PREROUTING -p udp --dport "${s_port}:${e_port}" -j REDIRECT --to-ports "${l_port}"
    
    # IPv6 兼容
    if command -v ip6tables >/dev/null 2>&1; then
        ip6tables -t nat -D PREROUTING -p udp --dport "${s_port}:${e_port}" -j REDIRECT --to-ports "${l_port}" 2>/dev/null || true
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

    cat > "$HY2_CONFIG" <<EOF
# Hysteria 2 Server Configuration
# Generated by hysteria2-installer
listen: :${LISTEN_PORT}

tls:
  cert: ${CERT_FILE}
  key: ${KEY_FILE}

auth:
  type: password
  password: ${AUTH_PASSWORD}

masquerade:
  type: 404

ignoreClientBandwidth: false
disableUDP: false

bandwidth:
  up: 1 gbps
  down: 1 gbps
EOF

    # 写入混淆（如果有）
    if [[ -n "$OBFS_PASSWORD" ]]; then
        cat >> "$HY2_CONFIG" <<EOF

obfs:
  type: salamander
  salamander:
    password: ${OBFS_PASSWORD}
EOF
    fi

    # 保存元数据供客户端与菜单展示
    cat > "$HY2_META_FILE" <<EOF
{
  "public_ip": "${PUBLIC_IP}",
  "listen_port": ${LISTEN_PORT},
  "auth_password": "${AUTH_PASSWORD}",
  "server_name": "${SERVER_NAME}",
  "is_insecure": ${IS_INSECURE},
  "hop_port_range": "${HOP_PORT_RANGE}",
  "obfs_password": "${OBFS_PASSWORD}"
}
EOF

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
    fi
}

# 6. 生成多客户端连接格式
show_client_configs() {
    if [[ ! -f "$HY2_META_FILE" ]]; then
        log_err "未找到配置元数据，请先安装或重新配置！"
        return
    fi

    local ip=$(jq -r '.public_ip' "$HY2_META_FILE")
    local port=$(jq -r '.listen_port' "$HY2_META_FILE")
    local pass=$(jq -r '.auth_password' "$HY2_META_FILE")
    local sni=$(jq -r '.server_name' "$HY2_META_FILE")
    local insecure=$(jq -r '.is_insecure' "$HY2_META_FILE")
    local hop=$(jq -r '.hop_port_range' "$HY2_META_FILE")
    local obfs=$(jq -r '.obfs_password' "$HY2_META_FILE")

    local connect_ports="${port}"
    local url_ports="${port}"
    if [[ -n "$hop" ]]; then
        connect_ports="${port},${hop}"
        url_ports="${port},${hop}"
    fi

    # 标准 Hysteria2 URL
    # hysteria2://password@host:ports?insecure=1&sni=xxx&obfs=salamander&obfs-password=xxx#Remark
    local query="sni=${sni}"
    if [[ "$insecure" == "true" ]]; then
        query="${query}&insecure=1"
    fi
    if [[ -n "$obfs" ]]; then
        query="${query}&obfs=salamander&obfs-password=${obfs}"
    fi
    if [[ -n "$hop" ]]; then
        query="${query}&mport=${hop}"
    fi

    local hy2_url="hysteria2://${pass}@${ip}:${port}?${query}#Hy2-${ip}"

    echo -e "\n${CYAN}================================================================${PLAIN}"
    echo -e "${GREEN}          Hysteria 2 节点配置与订阅信息                         ${PLAIN}"
    echo -e "${CYAN}================================================================${PLAIN}"
    echo -e "${YELLOW}服务器地址 (Host):${PLAIN}       ${ip}"
    echo -e "${YELLOW}主连接端口 (Port):${PLAIN}       ${port}"
    if [[ -n "$hop" ]]; then
        echo -e "${YELLOW}端口跳跃范围 (Hop Ports):${PLAIN} ${hop}"
    fi
    echo -e "${YELLOW}认证密码 (Password):${PLAIN}     ${pass}"
    echo -e "${YELLOW}TLS 伪装 SNI:${PLAIN}            ${sni}"
    echo -e "${YELLOW}跳过证书验证 (Insecure):${PLAIN} ${insecure}"
    if [[ -n "$obfs" ]]; then
        echo -e "${YELLOW}Salamander 混淆密码:${PLAIN}     ${obfs}"
    fi
    echo -e "${CYAN}----------------------------------------------------------------${PLAIN}"
    echo -e "${GREEN}【标准 Hysteria2 节点链接 (v2rayN, Nekobox, Shadowrocket)】:${PLAIN}"
    echo -e "${CYAN}${hy2_url}${PLAIN}"
    echo -e "${CYAN}----------------------------------------------------------------${PLAIN}"

    # Clash.Meta / Mihomo 节点配置
    echo -e "${GREEN}【Clash.Meta / Mihomo (Clash Verge Rev) 节点配置片断】：${PLAIN}"
    cat <<EOF
- name: "Hy2-${ip}"
  type: hysteria2
  server: ${ip}
  port: ${port}
$( [[ -n "$hop" ]] && echo "  ports: ${hop}" )
  password: "${pass}"
  sni: ${sni}
  skip-cert-verify: ${insecure}
$( [[ -n "$obfs" ]] && cat <<OBFS_EOF
  obfs: salamander
  obfs-password: "${obfs}"
OBFS_EOF
)
  alpn:
    - h3
EOF
    echo -e "${CYAN}----------------------------------------------------------------${PLAIN}"

    # Sing-box 节点配置
    echo -e "${GREEN}【Sing-box (SFA / SFI) Outbound 节点配置片断】：${PLAIN}"
    cat <<EOF
{
  "type": "hysteria2",
  "tag": "Hy2-${ip}",
  "server": "${ip}",
  "server_port": ${port},
  "password": "${pass}",
  "tls": {
    "enabled": true,
    "server_name": "${sni}",
    "insecure": ${insecure},
    "alpn": ["h3"]
  }$( [[ -n "$obfs" ]] && echo ',
  "obfs": {
    "type": "salamander",
    "password": "'"${obfs}"'"
  }' )
}
EOF
    echo -e "${CYAN}================================================================${PLAIN}\n"
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
    clear
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
    echo -e "  ${GREEN}3.${PLAIN} 查看客户端节点连接信息 (链接/Clash/Sing-box)"
    echo -e "  ${GREEN}4.${PLAIN} 重新修改配置 (端口/密码/证书/混淆)"
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
            restart_service
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
