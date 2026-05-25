# RuleNova

[![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc-sa/4.0/)
[![Update Rules](https://img.shields.io/github/actions/workflow/status/harryheros/rulenova/update.yml?label=weekly%20update)](https://github.com/harryheros/rulenova/actions/workflows/update.yml)

Automated proxy rule sets for Clash, Surge, Shadowrocket, Quantumult X and sing-box — built on [IPNova](https://github.com/harryheros/ipnova) and [DomainNova](https://github.com/harryheros/domainnova).

---

## Two tiers

### Tier 1 — Combined (recommended)

Two rule sets cover most users:

| Rule set | Policy name | Coverage |
|---|---|---|
| `china` | `China` | CN domains and IPs |
| `global` | `Global` | HK / TW / MO / JP / KR / SG merged |

Add these to your client and map each policy name to your preferred proxy or direct connection. No need to touch the rule set again when you change nodes or travel.

### Tier 2 — Per-region (advanced)

Individual rule sets under `regions/` for users who need fine-grained control:

`cn` `hk` `tw` `mo` `jp` `kr` `sg`

---

## Formats

| Format | Files |
|---|---|
| Clash / Mihomo | `output/clash-mihomo/china.list` + `.yaml` |
| Surge | `output/surge/china.list` |
| sing-box | `output/sing-box/china.json` |
| Shadowrocket | `output/shadowrocket/china.conf` |
| Quantumult X | `output/quantumult-x/china.conf` |

---

## Raw URLs

```
# Tier 1 — Clash / Mihomo
https://raw.githubusercontent.com/harryheros/rulenova/main/output/clash-mihomo/china.list
https://raw.githubusercontent.com/harryheros/rulenova/main/output/clash-mihomo/global.list

# Tier 1 — Surge
https://raw.githubusercontent.com/harryheros/rulenova/main/output/surge/china.list
https://raw.githubusercontent.com/harryheros/rulenova/main/output/surge/global.list

# Tier 1 — sing-box
https://raw.githubusercontent.com/harryheros/rulenova/main/output/sing-box/china.json
https://raw.githubusercontent.com/harryheros/rulenova/main/output/sing-box/global.json

# Tier 1 — Shadowrocket
https://raw.githubusercontent.com/harryheros/rulenova/main/output/shadowrocket/china.conf
https://raw.githubusercontent.com/harryheros/rulenova/main/output/shadowrocket/global.conf

# Tier 1 — Quantumult X
https://raw.githubusercontent.com/harryheros/rulenova/main/output/quantumult-x/china.conf
https://raw.githubusercontent.com/harryheros/rulenova/main/output/quantumult-x/global.conf

# Tier 2 — per-region (example: HK)
https://raw.githubusercontent.com/harryheros/rulenova/main/output/clash-mihomo/regions/hk.list
```

---

## Update schedule

Every Monday 06:00 UTC — 4 hours after IPNova and DomainNova complete their weekly update.

## Data sources

- Domains: [DomainNova](https://github.com/harryheros/domainnova) `dist/domains_{region}.txt`
- IP CIDRs: [IPNova](https://github.com/harryheros/ipnova) `output/plain/{region}.txt`

---

## ⚠️ Notes

- Rule sets are generated from allocation-based data, not real-time traffic analysis
- IP rules reflect RIR assignment (APNIC + BGP), not precise geolocation
- Domain rules are curated for proxy routing accuracy, not exhaustive coverage
- HK / TW / MO / JP / KR / SG are intentionally separated from CN

---

## ❤️ Support

If RuleNova is useful to you, consider giving it a ⭐ on GitHub.

---

## 📄 License

[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) — Attribution-NonCommercial-ShareAlike.

- **Non-commercial use**: Permitted under the terms of CC BY-NC-SA 4.0.
- **Commercial use**: Commercial use, SaaS deployment, API resale, redistribution, or integration into paid products or services requires explicit prior written authorization from the author. See [COMMERCIAL_LICENSE.md](./COMMERCIAL_LICENSE.md) or contact via [GitHub Issues](https://github.com/harryheros/rulenova/issues).

---

Part of the [Nova infrastructure toolkit](https://github.com/harryheros).
