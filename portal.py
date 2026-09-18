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
