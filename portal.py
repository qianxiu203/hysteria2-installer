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
