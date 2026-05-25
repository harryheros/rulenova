#!/usr/bin/env python3
"""
build_rules.py — RuleNova main build script

Fetches the latest domain and IP data from domainnova and ipnova,
then generates proxy rule sets for:
  - Clash / Mihomo   (.list + .yaml)   no action — user assigns in config
  - Surge            (.list)            no action — user assigns in config
  - sing-box         (.json)            no action — user assigns in config
  - Shadowrocket     (.conf)            direct + proxy variants
  - Quantumult X     (.conf)            direct + proxy variants

Clash, Surge and sing-box carry no action because these formats let the user
assign any policy group in their own configuration file. Shadowrocket and
Quantumult X require action embedded in the rule syntax, so both direct and
proxy variants are generated.

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

# ── Helpers ──────────────────────────────────────────────────────────────────

def _header(region: str, fmt: str, generated_at: str, intent: str = "") -> str:
    intent_str = f" ({intent.upper()})" if intent else ""
    return (
        f"# RuleNova — {REGION_NAMES.get(region, region)}{intent_str}\n"
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


def write_clash(out_dir: Path, region: str,
                domains: list[str], cidrs: list[str],
                generated_at: str) -> Path:
    """Clash rule-set provider format (classical text). No action — user decides."""
    lines = [_header(region, "Clash/Mihomo", generated_at)]
    for d in domains:
        lines.append(f"DOMAIN-SUFFIX,{d}")
    for cidr in cidrs:
        lines.append(f"IP-CIDR,{cidr},no-resolve")
    path = out_dir / f"{region.lower()}.list"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_clash_yaml(out_dir: Path, region: str,
                     domains: list[str], cidrs: list[str],
                     generated_at: str) -> Path:
    """Clash rule-set provider YAML format. No action."""
    rules = []
    for d in domains:
        rules.append(f"  - DOMAIN-SUFFIX,{d}")
    for cidr in cidrs:
        rules.append(f"  - IP-CIDR,{cidr},no-resolve")
    content = (
        f"# RuleNova — {REGION_NAMES.get(region, region)}\n"
        f"# Format: Clash/Mihomo YAML rule-provider\n"
        f"# Generated: {generated_at}\n"
        f"payload:\n"
        + "\n".join(rules) + "\n"
    )
    path = out_dir / f"{region.lower()}.yaml"
    path.write_text(content, encoding="utf-8")
    return path


def write_surge(out_dir: Path, region: str,
                domains: list[str], cidrs: list[str],
                generated_at: str) -> Path:
    """Surge rule list. No action — user assigns in config."""
    lines = [_header(region, "Surge", generated_at)]
    for d in domains:
        lines.append(f".{d}")
    for cidr in cidrs:
        lines.append(cidr)
    path = out_dir / f"{region.lower()}.list"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_shadowrocket(out_dir: Path, region: str,
                       domains: list[str], cidrs: list[str],
                       generated_at: str) -> Path:
    """Shadowrocket rule list. No action — user assigns in config."""
    lines = [_header(region, "Shadowrocket", generated_at)]
    for d in domains:
        lines.append(f"DOMAIN-SUFFIX,{d}")
    for cidr in cidrs:
        lines.append(f"IP-CIDR,{cidr},no-resolve")
    path = out_dir / f"{region.lower()}.conf"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_quanx(out_dir: Path, region: str,
                domains: list[str], cidrs: list[str],
                generated_at: str) -> Path:
    """Quantumult X filter list. No action — user assigns in config."""
    lines = [_header(region, "Quantumult X", generated_at)]
    for d in domains:
        lines.append(f"host-suffix, {d}")
    for cidr in cidrs:
        lines.append(f"ip-cidr, {cidr}")
    path = out_dir / f"{region.lower()}.conf"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_singbox(out_dir: Path, region: str,
                  domains: list[str], cidrs: list[str],
                  generated_at: str) -> Path:
    """sing-box rule-set source format. No action."""
    rule = {
        "version": 2,
        "metadata": {
            "region":      region,
            "region_name": REGION_NAMES.get(region, region),
            "generated":   generated_at,
            "domains":     len(domains),
            "cidrs":       len(cidrs),
            "source":      "https://github.com/harryheros/rulenova",
        },
        "rules": [{"domain_suffix": domains, "ip_cidr": cidrs}],
    }
    path = out_dir / f"{region.lower()}.json"
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

NO_ACTION_FORMATS = {
    "clash-mihomo":  (write_clash, write_clash_yaml),
    "surge":         (write_surge,),
    "sing-box":      (write_singbox,),
    "shadowrocket":  (write_shadowrocket,),
    "quantumult-x":  (write_quanx,),
}


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

        log.info(f"  domains={len(domains)}, cidrs={len(cidrs)}")
        stats[region] = {"domains": len(domains), "cidrs": len(cidrs)}

        # All formats: one file per region, no action
        for fmt, writers in NO_ACTION_FORMATS.items():
            fmt_dir = out_root / fmt
            fmt_dir.mkdir(parents=True, exist_ok=True)
            for writer in writers:
                path = writer(fmt_dir, region, domains, cidrs, generated_at)
                log.info(f"  [{fmt}] {path.name}")

    write_meta(repo_root, stats, generated_at)
    write_checksums(repo_root)

    log.info("\nBuild complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
