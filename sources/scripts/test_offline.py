#!/usr/bin/env python3
"""test_offline.py — RuleNova offline unit tests"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_rules import (
    write_clash, write_clash_yaml, write_surge,
    write_shadowrocket, write_quanx, write_singbox,
    REGIONS,
)

SAMPLE_DOMAINS = ["example.com", "test.org", "sample.net"]
SAMPLE_CIDRS   = ["1.2.3.0/24", "10.0.0.0/8"]
GENERATED_AT   = "2026-01-01T00:00:00Z"


class TestNoAction(unittest.TestCase):
    """All formats must produce no action keywords in output."""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _assert_no_action(self, path: Path):
        text = path.read_text()
        self.assertNotIn(",DIRECT", text)
        self.assertNotIn(",PROXY", text)
        self.assertNotIn(", direct", text)
        self.assertNotIn(", proxy", text)

    def test_clash_no_action(self):
        p = write_clash(self.out, "CN", SAMPLE_DOMAINS, SAMPLE_CIDRS, GENERATED_AT)
        self._assert_no_action(p)

    def test_surge_no_action(self):
        p = write_surge(self.out, "CN", SAMPLE_DOMAINS, SAMPLE_CIDRS, GENERATED_AT)
        self._assert_no_action(p)

    def test_shadowrocket_no_action(self):
        p = write_shadowrocket(self.out, "CN", SAMPLE_DOMAINS, SAMPLE_CIDRS, GENERATED_AT)
        self._assert_no_action(p)

    def test_quanx_no_action(self):
        p = write_quanx(self.out, "CN", SAMPLE_DOMAINS, SAMPLE_CIDRS, GENERATED_AT)
        self._assert_no_action(p)

    def test_singbox_no_action(self):
        p = write_singbox(self.out, "CN", SAMPLE_DOMAINS, SAMPLE_CIDRS, GENERATED_AT)
        data = json.loads(p.read_text())
        self.assertNotIn("action", data.get("metadata", {}))


class TestFormatContent(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_clash_domain_suffix(self):
        p = write_clash(self.out, "CN", SAMPLE_DOMAINS, SAMPLE_CIDRS, GENERATED_AT)
        self.assertIn("DOMAIN-SUFFIX,example.com", p.read_text())

    def test_clash_ip_cidr_no_resolve(self):
        p = write_clash(self.out, "CN", SAMPLE_DOMAINS, SAMPLE_CIDRS, GENERATED_AT)
        self.assertIn("IP-CIDR,1.2.3.0/24,no-resolve", p.read_text())

    def test_clash_yaml_payload(self):
        p = write_clash_yaml(self.out, "CN", SAMPLE_DOMAINS, SAMPLE_CIDRS, GENERATED_AT)
        self.assertIn("payload:", p.read_text())

    def test_surge_leading_dot(self):
        p = write_surge(self.out, "CN", SAMPLE_DOMAINS, SAMPLE_CIDRS, GENERATED_AT)
        self.assertIn(".example.com", p.read_text())

    def test_shadowrocket_domain_suffix(self):
        p = write_shadowrocket(self.out, "CN", SAMPLE_DOMAINS, SAMPLE_CIDRS, GENERATED_AT)
        self.assertIn("DOMAIN-SUFFIX,example.com", p.read_text())

    def test_quanx_host_suffix(self):
        p = write_quanx(self.out, "CN", SAMPLE_DOMAINS, SAMPLE_CIDRS, GENERATED_AT)
        self.assertIn("host-suffix, example.com", p.read_text())

    def test_quanx_ip_cidr(self):
        p = write_quanx(self.out, "CN", SAMPLE_DOMAINS, SAMPLE_CIDRS, GENERATED_AT)
        self.assertIn("ip-cidr, 1.2.3.0/24", p.read_text())

    def test_singbox_structure(self):
        p = write_singbox(self.out, "CN", SAMPLE_DOMAINS, SAMPLE_CIDRS, GENERATED_AT)
        data = json.loads(p.read_text())
        self.assertEqual(data["rules"][0]["domain_suffix"], SAMPLE_DOMAINS)
        self.assertEqual(data["rules"][0]["ip_cidr"], SAMPLE_CIDRS)


class TestFilenames(unittest.TestCase):
    """All formats: {region}.{ext}, no intent in filename or path."""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_all_formats_all_regions(self):
        for region in REGIONS:
            for writer, ext in [
                (write_clash,        ".list"),
                (write_clash_yaml,   ".yaml"),
                (write_surge,        ".list"),
                (write_shadowrocket, ".conf"),
                (write_quanx,        ".conf"),
                (write_singbox,      ".json"),
            ]:
                p = writer(self.out, region, SAMPLE_DOMAINS, SAMPLE_CIDRS, GENERATED_AT)
                expected = f"{region.lower()}{ext}"
                self.assertEqual(p.name, expected,
                    f"{writer.__name__}: expected {expected}, got {p.name}")


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite  = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if result.wasSuccessful():
        print("\nAll offline tests passed.")
    sys.exit(0 if result.wasSuccessful() else 1)
