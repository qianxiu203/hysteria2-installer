"""最终注入验证：所有 Reality 相关测试是否真的会红。

新增两条针对本轮真实踩到的坑：
  * 去掉 save_data 的 encoding → 编码守卫测试必须红
  * 去掉 _sync_reality_clients 的存在性判断 → 守卫测试必须红
"""
import io
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PORTAL = ROOT / 'portal.py'
BACKUP = ROOT / 'portal.py.finalbak'
TESTS = [
    'tests.test_portal_reality_multiuser',
    'tests.test_portal_reality_e2e_5rounds',
    'tests.test_portal_reality_guards',
]

CASES = [
    ('UUID 改成随机（订阅链接每次都变）',
     "return str(uuid.uuid5(uuid.NAMESPACE_URL, 'hy2-portal-reality:' + str(user_id)))",
     "return str(uuid.uuid4())"),

    ('注册表不回填老用户',
     "    for uid in list(data.get('users', {}).keys()):\n        if uid not in reg:",
     "    for uid in list(data.get('users', {}).keys())[:0]:\n        if uid not in reg:"),

    ('clients 可以为空（xray 拒绝所有连接但仍 active）',
     "    if not clients:\n        clients = [{'id': str(uuid.uuid4()), 'flow': 'xtls-rprx-vision',\n                    'email': 'placeholder'}]",
     "    clients = []"),

    ('Reality 直链用全局 uuid（所有人共用）',
     "    uid_uuid = reality_uuid_for_user(user_id)\n    tag = label or ('VLESS-Reality-' + str(user_id))",
     "    uid_uuid = (rcfg.get('uuid') or '')\n    tag = label or ('VLESS-Reality-' + str(user_id))"),

    ('复合订阅退回 select（要用户手动切）',
     "        group = {'name': 'PROXY', 'type': 'url-test', 'proxies': group_proxies,",
     "        group = {'name': 'PROXY', 'type': 'select', 'proxies': group_proxies,"),

    ('无条件追加 Reality（单机视角也多一个节点）',
     "    if reality and user_id:",
     "    if reality:"),

    ('sing-box 缺 urltest outbound',
     "            'type': 'urltest', 'tag': 'PROXY',",
     "            'type': 'selector', 'tag': 'PROXY',"),

    ('save_data 去掉 encoding（Windows 上打死 HTTP handler）',
     "                temp.write_text(json.dumps(data, ensure_ascii=False),\n                                encoding='utf-8')",
     "                temp.write_text(json.dumps(data, ensure_ascii=False))"),

    ('_sync_reality_clients 去掉存在性判断',
     "            xj = Path('/etc/hysteria/xray.json')\n            if not xj.exists():\n                return False",
     "            xj = Path('/etc/hysteria/xray.json')"),
]


def run():
    r = subprocess.run(
        [sys.executable, '-m', 'unittest'] + TESTS + ['-q'],
        cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace')
    return r.returncode


def main():
    raw = io.open(PORTAL, encoding='utf-8').read()
    shutil.copy(PORTAL, BACKUP)

    base = run()
    print(f'基线 exit={base} {"绿" if base == 0 else "★ 红"}')
    if base != 0:
        shutil.move(str(BACKUP), str(PORTAL))
        return 1

    ok = 0
    try:
        for name, old, new in CASES:
            if old not in raw:
                print(f'  ★ 注入点未找到（会静默跳过!）: {name}')
                continue
            io.open(PORTAL, 'w', encoding='utf-8', newline='\n').write(
                raw.replace(old, new, 1))
            now = io.open(PORTAL, encoding='utf-8').read()
            if now == raw:
                print(f'  ★ 注入无效（内容未变）: {name}')
                continue
            rc = run()
            red = rc != 0
            print(f'  [{"会红 OK" if red else "* 不会红"}] {name}')
            if red:
                ok += 1
    finally:
        shutil.move(str(BACKUP), str(PORTAL))

    after = run()
    print()
    print(f'还原后 exit={after} {"绿" if after == 0 else "* 红"}')
    print(f'{ok}/{len(CASES)} 条注入会红')
    return 0 if ok == len(CASES) and after == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
