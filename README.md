# RuleNova

[![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc-sa/4.0/)
![Version](https://img.shields.io/badge/version-2.3.0-blue)
[![Update Rules](https://img.shields.io/github/actions/workflow/status/harryheros/rulenova/update.yml?label=weekly%20update)](https://github.com/harryheros/rulenova/actions/workflows/update.yml)

Region-based routing rule sets for Clash / Mihomo, Stash, Surge, Shadowrocket, Quantumult X, Loon and sing-box: match traffic by the region a domain or IP address belongs to, and send each region to the exit you choose. Updated weekly.

```txt
rules decide what to match
policy groups decide how to route
```

RuleNova never hard-codes `DIRECT` or `PROXY`. Rules use short region policy names, such as `China`, `HK` or `JP`, which you map to any policy group.

---

## Rule sets

| Rule set | Contents | Policy |
|---|---|---|
| `regions/{cn,hk,tw,mo,jp,kr,sg}` | One region each, also with `-domain` / `-ip` variants | `China`, `HK`, `TW`, `MO`, `JP`, `KR`, `SG` |
| `china` | Combination: CN domains + CN IPv4 / IPv6 | `China` |
| `global` | Combination: HK / TW / MO / JP / KR / SG | `Global` |
| `china-domain`, `global-domain` | Domains only — safest choice, good for DNS-based setups | |
| `china-ip`, `global-ip` | IPv4 + IPv6 CIDRs only | |

The per-region sets are the building blocks; `china` and `global` are ready-made combinations of them. `global` covers only the six regions listed, not the whole world. Anything outside the covered regions falls through to your client's final rule (`MATCH` / `FINAL`).

If something is misrouted, disable the `*-ip` rule first and keep `*-domain`.

---

## Policy mapping

Map each policy to the exit that fits where you are:

```txt
Traffic for the region you are in:        DIRECT
Traffic for another covered region:       a node in or near that region (e.g. JP -> Japan node)
Everything else:                          your client's final rule
```

A common case is reaching services back home while abroad: map `China` to a node in or near China, and keep everything else as usual. The rule files stay the same when you travel; only the mapping changes.

**Rule order**: clients use the first rule that matches. A few subdomains belong to a different region than their parent (`asia.ccb.com` is HK, `ccb.com` is CN), so put **`global` before `china`**.

---

## URLs

```txt
https://raw.githubusercontent.com/harryheros/rulenova/main/output/<client>/<rule set>.<ext>
```

| Client | `<client>` | `<ext>` | Policy in file |
|---|---|---|---|
| Clash / Mihomo | `clash-mihomo` | `.list`, `.yaml` | No — bind with `RULE-SET` |
| Stash | `stash` | `.list`, `.yaml` | No |
| Surge | `surge` | `.list` | No — bind with `RULE-SET` |
| sing-box | `sing-box` | `.json` (source rule-set) | No — bind in route rules |
| Shadowrocket | `shadowrocket` | `.conf` | Yes |
| Quantumult X | `quantumult-x` | `.conf` | Yes — or override with `force-policy` |
| Loon | `loon` | `.list` | Yes |

Example: `https://raw.githubusercontent.com/harryheros/rulenova/main/output/surge/china.list`

---

## Examples

**Clash / Mihomo**

```yaml
rule-providers:
  rulenova-global:
    type: http
    behavior: classical
    format: text
    url: https://raw.githubusercontent.com/harryheros/rulenova/main/output/clash-mihomo/global.list
    path: ./ruleset/rulenova/global.list
    interval: 86400
  rulenova-china:
    type: http
    behavior: classical
    format: text
    url: https://raw.githubusercontent.com/harryheros/rulenova/main/output/clash-mihomo/china.list
    path: ./ruleset/rulenova/china.list
    interval: 86400

rules:
  - RULE-SET,rulenova-global,Global
  - RULE-SET,rulenova-china,China
```

For the split variants use `behavior: domain` (`*-domain.list`) and `behavior: ipcidr` (`*-ip.list`, add `no-resolve` to the rule).

**Surge**

```txt
RULE-SET,https://raw.githubusercontent.com/harryheros/rulenova/main/output/surge/global.list,Global
RULE-SET,https://raw.githubusercontent.com/harryheros/rulenova/main/output/surge/china.list,China
```

**Quantumult X**

```txt
filter_remote=https://raw.githubusercontent.com/harryheros/rulenova/main/output/quantumult-x/global.conf, tag=RuleNova Global, enabled=true
filter_remote=https://raw.githubusercontent.com/harryheros/rulenova/main/output/quantumult-x/china.conf, tag=RuleNova China, enabled=true
```

**sing-box**

```json
{
  "route": {
    "rule_set": [
      { "type": "remote", "tag": "rulenova-china", "format": "source",
        "url": "https://raw.githubusercontent.com/harryheros/rulenova/main/output/sing-box/china.json" }
    ],
    "rules": [ { "rule_set": "rulenova-china", "outbound": "China" } ]
  }
}
```

`China` here is the tag of an outbound you define, such as a `selector`, like the policy groups in the other clients.

---

## Extras

- **Icons**: 16 original policy-group icons in solid and transparent styles — [`icons/`](icons/README.md).
- **Quantumult X tools**: GeoCheck (node location check) and RuleNova Parser (rule and module conversion) — [`extras/`](extras/README.md).

<img src="icons/preview-solid.png" alt="RuleNova icons" width="440">

---

## Updates and data

- Every Monday 06:00 UTC, after IPNova and DomainNova finish their weekly update.
- If any region loses more than half of its domains or CIDRs, usually a failed upstream download, the build is refused and the previous rules stay online.
- Domain and IP data from [IPNova](https://github.com/harryheros/ipnova) and [DomainNova](https://github.com/harryheros/domainnova), based on public registry and routing data.
- Rules reflect registration and routing data, not real-time traffic or exact service ownership.

Development: `python3 sources/scripts/build_rules.py --repo-root .`, then `validate_output.py`; tests are in `sources/scripts/`.

---

## Changelog

See [CHANGELOG.md](./CHANGELOG.md).

---

## License

[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/): free for non-commercial use with attribution. For what counts as commercial use and how to get permission, see [COMMERCIAL_LICENSE.md](./COMMERCIAL_LICENSE.md).

Data powered by [IPNova](https://github.com/harryheros/ipnova) and [DomainNova](https://github.com/harryheros/domainnova).
