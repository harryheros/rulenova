#!/usr/bin/env python3
"""
test_offline.py — RuleNova offline unit tests
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
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
        p = write_clash(self.out, "CN", SAMPLE_DOMAINS, SAMPLE_CIDRS, GENERATED_AT)
        self.assertIn("DOMAIN-SUFFIX,example.com", p.read_text())

    def test_list_contains_ip_cidr(self):
        p = write_clash(self.out, "CN", SAMPLE_DOMAINS, SAMPLE_CIDRS, GENERATED_AT)
        self.assertIn("IP-CIDR,1.2.3.0/24,no-resolve", p.read_text())

    def test_no_action_in_list(self):
        p = write_clash(self.out, "CN", SAMPLE_DOMAINS, SAMPLE_CIDRS, GENERATED_AT)
        text = p.read_text()
        self.assertNotIn(",DIRECT", text)
        self.assertNotIn(",PROXY", text)

    def test_yaml_payload_structure(self):
        p = write_clash_yaml(self.out, "CN", SAMPLE_DOMAINS, SAMPLE_CIDRS, GENERATED_AT)
        text = p.read_text()
        self.assertIn("payload:", text)
        self.assertIn("DOMAIN-SUFFIX,example.com", text)

    def test_filename_no_intent(self):
        p = write_clash(self.out, "HK", SAMPLE_DOMAINS, SAMPLE_CIDRS, GENERATED_AT)
        self.assertEqual(p.name, "hk.list")


class TestSurge(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_leading_dot_for_domains(self):
        p = write_surge(self.out, "TW", SAMPLE_DOMAINS, SAMPLE_CIDRS, GENERATED_AT)
        self.assertIn(".example.com", p.read_text())

    def test_no_action(self):
        p = write_surge(self.out, "TW", SAMPLE_DOMAINS, SAMPLE_CIDRS, GENERATED_AT)
        text = p.read_text()
        self.assertNotIn(",DIRECT", text)
        self.assertNotIn(",PROXY", text)

    def test_filename_no_intent(self):
        p = write_surge(self.out, "TW", SAMPLE_DOMAINS, SAMPLE_CIDRS, GENERATED_AT)
        self.assertEqual(p.name, "tw.list")


class TestShadowrocket(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_direct_action(self):
        p = write_shadowrocket(self.out, "JP", "direct", SAMPLE_DOMAINS,
                               SAMPLE_CIDRS, GENERATED_AT, "DIRECT")
        text = p.read_text()
        self.assertIn("DOMAIN-SUFFIX,example.com,DIRECT", text)
        self.assertIn("IP-CIDR,1.2.3.0/24,DIRECT", text)

    def test_proxy_action(self):
        p = write_shadowrocket(self.out, "JP", "proxy", SAMPLE_DOMAINS,
                               SAMPLE_CIDRS, GENERATED_AT, "PROXY")
        self.assertIn(",PROXY", p.read_text())

    def test_filename_no_region_intent(self):
        p = write_shadowrocket(self.out, "JP", "direct", SAMPLE_DOMAINS,
                               SAMPLE_CIDRS, GENERATED_AT, "DIRECT")
        self.assertEqual(p.name, "jp.conf")


class TestQuanX(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_host_suffix_direct(self):
        p = write_quanx(self.out, "KR", "direct", SAMPLE_DOMAINS,
                        SAMPLE_CIDRS, GENERATED_AT, "DIRECT")
        self.assertIn("host-suffix, example.com, direct", p.read_text())

    def test_proxy_tag(self):
        p = write_quanx(self.out, "KR", "proxy", SAMPLE_DOMAINS,
                        SAMPLE_CIDRS, GENERATED_AT, "PROXY")
        self.assertIn("proxy,tag=KR", p.read_text())

    def test_filename_no_region_intent(self):
        p = write_quanx(self.out, "KR", "direct", SAMPLE_DOMAINS,
                        SAMPLE_CIDRS, GENERATED_AT, "DIRECT")
        self.assertEqual(p.name, "kr.conf")


class TestSingBox(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_json_structure(self):
        p = write_singbox(self.out, "SG", SAMPLE_DOMAINS, SAMPLE_CIDRS, GENERATED_AT)
        data = json.loads(p.read_text())
        self.assertEqual(data["version"], 2)
        self.assertEqual(data["rules"][0]["domain_suffix"], SAMPLE_DOMAINS)
        self.assertEqual(data["rules"][0]["ip_cidr"], SAMPLE_CIDRS)

    def test_no_action_in_metadata(self):
        p = write_singbox(self.out, "SG", SAMPLE_DOMAINS, SAMPLE_CIDRS, GENERATED_AT)
        data = json.loads(p.read_text())
        self.assertNotIn("action", data["metadata"])
        self.assertNotIn("intent", data["metadata"])

    def test_filename_no_intent(self):
        p = write_singbox(self.out, "SG", SAMPLE_DOMAINS, SAMPLE_CIDRS, GENERATED_AT)
        self.assertEqual(p.name, "sg.json")


class TestFilenameConventions(unittest.TestCase):
    """No-action formats must use {region}.{ext}, action formats {region}.{ext}."""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_no_action_filenames(self):
        for region in REGIONS:
            for writer, ext in [
                (write_clash,      ".list"),
                (write_clash_yaml, ".yaml"),
                (write_surge,      ".list"),
                (write_singbox,    ".json"),
            ]:
                p = writer(self.out, region, SAMPLE_DOMAINS, SAMPLE_CIDRS, GENERATED_AT)
                self.assertEqual(p.name, f"{region.lower()}{ext}",
                    f"{writer.__name__}: expected {region.lower()}{ext}, got {p.name}")

    def test_action_filenames(self):
        for region in REGIONS:
            for intent, action in [("direct", "DIRECT"), ("proxy", "PROXY")]:
                for writer, ext in [
                    (write_shadowrocket, ".conf"),
                    (write_quanx,        ".conf"),
                ]:
                    p = writer(self.out, region, intent,
                                SAMPLE_DOMAINS, SAMPLE_CIDRS, GENERATED_AT, action)
                    self.assertEqual(p.name, f"{region.lower()}{ext}",
                        f"{writer.__name__}: expected {region.lower()}{ext}, got {p.name}")


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite  = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if result.wasSuccessful():
        print("\nAll offline tests passed.")
    sys.exit(0 if result.wasSuccessful() else 1)
