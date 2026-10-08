#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regression tests for the certificate trust-model self-heal (problem 3).

背景（真实 bug，2026-10-08）：
  client_meta.json 的 cert_type / server_name / is_insecure / pin_sha256 是
  安装那一刻写死的。证书文件在安装后被带外替换（Caddy 续期、手工 cp、
  menu-4 只换证书）时，四个字段会同时与真实证书漂移，面板于是把错误的
  sni 发给客户端 → CRYPTO_ERROR 0x150。

这两组测试锁定「以证书为唯一事实来源、幂等自愈」的不变量：
  * portal.py::sync_cert_trust
  * install.sh::sync_cert_meta

环境注意事项（Windows/Git Bash 上踩过的坑，已规避）：
  * shutil.which('bash') 可能解析到 WorkBuddy PortableGit（/tmp 语义不同），
    因此显式优先 C:\\Program Files\\Git\\bin\\bash.exe。
  * 多行脚本不能当 -c 参数传（MSYS 会做路径转换），一律写文件再 bash <file>。
  * printf '%s' 'a\\nb' 会写出字面 \\n，所以写文件用带引号的 heredoc。
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PORTAL = REPO / "portal.py"
INSTALL = REPO / "install.sh"


def _find_bash():
    candidates = []
    for name in ("bash", "bash.exe"):
        found = shutil.which(name)
        if found:
            candidates.append(found)
    candidates += [
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files\Git\usr\bin\bash.exe",
        "/bin/bash",
        "/usr/bin/bash",
    ]
    for c in candidates:
        if c and Path(c).exists():
            return c
    return None


BASH = _find_bash()


def _run_bash(script_text, cwd=None, env=None):
    """Write script to a file and run `bash <file>` (never `-c`)."""
    fd, path = tempfile.mkstemp(suffix=".sh")
    os.close(fd)
    try:
        Path(path).write_text(script_text, encoding="utf-8", newline="\n")
        return subprocess.run([BASH, path], cwd=cwd, env=env,
                              capture_output=True, text=True)
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def _openssl(*args, cwd=None):
    return subprocess.run(["openssl", *args], cwd=cwd,
                          capture_output=True, text=True)


def _make_self_signed(certdir, cn="www.bing.com"):
    certdir = Path(certdir)
    certdir.mkdir(parents=True, exist_ok=True)
    _openssl("ecparam", "-genkey", "-name", "prime256v1",
             "-out", str(certdir / "server.key"))
    _openssl("req", "-new", "-x509", "-days", "3650",
             "-key", str(certdir / "server.key"),
             "-out", str(certdir / "server.crt"),
             "-subj", f"/CN={cn}")
    assert (certdir / "server.crt").exists(), "openssl self-signed failed"


def _make_public(certdir, cn="se.zy3a.com"):
    """A cert that looks like a real CA-issued one: CN + SAN, self-issuer won't
    matter for the SAN-first logic, but here we make issuer != subject by using
    a separate CA so `self_signed` is False."""
    certdir = Path(certdir)
    certdir.mkdir(parents=True, exist_ok=True)
    ca_key = certdir / "ca.key"
    ca_crt = certdir / "ca.crt"
    _openssl("ecparam", "-genkey", "-name", "prime256v1", "-out", str(ca_key))
    _openssl("req", "-new", "-x509", "-days", "3650", "-key", str(ca_key),
             "-out", str(ca_crt), "-subj", "/CN=Fake Root CA")
    key = certdir / "leaf.key"
    csr = certdir / "leaf.csr"
    ext = certdir / "leaf.ext"
    _openssl("ecparam", "-genkey", "-name", "prime256v1", "-out", str(key))
    _openssl("req", "-new", "-key", str(key), "-out", str(csr),
             "-subj", f"/CN={cn}")
    ext.write_text(f"subjectAltName=DNS:{cn}\n")
    r = _openssl("x509", "-req", "-days", "3650", "-in", str(csr),
                 "-CA", str(ca_crt), "-CAkey", str(ca_key), "-CAcreateserial",
                 "-extfile", str(ext), "-out", str(certdir / "fullchain.pem"))
    assert r.returncode == 0, f"openssl sign failed: {r.stderr}"
    # fullchain = leaf + CA
    with open(certdir / "fullchain.pem", "a") as fh:
        fh.write(Path(ca_crt).read_text())
    assert (certdir / "fullchain.pem").exists(), "openssl public cert failed"


