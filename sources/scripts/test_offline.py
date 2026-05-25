#!/usr/bin/env python3
"""Offline tests for RuleNova writers and cleaners."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_rules import (  # noqa: E402
    POLICY_CHINA,
    POLICY_GLOBAL,
    REGIONS,
    REGION_POLICY,
    clean_cidr,
    clean_domain,
    write_clash_text,
    write_clash_yaml,
    write_loon,
    write_quanx,
    write_shadowrocket,
    write_singbox,
    write_surge,
)

SAMPLE_DOMAINS = ["example.com", "test.org"]
SAMPLE_CIDRS = ["1.2.3.0/24", "10.0.0.0/8"]
GENERATED_AT = "2026-01-01T00:00:00Z"


def rule_lines(path: Path) -> list[str]:
    return [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip() and not line.startswith("#")]


class WriterCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()


class TestCleaners(unittest.TestCase):
    def test_clean_domain_plain_and_client_rules(self) -> None:
        self.assertEqual(clean_domain(".Example.COM"), "example.com")
        self.assertEqual(clean_domain("DOMAIN-SUFFIX,Example.COM,Proxy"), "example.com")
        self.assertEqual(clean_domain("host-suffix, example.org, China"), "example.org")
        self.assertIsNone(clean_domain("IP-CIDR,1.2.3.0/24"))
        self.assertIsNone(clean_domain("bad domain.com"))

    def test_clean_cidr_plain_and_client_rules(self) -> None:
        self.assertEqual(clean_cidr("1.2.3.4/24"), "1.2.3.0/24")
        self.assertEqual(clean_cidr("IP-CIDR, 10.0.0.0/8, no-resolve"), "10.0.0.0/8")
        self.assertEqual(clean_cidr("IP-CIDR6, 2001:db8::/32, no-resolve"), "2001:db8::/32")
        self.assertIsNone(clean_cidr("example.com"))


class TestClashProviderFormats(WriterCase):
    def test_combined_classical_has_no_policy(self) -> None:
        path = write_clash_text(self.out, "china", "China", POLICY_CHINA, SAMPLE_DOMAINS, SAMPLE_CIDRS, GENERATED_AT)
        lines = rule_lines(path)
        self.assertIn("DOMAIN-SUFFIX,example.com", lines)
        self.assertIn("IP-CIDR,1.2.3.0/24,no-resolve", lines)
        self.assertFalse(any(POLICY_CHINA in line for line in lines))

    def test_domain_variant_is_plain_domain_provider(self) -> None:
        path = write_clash_text(self.out, "china-domain", "China", POLICY_CHINA, SAMPLE_DOMAINS, [], GENERATED_AT, "domain")
        self.assertEqual(rule_lines(path), SAMPLE_DOMAINS)

    def test_ip_variant_is_plain_cidr_provider(self) -> None:
        path = write_clash_yaml(self.out, "china-ip", "China", POLICY_CHINA, [], SAMPLE_CIDRS, GENERATED_AT, "ip")
        text = path.read_text(encoding="utf-8")
        self.assertIn('  - "1.2.3.0/24"', text)
        self.assertIn("payload:", text)


class TestClientPolicyFormats(WriterCase):
    def assert_policy_in_all_rules(self, writer, ext: str) -> None:
        path = writer(self.out, "china", "China", POLICY_CHINA, SAMPLE_DOMAINS, SAMPLE_CIDRS, GENERATED_AT)
        self.assertEqual(path.suffix, ext)
        self.assertTrue(all(POLICY_CHINA in line for line in rule_lines(path)))

    def test_surge_ruleset_has_no_embedded_policy(self) -> None:
        path = write_surge(self.out, "china", "China", POLICY_CHINA, SAMPLE_DOMAINS, SAMPLE_CIDRS, GENERATED_AT)
        lines = rule_lines(path)
        self.assertIn("DOMAIN-SUFFIX,example.com", lines)
        self.assertIn("IP-CIDR,1.2.3.0/24,no-resolve", lines)
        self.assertFalse(any(POLICY_CHINA in line for line in lines))

    def test_shadowrocket_policy(self) -> None:
        self.assert_policy_in_all_rules(write_shadowrocket, ".conf")

    def test_quanx_policy(self) -> None:
        self.assert_policy_in_all_rules(write_quanx, ".conf")

    def test_loon_policy(self) -> None:
        self.assert_policy_in_all_rules(write_loon, ".list")


class TestSingBox(WriterCase):
    def test_singbox_combined_structure(self) -> None:
        path = write_singbox(self.out, "china", "China", POLICY_CHINA, SAMPLE_DOMAINS, SAMPLE_CIDRS, GENERATED_AT)
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data["version"], 2)
        self.assertEqual(data["metadata"]["suggested_policy"], POLICY_CHINA)
        self.assertEqual(data["rules"][0]["domain_suffix"], SAMPLE_DOMAINS)
        self.assertEqual(data["rules"][0]["ip_cidr"], SAMPLE_CIDRS)

    def test_singbox_domain_only(self) -> None:
        path = write_singbox(self.out, "china-domain", "China", POLICY_CHINA, SAMPLE_DOMAINS, [], GENERATED_AT, "domain")
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertIn("domain_suffix", data["rules"][0])
        self.assertNotIn("ip_cidr", data["rules"][0])


class TestNames(unittest.TestCase):
    def test_policy_names_are_short(self) -> None:
        self.assertEqual(POLICY_CHINA, "China")
        self.assertEqual(POLICY_GLOBAL, "Global")
        self.assertEqual(REGION_POLICY["HK"], "HK")
        self.assertTrue(all(len(REGION_POLICY[region]) <= 6 for region in REGIONS))


if __name__ == "__main__":
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    if result.wasSuccessful():
        print("\nAll offline tests passed.")
    sys.exit(0 if result.wasSuccessful() else 1)
