#!/usr/bin/env python3
"""
build_rules.py — RuleNova main build script

Generates two tiers of output:

  Tier 1 — Combined (recommended for most users):
    china.list   — CN domains and IPs, policy name: China
    global.list  — HK/TW/MO/JP/KR/SG merged, policy name: Global

  Tier 2 — Per-region (for advanced users):
    regions/cn.list, regions/hk.list, regions/tw.list ...

Formats: Clash/Mihomo, Surge, sing-box, Shadowrocket, Quantumult X

Usage:
    python3 sources/scripts/build_rules.py [--repo-root /path/to/repo]
"""

import argparse
import datetime
import hashlib
import json
import logging
import os
import sys
import urllib.request
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

# ── Upstream data sources ────────────────────────────────────────────────────

DOMAINNOVA_BASE = "https://raw.githubusercontent.com/harryheros/domainnova/main/dist"
IPNOVA_BASE     = "https://raw.githubusercontent.com/harryheros/ipnova/main/output/plain"

REGIONS = ["CN", "HK", "TW", "MO", "JP", "KR", "SG"]

# Regions merged into the Global rule set
GLOBAL_REGIONS = ["HK", "TW", "MO", "JP", "KR", "SG"]

REGION_NAMES = {
    "CN": "China Mainland",
    "HK": "Hong Kong",
    "TW": "Taiwan",
    "MO": "Macau",
    "JP": "Japan",
    "KR": "South Korea",
    "SG": "Singapore",
}

# Policy group names embedded in rules — users map these to their chosen proxy
POLICY_CHINA  = "China"
POLICY_GLOBAL = "Global"

# Per-region policy names (for regions/ output)
REGION_POLICY = {
    "CN": "China",
    "HK": "HongKong",
    "TW": "Taiwan",
    "MO": "Macau",
    "JP": "Japan",
    "KR": "Korea",
    "SG": "Singapore",
}

# ── Helpers ──────────────────────────────────────────────────────────────────

def _header(label: str, fmt: str, generated_at: str, policy: str = "") -> str:
    policy_str = f"\n# Policy    : {policy}" if policy else ""
    return (
        f"# RuleNova — {label}{policy_str}\n"
        f"# Format   : {fmt}\n"
        f"# Generated: {generated_at}\n"
        f"# Source   : https://github.com/harryheros/rulenova\n"
        f"#\n"
    )


# ── Fetch ────────────────────────────────────────────────────────────────────

