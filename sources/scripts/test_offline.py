#!/usr/bin/env python3
"""
test_offline.py — RuleNova offline unit tests

Tests all format writers with synthetic data without network access.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from build_rules import (
    write_clash, write_clash_yaml, write_surge,
    write_shadowrocket, write_quanx, write_singbox,
    REGIONS, REGION_NAMES,
)

SAMPLE_DOMAINS = ["example.com", "test.org", "sample.net"]
SAMPLE_CIDRS   = ["1.2.3.0/24", "10.0.0.0/8"]
GENERATED_AT   = "2026-01-01T00:00:00Z"


class TestClash(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_list_contains_domain_suffix(self):
        p = write_clash(self.out, "CN", "direct", SAMPLE_DOMAINS, SAMPLE_CIDRS,
                        GENERATED_AT, "DIRECT")
        text = p.read_text()
        self.assertIn("DOMAIN-SUFFIX,example.com", text)

    def test_list_contains_ip_cidr(self):
        p = write_clash(self.out, "CN", "direct", SAMPLE_DOMAINS, SAMPLE_CIDRS,
                        GENERATED_AT, "DIRECT")
        text = p.read_text()
        self.assertIn("IP-CIDR,1.2.3.0/24,no-resolve", text)

    def test_yaml_payload_structure(self):
        p = write_clash_yaml(self.out, "CN", "direct", SAMPLE_DOMAINS, SAMPLE_CIDRS,
                             GENERATED_AT, "DIRECT")
        text = p.read_text()
        self.assertIn("payload:", text)
        self.assertIn("DOMAIN-SUFFIX,example.com", text)

    def test_filename_convention(self):
        p = write_clash(self.out, "HK", "proxy", SAMPLE_DOMAINS, SAMPLE_CIDRS,
                        GENERATED_AT, "PROXY")
        self.assertEqual(p.name, "hk_proxy.list")


class TestSurge(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_leading_dot_for_domains(self):
        p = write_surge(self.out, "TW", "direct", SAMPLE_DOMAINS, SAMPLE_CIDRS,
                        GENERATED_AT, "DIRECT")
        text = p.read_text()
        self.assertIn(".example.com", text)

    def test_bare_cidr(self):
        p = write_surge(self.out, "TW", "direct", SAMPLE_DOMAINS, SAMPLE_CIDRS,
                        GENERATED_AT, "DIRECT")
        text = p.read_text()
        self.assertIn("1.2.3.0/24", text)
        self.assertNotIn("IP-CIDR", text)


class TestShadowrocket(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_direct_action(self):
        p = write_shadowrocket(self.out, "JP", "direct", SAMPLE_DOMAINS, SAMPLE_CIDRS,
                               GENERATED_AT, "DIRECT")
        text = p.read_text()
        self.assertIn("DOMAIN-SUFFIX,example.com,DIRECT", text)
        self.assertIn("IP-CIDR,1.2.3.0/24,DIRECT", text)

    def test_proxy_action(self):
        p = write_shadowrocket(self.out, "JP", "proxy", SAMPLE_DOMAINS, SAMPLE_CIDRS,
                               GENERATED_AT, "PROXY")
        text = p.read_text()
        self.assertIn(",PROXY", text)


class TestQuanX(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_host_suffix_format(self):
        p = write_quanx(self.out, "KR", "direct", SAMPLE_DOMAINS, SAMPLE_CIDRS,
                        GENERATED_AT, "DIRECT")
        text = p.read_text()
        self.assertIn("host-suffix, example.com, direct", text)

    def test_proxy_tag_format(self):
        p = write_quanx(self.out, "KR", "proxy", SAMPLE_DOMAINS, SAMPLE_CIDRS,
                        GENERATED_AT, "PROXY")
        text = p.read_text()
        self.assertIn("proxy,tag=KR", text)

    def test_ip_cidr_format(self):
        p = write_quanx(self.out, "KR", "direct", SAMPLE_DOMAINS, SAMPLE_CIDRS,
                        GENERATED_AT, "DIRECT")
        text = p.read_text()
        self.assertIn("ip-cidr, 1.2.3.0/24, direct", text)


class TestSingBox(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_json_structure(self):
        p = write_singbox(self.out, "SG", "direct", SAMPLE_DOMAINS, SAMPLE_CIDRS,
                          GENERATED_AT, "DIRECT")
        data = json.loads(p.read_text())
        self.assertEqual(data["version"], 2)
        self.assertIn("rules", data)
        self.assertEqual(data["rules"][0]["domain_suffix"], SAMPLE_DOMAINS)
        self.assertEqual(data["rules"][0]["ip_cidr"], SAMPLE_CIDRS)

    def test_metadata_fields(self):
        p = write_singbox(self.out, "SG", "proxy", SAMPLE_DOMAINS, SAMPLE_CIDRS,
                          GENERATED_AT, "PROXY")
        data = json.loads(p.read_text())
        meta = data["metadata"]
        self.assertEqual(meta["region"], "SG")
        self.assertEqual(meta["intent"], "proxy")
        self.assertEqual(meta["action"], "PROXY")

    def test_counts_in_metadata(self):
        p = write_singbox(self.out, "MO", "direct", SAMPLE_DOMAINS, SAMPLE_CIDRS,
                          GENERATED_AT, "DIRECT")
        data = json.loads(p.read_text())
        self.assertEqual(data["metadata"]["domains"], len(SAMPLE_DOMAINS))
        self.assertEqual(data["metadata"]["cidrs"], len(SAMPLE_CIDRS))


class TestFilenameConventions(unittest.TestCase):
    """All writers must follow {region_lower}_{intent}.{ext} naming."""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_all_regions_all_intents(self):
        for region in REGIONS:
            for intent, action in [("direct", "DIRECT"), ("proxy", "PROXY")]:
                for writer, expected_ext in [
                    (write_clash,        ".list"),
                    (write_clash_yaml,   ".yaml"),
                    (write_surge,        ".list"),
                    (write_shadowrocket, ".conf"),
                    (write_quanx,        ".conf"),
                    (write_singbox,      ".json"),
                ]:
                    p = writer(self.out, region, intent,
                                SAMPLE_DOMAINS, SAMPLE_CIDRS, GENERATED_AT, action)
                    expected = f"{region.lower()}_{intent}{expected_ext}"
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
