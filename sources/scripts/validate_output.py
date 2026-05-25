#!/usr/bin/env python3
"""validate_output.py — RuleNova output validation"""

import hashlib
import json
import sys
from pathlib import Path

ROOT    = Path(__file__).resolve().parent.parent.parent
OUT_DIR = ROOT / "output"

REGIONS = ["CN", "HK", "TW", "MO", "JP", "KR", "SG"]

MIN_LINES = {
    "china":  3000,
    "global": 500,
    "CN": 3000, "HK": 100, "TW": 100, "MO": 20,
    "JP": 100,  "KR": 100, "SG": 100,
}

FMT_EXTS = {
    "clash-mihomo": [".list", ".yaml"],
    "surge":        [".list"],
    "sing-box":     [".json"],
    "shadowrocket": [".conf"],
    "quantumult-x": [".conf"],
}


def count_rule_lines(path: Path) -> int:
    if path.suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        rules = data.get("rules", [{}])[0]
        return len(rules.get("domain_suffix", [])) + len(rules.get("ip_cidr", []))
    if path.suffix == ".yaml":
        return sum(1 for l in path.read_text().splitlines()
                   if l.strip().startswith("- "))
    return sum(1 for l in path.read_text(encoding="utf-8").splitlines()
               if l.strip() and not l.strip().startswith("#"))


def validate_files(errors: list) -> None:
    # Tier 1: china + global
    for name in ["china", "global"]:
        min_lines = MIN_LINES[name]
        for fmt, exts in FMT_EXTS.items():
            for ext in exts:
                path = OUT_DIR / fmt / f"{name}{ext}"
                if not path.exists():
                    errors.append(f"MISSING: output/{fmt}/{name}{ext}")
                    continue
                count = count_rule_lines(path)
                if count < min_lines:
                    errors.append(f"TOO_SMALL: output/{fmt}/{name}{ext} "
                                  f"({count} rules, expected >= {min_lines})")

    # Tier 2: per-region under regions/
    for region in REGIONS:
        name = region.lower()
        min_lines = MIN_LINES.get(region, 10)
        for fmt, exts in FMT_EXTS.items():
            for ext in exts:
                path = OUT_DIR / fmt / "regions" / f"{name}{ext}"
                if not path.exists():
                    errors.append(f"MISSING: output/{fmt}/regions/{name}{ext}")
                    continue
                count = count_rule_lines(path)
                if count < min_lines:
                    errors.append(f"TOO_SMALL: output/{fmt}/regions/{name}{ext} "
                                  f"({count} rules, expected >= {min_lines})")


def validate_checksums(errors: list) -> None:
    ck_path = OUT_DIR / "checksums.txt"
    if not ck_path.exists():
        errors.append("MISSING: output/checksums.txt")
        return
    for line in ck_path.read_text().splitlines():
        if not line.strip():
            continue
        sha, rel = line.split("  ", 1)
        path = OUT_DIR / rel
        if not path.exists():
            errors.append(f"CHECKSUM_MISSING_FILE: {rel}")
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != sha:
            errors.append(f"CHECKSUM_MISMATCH: {rel}")


def validate_meta(errors: list) -> None:
    meta_path = OUT_DIR / "meta.json"
    if not meta_path.exists():
        errors.append("MISSING: output/meta.json")
        return
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    for region, counts in meta.get("regions", {}).items():
        if counts.get("domains", 0) < MIN_LINES.get(region, 1):
            errors.append(f"META_LOW_DOMAINS: {region} has {counts.get('domains')} domains")


def main() -> int:
    print("RuleNova output validation")
    print(f"  Output dir: {OUT_DIR}")

    errors: list[str] = []
    validate_files(errors)
    validate_checksums(errors)
    validate_meta(errors)

    if errors:
        print(f"\n❌ {len(errors)} error(s):")
        for e in errors:
            print(f"  {e}")
        return 1

    n_combined = 2 * sum(len(v) for v in FMT_EXTS.values())
    n_regions  = len(REGIONS) * sum(len(v) for v in FMT_EXTS.values())
    print(f"\n✅ All checks passed ({n_combined + n_regions} files validated)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
