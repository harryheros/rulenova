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
        self.assertIn("  - 1.2.3.0/24", text)
        self.assertIn("payload:", text)
        # No JSON-quoted scalars; payload entries must be plain YAML
        self.assertNotIn('  - "1.2.3.0/24"', text)


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


class TestFetchRegionResilience(unittest.TestCase):
    """fetch_region must isolate per-source failures and warn on high drop rates."""

    def test_domain_fetch_failure_does_not_break_cidr(self) -> None:
        import build_rules as br
        original = br.fetch_text

        def selective_fail(url: str) -> list[str]:
            if "domains_" in url:
                raise RuntimeError("simulated upstream failure")
            return ["1.2.3.0/24", "10.0.0.0/8"]

        br.fetch_text = selective_fail
        try:
            domains, cidrs = br.fetch_region("CN")
        finally:
            br.fetch_text = original
        self.assertEqual(domains, [])
        self.assertEqual(cidrs, ["1.2.3.0/24", "10.0.0.0/8"])

    def test_cidr_fetch_failure_does_not_break_domain(self) -> None:
        import build_rules as br
        original = br.fetch_text

        def selective_fail(url: str) -> list[str]:
            if url.endswith("/CN.txt"):
                raise RuntimeError("simulated upstream failure")
            return ["example.com", "test.org"]

        br.fetch_text = selective_fail
        try:
            domains, cidrs = br.fetch_region("CN")
        finally:
            br.fetch_text = original
        self.assertEqual(domains, ["example.com", "test.org"])
        self.assertEqual(cidrs, [])

    def test_high_drop_rate_emits_warning(self) -> None:
        import build_rules as br
        import logging
        original = br.fetch_text
        # 10 raw items, 8 are garbage that clean_domain rejects → 80% drop
        br.fetch_text = lambda url: (
            ["example.com", "test.org"] + ["bad domain!"] * 8
            if "domains_" in url else ["1.2.3.0/24"]
        )
        with self.assertLogs("rulenova", level="WARNING") as captured:
            try:
                br.fetch_region("CN")
            finally:
                br.fetch_text = original
        self.assertTrue(any("dropped" in m for m in captured.output))


class TestShrinkGuard(unittest.TestCase):
    """The build must not publish when upstream data collapsed (v2.2)."""

    PREV = {r: {"domains": 100, "cidrs": 1000} for r in REGIONS}

    def test_normal_fluctuation_passes(self) -> None:
        import build_rules as br
        cur = {r: {"domains": 95, "cidrs": 980} for r in REGIONS}
        self.assertEqual(br.check_shrink(self.PREV, cur), [])

    def test_collapse_detected(self) -> None:
        import build_rules as br
        cur = {r: dict(v) for r, v in self.PREV.items()}
        cur["HK"]["cidrs"] = 0          # failed ipnova download
        cur["CN"]["domains"] = 40       # truncated domainnova file
        problems = br.check_shrink(self.PREV, cur)
        self.assertEqual(len(problems), 2)
        self.assertTrue(any("HK cidrs" in p for p in problems))

    def test_first_build_has_no_baseline(self) -> None:
        import build_rules as br
        self.assertEqual(br.check_shrink({}, {r: {"domains": 0, "cidrs": 0} for r in REGIONS}), [])

    def _fake_build(self, root: Path, per_region: tuple[int, int], allow: bool = False) -> None:
        import build_rules as br
        n_dom, n_cidr = per_region
        original = br.fetch_region
        br.fetch_region = lambda region: (
            [f"d{i}.{region.lower()}-example.com" for i in range(n_dom)],
            [f"10.{i // 256}.{i % 256}.0/24" for i in range(n_cidr)],
        )
        try:
            br.build(root, allow_shrink=allow)
        finally:
            br.fetch_region = original

    def test_build_refuses_and_keeps_last_good_output(self) -> None:
        import logging
        import build_rules as br
        logging.disable(logging.CRITICAL)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self._fake_build(root, (20, 40))
                before = (root / "output" / "checksums.txt").read_text()
                with self.assertRaises(br.ShrinkGuardError):
                    self._fake_build(root, (20, 0))       # all CIDR downloads failed
                self.assertEqual((root / "output" / "checksums.txt").read_text(), before)
                self._fake_build(root, (20, 0), allow=True)  # explicit override
                meta = json.loads((root / "output" / "meta.json").read_text())
                self.assertEqual(meta["regions"]["CN"]["cidrs"], 0)
        finally:
            logging.disable(logging.NOTSET)

    def test_fetch_text_does_not_retry_404(self) -> None:
        import urllib.error
        import urllib.request
        import build_rules as br
        calls = []

        def fake(req, timeout=None):
            calls.append(1)
            raise urllib.error.HTTPError(req.full_url, 404, "nf", {}, None)

        original = urllib.request.urlopen
        urllib.request.urlopen = fake
        try:
            with self.assertRaises(urllib.error.HTTPError):
                br.fetch_text("https://example.invalid/x.txt")
        finally:
            urllib.request.urlopen = original
        self.assertEqual(len(calls), 1)


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