def fetch_text(url: str) -> list[str]:
    """Fetch a plain-text URL and return non-empty, non-comment lines."""
    log.info(f"  Fetching {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "rulenova/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        text = resp.read().decode("utf-8")
    return [l.strip() for l in text.splitlines()
            if l.strip() and not l.strip().startswith("#")]


# ── Format writers ───────────────────────────────────────────────────────────
    intent_str = f" ({intent.upper()})" if intent else ""
    return (
        f"# RuleNova — {REGION_NAMES.get(region, region)}{intent_str}\n"
        f"# Format   : {fmt}\n"
        f"# Generated: {generated_at}\n"
        f"# Source   : https://github.com/harryheros/rulenova\n"
        f"#\n"
    )


def write_clash(out_dir: Path, name: str, label: str, policy: str,
                domains: list[str], cidrs: list[str],
                generated_at: str) -> Path:
    """Clash rule-set provider format. Policy name embedded in each rule."""
    lines = [_header(label, "Clash/Mihomo", generated_at, policy)]
    for d in domains:
        lines.append(f"DOMAIN-SUFFIX,{d},{policy}")
    for cidr in cidrs:
        lines.append(f"IP-CIDR,{cidr},{policy},no-resolve")
    path = out_dir / f"{name}.list"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_clash_yaml(out_dir: Path, name: str, label: str, policy: str,
                     domains: list[str], cidrs: list[str],
                     generated_at: str) -> Path:
    """Clash rule-set provider YAML format."""
    rules = []
    for d in domains:
        rules.append(f"  - DOMAIN-SUFFIX,{d},{policy}")
    for cidr in cidrs:
        rules.append(f"  - IP-CIDR,{cidr},{policy},no-resolve")
    content = (
        f"# RuleNova — {label}\n"
        f"# Policy: {policy}\n"
        f"# Format: Clash/Mihomo YAML rule-provider\n"
        f"# Generated: {generated_at}\n"
        f"payload:\n"
        + "\n".join(rules) + "\n"
    )
    path = out_dir / f"{name}.yaml"
    path.write_text(content, encoding="utf-8")
    return path


def write_surge(out_dir: Path, name: str, label: str, policy: str,
                domains: list[str], cidrs: list[str],
                generated_at: str) -> Path:
    """Surge rule list with policy name."""
    lines = [_header(label, "Surge", generated_at, policy)]
    for d in domains:
        lines.append(f"DOMAIN-SUFFIX,{d},{policy}")
    for cidr in cidrs:
        lines.append(f"IP-CIDR,{cidr},{policy},no-resolve")
    path = out_dir / f"{name}.list"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_shadowrocket(out_dir: Path, name: str, label: str, policy: str,
                       domains: list[str], cidrs: list[str],
                       generated_at: str) -> Path:
    """Shadowrocket rule list with policy name."""
    lines = [_header(label, "Shadowrocket", generated_at, policy)]
    for d in domains:
        lines.append(f"DOMAIN-SUFFIX,{d},{policy}")
    for cidr in cidrs:
        lines.append(f"IP-CIDR,{cidr},{policy}")
    path = out_dir / f"{name}.conf"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_quanx(out_dir: Path, name: str, label: str, policy: str,
                domains: list[str], cidrs: list[str],
                generated_at: str) -> Path:
    """Quantumult X remote filter list. Policy overridden by force-policy."""
    lines = [_header(label, "Quantumult X", generated_at, policy)]
    for d in domains:
        lines.append(f"host-suffix, {d}, {policy}")
    for cidr in cidrs:
        lines.append(f"ip-cidr, {cidr}, {policy}")
    path = out_dir / f"{name}.conf"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_singbox(out_dir: Path, name: str, label: str, policy: str,
                  domains: list[str], cidrs: list[str],
                  generated_at: str) -> Path:
    """sing-box rule-set source format."""
    rule = {
        "version": 2,
        "metadata": {
            "label":     label,
            "policy":    policy,
            "generated": generated_at,
            "domains":   len(domains),
            "cidrs":     len(cidrs),
            "source":    "https://github.com/harryheros/rulenova",
        },
        "rules": [{"domain_suffix": domains, "ip_cidr": cidrs}],
    }
    path = out_dir / f"{name}.json"
    path.write_text(json.dumps(rule, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    return path


# ── Stats / meta ─────────────────────────────────────────────────────────────

def write_meta(repo_root: Path, stats: dict, generated_at: str) -> None:
    meta = {
        "schema_version": "1.0",
        "project":        "rulenova",
        "generated_at":   generated_at,
        "regions":        stats,
        "formats": ["clash-mihomo", "surge", "sing-box", "shadowrocket", "quantumult-x"],
    }
    out = repo_root / "output" / "meta.json"
    out.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    log.info(f"Wrote {out}")


def write_checksums(repo_root: Path) -> None:
    out_dir = repo_root / "output"
    lines = []
    for path in sorted(out_dir.rglob("*")):
        if path.is_file() and path.name not in ("checksums.txt", "meta.json"):
            sha = hashlib.sha256(path.read_bytes()).hexdigest()
            rel = path.relative_to(out_dir)
            lines.append(f"{sha}  {rel}")
    ck_path = out_dir / "checksums.txt"
    ck_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log.info(f"Wrote {ck_path} ({len(lines)} files)")


# ── Main ─────────────────────────────────────────────────────────────────────

FORMATS = {
    "clash-mihomo":  (write_clash, write_clash_yaml),
    "surge":         (write_surge,),
    "sing-box":      (write_singbox,),
    "shadowrocket":  (write_shadowrocket,),
    "quantumult-x":  (write_quanx,),
}


def write_ruleset(out_root: Path, name: str, label: str, policy: str,
                  domains: list[str], cidrs: list[str], generated_at: str,
                  subdir: str = "") -> None:
    """Write a named rule set in all formats."""
    for fmt, writers in FORMATS.items():
        fmt_dir = out_root / fmt / subdir if subdir else out_root / fmt
        fmt_dir.mkdir(parents=True, exist_ok=True)
        for writer in writers:
            path = writer(fmt_dir, name, label, policy,
                          domains, cidrs, generated_at)
            log.info(f"  [{fmt}{'/' + subdir if subdir else ''}] {path.name}")


def main() -> int:
    parser = argparse.ArgumentParser(description="RuleNova build script")
    parser.add_argument("--repo-root", default=None)
    args = parser.parse_args()

    repo_root = Path(args.repo_root) if args.repo_root else \
        Path(__file__).resolve().parent.parent.parent
    out_root = repo_root / "output"

    generated_at = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")
    log.info(f"RuleNova build — {generated_at}")
    log.info(f"Repo root: {repo_root}")

    # Fetch all regions
    all_domains: dict[str, list[str]] = {}
    all_cidrs:   dict[str, list[str]] = {}
    stats = {}

    for region in REGIONS:
        log.info(f"\n── {region} ({REGION_NAMES[region]}) ──")
        try:
            domains = fetch_text(
                f"{DOMAINNOVA_BASE}/domains_{region.lower()}.txt")
        except Exception as e:
            log.error(f"  Failed to fetch domains for {region}: {e}")
            domains = []
        try:
            cidrs = fetch_text(f"{IPNOVA_BASE}/{region}.txt")
        except Exception as e:
            log.error(f"  Failed to fetch CIDRs for {region}: {e}")
            cidrs = []

        all_domains[region] = domains
        all_cidrs[region]   = cidrs
        stats[region] = {"domains": len(domains), "cidrs": len(cidrs)}
        log.info(f"  domains={len(domains)}, cidrs={len(cidrs)}")

    # ── Tier 1: Combined (recommended) ───────────────────────────────────────
    log.info("\n── Tier 1: Combined ──")

    # China
    write_ruleset(out_root, "china", "China Mainland", POLICY_CHINA,
                  all_domains["CN"], all_cidrs["CN"], generated_at)

    # Global (HK + TW + MO + JP + KR + SG merged)
    global_domains = []
    global_cidrs   = []
    for r in GLOBAL_REGIONS:
        global_domains += all_domains.get(r, [])
        global_cidrs   += all_cidrs.get(r, [])
    write_ruleset(out_root, "global", "Global (HK/TW/MO/JP/KR/SG)", POLICY_GLOBAL,
                  global_domains, global_cidrs, generated_at)

    # ── Tier 2: Per-region (advanced) ────────────────────────────────────────
    log.info("\n── Tier 2: Per-region ──")
    for region in REGIONS:
        policy = REGION_POLICY[region]
        label  = REGION_NAMES[region]
        write_ruleset(out_root, region.lower(), label, policy,
                      all_domains[region], all_cidrs[region],
                      generated_at, subdir="regions")

    write_meta(repo_root, stats, generated_at)
    write_checksums(repo_root)

    log.info("\nBuild complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
