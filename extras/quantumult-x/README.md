# Quantumult X tools

Two scripts for Quantumult X, served through jsDelivr. Both are optional; the rule sets work without them.

## GeoCheck — node location check

Shows each node's exit country, city, ISP and ASN in Quantumult X. Add to the `[general]` section:

```ini
geo_location_checker=http://ip-api.com/json/?lang=en, https://cdn.jsdelivr.net/gh/harryheros/rulenova@main/extras/quantumult-x/geocheck.js
```

**Why another geo script?** The lookup is sent *through* each node, from the node's exit IP — which is often shared by many users. Free geo APIs limit requests per IP, so on popular nodes other scripts often show nothing, which looks exactly like a dead node. GeoCheck treats any answer from the API as proof the node works:

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
| `http://ip-api.com/json/?lang=en` | 45 requests / minute, 1 h block if exceeded | **Recommended**: best city coverage; GeoCheck turns its rate limiting into "Node OK" instead of a blank result |
| `https://api.ip.sb/geoip` | 100 requests / minute | HTTPS, but often has no city data for proxy/datacenter IPs (the title then falls back to the country) |
| `https://ipwho.is/` | 1,000 requests / day, 24 h block if exceeded | Not recommended for shared nodes |

Tap a node's location to see the details, including the GeoCheck version on the last line — useful when reporting a problem.

**If results stay blank or look outdated:**

- The URL is case-sensitive: the file name is `geocheck.js` (all lowercase).
- Quantumult X keeps its own copy of remote scripts. After an update, restart Quantumult X and check the version in the details. A brand-new URL always forces a fresh download.

GeoCheck uses the conservative structure of long-established Quantumult X scripts: plain ES5, a single `$done()` call at the top level, and `__gc_`-prefixed global names. `sources/scripts/test_geocheck.js` checks this, the behaviour for every response type, and that every script URL in the READMEs matches a real file, in CI.

The script is served through jsDelivr, which is usually faster and more reliable than raw.githubusercontent.com — important because Quantumult X fetches it before any policy group is ready. The geo data comes from the respective API providers; their free tiers are for non-commercial use.

## RuleNova Parser — rule and module conversion

Converts rule lists and Surge modules into Quantumult X format. Add to the `[general]` section:

```ini
resource_parser_url=https://cdn.jsdelivr.net/gh/harryheros/rulenova@main/extras/quantumult-x/parser.js
```

Then add `opt-parser=true` to a remote filter or rewrite resource:

```ini
[filter_remote]
https://example.com/streaming.list, tag=Streaming, force-policy=Streaming, opt-parser=true, enabled=true

[rewrite_remote]
https://example.com/ad-block.sgmodule, tag=Ad Block, opt-parser=true, enabled=true
```

| Input | Output |
|-------|--------|
| Surge / Clash rule lists (`DOMAIN-SUFFIX,example.com`) | filter |
| Clash rule-provider YAML (`payload:` with domain, ipcidr or classical entries) | filter |
| Domain sets (`.example.com`, `+.example.com`), IP / CIDR lists | filter |
| Hosts files (`0.0.0.0 ads.example.com`) and simple `\|\|domain^` filter lists | filter, policy `reject` |
| Surge modules (`.sgmodule`): URL Rewrite, Map Local, Script, Body Rewrite, MITM, URL-REGEX reject rules | rewrite |
| Quantumult X filter or rewrite snippets | unchanged, options applied |

Options go after `#` in the resource URL, joined with `&`, for example `https://example.com/list.txt#policy=Streaming&exclude=ads`. Quantumult X 1.5.6 and later also show them as a form when you edit the resource.

| Option | Effect |
|--------|--------|
| `policy=NAME` | Policy for every rule. Default: the rule's own policy, otherwise `proxy`. `force-policy` on the resource overrides both. |
| `include=a+b` / `exclude=a+b` | Keep only / drop lines containing any keyword (case-insensitive). |
| `host-include=a+b` / `host-exclude=a+b` | Keep only / drop MITM hostnames containing any keyword. |
| `replace=REGEX@TEXT` | Regex replace on every output line; join several with `+`. |
| `output=filter` / `output=rewrite` | Force the output type, e.g. `output=filter` to use the `[Rule]` section of a module. |
| `notify=1` / `notify=0` | Always / never notify. Default: notify only when something was skipped. |

In option values, write a literal `+` as `%2B`, `@` as `%40`, `&` as `%26` and `#` as `%23`.

**Skipped, never guessed.** Rules and module features that Quantumult X cannot express are left out instead of being converted into something that behaves differently: for example `PROCESS-NAME`, logical rules (`AND` / `OR` / `NOT`), cron scripts, header rewrites and Map Local entries with custom data. The notification lists what was skipped. Scripts that use a module `argument` are converted, but the argument is not passed; the notification points this out.

**Node subscriptions are left alone.** The parser does not convert server subscriptions; it returns them unchanged, so Quantumult X parses them itself. Quantumult X allows only one `resource_parser_url` — if you rely on another parser to convert your node subscriptions, keep using that one.

The parser follows the same conservative structure as GeoCheck (plain ES5, a single top-level `$done()`, `__np_`-prefixed names). It uses no `eval`, makes no network requests and stores nothing. `sources/scripts/test_parser.js` checks the structure and every input format and option above in CI.
