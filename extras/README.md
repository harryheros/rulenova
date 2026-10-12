# RuleNova extras

Client-specific tools that complement the rule sets in [`output/`](../output).

Each client has its own folder, using the same names as `output/`. A tool lives in the folder of the client whose scripting interface it is written for — scripts are not portable between clients, so a tool for another client is a separate script in that client's folder.

## Quantumult X — [`quantumult-x/`](quantumult-x)

| Tool | File | Purpose |
|------|------|---------|
| GeoCheck | [`geocheck.js`](quantumult-x/geocheck.js) | Node location check (`geo_location_checker`): exit country, city, ISP and ASN, and a clear "Node OK" when the geo service is rate-limited |
| RuleNova Parser | [`parser.js`](quantumult-x/parser.js) | Resource parser (`resource_parser_url`): converts rule lists and Surge modules into Quantumult X format |

Setup and options: see the [main README](../README.md#quantumult-x-node-location-check-geocheck).

## Conventions

- Plain ES5, a single top-level `$done()`, and a unique global name prefix per script — the most compatible structure across client versions.
- No `eval`, no tracking, no network requests beyond what the tool is for.
- Every tool has an automated test in `sources/scripts/` that runs in CI.
- URLs are case-sensitive: file names are lowercase.
- Scripts are served through jsDelivr: `https://cdn.jsdelivr.net/gh/harryheros/rulenova@main/extras/<client>/<file>`
