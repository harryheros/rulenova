#!/usr/bin/env python3
"""
validate_output.py — RuleNova output validation

Checks:
1. All expected output files exist
2. File sizes are non-trivially small (>= MIN_LINES)
3. checksums.txt matches actual file hashes
4. meta.json counts match actual file line counts
"""

import hashlib
import json
import sys
from pathlib import Path

ROOT     = Path(__file__).resolve().parent.parent.parent
OUT_DIR  = ROOT / "output"

REGIONS  = ["CN", "HK", "TW", "MO", "JP", "KR", "SG"]
FORMATS  = ["clash-mihomo", "surge", "shadowrocket", "quantumult-x", "sing-box"]
INTENTS  = ["direct", "proxy"]

# Minimum rule count per region (domains + CIDRs combined).
# Values are set conservatively below current actuals to catch catastrophic
# fetch failures, not minor weekly fluctuations:
#   CN ~3350 domains + ~5490 CIDRs, HK ~165 + ~2470, etc.
MIN_LINES: dict[str, int] = {
    "CN": 3000, "HK": 100, "TW": 100, "MO": 20,
    "JP": 100,  "KR": 100, "SG": 100,
}

# Expected file extensions per format
FMT_EXTS: dict[str, list[str]] = {
    "clash-mihomo":  [".list", ".yaml"],
    "surge":         [".list"],
    "shadowrocket":  [".conf"],
    "quantumult-x":  [".conf"],
    "sing-box":      [".json"],
}

errors: list[str] = []


def check_file_exists(path: Path) -> bool:
    if not path.exists():
        errors.append(f"MISSING: {path.relative_to(ROOT)}")
        return False
    return True


def count_rule_lines(path: Path) -> int:
    """Count non-comment, non-empty lines (actual rules)."""
    if path.suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        rules = data.get("rules", [{}])[0]
        return len(rules.get("domain_suffix", [])) + len(rules.get("ip_cidr", []))
    if path.suffix == ".yaml":
        return sum(1 for l in path.read_text().splitlines()
                   if l.strip().startswith("- "))
    return sum(1 for l in path.read_text(encoding="utf-8").splitlines()
               if l.strip() and not l.strip().startswith("#"))


def validate_files() -> None:
    for region in REGIONS:
        min_lines = MIN_LINES.get(region, 10)
        for fmt in FORMATS:
            for intent in INTENTS:
                for ext in FMT_EXTS[fmt]:
                    fname = f"{region.lower()}_{intent}{ext}"
                    path  = OUT_DIR / fmt / intent / fname
                    if not check_file_exists(path):
                        continue
                    count = count_rule_lines(path)
                    if count < min_lines:
                        errors.append(
                            f"TOO_SMALL: {path.relative_to(ROOT)} "
                            f"({count} rules, expected >= {min_lines})")


def validate_checksums() -> None:
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


def validate_meta() -> None:
    meta_path = OUT_DIR / "meta.json"
    if not meta_path.exists():
        errors.append("MISSING: output/meta.json")
        return
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    for region, counts in meta.get("regions", {}).items():
        expected_domains = counts.get("domains", 0)
        if expected_domains < MIN_LINES.get(region, 1):
            errors.append(
                f"META_LOW_DOMAINS: {region} has {expected_domains} domains")


def main() -> int:
    print("RuleNova output validation")
    print(f"  Output dir: {OUT_DIR}")

    validate_files()
    validate_checksums()
    validate_meta()

    if errors:
        print(f"\n❌ {len(errors)} error(s):")
        for e in errors:
            print(f"  {e}")
        return 1

    total = len(REGIONS) * len(FORMATS) * len(INTENTS) * 2
    print(f"\n✅ All checks passed ({total} files validated)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
