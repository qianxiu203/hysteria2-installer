"""使用指定的官方 Hysteria 二进制验证真实 HTTPS 代理链路。"""
import base64
import http.client
import json
from pathlib import Path
import socket
import ssl
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import portal

def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]

with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    local, tls, udp = free_port(), free_port(), free_port()
    meta = dict(public_ip='127.0.0.1', server_name='localhost', listen_port=udp,
                auth_password='test-only', obfs_password='test-obfs', is_insecure=True,
                hop_port_range='', subscription_port=tls)
    (root/'meta.json').write_text(json.dumps(meta))
    portal.prepare(root/'meta.json', local)
    subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1',
                    '-subj', '/CN=localhost', '-keyout', str(root/'key.pem'), '-out', str(root/'cert.pem')],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    config = dict(listen=f'127.0.0.1:{udp}', tls=dict(cert=str(root/'cert.pem'), key=str(root/'key.pem')),
                  auth=dict(type='password', password='test-only'),
                  obfs=dict(type='salamander', salamander=dict(password='test-obfs')),
                  masquerade=dict(type='proxy', proxy=dict(url=f'http://127.0.0.1:{local}/', rewriteHost=False), listenHTTPS=f'127.0.0.1:{tls}'))
    (root/'config.json').write_text(json.dumps(config))
    backend = subprocess.Popen([sys.executable, portal.__file__, 'serve', str(root/'portal.json')])
    with (root/'server.log').open('w') as log:
        hy = subprocess.Popen([str(Path(sys.argv[1]).resolve()), 'server', '-c', str(root/'config.json')], stdout=log, stderr=log)
        try:
            for _ in range(100):
                try:
                    with socket.create_connection(('127.0.0.1', tls), .1):
                        break
                except OSError:
                    time.sleep(.05)
            access = json.loads((root/'portal-access.json').read_text())
            data = json.loads((root/'portal.json').read_text())
            auth = 'Basic ' + base64.b64encode((access['username']+':'+access['password']).encode()).decode()
            for endpoint in ['', 'qr.svg', 'clash.yaml', 'sing-box.json']:
                for headers, expected in [({}, 401), ({'Authorization': auth}, 200)]:
                    conn = http.client.HTTPSConnection('127.0.0.1', tls, context=ssl._create_unverified_context(), timeout=3)
                    conn.request('GET', '/'+data['token']+'/'+endpoint, headers=headers)
                    response = conn.getresponse()
                    assert response.status == expected, (endpoint, response.status)
                    assert response.getheader('Cache-Control') == 'no-store'
                    response.read()
                    conn.close()
            print('PASS: real Hysteria HTTPS + Salamander + authenticated page/QR/subscriptions')
        except Exception:
            print((root/'server.log').read_text())
            raise
        finally:
            hy.terminate()
            backend.terminate()
            hy.wait(timeout=5)
            backend.wait(timeout=5)
