#!/usr/bin/env python3
"""Build RuleNova outputs.

RuleNova keeps routing decisions abstract:

- China / Global are policy names, not hard-coded DIRECT or PROXY actions.
- Clash/Mihomo/Stash, Surge and sing-box outputs stay provider-friendly.
- Shadowrocket, Quantumult X and Loon outputs include short policy names because
  those clients commonly expect a policy column inside imported rules.

The build always recreates output/ unless --keep-output is passed, so stale
variants such as old direct/proxy folders cannot survive accidentally.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import ipaddress
import json
import logging
import re
import shutil
import sys
import urllib.request
from collections.abc import Callable
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
LOG = logging.getLogger("rulenova")

DOMAINNOVA_BASE = "https://raw.githubusercontent.com/harryheros/domainnova/main/dist"
IPNOVA_BASE = "https://raw.githubusercontent.com/harryheros/ipnova/main/output/plain"

REGIONS = ("CN", "HK", "TW", "MO", "JP", "KR", "SG")
GLOBAL_REGIONS = ("HK", "TW", "MO", "JP", "KR", "SG")

REGION_NAMES = {
    "CN": "China Mainland",
    "HK": "Hong Kong",
    "TW": "Taiwan",
    "MO": "Macau",
    "JP": "Japan",
    "KR": "South Korea",
    "SG": "Singapore",
}

POLICY_CHINA = "China"
POLICY_GLOBAL = "Global"

REGION_POLICY = {
    "CN": POLICY_CHINA,
    "HK": "HK",
    "TW": "TW",
    "MO": "MO",
    "JP": "JP",
    "KR": "KR",
    "SG": "SG",
}

VARIANTS = ("combined", "domain", "ip")
DOMAIN_RE = re.compile(
    r"^(?=.{1,253}$)(?!-)(?:[a-z0-9-]{1,63}\.)+[a-z0-9-]{2,63}$"
)

# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------


def header(label: str, fmt: str, generated_at: str, *, policy: str | None = None,
           variant: str = "combined") -> str:
    policy_line = f"# Policy   : {policy}\n" if policy else ""
    return (
        f"# RuleNova — {label}\n"
        f"# Variant  : {variant}\n"
        f"# Format   : {fmt}\n"
        f"{policy_line}"
        f"# Generated: {generated_at}\n"
        f"# Source   : https://github.com/harryheros/rulenova\n"
        "#\n"
    )


def unique_sorted(items: list[str]) -> list[str]:
    return sorted(dict.fromkeys(item.strip() for item in items if item and item.strip()))


def strip_comment(line: str) -> str:
    # Keep it conservative: source files are one rule per line; inline comments are
    # not expected, but this makes local test fixtures safer.
    return line.split("#", 1)[0].strip()


def clean_domain(line: str) -> str | None:
    value = strip_comment(line).lower().strip("'\"")
    if not value:
        return None

    parts = [part.strip() for part in value.split(",")]
    rule_type = parts[0].upper()
    if rule_type in {"DOMAIN-SUFFIX", "HOST-SUFFIX", "HOST"} and len(parts) >= 2:
        value = parts[1]
    elif "," in value:
        return None

    value = value.lstrip(".").rstrip(".")
    if not DOMAIN_RE.fullmatch(value):
        return None
    return value


def clean_cidr(line: str) -> str | None:
    value = strip_comment(line).strip("'\"")
    if not value:
        return None

    parts = [part.strip() for part in value.split(",")]
    rule_type = parts[0].upper()
    if rule_type in {"IP-CIDR", "IP-CIDR6", "IP6-CIDR"} and len(parts) >= 2:
        value = parts[1]
    elif "," in value:
        return None

    try:
        return str(ipaddress.ip_network(value, strict=False))
    except ValueError:
        return None


def fetch_text(url: str) -> list[str]:
    LOG.info("  Fetching %s", url)
    req = urllib.request.Request(url, headers={"User-Agent": "rulenova/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        text = resp.read().decode("utf-8")
    return [line for line in (strip_comment(x) for x in text.splitlines()) if line]


def fetch_region(region: str) -> tuple[list[str], list[str]]:
    """Fetch one region's domain + CIDR data with isolated error handling.

    Each upstream is fetched independently so a transient failure on one
    source does not break the other. Cleansing drop rates above 20% emit a
    WARNING so silent upstream format changes surface during CI rather than
    after rules are already published.
    """
    try:
        raw_domains = fetch_text(f"{DOMAINNOVA_BASE}/domains_{region.lower()}.txt")
    except Exception as exc:
        LOG.warning("  [%s] domain fetch failed: %s", region, exc)
        raw_domains = []

    try:
        raw_cidrs = fetch_text(f"{IPNOVA_BASE}/{region}.txt")
    except Exception as exc:
        LOG.warning("  [%s] CIDR fetch failed: %s", region, exc)
        raw_cidrs = []

    domains = unique_sorted([d for d in map(clean_domain, raw_domains) if d])
    cidrs = unique_sorted([c for c in map(clean_cidr, raw_cidrs) if c])

    # Surface silent drops — if cleansing rejects >20% of upstream items,
    # upstream format likely changed and the rule set is degrading.
    _warn_drop_rate(region, "domains", len(raw_domains), len(domains))
    _warn_drop_rate(region, "cidrs", len(raw_cidrs), len(cidrs))

    return domains, cidrs


def _warn_drop_rate(region: str, kind: str, raw: int, kept: int) -> None:
    if raw == 0:
        return
    dropped = raw - kept
    rate = dropped / raw
    if rate > 0.20:
        LOG.warning(
            "  [%s] %s: kept %d/%d (dropped %.0f%%) — upstream format may have changed",
            region, kind, kept, raw, rate * 100,
        )


def write_text(path: Path, lines: list[str]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path

# ---------------------------------------------------------------------------
# Writers: Clash/Mihomo/Stash provider-friendly outputs
# ---------------------------------------------------------------------------


def clash_payload(domains: list[str], cidrs: list[str], variant: str) -> list[str]:
    if variant == "domain":
        return domains
    if variant == "ip":
        return cidrs
    return [f"DOMAIN-SUFFIX,{d}" for d in domains] + [f"IP-CIDR,{c},no-resolve" for c in cidrs]


def write_clash_text(out_dir: Path, name: str, label: str, policy: str,
                     domains: list[str], cidrs: list[str], generated_at: str,
                     variant: str = "combined") -> Path:
    del policy
    lines = [header(label, "Clash/Mihomo/Stash text", generated_at, variant=variant)]
    lines.extend(clash_payload(domains, cidrs, variant))
    return write_text(out_dir / f"{name}.list", lines)


def write_clash_yaml(out_dir: Path, name: str, label: str, policy: str,
                     domains: list[str], cidrs: list[str], generated_at: str,
                     variant: str = "combined") -> Path:
    del policy
    payload = clash_payload(domains, cidrs, variant)
    lines = [
        f"# RuleNova — {label}",
        f"# Variant: {variant}",
        "# Format: Clash/Mihomo/Stash YAML rule-provider",
        f"# Generated: {generated_at}",
        "payload:",
    ]
    # Plain YAML scalars per Clash/Mihomo provider conventions
    # (https://wiki.metacubex.one/config/rule-providers/). Items contain only
    # safe characters (letters, digits, dots, slashes, commas, hyphens) so
    # quoting would be syntactically valid but visually inconsistent with
    # ecosystem norms and may confuse older parsers.
    lines.extend(f"  - {item}" for item in payload)
    return write_text(out_dir / f"{name}.yaml", lines)

# ---------------------------------------------------------------------------
# Writers: client-specific rule formats
# ---------------------------------------------------------------------------


def write_surge(out_dir: Path, name: str, label: str, policy: str,
                domains: list[str], cidrs: list[str], generated_at: str,
                variant: str = "combined") -> Path:
    """Surge RULE-SET output: no embedded policy column."""
    del policy
    lines = [header(label, "Surge RULE-SET", generated_at, variant=variant)]
    if variant in {"combined", "domain"}:
        lines.extend(f"DOMAIN-SUFFIX,{d}" for d in domains)
    if variant in {"combined", "ip"}:
        lines.extend(f"IP-CIDR,{c},no-resolve" for c in cidrs)
    return write_text(out_dir / f"{name}.list", lines)


def write_shadowrocket(out_dir: Path, name: str, label: str, policy: str,
                       domains: list[str], cidrs: list[str], generated_at: str,
                       variant: str = "combined") -> Path:
    lines = [header(label, "Shadowrocket", generated_at, policy=policy, variant=variant)]
    if variant in {"combined", "domain"}:
        lines.extend(f"DOMAIN-SUFFIX,{d},{policy}" for d in domains)
    if variant in {"combined", "ip"}:
        lines.extend(f"IP-CIDR,{c},{policy},no-resolve" for c in cidrs)
    return write_text(out_dir / f"{name}.conf", lines)


def write_quanx(out_dir: Path, name: str, label: str, policy: str,
                domains: list[str], cidrs: list[str], generated_at: str,
                variant: str = "combined") -> Path:
    lines = [header(label, "Quantumult X", generated_at, policy=policy, variant=variant)]
    if variant in {"combined", "domain"}:
        lines.extend(f"host-suffix, {d}, {policy}" for d in domains)
    if variant in {"combined", "ip"}:
        lines.extend(f"ip-cidr, {c}, {policy}" for c in cidrs)
    return write_text(out_dir / f"{name}.conf", lines)


def write_loon(out_dir: Path, name: str, label: str, policy: str,
               domains: list[str], cidrs: list[str], generated_at: str,
               variant: str = "combined") -> Path:
    lines = [header(label, "Loon", generated_at, policy=policy, variant=variant)]
    if variant in {"combined", "domain"}:
        lines.extend(f"DOMAIN-SUFFIX,{d},{policy}" for d in domains)
    if variant in {"combined", "ip"}:
        lines.extend(f"IP-CIDR,{c},{policy},no-resolve" for c in cidrs)
    return write_text(out_dir / f"{name}.list", lines)


def write_singbox(out_dir: Path, name: str, label: str, policy: str,
                  domains: list[str], cidrs: list[str], generated_at: str,
                  variant: str = "combined") -> Path:
    rule: dict[str, list[str]] = {}
    if variant in {"combined", "domain"} and domains:
        rule["domain_suffix"] = domains
    if variant in {"combined", "ip"} and cidrs:
        rule["ip_cidr"] = cidrs

    data = {
        "version": 2,
        "metadata": {
            "label": label,
            "variant": variant,
            "suggested_policy": policy,
            "generated": generated_at,
            "domains": len(domains) if variant in {"combined", "domain"} else 0,
            "cidrs": len(cidrs) if variant in {"combined", "ip"} else 0,
            "source": "https://github.com/harryheros/rulenova",
        },
        "rules": [rule] if rule else [],
    }
    path = out_dir / f"{name}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


Writer = Callable[[Path, str, str, str, list[str], list[str], str, str], Path]
FORMATS: dict[str, tuple[Writer, ...]] = {
    "clash-mihomo": (write_clash_text, write_clash_yaml),
    "stash": (write_clash_text, write_clash_yaml),
    "surge": (write_surge,),
    "sing-box": (write_singbox,),
    "shadowrocket": (write_shadowrocket,),
    "quantumult-x": (write_quanx,),
    "loon": (write_loon,),
}

# ---------------------------------------------------------------------------
# Output orchestration
# ---------------------------------------------------------------------------


def variant_data(name: str, domains: list[str], cidrs: list[str]) -> list[tuple[str, str, list[str], list[str]]]:
    return [
        (name, "combined", domains, cidrs),
        (f"{name}-domain", "domain", domains, []),
        (f"{name}-ip", "ip", [], cidrs),
    ]


def write_ruleset(out_root: Path, name: str, label: str, policy: str,
                  domains: list[str], cidrs: list[str], generated_at: str,
                  subdir: str = "") -> None:
    for fmt, writers in FORMATS.items():
        fmt_dir = out_root / fmt / subdir if subdir else out_root / fmt
        for file_name, variant, ds, cs in variant_data(name, domains, cidrs):
            for writer in writers:
                path = writer(fmt_dir, file_name, label, policy, ds, cs, generated_at, variant)
                shown_dir = f"{fmt}/{subdir}" if subdir else fmt
                LOG.info("  [%s] %s", shown_dir, path.name)


def write_meta(repo_root: Path, stats: dict[str, dict[str, int]], generated_at: str) -> None:
    meta = {
        "schema_version": "2.1",
        "project": "rulenova",
        "generated_at": generated_at,
        "policy_names": {
            "china": POLICY_CHINA,
            "global": POLICY_GLOBAL,
            "regions": REGION_POLICY,
            "note": "Short abstract names are intentional. Users map them to DIRECT, PROXY, Auto, or a node group.",
        },
        "tiers": ["combined", "domain", "ip", "regions"],
        "regions": stats,
        "global_regions": list(GLOBAL_REGIONS),
        "formats": sorted(FORMATS.keys()),
    }
    out = repo_root / "output" / "meta.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    LOG.info("Wrote %s", out)


def write_checksums(repo_root: Path) -> None:
    out_dir = repo_root / "output"
    lines: list[str] = []
    for path in sorted(out_dir.rglob("*")):
        if path.is_file() and path.name not in {"checksums.txt", "meta.json"}:
            rel = path.relative_to(out_dir).as_posix()
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            lines.append(f"{digest}  {rel}")
    ck_path = out_dir / "checksums.txt"
    ck_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    LOG.info("Wrote %s (%d files)", ck_path, len(lines))


def build(repo_root: Path, *, keep_output: bool = False) -> None:
    out_root = repo_root / "output"
    generated_at = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    LOG.info("RuleNova build — %s", generated_at)
    LOG.info("Repo root: %s", repo_root)

    if out_root.exists() and not keep_output:
        shutil.rmtree(out_root)
    out_root.mkdir(parents=True, exist_ok=True)

    all_domains: dict[str, list[str]] = {}
    all_cidrs: dict[str, list[str]] = {}
    stats: dict[str, dict[str, int]] = {}

    for region in REGIONS:
        LOG.info("\n── %s (%s) ──", region, REGION_NAMES[region])
        domains, cidrs = fetch_region(region)
        all_domains[region] = domains
        all_cidrs[region] = cidrs
        stats[region] = {"domains": len(domains), "cidrs": len(cidrs)}
        LOG.info("  domains=%d, cidrs=%d", len(domains), len(cidrs))

    LOG.info("\n── Tier 1: China / Global ──")
    write_ruleset(out_root, "china", "China Mainland", POLICY_CHINA,
                  all_domains["CN"], all_cidrs["CN"], generated_at)

    global_domains = unique_sorted([d for r in GLOBAL_REGIONS for d in all_domains[r]])
    global_cidrs = unique_sorted([c for r in GLOBAL_REGIONS for c in all_cidrs[r]])
    stats["GLOBAL"] = {"domains": len(global_domains), "cidrs": len(global_cidrs)}
    write_ruleset(out_root, "global", "Global (HK/TW/MO/JP/KR/SG)", POLICY_GLOBAL,
                  global_domains, global_cidrs, generated_at)

    LOG.info("\n── Tier 2: Per-region ──")
    for region in REGIONS:
        write_ruleset(out_root, region.lower(), REGION_NAMES[region], REGION_POLICY[region],
                      all_domains[region], all_cidrs[region], generated_at, subdir="regions")

    write_meta(repo_root, stats, generated_at)
    write_checksums(repo_root)
    LOG.info("\nBuild complete.")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build RuleNova rule outputs")
    parser.add_argument("--repo-root", type=Path, default=None)
    parser.add_argument("--keep-output", action="store_true", help="Do not delete output before writing new files")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    repo_root = args.repo_root or Path(__file__).resolve().parents[2]
    build(repo_root.resolve(), keep_output=args.keep_output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
