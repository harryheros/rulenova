# RuleNova

[![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc-sa/4.0/)
[![Update Rules](https://img.shields.io/github/actions/workflow/status/harryheros/rulenova/update.yml?label=weekly%20update)](https://github.com/harryheros/rulenova/actions/workflows/update.yml)

Automated proxy rule sets for CN/HK/TW/MO/JP/KR/SG, generated weekly from
[IPNova](https://github.com/harryheros/ipnova) (IP CIDRs) and
[DomainNova](https://github.com/harryheros/domainnova) (domains).

---

## Formats

| Format | Action | Files |
|---|---|---|
| Clash / Mihomo | user-defined | `output/clash-mihomo/{region}.list` + `.yaml` |
| Surge | user-defined | `output/surge/{region}.list` |
| sing-box | user-defined | `output/sing-box/{region}.json` |
| Shadowrocket | built-in | `output/shadowrocket/{direct,proxy}/{region}.conf` |
| Quantumult X | built-in | `output/quantumult-x/{direct,proxy}/{region}.conf` |

Clash, Surge and sing-box rule sets carry no action — you assign `DIRECT`, `PROXY`, or any policy group in your own config. Shadowrocket and Quantumult X require action in the rule syntax, so both `direct` and `proxy` variants are provided.

## Regions

`CN` `HK` `TW` `MO` `JP` `KR` `SG`

## Raw URLs

```
# Clash / Mihomo (list)
https://raw.githubusercontent.com/harryheros/rulenova/main/output/clash-mihomo/cn.list

# Clash / Mihomo (yaml rule-provider)
https://raw.githubusercontent.com/harryheros/rulenova/main/output/clash-mihomo/cn.yaml

# Surge
https://raw.githubusercontent.com/harryheros/rulenova/main/output/surge/cn.list

# sing-box
https://raw.githubusercontent.com/harryheros/rulenova/main/output/sing-box/cn.json

# Shadowrocket (direct)
https://raw.githubusercontent.com/harryheros/rulenova/main/output/shadowrocket/direct/cn.conf

# Shadowrocket (proxy)
https://raw.githubusercontent.com/harryheros/rulenova/main/output/shadowrocket/proxy/cn.conf

# Quantumult X (direct)
https://raw.githubusercontent.com/harryheros/rulenova/main/output/quantumult-x/direct/cn.conf

# Quantumult X (proxy)
https://raw.githubusercontent.com/harryheros/rulenova/main/output/quantumult-x/proxy/cn.conf
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
