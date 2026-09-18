# Hysteria 2 全功能生产级一键部署与管理脚本

[![GitHub License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Debian%20%7C%20Ubuntu%20%7C%20CentOS%20%7C%20Alpine-success.svg)](#)
[![Hysteria Version](https://img.shields.io/badge/Hysteria-v2.x-orange.svg)](https://v2.hysteria.network/)

极速、轻量、高可用的 **Hysteria 2 (Hy2)** 官方服务端一键自动化部署脚本。针对恶劣网络环境、高丢包率场景与运营商 UDP QoS 做了深度优化。

---

## ✨ 核心特性

- ⚡ **官方核心保证**：自动检测 CPU 架构（amd64 / arm64 / armv7），直接拉取 Hysteria 官方最新发布版二进制。
- 🛡️ **自签 / 自定义 / 域名证书**：支持一键生成 ECC (prime256v1) 自签证书、指定已有 acme.sh / certbot 证书，或绑定域名并自动申请 Let's Encrypt 证书。
- 🔀 **端口跳跃 (Port Hopping)**：内置自动化 `iptables` 多端口转发规则配置，有效突破单一 UDP 端口被限速或丢包。
- 🎭 **Salamander 混淆**：可选开启 Salamander 混淆，将 QUIC 数据报文伪装为完全随机的高熵杂波，彻底免疫 GFW 主动探测。
- 📱 **多客户端格式全覆盖**：
  - 标准 **`hysteria2://`** 节点直链（支持 v2rayN、Nekobox、Shadowrocket、Sing-box 等一键导入）
  - **Clash.Meta / Mihomo** (Clash Verge Rev) 节点配置片段
  - **Sing-box** (SFA / SFI) Outbound 节点配置片段
  - 安装完成显示私密 HTTPS 信息页地址和随机登录凭据；二维码、订阅和配置统一在登录后的网页查看。
- 🏢 **多租户集群 Agent 节点模式（电商/多用户对接）**：
  - 支持作为分布式集群节点接入发卡商城或统一控制台（如 `pay.isoziyuan.com`）。
  - 内置高性能 REST API（`/api/v1/users/create`, `renew`, `delete`, `node/meta`）与 Hysteria 2 本地 HTTP 动态鉴权。
  - 用户开通、续费与注销实时生效，**零中断、无需重启 Hysteria 2 服务**。
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
  3. 查看私密信息页地址和登录凭据
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
| `bash install.sh info` | 再次显示私密信息页地址与登录凭据 |
| `bash install.sh refresh-page` | 只更新网页外观，保留节点参数、网页路径和账号密码 |
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

### 绑定域名并自动申请证书

安装或菜单中的“重新修改配置”时，在 TLS 证书方式中选择 `3`，输入域名和通知邮箱即可。脚本会让 Hysteria 使用 ACME HTTP-01 自动申请和续期证书。

开始前必须完成以下事项：

- 为域名创建指向服务器公网 IPv4 的 `A` 记录；若设置了 `AAAA` 记录，也必须确保 IPv6 可访问，否则请删除它。
- 在云厂商安全组中放行 **TCP 80**；若启用 Clash 订阅，还需放行脚本显示的订阅 TCP 端口（优先使用 8443，如被占用会自动选择空闲高位端口）。
- 脚本会自动放行本机 UFW/firewalld 的 TCP 80，但云安全组需要自行放行。

成功后客户端会使用该域名作为服务器地址和 SNI，且不再需要开启 `skip-cert-verify` / `insecure`。

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

# 默认使用 IPv4 直连，避免没有 IPv6 出站路由的 VPS 在访问
# YouTube 等同时返回 IPv4 / IPv6 地址的网站时连接失败。
outbounds:
  - name: direct-ipv4
    type: direct
    direct:
      mode: "4"

# 若开启混淆
obfs:
  type: salamander
  salamander:
    password: your_obfs_password
```

> 脚本默认将 Hysteria 的 direct 出站固定为 IPv4。这可以避免部分仅有 IPv4
> 出站能力的 VPS 因 DNS 返回 IPv6 地址而出现 `network is unreachable`，进而无法播放
> YouTube 等双栈网站的视频。若服务器已配置并验证 IPv6 出站，也可将
> `outbounds[0].direct.mode` 改为 `auto`，恢复双栈 Happy Eyeballs 策略。

---

## 📲 客户端配置说明

### 1. v2rayN / Nekobox / Shadowrocket
打开终端显示的私密信息页，输入账号密码后，扫描二维码或复制 HY2 链接导入。

### 2. Clash.Meta / Mihomo
复制网页中的带认证订阅地址到客户端。订阅为完整配置，含代理组和路由；JSON 格式也是合法 YAML。若客户端不支持 URL 中的 Basic Auth 用户信息，请在浏览器登录后下载配置导入。

### 3. Sing-box
将生成的 JSON 片断添加进 `outbounds` 节点列表中。

## 私密信息页的安全与运行要求

需要 Python 3.9+、qrencode 和 systemd 247+（使用 LoadCredential）。一键脚本内嵌网页程序，不依赖外部二维码网站或第三方 JS。二维码仅在服务器本地生成。

Hysteria 在空闲 TCP 端口上提供 HTTPS，并将请求转发到只监听 127.0.0.1 的独立低权限网页服务。共用 Hysteria 当前证书与续期机制；不占用已有网站的 80/443。使用 ACME HTTP-01 申请证书本身仍需要 TCP 80 可用。自签证书会触发浏览器证书告警；推荐使用受信任的域名证书。

页面路径使用 256-bit 随机值，随机密码同样具有 256-bit 熵。页面、二维码、订阅与下载均验证 Basic Auth；没有免登录订阅后门。随机路径不代表端口不可扫描，认证才是访问控制。请保密 URL 与账号密码，订阅 URL 内含凭据。

只开放四个固定路由，禁止目录浏览；响应带 no-store、CSP、禁止嵌入、禁止索引及禁止 referrer 标头。后端不记录访问路径或密码，使用恒定时间摘要比较验证认证。全局每秒最多 20 个请求，60 秒内 30 次失败认证后临时限流；高频攻击仍可能导致暂时不可用。可在云安全组将网页端口限制为自己的 IP。

每次重新配置都会轮换网页路径和登录凭据，旧链接失效，客户端需更新订阅。菜单 3 仅显示已有访问凭据。卸载时停止并删除 hysteria-portal.service 及其配置。已有旧版安装需重新配置才启用网页；本次仓库更新不会自动部署到服务器。

开发检查：`bash -n install.sh` 和 `python3 -m unittest discover -s tests -v`。维护 portal.py 后须同步 install.sh 的 PYPORTAL 内嵌段；回归测试会验证一致性。

---

## 📄 开源许可证

本项目基于 [MIT License](LICENSE) 开源。
