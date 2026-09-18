# Hysteria 2 全功能生产级一键部署与管理脚本

[![GitHub License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Debian%20%7C%20Ubuntu%20%7C%20CentOS%20%7C%20Alpine-success.svg)](#)
[![Hysteria Version](https://img.shields.io/badge/Hysteria-v2.x-orange.svg)](https://v2.hysteria.network/)

极速、轻量、高可用的 **Hysteria 2 (Hy2)** 官方服务端一键自动化部署脚本。针对恶劣网络环境、高丢包率场景与运营商 UDP QoS 做了深度优化。

---

## ✨ 核心特性

- ⚡ **官方核心保证**：自动检测 CPU 架构（amd64 / arm64 / armv7），直接拉取 Hysteria 官方最新发布版二进制。
- 🛡️ **高拟真自签 / 自定义证书**：支持一键生成高拟真 ECC (prime256v1) 证书伪装知名站点，或指定已有 acme.sh / certbot 证书。
- 🔀 **端口跳跃 (Port Hopping)**：内置自动化 `iptables` 多端口转发规则配置，有效突破单一 UDP 端口被限速或丢包。
- 🎭 **Salamander 混淆**：可选开启 Salamander 混淆，将 QUIC 数据报文伪装为完全随机的高熵杂波，彻底免疫 GFW 主动探测。
- 📱 **多客户端格式全覆盖**：
  - 标准 **`hysteria2://`** 节点直链（支持 v2rayN、Nekobox、Shadowrocket、Sing-box 等一键导入）
  - **Clash.Meta / Mihomo** (Clash Verge Rev) 节点配置片段
  - **Sing-box** (SFA / SFI) Outbound 节点配置片段
- 🛠️ **全生命周期管理**：Systemd 服务自动守护、开机自启、内核 UDP 缓冲与参数调优、一键升级、实时日志监控与彻底卸载。

---

## 🚀 极速一键安装

在你的 Linux 服务器终端（以 `root` 用户）执行以下单行命令即可启动管理交互菜单：

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/yys9253462-gif/hysteria2-installer/main/install.sh)
```

或使用 `wget`：

```bash
bash <(wget -qO- https://raw.githubusercontent.com/yys9253462-gif/hysteria2-installer/main/install.sh)
```

---

## 📋 控制台交互菜单

安装后，随时在终端直接执行脚本即可呼出管理菜单：

```
================================================================
       Hysteria 2 全功能生产级管理脚本 (x86_64)         
       GitHub: https://github.com/yys9253462-gif/hysteria2-installer    
================================================================
核心状态: 运行中 (Active) | 版本: 2.6.x
----------------------------------------------------------------
  1. 全新安装 Hysteria 2
  2. 更新 Hysteria 2 核心至最新版
  3. 查看客户端节点连接信息 (链接/Clash/Sing-box)
  4. 重新修改配置 (端口/密码/证书/混淆)
----------------------------------------------------------------
  5. 启动服务
  6. 停止服务
  7. 重启服务
  8. 查看实时运行日志
  9. 彻底卸载 Hysteria 2
  0. 退出脚本
================================================================
```

---

## ⚡ 常用快捷命令

支持命令行无交互直达指令：

| 快捷命令 | 功能说明 |
| :--- | :--- |
| `bash install.sh info` | 再次打印当前节点的连接链接与配置信息 |
| `bash install.sh status` | 查看 Systemd 运行状态 |
| `bash install.sh restart` | 重启 Hysteria 2 服务端 |
| `bash install.sh update` | 一键检查并更新 Hysteria 官方二进制 |
| `bash install.sh uninstall`| 彻底卸载服务并清理配置文件 |

---

## ⚙️ 目录结构与配置参考

- **服务端主配置文件**：`/etc/hysteria/config.yaml`
- **自签证书存放目录**：`/etc/hysteria/cert/`
- **连接元数据备份**：`/etc/hysteria/client_meta.json`
- **Systemd 服务单元**：`/etc/systemd/system/hysteria-server.service`

### 服务端配置模板 (`config.yaml`)

```yaml
listen: :4433

tls:
  cert: /etc/hysteria/cert/server.crt
  key: /etc/hysteria/cert/server.key

auth:
  type: password
  password: your_secure_password

masquerade:
  type: proxy
  proxy:
    url: https://www.bing.com/
    rewriteHost: true

bandwidth:
  up: 1 gbps
  down: 1 gbps

# 若开启混淆
obfs:
  type: salamander
  salamander:
    password: your_obfs_password
```

---

## 📲 客户端配置说明

### 1. v2rayN / Nekobox / Shadowrocket
直接复制终端生成的 `hysteria2://...` 格式直链，导入客户端即可秒开。

### 2. Clash.Meta / Mihomo
将脚本生成的 YAML 片断粘贴进你的配置 `proxies` 列表中，如果使用自签名证书，请确保包含 `skip-cert-verify: true`。

### 3. Sing-box
将生成的 JSON 片断添加进 `outbounds` 节点列表中。

---

## 📄 开源许可证

本项目基于 [MIT License](LICENSE) 开源。
