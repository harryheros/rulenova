# RuleNova

[![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc-sa/4.0/)
[![Update Rules](https://img.shields.io/github/actions/workflow/status/harryheros/rulenova/update.yml?label=weekly%20update)](https://github.com/harryheros/rulenova/actions/workflows/update.yml)

Automated proxy rule sets for CN/HK/TW/MO/JP/KR/SG, generated weekly from
[IPNova](https://github.com/harryheros/ipnova) (IP CIDRs) and
[DomainNova](https://github.com/harryheros/domainnova) (domains).

---

## Formats

| Format | Files |
|---|---|
| Clash / Mihomo | `output/clash-mihomo/{direct,proxy}/{region}_{intent}.list` + `.yaml` |
| Surge | `output/surge/{direct,proxy}/{region}_{intent}.list` |
| Shadowrocket | `output/shadowrocket/{direct,proxy}/{region}_{intent}.conf` |
| Quantumult X | `output/quantumult-x/{direct,proxy}/{region}_{intent}.conf` |
| sing-box | `output/sing-box/{direct,proxy}/{region}_{intent}.json` |

## Intents

- **direct** — matched traffic → `DIRECT`, everything else → proxy.
  Typical use: mainland users routing CN traffic locally.
- **proxy** — matched traffic → regional proxy group, everything else → default.
  Typical use: multi-region users routing HK/JP/SG to corresponding landing nodes.

## Regions

`CN` `HK` `TW` `MO` `JP` `KR` `SG`

## Raw URLs

```
# Clash (list)
https://raw.githubusercontent.com/harryheros/rulenova/main/output/clash-mihomo/direct/cn_direct.list

# Clash (yaml rule-provider)
https://raw.githubusercontent.com/harryheros/rulenova/main/output/clash-mihomo/direct/cn_direct.yaml

# Surge
https://raw.githubusercontent.com/harryheros/rulenova/main/output/surge/direct/cn_direct.list

# Shadowrocket
https://raw.githubusercontent.com/harryheros/rulenova/main/output/shadowrocket/direct/cn_direct.conf

# Quantumult X
https://raw.githubusercontent.com/harryheros/rulenova/main/output/quantumult-x/direct/cn_direct.conf

# sing-box
https://raw.githubusercontent.com/harryheros/rulenova/main/output/sing-box/direct/cn_direct.json
```

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
