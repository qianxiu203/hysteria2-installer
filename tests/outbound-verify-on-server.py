#!/usr/bin/env python3
"""用【真实 hysteria 二进制】校验自定义出站生成的配置能否被接受。

为什么必须这么做：YAML 写对了不等于 Hysteria 能启动。ACL 引用不存在的
出站名、字段名拼错、http 出站缺 url 等，都会让服务端 invalid config 起不来。
只做 Python 侧断言是自欺欺人，必须让真正的 hysteria 来验。

判据说明（hysteria 没有 config check 子命令，只能真起进程）：
  - 出现 failed to load server config / invalid config => 配置有问题
  - 只报 address already in use                      => 配置已通过解析
  - 进程一直运行到超时                                => 配置合法
所以必须先把 listen 端口改成空闲的高位端口，否则会因端口占用而误判。
"""
import json
import os
import re
import signal
import subprocess
import sys
import threading
from pathlib import Path

SRC = '/tmp/ymlcheck/portal.py'
BASE_FILE = '/tmp/ymlcheck/base.yaml'
TMP = Path('/tmp/ymlcheck/gen.yaml')
HY = '/usr/local/bin/hysteria'
FREE_PORT = 45777

# ---- 从 portal.py 抽出自定义出站模块 -------------------------------------
# 截取起点必须是 strip_acl_block（它在 OUTBOUND_TYPES 之前定义），
# 否则会 KeyError: strip_acl_block。
src = open(SRC, encoding='utf-8').read()
start = src.index('def strip_acl_block')
end = src.index('# \U0001f534 必须是原始字符串')
ns = {'re': re, 'json': json, 'Path': Path,
      'data': {}, 'data_lock': threading.RLock()}
exec('import re\n' + src[start:end], ns)

def _ensure_cert():
    """自签一张证书，供下面自造配置里的 tls 段引用。"""
    c, k = '/tmp/ymlcheck/t.crt', '/tmp/ymlcheck/t.key'
    if os.path.exists(c) and os.path.exists(k):
        return
    os.makedirs('/tmp/ymlcheck', exist_ok=True)
    subprocess.run(
        ['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes',
         '-keyout', k, '-out', c, '-days', '1', '-subj', '/CN=regress.test'],
        capture_output=True, timeout=30)


def _load_base():
    """读取基准配置；缺失或不含tls 时自造一份完整合法的。

    🔴 本脚本要能在**干净机器**上独立跑（不依赖已装 Hysteria），
    所以 base.yaml 不可用时自己造。两条硬要求都是实测踩出来的：
      · 必须有 tls 段，否则报 `invalid config: tls: must set either tls or acme`
      · obfs/auth 密码必须 >= 4 字节，否则报 `PSK must be at least 4 bytes`
    """
    if os.path.exists(BASE_FILE):
        txt = open(BASE_FILE, encoding='utf-8').read()
        if 'tls:' in txt and 'password:' in txt:
            return txt
    L = []
    L.append('listen: :443')
    L.append('tls:')
    L.append('  cert: /tmp/ymlcheck/t.crt')
    L.append('  key: /tmp/ymlcheck/t.key')
    L.append('auth:')
    L.append('  type: password')
    L.append('  password: "test-auth-pwd-1234"')
    L.append('obfs:')
    L.append('  type: salamander')
    L.append('  salamander:')
    L.append('    password: "test-obfs-pwd-1234"')
    L.append('outbounds:')
    L.append('  - name: direct_ipv4')
    L.append('    type: direct')
    L.append('    direct:')
    L.append('      mode: "4"')
    L.append('  - name: warp_socks')
    L.append('    type: socks5')
    L.append('    socks5:')
    L.append('      addr: 127.0.0.1:19898')
    return '\n'.join(L) + '\n'


_ensure_cert()
BASE = _load_base()


def check(text, timeout=8):
    """让真实 hysteria 校验配置。返回 (ok, 输出)。"""
    text = re.sub(r'(?m)^listen:\s*.*$', 'listen: :%d' % FREE_PORT, text, count=1)
    text = re.sub(r'(?m)^(\s*)listenHTTPS:\s*.*$',
                  r'\g<1>listenHTTPS: :%d' % (FREE_PORT + 1), text)
    TMP.write_text(text, encoding='utf-8')
    proc = subprocess.Popen([HY, 'server', '-c', str(TMP)],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, preexec_fn=os.setsid)
    try:
        out, _ = proc.communicate(timeout=timeout)
        if 'address already in use' in (out or ''):
            return True, (out or '').strip()
        return False, (out or '').strip()
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except Exception:
            pass
        return True, 'started-and-running (config accepted)'
    finally:
        try:
            if proc.poll() is None:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except Exception:
            pass


PASS = 0
FAIL = 0


def case(name, ok, extra=''):
    global PASS, FAIL
    if ok:
        PASS += 1
        print('  PASS  ' + name)
    else:
        FAIL += 1
        print('  FAIL  ' + name)
        if extra:
            for line in str(extra).splitlines()[:8]:
                print('        | ' + line)


