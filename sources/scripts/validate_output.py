#!/usr/bin/env python3
"""validate_output.py — RuleNova output validation"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
OUT_DIR = ROOT / "output"
REGIONS = ["cn", "hk", "tw", "mo", "jp", "kr", "sg"]

MIN_RULES = {
    "china": 3000,
    "china-domain": 3000,
    "china-ip": 10,
    "global": 500,
    "global-domain": 500,
    "global-ip": 10,
    "cn": 3000, "hk": 50, "tw": 50, "mo": 10, "jp": 50, "kr": 50, "sg": 50,
}

FMT_EXTS = {
    "clash-mihomo": [".list", ".yaml"],
    "stash": [".list", ".yaml"],
    "surge": [".list"],
    "sing-box": [".json"],
    "shadowrocket": [".conf"],
    "quantumult-x": [".conf"],
    "loon": [".list"],
}


def count_rule_lines(path: Path) -> int:
    if path.suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        total = 0
        for rule in data.get("rules", []):
            total += len(rule.get("domain_suffix", []))
            total += len(rule.get("ip_cidr", []))
        return total
    if path.suffix == ".yaml":
        return sum(1 for line in path.read_text(encoding="utf-8").splitlines()
                   if line.strip().startswith("- "))
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines()
               if line.strip() and not line.startswith("#"))


def expected_names(base: str) -> list[str]:
    return [base, f"{base}-domain", f"{base}-ip"]


def validate_file_set(errors: list[str]) -> None:
    for base in ["china", "global"]:
        for name in expected_names(base):
            min_rules = MIN_RULES[name]
            for fmt, exts in FMT_EXTS.items():
                for ext in exts:
                    path = OUT_DIR / fmt / f"{name}{ext}"
                    if not path.exists():
                        errors.append(f"MISSING: output/{fmt}/{name}{ext}")
                        continue
                    count = count_rule_lines(path)
                    if count < min_rules:
                        errors.append(f"TOO_SMALL: output/{fmt}/{name}{ext} ({count}, expected >= {min_rules})")

    for region in REGIONS:
        for name in expected_names(region):
            base = region if not name.endswith(("-domain", "-ip")) else name.rsplit("-", 1)[0]
            min_rules = MIN_RULES.get(base, 10)
            if name.endswith("-ip"):
                min_rules = 1
            for fmt, exts in FMT_EXTS.items():
                for ext in exts:
                    path = OUT_DIR / fmt / "regions" / f"{name}{ext}"
                    if not path.exists():
                        errors.append(f"MISSING: output/{fmt}/regions/{name}{ext}")
                        continue
                    count = count_rule_lines(path)
                    if count < min_rules:
                        errors.append(f"TOO_SMALL: output/{fmt}/regions/{name}{ext} ({count}, expected >= {min_rules})")


def validate_checksums(errors: list[str]) -> None:
    ck_path = OUT_DIR / "checksums.txt"
    if not ck_path.exists():
        errors.append("MISSING: output/checksums.txt")
        return
    seen = 0
    for line in ck_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        seen += 1
        try:
            sha, rel = line.split("  ", 1)
        except ValueError:
            errors.append(f"BAD_CHECKSUM_LINE: {line}")
            continue
        path = OUT_DIR / rel
        if not path.exists():
            errors.append(f"CHECKSUM_MISSING_FILE: {rel}")
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != sha:
            errors.append(f"CHECKSUM_MISMATCH: {rel}")
    if seen == 0:
        errors.append("EMPTY: output/checksums.txt")


def validate_meta(errors: list[str]) -> None:
    meta_path = OUT_DIR / "meta.json"
    if not meta_path.exists():
        errors.append("MISSING: output/meta.json")
        return
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if meta.get("schema_version") != "2.1":
        errors.append("META_SCHEMA_NOT_2_1")
    for fmt in FMT_EXTS:
        if fmt not in meta.get("formats", []):
            errors.append(f"META_MISSING_FORMAT: {fmt}")



def validate_policy_names(errors: list[str]) -> None:
    bad_token = "RuleNova-"
    for path in OUT_DIR.rglob("*"):
        if not path.is_file() or path.name == "checksums.txt":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if bad_token in text:
            errors.append(f"LONG_POLICY_NAME_FOUND: {path.relative_to(OUT_DIR)}")

    # Surge files are intended for RULE-SET usage, so remote rules must not
    # include a policy column. Accepted examples:
    #   DOMAIN-SUFFIX,example.com
    #   IP-CIDR,1.2.3.0/24,no-resolve
    for path in (OUT_DIR / "surge").rglob("*.list"):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            parts = [x.strip() for x in stripped.split(",")]
            rule_type = parts[0].upper()
            if rule_type == "DOMAIN-SUFFIX" and len(parts) != 2:
                errors.append(f"SURGE_BAD_DOMAIN_RULE: {path.relative_to(OUT_DIR)}:{lineno}")
            if rule_type in {"IP-CIDR", "IP-CIDR6", "IP6-CIDR"}:
                if len(parts) not in {2, 3} or (len(parts) == 3 and parts[2] != "no-resolve"):
                    errors.append(f"SURGE_BAD_IP_RULE: {path.relative_to(OUT_DIR)}:{lineno}")

def validate_no_stale_action_dirs(errors: list[str]) -> None:
    stale = [p for p in OUT_DIR.rglob("*") if p.is_dir() and p.name in {"direct", "proxy"}]
    for path in stale:
        errors.append(f"STALE_ACTION_DIR: {path.relative_to(OUT_DIR)}")


def main() -> int:
    print("RuleNova output validation")
    print(f"  Output dir: {OUT_DIR}")
    errors: list[str] = []
    validate_file_set(errors)
    validate_checksums(errors)
    validate_meta(errors)
    validate_policy_names(errors)
    validate_no_stale_action_dirs(errors)
    if errors:
        print(f"\n❌ {len(errors)} error(s):")
        for error in errors:
            print(f"  {error}")
        return 1
    print("\n✅ All checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
