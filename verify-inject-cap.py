"""注入验证：capabilities 端点测试是否真的会红。"""
import io
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PORTAL = ROOT / 'portal.py'
BACKUP = ROOT / 'portal.py.capbak'
TEST = 'tests.test_portal_capabilities'

CASES = [
    ('端点被挪出 Bearer 分支（主面板读不到）',
     "                if sub == 'capabilities':",
     "                if False and sub == 'capabilities':"),

    ('响应体里塞了私钥（泄密）',
     "'configured': bool(d_snap['reality'].get('short_id')),",
     "'configured': bool(d_snap['reality'].get('short_id')),\n                                'private_key': d_snap['reality'].get('private_key'),"),

    ('版本号读文件改成硬编码（与常量漂移）',
     "for line in Path(__file__).read_text(encoding='utf-8').splitlines()[:80]:",
     "for line in []:"),

    ('Reality 端口写死 443（tokyo 实为 8443）',
     "'port': int(d_snap['reality'].get('port', 0) or 0),",
     "'port': 443,"),

    ('丢掉 gost 能力项',
     "'gost': {'installed': _bin('gost'),",
     "'gostX': {'installed': _bin('gost'),"),

    ('版本常量被删',
     "PORTAL_VERSION = '2.2'",
     "PORTAL_VERSION_X = '2.2'"),
]


def run():
    r = subprocess.run([sys.executable, '-m', 'unittest', TEST, '-q'],
                       cwd=ROOT, capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
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
                print(f'  ★ 注入点未找到: {name}')
                continue
            changed = raw.replace(old, new, 1)
            if changed == raw:
                print(f'  ★ 注入无效: {name}')
                continue
            io.open(PORTAL, 'w', encoding='utf-8', newline='\n').write(changed)
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