print('=== baseline ===')
case('原始 config.yaml 可被 hysteria 接受', *check(BASE))

print('\n=== 场景1: socks5 + http 两条自定义出站 + 分流 ACL ===')
outs = []
for e in [{'name': 'my-proxy', 'type': 'socks5', 'addr': '1.2.3.4:1080'},
          {'name': 'us_exit', 'type': 'http', 'url': 'http://5.6.7.8:8080'}]:
    ok, cl, err = ns['validate_outbound'](e)
    assert ok, err
    outs.append(cl)
t = ns['upsert_outbound_block'](ns['strip_acl_block'](BASE), outs)
t = t.rstrip('\n') + '\n\n' + ns['build_acl_block'](
    'rules', [{'domain': 'openai.com', 'outbound': 'my_proxy'}], outs, 'direct_ipv4') + '\n'
case('两条出站 + ACL 可被 hysteria 接受', *check(t))

print('\n=== 场景2: 全局出站 ===')
t2 = ns['upsert_outbound_block'](ns['strip_acl_block'](BASE), outs)
t2 = t2.rstrip('\n') + '\n\n' + ns['build_acl_block']('global', [], outs, 'direct_ipv4') + '\n'
case('全局模式 ACL 可被 hysteria 接受', *check(t2))
print('        生成: ' + t2.split('acl:')[1].strip().replace('\n', ' '))

print('\n=== 场景3: 幂等性（连续保存 3 次）===')
t3 = ns['strip_acl_block'](BASE)
for _ in range(3):
    t3 = ns['upsert_outbound_block'](t3, outs)
cnt = t3.count('name: my_proxy')
case('保存 3 次后仍只有 1 条 my_proxy (实际 %d)' % cnt, cnt == 1)
t3f = t3.rstrip('\n') + '\n\n' + ns['build_acl_block']('rules', [], outs, 'direct_ipv4') + '\n'
case('多次保存后配置仍合法', *check(t3f))

print('\n=== 场景4: 内建出站与 obfs 必须完好 ===')
case('direct_ipv4 保留', 'name: direct_ipv4' in t3)
case('warp_socks 保留', 'name: warp_socks' in t3)
case('obfs 段保留', 'salamander' in t3)

print('\n=== 场景5: 规则引用已删除出站必须兜底 ===')
Path('/etc/hysteria').mkdir(parents=True, exist_ok=True)
Path('/etc/hysteria/config.yaml').write_text(t3, encoding='utf-8')
acl = ns['build_acl_block']('rules',
                            [{'domain': 'openai.com', 'outbound': 'GONE'}],
                            outs, 'direct_ipv4')
case('未生成不存在的出站引用', 'GONE' not in acl)
t5 = ns['upsert_outbound_block'](ns['strip_acl_block'](BASE), outs)
t5 = t5.rstrip('\n') + '\n\n' + acl + '\n'
case('兜底后的配置仍合法', *check(t5))

print('\n=== 场景6: 出站名含横线必须规范化 ===')
nm = ns['sanitize_outbound_name']('my-proxy-x')
case('my-proxy-x -> %r (无横线)' % nm, '-' not in nm)
outs6 = []
for e in [{'name': 'my-proxy-x', 'type': 'socks5', 'addr': '9.9.9.9:1080'},
          {'name': 'my_proxy_x', 'type': 'socks5', 'addr': '8.8.8.8:1080'}]:
    ok, cl, err = ns['validate_outbound'](e)
    assert ok, err
    outs6.append(cl)
t6 = ns['upsert_outbound_block'](ns['strip_acl_block'](BASE), outs6)
t6 = t6.rstrip('\n') + '\n\n' + ns['build_acl_block'](
    'rules', [{'domain': 'a.com', 'outbound': 'my_proxy_x'}], outs6, 'direct_ipv4') + '\n'
case('两个相似名字归一后不冲突且配置合法', *check(t6))

print('\n=== 场景7: 删除全部自定义出站 ===')
t7 = ns['upsert_outbound_block'](t3, [])
case('清空后无残留自定义出站', 'my_proxy' not in t7)
t7 = t7.rstrip('\n') + '\n\n' + ns['build_acl_block']('rules', [], [], 'direct_ipv4') + '\n'
case('清空后配置仍合法', *check(t7))

print('\n=== 场景8: direct 类型出站 ===')
ok8, cl8, err8 = ns['validate_outbound']({'name': 'd1', 'type': 'direct', 'ob_mode': '4'})
case('direct 类型校验通过 (%s)' % (err8 or 'ok'), ok8)
t8 = ns['upsert_outbound_block'](ns['strip_acl_block'](BASE), [cl8])
t8 = t8.rstrip('\n') + '\n\n' + ns['build_acl_block']('global', [], [cl8], 'direct_ipv4') + '\n'
case('direct 出站 + 全局 ACL 合法', *check(t8))

print('\n================ 结果 ================')
print('  通过: %d   失败: %d' % (PASS, FAIL))
sys.exit(0 if FAIL == 0 else 1)