def _pin_of(path):
    p = subprocess.run(f"openssl x509 -in {path} -outform DER | "
                       f"openssl dgst -sha256 | awk '{{print $NF}}'",
                       shell=True, capture_output=True, text=True)
    return p.stdout.strip().lower()


# ----------------------------------------------------------------------------
# portal.py::sync_cert_trust
# ----------------------------------------------------------------------------
class TestPortalSyncCertTrust(unittest.TestCase):
    def _call(self, root, meta, config_path=None):
        """Import sync_cert_trust from portal.py with the repo on sys.path."""
        sys.path.insert(0, str(REPO))
        try:
            if "portal" in sys.modules:
                del sys.modules["portal"]
            import portal  # noqa
            return portal.sync_cert_trust(
                meta, root, str(root / "client_meta.json"),
                config_path=str(config_path or (root / "config.yaml")))
        finally:
            sys.path.pop(0)

    def test_self_signed_heals_all_four_fields(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            _make_self_signed(td / "cert", cn="www.bing.com")
            (td / "config.yaml").write_text(
                "listen: :443\ntls:\n  cert: cert/server.crt\n  key: cert/server.key\n")
            meta = {"public_ip": "1.2.3.4", "server_name": "stale.example.com",
                    "cert_type": "custom", "is_insecure": False, "pin_sha256": ""}
            (td / "client_meta.json").write_text(json.dumps(meta))
            changed = self._call(td, meta)
            self.assertTrue(changed)
            out = json.loads((td / "client_meta.json").read_text())
            self.assertEqual(out["cert_type"], "self_signed")
            self.assertIs(out["is_insecure"], True)
            self.assertEqual(out["server_name"], "www.bing.com")
            self.assertEqual(out["pin_sha256"], _pin_of(td / "cert" / "server.crt"))

    def test_public_cert_prefers_san_and_clears_pin(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            _make_public(td / "cert", cn="se.zy3a.com")
            (td / "config.yaml").write_text(
                "listen: :443\ntls:\n  cert: cert/fullchain.pem\n  key: cert/leaf.key\n")
            # The exact drift measured on `se`: everything wrong.
            meta = {"public_ip": "13.63.71.232", "server_name": "www.bing.com",
                    "cert_type": "self_signed", "is_insecure": True,
                    "pin_sha256": "8037cef0000000000000000000000000000000000000000000000000000000000"}
            (td / "client_meta.json").write_text(json.dumps(meta))
            changed = self._call(td, meta)
            self.assertTrue(changed)
            out = json.loads((td / "client_meta.json").read_text())
            self.assertEqual(out["cert_type"], "custom")
            self.assertIs(out["is_insecure"], False)
            self.assertEqual(out["server_name"], "se.zy3a.com")
            self.assertEqual(out["pin_sha256"], "")

    def test_acme_block_maps_to_acme_type(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            _make_public(td / "cert", cn="node.example.com")
            (td / "config.yaml").write_text(
                "listen: :443\nacme:\n  domains:\n    - node.example.com\n"
                "  email: a@b.c\n  type: http\n")
            # acme mode: no tls.cert, fall back to cert/server.crt -> put one there
            shutil.copy(td / "cert" / "fullchain.pem", td / "cert" / "server.crt")
            meta = {"public_ip": "5.6.7.8", "server_name": "node.example.com",
                    "cert_type": "custom", "is_insecure": False, "pin_sha256": ""}
            (td / "client_meta.json").write_text(json.dumps(meta))
            self.assertTrue(self._call(td, meta))
            out = json.loads((td / "client_meta.json").read_text())
            self.assertEqual(out["cert_type"], "acme")
            self.assertIs(out["is_insecure"], False)
            self.assertEqual(out["server_name"], "node.example.com")

    def test_idempotent_second_call_reports_no_change(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            _make_self_signed(td / "cert", cn="www.bing.com")
            (td / "config.yaml").write_text(
                "listen: :443\ntls:\n  cert: cert/server.crt\n  key: cert/server.key\n")
            meta = {"public_ip": "1.2.3.4", "server_name": "x", "cert_type": "custom",
                    "is_insecure": False, "pin_sha256": ""}
            (td / "client_meta.json").write_text(json.dumps(meta))
            self.assertTrue(self._call(td, meta))
            # second run: read the healed meta back in, must be a no-op
            healed = json.loads((td / "client_meta.json").read_text())
            self.assertFalse(self._call(td, healed))


# ----------------------------------------------------------------------------
# install.sh::sync_cert_meta  (extracted and executed for real)
# ----------------------------------------------------------------------------
def _extract_shell_fn(name):
    text = INSTALL.read_text(encoding="utf-8")
    start = text.index(f"{name}() {{")
    # brace matching from the opening '{'
    i = text.index("{", start)
    depth = 0
    for j in range(i, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return text[start:j + 1]
    raise AssertionError(f"unbalanced braces extracting {name}")


@unittest.skipUnless(BASH and shutil.which("jq") and shutil.which("openssl"),
                     "needs bash + jq + openssl")
class TestShellSyncCertMeta(unittest.TestCase):
    def _harness(self, td, config_text, meta):
        fn = _extract_shell_fn("sync_cert_meta")
        (td / "config.yaml").write_text(config_text)
        (td / "client_meta.json").write_text(json.dumps(meta))
        script = (
            "set -e\n"
            'HY2_DIR="$1"\n'
            'HY2_CONFIG="$HY2_DIR/config.yaml"\n'
            'HY2_META_FILE="$HY2_DIR/client_meta.json"\n'
            'HY2_CERT_DIR="$HY2_DIR/cert"\n'
            "log_warn(){ echo \"WARN: $*\" >&2; }\n"
            "log_info(){ echo \"INFO: $*\" >&2; }\n"
            "log_err(){ echo \"ERR: $*\" >&2; }\n"
            + fn + "\n"
            'sync_cert_meta\n'
        )

        def runner():
            fd, p = tempfile.mkstemp(suffix=".sh")
            os.close(fd)
            # convert the Windows temp path to a posix one the chosen bash understands
            raw = str(td)
            if os.name == "nt" and BASH and BASH.lower().endswith(".exe"):
                drive, rest = os.path.splitdrive(raw)
                raw = "/" + drive.rstrip(":").lower() + rest.replace("\\", "/")
            Path(p).write_text(script, encoding="utf-8", newline="\n")
            try:
                return subprocess.run([BASH, p, raw], capture_output=True, text=True)
            finally:
                try:
                    os.unlink(p)
                except OSError:
                    pass

        return runner

    def test_shell_heals_self_signed(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            _make_self_signed(td / "cert", cn="www.bing.com")
            runner = self._harness(
                td,
                "listen: :443\ntls:\n  cert: cert/server.crt\n  key: cert/server.key\n",
                {"public_ip": "1.2.3.4", "server_name": "stale", "cert_type": "custom",
                 "is_insecure": False, "pin_sha256": ""})
            r = runner()
            self.assertEqual(r.returncode, 0, r.stderr)
            out = json.loads((td / "client_meta.json").read_text())
            self.assertEqual(out["cert_type"], "self_signed")
            self.assertIs(out["is_insecure"], True)
            self.assertEqual(out["server_name"], "www.bing.com")
            self.assertEqual(out["pin_sha256"], _pin_of(td / "cert" / "server.crt"))

    def test_shell_heals_drifted_public_cert(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            _make_public(td / "cert", cn="se.zy3a.com")
            runner = self._harness(
                td,
                "listen: :443\ntls:\n  cert: cert/fullchain.pem\n  key: cert/leaf.key\n",
                {"public_ip": "13.63.71.232", "server_name": "www.bing.com",
                 "cert_type": "self_signed", "is_insecure": True,
                 "pin_sha256": "8" * 64})
            r = runner()
            self.assertEqual(r.returncode, 0, r.stderr)
            out = json.loads((td / "client_meta.json").read_text())
            self.assertEqual(out["cert_type"], "custom")
            self.assertIs(out["is_insecure"], False)
            self.assertEqual(out["server_name"], "se.zy3a.com")
            self.assertEqual(out["pin_sha256"], "")

    def test_shell_idempotent(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            _make_self_signed(td / "cert", cn="www.bing.com")
            runner = self._harness(
                td,
                "listen: :443\ntls:\n  cert: cert/server.crt\n  key: cert/server.key\n",
                {"public_ip": "1.2.3.4", "server_name": "x", "cert_type": "custom",
                 "is_insecure": False, "pin_sha256": ""})
            r1 = runner()
            self.assertEqual(r1.returncode, 0, r1.stderr)
            self.assertIn("已自愈", r1.stderr)
            snapshot = (td / "client_meta.json").read_text()
            r2 = runner()  # same dir, meta now healed -> must not rewrite
            self.assertEqual(r2.returncode, 0, r2.stderr)
            self.assertNotIn("已自愈", r2.stderr)
            self.assertEqual(snapshot, (td / "client_meta.json").read_text())

    def test_shell_idempotent_with_false_is_insecure(self):
        """jq 的 `//` 把布尔 false 当 null —— 这条锁死 is_insecure=false 时的幂等。

        回归场景（真实踩到）：healed 后 meta 里 `is_insecure: false`。若自愈用
        `.is_insecure // empty` 读取，false 会被转成空串，与期望的 "false" 不等，
        于是每轮都判成漂移、反复写盘。必须用 tostring 显式取值。
        """
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            _make_public(td / "cert", cn="se.zy3a.com")
            runner = self._harness(
                td,
                "listen: :443\ntls:\n  cert: cert/fullchain.pem\n  key: cert/leaf.key\n",
                {"public_ip": "13.63.71.232", "server_name": "www.bing.com",
                 "cert_type": "self_signed", "is_insecure": True,
                 "pin_sha256": "8" * 64})
            r1 = runner()
            self.assertEqual(r1.returncode, 0, r1.stderr)
            out = json.loads((td / "client_meta.json").read_text())
            self.assertIs(out["is_insecure"], False)   # healed to boolean false
            snapshot = (td / "client_meta.json").read_text()
            # second run MUST be a no-op even though is_insecure is now false
            r2 = runner()
            self.assertEqual(r2.returncode, 0, r2.stderr)
            self.assertNotIn("已自愈", r2.stderr,
                             "is_insecure=false 时自愈不幂等（jq `//` 把 false 当 null）")
            self.assertEqual(snapshot, (td / "client_meta.json").read_text())


# ----------------------------------------------------------------------------
# repo invariants (guard against silent removal of the fix)
# ----------------------------------------------------------------------------
class TestRepoInvariants(unittest.TestCase):
    def test_portal_has_sync_cert_trust_and_it_is_wired(self):
        text = PORTAL.read_text(encoding="utf-8")
        self.assertIn("def sync_cert_trust(", text)
        # the call must exist inside prepare(), before sync_pin()
        call_trust = text.index("    sync_cert_trust(m, root, meta_path)")
        call_pin = text.index("    sync_pin(m, root, meta_path)")
        self.assertLess(call_trust, call_pin)

    def test_install_has_sync_cert_meta_and_it_is_wired(self):
        text = INSTALL.read_text(encoding="utf-8")
        self.assertIn("sync_cert_meta() {", text)
        self.assertIn("sync_cert_meta\n", text)  # called
        self.assertIn("证书信任模型已自愈", text)
        # do_upgrade.sh portal path must self-heal too
        self.assertIn("证书信任模型已自愈:", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
