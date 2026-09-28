# RuleNova

[![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc-sa/4.0/)
[![Update Rules](https://img.shields.io/github/actions/workflow/status/harryheros/rulenova/update.yml?label=weekly%20update)](https://github.com/harryheros/rulenova/actions/workflows/update.yml)

RuleNova is a lightweight routing-rule generation project that transforms infrastructure attribution datasets into client-specific routing rule formats.

RuleNova generates outputs for Clash / Mihomo, Stash, Surge, Shadowrocket, Quantumult X, Loon and sing-box using public dataset outputs from [IPNova](https://github.com/harryheros/ipnova) and [DomainNova](https://github.com/harryheros/domainnova).

The core design is simple:

```txt
rules decide what to match
policy groups decide how to route
```

RuleNova does **not** hard-code `DIRECT` or `PROXY`. For clients that require a policy column, RuleNova uses short abstract policy names such as `China` and `Global`. Users only need to map those policy groups to `DIRECT`, `PROXY`, `Auto`, or a specific node group.

---

## Output model

### Tier 1 — simple mode, recommended

| Rule set | Meaning | Policy name |
|---|---|---|
| `china` | CN domains + CN IP CIDRs | `China` |
| `global` | HK / TW / MO / JP / KR / SG merged | `Global` |

This is the recommended entry point for most users.

### Tier 2 — domain / IP split

Every main rule set also has split variants:

| Variant | Use case |
|---|---|
| `china-domain` / `global-domain` | Safer domain-only routing and DNS-oriented setups |
| `china-ip` / `global-ip` | CIDR routing, fallback, or advanced debugging |

If something is misrouted, disable the `*-ip` rule first and keep the `*-domain` rule enabled.

### Tier 3 — per-region, advanced

Individual region rule sets are under `regions/`:

```txt
cn hk tw mo jp kr sg
```

Each region also includes `*-domain` and `*-ip` variants.

Region policy names are intentionally short:

```txt
China HK TW MO JP KR SG
```

---

## Client behavior

| Client | Output behavior |
|---|---|
| Clash / Mihomo | Rule-provider friendly. No embedded policy. Bind policy in `rules:` via `RULE-SET`. |
| Stash | Same as Clash / Mihomo. |
| Surge | `RULE-SET` friendly. No embedded policy. Bind policy in the main config. |
| sing-box | Source rule-set JSON. No `outbound` / `action`; bind outbound in route rules. |
| Shadowrocket | Rules include short abstract policy names, e.g. `China`. |
| Quantumult X | Rules include short abstract policy names, e.g. `China`; create matching policy groups or use `force-policy`. |
| Loon | Rules include short abstract policy names, e.g. `China`. |

---

## Files

Examples:

```txt
output/clash-mihomo/china.list
output/clash-mihomo/china-domain.list
output/clash-mihomo/china-ip.list

output/stash/china.yaml
output/stash/china-domain.yaml
output/stash/china-ip.yaml

output/surge/china.list
output/surge/china-domain.list
output/surge/china-ip.list

output/sing-box/china.json
output/sing-box/china-domain.json
output/sing-box/china-ip.json

output/quantumult-x/china.conf
output/shadowrocket/china.conf
output/loon/china.list

output/*/regions/hk.*
output/*/regions/hk-domain.*
output/*/regions/hk-ip.*
```

---

## Raw URLs

```txt
# Clash / Mihomo
https://raw.githubusercontent.com/harryheros/rulenova/main/output/clash-mihomo/china.list
https://raw.githubusercontent.com/harryheros/rulenova/main/output/clash-mihomo/china-domain.list
https://raw.githubusercontent.com/harryheros/rulenova/main/output/clash-mihomo/china-ip.list
https://raw.githubusercontent.com/harryheros/rulenova/main/output/clash-mihomo/global.list

# Stash
https://raw.githubusercontent.com/harryheros/rulenova/main/output/stash/china.yaml
https://raw.githubusercontent.com/harryheros/rulenova/main/output/stash/china-domain.yaml
https://raw.githubusercontent.com/harryheros/rulenova/main/output/stash/china-ip.yaml

# Surge
https://raw.githubusercontent.com/harryheros/rulenova/main/output/surge/china.list
https://raw.githubusercontent.com/harryheros/rulenova/main/output/surge/global.list

# sing-box
https://raw.githubusercontent.com/harryheros/rulenova/main/output/sing-box/china.json
https://raw.githubusercontent.com/harryheros/rulenova/main/output/sing-box/global.json

# Shadowrocket
https://raw.githubusercontent.com/harryheros/rulenova/main/output/shadowrocket/china.conf
https://raw.githubusercontent.com/harryheros/rulenova/main/output/shadowrocket/global.conf

# Quantumult X
https://raw.githubusercontent.com/harryheros/rulenova/main/output/quantumult-x/china.conf
https://raw.githubusercontent.com/harryheros/rulenova/main/output/quantumult-x/global.conf

# Loon
https://raw.githubusercontent.com/harryheros/rulenova/main/output/loon/china.list
https://raw.githubusercontent.com/harryheros/rulenova/main/output/loon/global.list
```

---

## Policy mapping examples

China mainland users usually map:

```txt
China  -> DIRECT
Global -> PROXY / Auto
```

Overseas users may map:

```txt
China  -> PROXY / Auto / HK node
Global -> PROXY / Auto
```

The rule files do not need to change when the user travels. Only the policy group mapping changes.

---

## Client examples

### Clash / Mihomo

```yaml
rule-providers:
  rulenova-china:
    type: http
    behavior: classical
    format: text
    url: https://raw.githubusercontent.com/harryheros/rulenova/main/output/clash-mihomo/china.list
    path: ./ruleset/rulenova/china.list
    interval: 86400

rules:
  - RULE-SET,rulenova-china,China
```

For split mode:

```yaml
rule-providers:
  rulenova-china-domain:
    type: http
    behavior: domain
    format: text
    url: https://raw.githubusercontent.com/harryheros/rulenova/main/output/clash-mihomo/china-domain.list
    path: ./ruleset/rulenova/china-domain.list
    interval: 86400
  rulenova-china-ip:
    type: http
    behavior: ipcidr
    format: text
    url: https://raw.githubusercontent.com/harryheros/rulenova/main/output/clash-mihomo/china-ip.list
    path: ./ruleset/rulenova/china-ip.list
    interval: 86400

rules:
  - RULE-SET,rulenova-china-domain,China
  - RULE-SET,rulenova-china-ip,China,no-resolve
```

### Surge

```txt
RULE-SET,https://raw.githubusercontent.com/harryheros/rulenova/main/output/surge/china.list,China
RULE-SET,https://raw.githubusercontent.com/harryheros/rulenova/main/output/surge/global.list,Global
```

### Quantumult X

```txt
filter_remote=https://raw.githubusercontent.com/harryheros/rulenova/main/output/quantumult-x/china.conf, tag=RuleNova China, enabled=true
filter_remote=https://raw.githubusercontent.com/harryheros/rulenova/main/output/quantumult-x/global.conf, tag=RuleNova Global, enabled=true
```

Or override the embedded policy when needed:

```txt
filter_remote=https://raw.githubusercontent.com/harryheros/rulenova/main/output/quantumult-x/china.conf, tag=RuleNova China, force-policy=PROXY, enabled=true
```

### sing-box

```json
{
  "route": {
    "rule_set": [
      {
        "type": "remote",
        "tag": "rulenova-china",
        "format": "source",
        "url": "https://raw.githubusercontent.com/harryheros/rulenova/main/output/sing-box/china.json"
      }
    ],
    "rules": [
      {
        "rule_set": "rulenova-china",
        "outbound": "direct"
      }
    ]
  }
}
```

---

## Development

```bash
python3 sources/scripts/test_offline.py
python3 sources/scripts/build_rules.py --repo-root .
python3 sources/scripts/validate_output.py
```

`build_rules.py` deletes and regenerates `output/` by default to avoid stale action-based directories such as `direct/` or `proxy/`.

---

## Quantumult X: node location check (GeoCheck)

Shows each node's exit country, city, ISP and ASN in Quantumult X. Add to the `[general]` section:

```ini
geo_location_checker=https://api.ip.sb/geoip, https://cdn.jsdelivr.net/gh/harryheros/rulenova@main/extras/quantumult-x/GeoCheck.js
```

**Why another geo script?** The lookup is sent *through* each node, from the node's exit IP — which airport nodes share between many users. Free geo APIs limit requests per IP, so on popular nodes other scripts often show nothing, which looks exactly like a dead node. GeoCheck treats any answer from the API as proof the node works:

| API answer | GeoCheck shows |
|------------|----------------|
| Location data | Flag + city (e.g. 🇺🇸 Los Angeles) and ISP; details: IP, country, region, ASN, time zone |
| Rate limited (HTTP 429 / quota) | ✅ Node OK · Geo service rate-limited |
| No location for this IP | ✅ Node OK · No location data |
| Unreadable answer (e.g. an error page) | ✅ Node OK · Invalid geo data |
| No HTTP response at all | ❌ No response |

"Node OK" is only shown when an HTTP response actually came back through the node.

The script understands three APIs — switch the URL without changing the script:

| API URL | Free limit (per exit IP) | Notes |
|---------|--------------------------|-------|
| `https://api.ip.sb/geoip` | 100 requests / minute | **Recommended**: HTTPS, recovers within a minute |
| `http://ip-api.com/json/` | 45 requests / minute, 1 h block if exceeded | HTTP only |
| `https://ipwho.is/` | 1,000 requests / day, 24 h block if exceeded | Not recommended for shared nodes |

The script is served through jsDelivr, which is reachable in many networks where raw.githubusercontent.com is blocked or slow — important because Quantumult X fetches it before any proxy is up. The geo data comes from the respective API providers; their free tiers are for non-commercial use.

## Update schedule

Every Monday 06:00 UTC — 4 hours after IPNova and DomainNova complete their weekly update.

Before anything in `output/` is replaced, the new data is compared with the last published build. If any region lost more than 50% of its domains or CIDRs — typically a failed or truncated upstream download — the build is refused and the previous rules stay online. An intended large change can be published with `--allow-shrink` (or the `allow_shrink` input of a manual workflow run).

## Data sources

- Domains: [DomainNova](https://github.com/harryheros/domainnova) `dist/domains_{region}.txt`
- IP CIDRs: [IPNova](https://github.com/harryheros/ipnova) `output/plain/{region}.txt`

---

## Notes

- Rule sets are generated from allocation-based data, not real-time traffic analysis.
- IP rules reflect RIR assignment and BGP data, not precise service ownership.
- Domain rules are curated for geo-classification accuracy, not exhaustive coverage.
- HK / TW / MO / JP / KR / SG are intentionally separated from CN and merged into `global` for simple mode.

---

## Positioning

RuleNova is a downstream compatibility project within the Nova infrastructure toolkit.

IPNova and DomainNova are general-purpose infrastructure intelligence datasets. RuleNova demonstrates one possible routing-rule application built from those public datasets.

The upstream datasets remain independent of any specific routing client, policy model, or deployment environment.

---

## License

[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) — Attribution-NonCommercial-ShareAlike.

Commercial use, SaaS deployment, API resale, redistribution, or integration into paid products or services requires explicit prior written authorization from the author. See [COMMERCIAL_LICENSE.md](./COMMERCIAL_LICENSE.md).

---

Part of the [Nova infrastructure toolkit](https://github.com/harryheros).
