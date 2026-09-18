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


STYLE = """
:root{color-scheme:light;--ink:#122b31;--muted:#667c81;--line:#dce7e6;--accent:#087f74}
*{box-sizing:border-box}body{margin:0;background:#f3f7f6;color:var(--ink);font:15px/1.6 system-ui,-apple-system,"Segoe UI","Microsoft YaHei",sans-serif}
main{max-width:1160px;margin:auto;padding:32px 28px 48px}.topbar{display:flex;justify-content:space-between;align-items:center;padding-bottom:32px}
.brand{font-weight:800;letter-spacing:.04em;display:flex;gap:10px;align-items:center}.logo{background:var(--ink);color:white;border-radius:12px;padding:7px 12px;font-size:17px}.private{font-size:12px;color:var(--accent);border:1px solid #c3ddd5;border-radius:30px;padding:5px 12px;background:#eaf5ef}
.eyebrow{font-size:11px;letter-spacing:.16em;font-weight:750;color:var(--accent)}h1{font-size:34px;letter-spacing:-.04em;margin:6px 0}h2{font-size:18px;margin:0 0 4px}p{margin:0;color:var(--muted)}.hero{margin-bottom:26px}.hero p{font-size:14px}
.layout{display:grid;grid-template-columns:320px minmax(0,1fr);gap:22px;align-items:start}.card{background:#fff;border:1px solid var(--line);border-radius:20px;padding:24px;box-shadow:0 5px 22px #183f3505}.qr-card{text-align:center}.qr-frame{background:#fff;border:1px solid var(--line);border-radius:16px;padding:14px;margin:20px 0}.qr-frame img{display:block;width:100%;height:auto}.hint{font-size:12px}.tags{display:flex;gap:6px;justify-content:center;flex-wrap:wrap;margin-top:18px}.tag{background:#f0f5f4;color:#526a70;border-radius:6px;padding:3px 8px;font-size:11px}
.stack{display:grid;gap:18px}.card-head{display:flex;gap:14px;align-items:center;margin-bottom:16px}.step{display:grid;place-items:center;flex:0 0 38px;height:38px;border-radius:11px;background:#e8f4f0;color:var(--accent);font-weight:750}.card-head p{font-size:12px}textarea{display:block;width:100%;min-width:0;border:1px solid var(--line);background:#f7faf9;border-radius:12px;padding:14px;color:#35545c;font:12px/1.7 ui-monospace,SFMono-Regular,Consolas,monospace;resize:vertical;overflow-wrap:anywhere}textarea.link{height:92px}textarea.config{height:290px;margin-top:18px}textarea:focus{outline:2px solid #65b3a5;outline-offset:2px}.actions{display:flex;gap:10px;align-items:center;margin-top:14px;flex-wrap:wrap}.button{display:inline-flex;align-items:center;justify-content:center;gap:6px;border:1px solid var(--line);background:white;border-radius:9px;padding:9px 15px;color:var(--ink);text-decoration:none;font:600 12px/1.5 inherit;cursor:pointer}.button.primary{background:var(--accent);color:white;border-color:var(--accent)}.button:hover{filter:brightness(.94)}button:focus-visible,a:focus-visible,summary:focus-visible{outline:3px solid #65b3a5;outline-offset:3px}.note{font-size:12px;margin-top:12px}.advanced{margin-top:24px}.advanced-title{display:flex;align-items:center;justify-content:space-between;margin-bottom:12px}.advanced-title p{font-size:12px}.config-grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}summary{cursor:pointer;font-weight:650;list-style-position:inside}summary span{font-size:11px;font-weight:400;color:var(--muted);margin-left:10px}.security{margin-top:24px;padding:15px 18px;border:1px solid #d8e6df;border-radius:12px;background:#eaf2ed;color:#4f6a60;font-size:12px}footer{display:flex;justify-content:space-between;margin-top:22px;color:#879996;font-size:11px}.status{font-size:12px;color:var(--accent)}
@media(max-width:760px){main{padding:20px 16px 32px}.topbar{padding-bottom:24px}.layout,.config-grid{grid-template-columns:1fr}.qr-frame{max-width:248px;margin:18px auto}.card{padding:20px}h1{font-size:28px}.advanced-title{display:block}footer{gap:15px}.private{font-size:10px}.brand{font-size:13px}}
"""

SCRIPT = """
document.querySelectorAll('[data-copy]').forEach(button => {
  button.addEventListener('click', async () => {
    const field = document.getElementById(button.dataset.copy);
    const status = document.getElementById('copy-status');
    try {
      await navigator.clipboard.writeText(field.value);
      status.textContent = '已复制，可粘贴到客户端';
      button.textContent = '已复制 ✓';
      setTimeout(() => { button.textContent = '复制'; }, 1800);
    } catch (_) {
      field.focus(); field.select();
      status.textContent = '已选中，请按 Ctrl+C 或长按复制';
    }
  });
});
"""


