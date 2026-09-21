# 变更记录

## 未发布

### Security & Performance
- 引入 `ThreadingHTTPServer` 多线程并发模型与全局数据锁，彻底解决单线程 HTTP 服务下并发阻塞与数据竞争问题。
- 本地 `/auth` 动态鉴权通道豁免外部限流，同时将 REST API 与 Web 访问的限流桶解耦，杜绝误伤高频合法握手。
- 对所有用户标识 `user_id`（创建/续费/删除/用户专属直连）施加严格字符白名单正则校验（`^[a-zA-Z0-9_\-\.]{1,64}$`），防范路径遍历与标头注入风险。
- `ip_tracker` 增加过期键自动回收机制，防止长久运行下产生内存膨胀。

### Fixed & Hardened (全面排查与安全加固)
- 彻底修复 GOST 一键安装下载包格式失效问题：
  - 根除旧版硬编码过期的 `v3.0.0-nightly.20240128` 与失效反代源（404 导致报 `gzip: stdin: not in gzip format`）；
  - 全面升级为 Python 原生下载引擎，动态探测并锁定官方稳定正式版（`v3.3.0`），增加文件类型与 `tarfile` 完整性深度校验，多镜像源自动降级重试；
  - 同步更新 `portal.py` 及 `install.sh` 内嵌实现，杜绝代码分裂。
- 根除代码分裂与覆盖倒退 (P0)：将最新 `portal.py`（含独立代理与WARP扩展专区、一键安装GOST、秒级无表单生成、居中弹窗、SVG二维码）完整同步内嵌至 `install.sh`，杜绝终端重配时覆盖降级。
- 证书签发崩溃死循环熔断保护 (P1)：`hysteria-server.service` 增加 `Restart=on-failure`、`RestartSec=10`、`StartLimitIntervalSec=300`、`StartLimitBurst=5`，彻底避免因域名解析延迟打满 Let's Encrypt 配额被惩罚锁死 1 小时。
- 端口跳跃开机自愈守护 (P2)：新增 `hy2-iptables.service` 开机持久化守护服务，解决 Debian 12 / Ubuntu 默认缺少 `netfilter-persistent` 导致系统重启后端口跳跃全失效的隐患。
- 代理生成结果现代轻奢 UI 重构 + 动态 SVG 二维码：彻底消灭排版留白，顶部横幅大字体突出呈现「域名:端口」与彩色协议胶囊；中间对称布局用户名与密码卡片；左侧动态生成矢量 SVG 二维码支持 Shadowrocket/NekoBox 手机端扫码一键导入，右侧提供直链 URL 与通用格式的双模式快捷复制。
- 入站代理秒级一键生成模式：移除繁琐输入表单，支持直接点击「⚡ 一键生成 SOCKS5 / HTTP / HTTPS」，后端自动寻找高位空闲端口（智能避开跳跃段与系统服务）并生成高安全随机凭据。
- 代理生成成功高亮卡片：创建后立即在上方展开专属结果卡片，清晰呈现「代理协议、连接域名、端口号、用户名、密码」，并支持一键复制标准直连 URL（`protocol://user:pass@host:port`）与工具格式（`host:port:user:pass`）。
- 代理列表展示增强：表格中新增完整连接直链预览与「一键复制链接」快捷按钮，无需再手动拼装地址。
- Web 控制台支持一键安装/修复 GOST：新增 `/install-gost` 接口与前端一键安装交互，自动根据系统架构（x86_64 / aarch64）拉取官方二进制，自动化配置 `gost.service`、开机自启与配置热重载。
- 独立「入站代理 & WARP」扩展专区：将入站代理（GOST 驱动）与 Cloudflare WARP 智能分流从「多用户管理」页面彻底解耦，在顶部导航栏开设全新专属 Tab 页面（`#pane-proxies`），让用户管理页面回归纯粹。
- 入站代理服务管理：集成 gost 引擎，在 Web 控制台一键添加/删除 SOCKS5 / HTTP / HTTPS 三种入站代理服务（独立账号密码认证），客户端无需安装 Hysteria 也能直接把服务器当普通代理用；配置动态生成并平滑热重载。
- 节点实时吞吐与用户网速看板：利用 `/auth` 增量流量与 10 秒时间滑动窗口算法，在 Web 控制台实时渲染节点上行/下行并发带宽仪表盘与各个买家用户的瞬时网速（如 `↓ 12.4 MB/s · ↑ 1.2 MB/s`），每 2 秒无感轮询更新。
- Web 控制台双重版本检测与一键升级：在线比对 Hysteria 2 官方内核与控制面板自身版本，支持在 Web 端一键无损升级与平滑热重启。
- Web 控制台一键启闭 Cloudflare WARP 智能分流出口（AI 加速），秒级切换 OpenAI / Claude / Gemini 路由与 VPS 原生直连。
- 内置 Cloudflare WARP Local Proxy（端口 40000 · MASQUE）一键自动化配置与 3 分钟探活自愈 Watchdog（Systemd Timer 守护）。
- Hysteria 2 默认配置文件集成 `outbounds` 与 `acl` 私网回穿防御（`block(geoip:private)`）。
- 多租户集群 Agent 节点模式：支持外部电商/控制台（如 pay.isoziyuan.com）通过安全 REST API（`/api/v1/users/create`, `renew`, `delete`, `node/meta`）实时动态开户、延期续费与状态上报。
- Hysteria 2 HTTP 动态鉴权集成：基于本地高速 HTTP 认证通道（`/auth`），买家开通/续费/到期注销零中断，完全无需重启 Hysteria 2 核心服务。
- 私密 HTTPS 信息页，集中提供 HY2 链接、本地生成的二维码、Clash 完整订阅及 Sing-box 出站配置。
- 页面、二维码和下载均要求 Basic Auth，随机路径与密码、限流、禁缓存及安全响应头保护节点信息。
- 独立回环网页服务使用 systemd 动态用户和凭据隔离；卸载自动清理。

### Changed
- 一键安装流程极致精简：默认全自动开启端口跳跃（UDP 20000-40000 -> 监听端口）与 Salamander 混淆（自动生成高熵密钥），彻底取消冗余交互询问，实现真正的零打扰极速安装。
- 私密信息页将浏览器原生 Basic Auth 弹窗重构为高颜值 Web 登录界面，支持密码显隐切换、错误友好提示、30天安全免密 Session 保持；同时维持代理客户端（Clash/Sing-box）标准 Basic Auth 自动订阅兼容性。
- 信息页改为响应式卡片布局，提供复制按钮、二维码卡片和可折叠配置；使用 CSP 哈希白名单允许内置样式与脚本。refresh-page 可单独更新现有网页。
- 终端仅显示网页地址与登录凭据，重新配置会轮换访问凭据。
- TCP 端口通过真实 bind 检测选择；无 TERM 时菜单不会直接退出。
- 认证与混淆密码使用 OpenSSL 随机数生成，不再在输入提示中打印。

### Requirements
- Python 3.9+、systemd 247+ 和 qrencode。自签证书模式需要手动核对并信任证书；推荐使用有效域名证书。
