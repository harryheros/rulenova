#!/usr/bin/env python3
"""
build_rules.py — RuleNova main build script

Fetches the latest domain and IP data from domainnova and ipnova,
then generates proxy rule sets for:
  - Clash / Mihomo   (.yaml)
  - Surge            (.list)
  - Shadowrocket     (.conf)
  - Quantumult X     (.conf)
  - sing-box         (.json)

Two rule intents are produced for each region:
  direct — match → DIRECT, else → PROXY  (split-tunnel, mainland users)
  proxy  — match → regional proxy group   (multi-region landing users)

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

REGION_NAMES = {
    "CN": "China Mainland",
    "HK": "Hong Kong",
    "TW": "Taiwan",
    "MO": "Macau",
    "JP": "Japan",
    "KR": "South Korea",
    "SG": "Singapore",
}

# ── Format writers ───────────────────────────────────────────────────────────

def fetch_text(url: str) -> list[str]:
    """Fetch a plain-text URL and return non-empty, non-comment lines."""
    log.info(f"  Fetching {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "rulenova/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        text = resp.read().decode("utf-8")
    return [l.strip() for l in text.splitlines()
            if l.strip() and not l.strip().startswith("#")]


def _header(region: str, intent: str, fmt: str, domains: list, cidrs: list,
            generated_at: str) -> str:
    name = REGION_NAMES.get(region, region)
    return (
        f"# RuleNova — {name} ({intent.upper()})\n"
        f"# Format   : {fmt}\n"
        f"# Domains  : {len(domains)}\n"
        f"# CIDRs    : {len(cidrs)}\n"
        f"# Generated: {generated_at}\n"
        f"# Source   : https://github.com/harryheros/rulenova\n"
        f"#\n"
    )


# ── Clash / Mihomo ───────────────────────────────────────────────────────────

def write_clash(out_dir: Path, region: str, intent: str,
                domains: list[str], cidrs: list[str],
                generated_at: str, action: str) -> Path:
    """
    Clash rule-set provider format (classical text).
    DOMAIN-SUFFIX for apex/subdomains, IP-CIDR for CIDRs.
    """
    lines = [_header(region, intent, "Clash/Mihomo", domains, cidrs, generated_at)]
    for d in domains:
        lines.append(f"DOMAIN-SUFFIX,{d}")
    for cidr in cidrs:
        lines.append(f"IP-CIDR,{cidr},no-resolve")
    path = out_dir / f"{region.lower()}_{intent}.list"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_clash_yaml(out_dir: Path, region: str, intent: str,
                     domains: list[str], cidrs: list[str],
                     generated_at: str, action: str) -> Path:
    """
    Clash rule-set provider YAML format (for rule-providers).
    """
    rules = []
    for d in domains:
        rules.append(f"  - DOMAIN-SUFFIX,{d}")
    for cidr in cidrs:
        rules.append(f"  - IP-CIDR,{cidr},no-resolve")

    content = (
        f"# RuleNova — {REGION_NAMES.get(region, region)} ({intent.upper()})\n"
        f"# Format: Clash/Mihomo YAML rule-provider\n"
        f"# Generated: {generated_at}\n"
        f"payload:\n"
        + "\n".join(rules) + "\n"
    )
    path = out_dir / f"{region.lower()}_{intent}.yaml"
    path.write_text(content, encoding="utf-8")
    return path


# ── Surge ────────────────────────────────────────────────────────────────────

def write_surge(out_dir: Path, region: str, intent: str,
                domains: list[str], cidrs: list[str],
                generated_at: str, action: str) -> Path:
    lines = [_header(region, intent, "Surge", domains, cidrs, generated_at)]
    for d in domains:
        lines.append(f".{d}")           # Surge: leading dot = suffix match
    for cidr in cidrs:
        lines.append(cidr)
    path = out_dir / f"{region.lower()}_{intent}.list"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


# ── Shadowrocket ─────────────────────────────────────────────────────────────

def write_shadowrocket(out_dir: Path, region: str, intent: str,
                       domains: list[str], cidrs: list[str],
                       generated_at: str, action: str) -> Path:
    """
    Shadowrocket rule list format.
    DOMAIN-SUFFIX for domains, IP-CIDR for CIDRs.
    """
    lines = [_header(region, intent, "Shadowrocket", domains, cidrs, generated_at)]
    for d in domains:
        lines.append(f"DOMAIN-SUFFIX,{d},{action}")
    for cidr in cidrs:
        lines.append(f"IP-CIDR,{cidr},{action}")
    path = out_dir / f"{region.lower()}_{intent}.conf"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


# ── Quantumult X ─────────────────────────────────────────────────────────────

def write_quanx(out_dir: Path, region: str, intent: str,
                domains: list[str], cidrs: list[str],
                generated_at: str, action: str) -> Path:
    """
    Quantumult X filter list format.
    host-suffix for domains, ip-cidr for CIDRs.
    """
    lines = [_header(region, intent, "Quantumult X", domains, cidrs, generated_at)]
    qx_action = "direct" if action == "DIRECT" else f"proxy,tag={region}"
    for d in domains:
        lines.append(f"host-suffix, {d}, {qx_action}")
    for cidr in cidrs:
        lines.append(f"ip-cidr, {cidr}, {qx_action}")
    path = out_dir / f"{region.lower()}_{intent}.conf"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


# ── sing-box ─────────────────────────────────────────────────────────────────

def write_singbox(out_dir: Path, region: str, intent: str,
                  domains: list[str], cidrs: list[str],
                  generated_at: str, action: str) -> Path:
    """
    sing-box rule-set source format (JSON).
    """
    rule = {
        "version": 2,
        "metadata": {
            "region":     region,
            "region_name": REGION_NAMES.get(region, region),
            "intent":     intent,
            "action":     action,
            "generated":  generated_at,
            "domains":    len(domains),
            "cidrs":      len(cidrs),
            "source":     "https://github.com/harryheros/rulenova",
        },
        "rules": [
            {
                "domain_suffix": domains,
                "ip_cidr":       cidrs,
            }
        ],
    }
    path = out_dir / f"{region.lower()}_{intent}.json"
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
        "formats":        ["clash-mihomo", "surge", "shadowrocket", "quantumult-x", "sing-box"],
        "intents":        ["direct", "proxy"],
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

INTENT_ACTION = {
    "direct": "DIRECT",
    "proxy":  "PROXY",
}

FORMAT_WRITERS = {
    "clash-mihomo":  (write_clash, write_clash_yaml),
    "surge":         (write_surge,),
    "shadowrocket":  (write_shadowrocket,),
    "quantumult-x":  (write_quanx,),
    "sing-box":      (write_singbox,),
}


def main() -> int:
    parser = argparse.ArgumentParser(description="RuleNova build script")
    parser.add_argument("--repo-root", default=None,
                        help="Path to repo root (default: parent of this script)")
    args = parser.parse_args()

    repo_root = Path(args.repo_root) if args.repo_root else \
        Path(__file__).resolve().parent.parent.parent
    out_root = repo_root / "output"

    generated_at = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")
    log.info(f"RuleNova build — {generated_at}")
    log.info(f"Repo root: {repo_root}")

    stats = {}

    for region in REGIONS:
        log.info(f"\n── {region} ({REGION_NAMES[region]}) ──")

        # Fetch upstream data
        try:
            domains = fetch_text(
                f"{DOMAINNOVA_BASE}/domains_{region.lower()}.txt")
        except Exception as e:
            log.error(f"  Failed to fetch domains for {region}: {e}")
            domains = []

        try:
            cidrs = fetch_text(
                f"{IPNOVA_BASE}/{region}.txt")
        except Exception as e:
            log.error(f"  Failed to fetch CIDRs for {region}: {e}")
            cidrs = []

        log.info(f"  domains={len(domains)}, cidrs={len(cidrs)}")
        stats[region] = {"domains": len(domains), "cidrs": len(cidrs)}

        for intent, action in INTENT_ACTION.items():
            for fmt, writers in FORMAT_WRITERS.items():
                fmt_dir = out_root / fmt / intent
                fmt_dir.mkdir(parents=True, exist_ok=True)
                for writer in writers:
                    path = writer(fmt_dir, region, intent,
                                  domains, cidrs, generated_at, action)
                    log.info(f"  [{fmt}/{intent}] {path.name}")

    write_meta(repo_root, stats, generated_at)
    write_checksums(repo_root)

    log.info("\nBuild complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