def page_html(m, uri, subscription, clash, sing):
    def field(identifier, value, kind='link'):
        return f'<textarea id="{identifier}" class="{kind}" aria-label="{identifier}" readonly spellcheck="false">{html.escape(value)}</textarea>'
    def copy(identifier):
        return f'<button class="button primary" type="button" data-copy="{identifier}">复制</button>'
    host = m['public_ip'] if m['is_insecure'] else m['server_name']
    return '''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>HY2 · 私密节点中心</title><style>''' + STYLE + '''</style></head><body><main>
<nav class="topbar" aria-label="页面标识"><div class="brand"><span class="logo">H₂</span> HYSTERIA <span> / 节点中心</span></div><span class="private">● 私密访问</span></nav>
<header class="hero"><div class="eyebrow">YOUR PRIVATE CONNECTION</div><h1>连接，从这里开始。</h1><p>扫描、复制或订阅，选择适合你的导入方式。</p></header>
<div class="layout"><section class="card qr-card"><div class="eyebrow">QUICK CONNECT</div><h2>扫码导入节点</h2><p class="hint">适用于支持 Hysteria 2 的客户端</p><div class="qr-frame"><img src="qr.svg" alt="HY2 节点导入二维码" width="260" height="260"></div><p class="hint">打开客户端的「扫描二维码」功能</p><div class="tags"><span class="tag">Hysteria 2</span><span class="tag">TLS</span><span class="tag">''' + ('Salamander' if m['obfs_password'] else 'QUIC') + '''</span></div></section>
<div class="stack"><section class="card"><div class="card-head"><span class="step">01</span><div><h2>节点链接</h2><p>v2rayN / Nekobox / Shadowrocket</p></div></div>''' + field('hy2-link', uri) + '<div class="actions">' + copy('hy2-link') + '</div><p class="note">' + html.escape(host) + ' · UDP ' + str(int(m['listen_port'])) + '''</p></section>
<section class="card"><div class="card-head"><span class="step">02</span><div><h2>Clash 订阅</h2><p>适用于 Clash Meta / Mihomo 内核</p></div></div>''' + field('clash-subscription', subscription) + '<div class="actions">' + copy('clash-subscription') + '''<a class="button" href="clash.yaml" download="clash.yaml">下载配置 ↓</a></div><p class="note">在客户端添加订阅；若不支持带账号密码的 URL，可下载后导入。</p></section></div></div>
<section class="advanced"><div class="advanced-title"><h2>配置文件</h2><p>需要手动调整？展开查看完整内容。</p></div><div class="config-grid">
<details class="card"><summary>Clash / Mihomo <span>完整配置</span></summary>''' + field('clash-config', clash, 'config') + '<div class="actions">' + copy('clash-config') + '''<a class="button" href="clash.yaml" download="clash.yaml">下载 ↓</a></div></details>
<details class="card"><summary>Sing-box <span>出站配置片段</span></summary>''' + field('sing-config', sing, 'config') + '<div class="actions">' + copy('sing-config') + '''<a class="button" href="sing-box.json" download="sing-box.json">下载 ↓</a></div></details></div></section>
<div class="security">私密提示 · 链接和二维码包含连接凭据，请勿公开分享或发送截图给他人。</div><p id="copy-status" class="status" role="status" aria-live="polite"></p><footer><span>HYSTERIA 2 / PRIVATE PORTAL</span><span>配置由你的服务器生成</span></footer></main><script>''' + SCRIPT + '</script></body></html>'


def content_policy():
    def digest(value):
        return base64.b64encode(hashlib.sha256(value.encode()).digest()).decode()
    return ("default-src 'none'; img-src 'self'; style-src 'sha256-" + digest(STYLE)
            + "'; script-src 'sha256-" + digest(SCRIPT)
            + "'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")


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
    page = page_html(m, uri, subscription, clash, sing)
    auth = base64.b64encode(f'{user}:{password}'.encode())
    data = dict(port=int(port), token=token, auth_hash=hashlib.sha256(auth).hexdigest(), page=page,
                qr=qr.decode(), clash=clash, sing=sing)
    root = Path(meta_path).parent
    for filename, value in [('portal.json', data), ('portal-access.json', dict(url=base, username=user, password=password))]:
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
    data['page'] = page_html(m, uri, subscription, clash, sing)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False))
    temporary.chmod(0o600)
    temporary.replace(path)


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
            self.send_header('Content-Security-Policy', content_policy())
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
    elif sys.argv[1] == 'refresh':
        refresh(sys.argv[2])
    else:
        serve(sys.argv[2])
