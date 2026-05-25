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
    REGIONS, POLICY_CHINA, POLICY_GLOBAL, REGION_POLICY,
)

SAMPLE_DOMAINS = ["example.com", "test.org"]
SAMPLE_CIDRS   = ["1.2.3.0/24", "10.0.0.0/8"]
GENERATED_AT   = "2026-01-01T00:00:00Z"


class TestPolicyNames(unittest.TestCase):
    """Policy name must appear in every rule line."""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_clash_china_policy(self):
        p = write_clash(self.out, "china", "China", POLICY_CHINA,
                        SAMPLE_DOMAINS, SAMPLE_CIDRS, GENERATED_AT)
        rules = [l for l in p.read_text().splitlines() if not l.startswith("#") and l]
        self.assertTrue(all(f",{POLICY_CHINA}" in l for l in rules))

    def test_clash_global_policy(self):
        p = write_clash(self.out, "global", "Global", POLICY_GLOBAL,
                        SAMPLE_DOMAINS, SAMPLE_CIDRS, GENERATED_AT)
        rules = [l for l in p.read_text().splitlines() if not l.startswith("#") and l]
        self.assertTrue(all(f",{POLICY_GLOBAL}" in l for l in rules))

    def test_surge_policy(self):
        p = write_surge(self.out, "china", "China", POLICY_CHINA,
                        SAMPLE_DOMAINS, SAMPLE_CIDRS, GENERATED_AT)
        rules = [l for l in p.read_text().splitlines() if not l.startswith("#") and l]
        self.assertTrue(all(f",{POLICY_CHINA}" in l for l in rules))

    def test_shadowrocket_policy(self):
        p = write_shadowrocket(self.out, "china", "China", POLICY_CHINA,
                               SAMPLE_DOMAINS, SAMPLE_CIDRS, GENERATED_AT)
        rules = [l for l in p.read_text().splitlines() if not l.startswith("#") and l]
        self.assertTrue(all(POLICY_CHINA in l for l in rules))

    def test_quanx_policy(self):
        p = write_quanx(self.out, "china", "China", POLICY_CHINA,
                        SAMPLE_DOMAINS, SAMPLE_CIDRS, GENERATED_AT)
        rules = [l for l in p.read_text().splitlines() if not l.startswith("#") and l]
        self.assertTrue(all(POLICY_CHINA in l for l in rules))

    def test_singbox_policy_in_metadata(self):
        p = write_singbox(self.out, "china", "China", POLICY_CHINA,
                          SAMPLE_DOMAINS, SAMPLE_CIDRS, GENERATED_AT)
        data = json.loads(p.read_text())
        self.assertEqual(data["metadata"]["policy"], POLICY_CHINA)


class TestFormatContent(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_clash_yaml_payload(self):
        p = write_clash_yaml(self.out, "china", "China", POLICY_CHINA,
                             SAMPLE_DOMAINS, SAMPLE_CIDRS, GENERATED_AT)
        self.assertIn("payload:", p.read_text())

    def test_singbox_structure(self):
        p = write_singbox(self.out, "china", "China", POLICY_CHINA,
                          SAMPLE_DOMAINS, SAMPLE_CIDRS, GENERATED_AT)
        data = json.loads(p.read_text())
        self.assertEqual(data["rules"][0]["domain_suffix"], SAMPLE_DOMAINS)
        self.assertEqual(data["rules"][0]["ip_cidr"], SAMPLE_CIDRS)


class TestFilenames(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_combined_filenames(self):
        for name, policy, label in [
            ("china",  POLICY_CHINA,  "China"),
            ("global", POLICY_GLOBAL, "Global"),
        ]:
            for writer, ext in [
                (write_clash,        ".list"),
                (write_clash_yaml,   ".yaml"),
                (write_surge,        ".list"),
                (write_shadowrocket, ".conf"),
                (write_quanx,        ".conf"),
                (write_singbox,      ".json"),
            ]:
                p = writer(self.out, name, label, policy,
                            SAMPLE_DOMAINS, SAMPLE_CIDRS, GENERATED_AT)
                self.assertEqual(p.name, f"{name}{ext}")

    def test_region_filenames(self):
        for region in REGIONS:
            policy = REGION_POLICY[region]
            for writer, ext in [
                (write_clash,        ".list"),
                (write_surge,        ".list"),
                (write_singbox,      ".json"),
            ]:
                p = writer(self.out, region.lower(), region, policy,
                            SAMPLE_DOMAINS, SAMPLE_CIDRS, GENERATED_AT)
                self.assertEqual(p.name, f"{region.lower()}{ext}")


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite  = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if result.wasSuccessful():
        print("\nAll offline tests passed.")
    sys.exit(0 if result.wasSuccessful() else 1)
