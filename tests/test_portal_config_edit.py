"""门户修改 Hysteria 配置时的「不误删」测试。

来源事故：门户里点一下 WARP 开关，**把线上节点的 Hysteria 打成"能连上但没网"**。

根因：`apply_hy2_acl()` 重写配置时用的是「从 `acl:` 那行一路删到文件尾」，
而 `install.sh` 是把 `obfs` 段**追加在配置末尾**的（排在 `acl:` 之后）——
于是混淆配置被一起删掉。服务端不再有 obfs，客户端却仍带 salamander 混淆去连，
QUIC 握手直接超时；现象是「能连上但没网」，而且**服务端一行日志都没有**，极难定位。

修法：只删 `acl:` 块，保留文件里其它所有内容（`strip_acl_block`）。
本文件就锁死这条不变量。
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import portal


# 与 install.sh 生成的形状一致：acl 段在中间，obfs 段追加在【末尾】
CONFIG_WITH_OBFS_AT_END = """listen: :21242
acme:
  domains:
    - rd.hejige.com
  type: http
auth:
  type: http
  http:
    url: http://127.0.0.1:50045/auth
masquerade:
  type: proxy
  listenHTTPS: :8443
bandwidth:
  up: 1 gbps
  down: 1 gbps
outbounds:
  - name: warp_socks
    type: socks5
    socks5:
      addr: 127.0.0.1:19898
acl:
  inline:
    - warp_socks(suffix:openai.com)
    - direct_ipv4(all)

obfs:
  type: salamander
  salamander:
    password: 8b469ddec265021d2d9967a0af2d50e7
"""


class StripAclBlockTest(unittest.TestCase):

    def test_obfs_section_survives(self):
        """🔴 核心回归：acl 之后的 obfs 段必须原样保留。

        这条不变量一旦破了，服务端就会丢掉混淆配置 ——
        客户端仍带 salamander 混淆去连，QUIC 握手超时，表现为「连上了但没网」。
        """
        out = portal.strip_acl_block(CONFIG_WITH_OBFS_AT_END)
        self.assertIn('obfs:', out, 'obfs 段被误删了！这会让客户端无法完成握手')
        self.assertIn('type: salamander', out)
        self.assertIn('password: 8b469ddec265021d2d9967a0af2d50e7', out)

    def test_acl_block_is_removed(self):
        """acl 块本身要被删干净（含其缩进的子行）。"""
        out = portal.strip_acl_block(CONFIG_WITH_OBFS_AT_END)
        self.assertNotIn('acl:', out)
        self.assertNotIn('warp_socks(suffix:openai.com)', out)
        self.assertNotIn('direct_ipv4(all)', out)

    def test_content_before_acl_survives(self):
        """acl 之前的所有段落也要完整保留。"""
        out = portal.strip_acl_block(CONFIG_WITH_OBFS_AT_END)
        for key in ('listen: :21242', 'acme:', 'auth:', 'masquerade:',
                    'bandwidth:', 'outbounds:', 'name: warp_socks'):
            self.assertIn(key, out, f'{key} 丢失了')

    def test_sections_after_acl_survive_in_order(self):
        """acl 之后若有多个段落，全部保留且顺序不变。"""
        text = """listen: :21242
acl:
  inline:
    - direct(all)
obfs:
  type: salamander
  salamander:
    password: pw
extra_section:
  foo: bar
"""
        out = portal.strip_acl_block(text)
        self.assertNotIn('acl:', out)
        self.assertIn('obfs:', out)
        self.assertIn('extra_section:', out)
        self.assertIn('foo: bar', out)
        self.assertLess(out.index('obfs:'), out.index('extra_section:'))

    def test_no_acl_block_is_noop(self):
        """没有 acl 段时不应改动任何内容。"""
        text = """listen: :21242
obfs:
  type: salamander
  salamander:
    password: pw
"""
        out = portal.strip_acl_block(text)
        self.assertIn('listen: :21242', out)
        self.assertIn('obfs:', out)
        self.assertIn('password: pw', out)

    def test_indented_acl_string_not_treated_as_block(self):
        """缩进的 `acl:`（比如某个子键）不应被当成顶格块起始。"""
        text = """listen: :21242
some_section:
  acl: inner-value
obfs:
  type: salamander
"""
        out = portal.strip_acl_block(text)
        self.assertIn('acl: inner-value', out)
        self.assertIn('obfs:', out)

    def test_result_is_valid_yaml_like(self):
        """删掉 acl 块后剩下的内容应仍是合法 YAML（能被解析）。"""
        try:
            import yaml
        except ImportError:
            self.skipTest('无 PyYAML')
        out = portal.strip_acl_block(CONFIG_WITH_OBFS_AT_END)
        data = yaml.safe_load(out)
        self.assertIsInstance(data, dict)
        self.assertIn('obfs', data)
        self.assertEqual(data['obfs']['salamander']['password'],
                         '8b469ddec265021d2d9967a0af2d50e7')
        self.assertNotIn('acl', data)


if __name__ == '__main__':
    unittest.main()
