/*
 * RuleNova GeoCheck — Quantumult X geo_location_checker script
 * https://github.com/harryheros/rulenova
 *
 * Usage ([general] section of Quantumult X):
 *   geo_location_checker=https://api.ip.sb/geoip, https://cdn.jsdelivr.net/gh/harryheros/rulenova@main/extras/quantumult-x/GeoCheck.js
 *
 * Why it is different:
 *   The lookup is sent THROUGH each node, from the node's exit IP.
 *   Shared exit IPs can cause free geo APIs to rate-limit requests,
 *   which may otherwise look exactly like a dead node.
 *
 *   GeoCheck therefore distinguishes between:
 *     - location data       when the lookup succeeds
 *     - API rate limiting   when the API answered but refused/limited
 *     - missing location    when the API answered without location data
 *     - invalid response    when the API returned an unsupported format
 *     - no response         when nothing came back at all
 *
 *   Any HTTP response from the geo service proves that the request
 *   reached the service through the current network path. Only then
 *   is the node reported as OK.
 *
 * Supported API responses (switch the URL, keep this script):
 *   https://api.ip.sb/geoip    recommended — HTTPS, 100 requests/min per IP
 *   http://ip-api.com/json/    HTTP only, 45 requests/min per IP
 *   https://ipwho.is/          1,000 requests/day per IP
 *
 * License: same as the RuleNova repository.
 */

const TEXT = {
  ok: "Node OK",
  limited: "Geo service rate-limited",
  limitedHint:
    "Node is reachable. The request passed through this node, but the geo service rate-limited the lookup. This is common with shared exit IPs and should recover automatically.",
  refused: "No location data",
  refusedHint:
    "Node is reachable. The request passed through this node, but the geo service returned no location data for this IP.",
  badData: "Invalid geo data",
  badDataHint:
    "Node is reachable. The geo service responded, but the response format could not be recognized.",
  noResponse: "No response",
  noResponseHint:
    "No HTTP response was received from the geo service through this node. The node may be down, or the geo service may be unreachable from it.",
  unknown: "Unknown",
};

function flag(cc) {
  if (!cc || !/^[A-Za-z]{2}$/.test(cc)) return "🏳️";
  const up = cc.toUpperCase();
  return String.fromCodePoint(
    ...[...up].map((c) => 0x1f1e6 + c.charCodeAt(0) - 65)
  );
}

// Join non-empty parts with spaces, dropping case-insensitive duplicates.
function clean(...parts) {
  const seen = new Set();
  return parts
    .map((p) => (p === undefined || p === null ? "" : String(p).trim()))
    .filter((p) => {
      const key = p.toLowerCase();
      if (!p || seen.has(key)) return false;
      seen.add(key);
      return true;
    })
    .join(" ");
}

function asnText(asn) {
  return asn ? `AS${String(asn).replace(/^AS/i, "")}` : "";
}

/*
 * Normalize supported API responses into one common structure.
 * Returns null when the response does not represent a successful lookup.
 */
function normalize(d) {
  if (!d || typeof d !== "object") return null;

  // ip-api.com
  // { status, query, country, countryCode, regionName, city, isp, org, as, timezone }
  if ("status" in d && "query" in d) {
    if (d.status !== "success") return null;
    const asn = String(d.as || "").match(/^AS(\d+)\s*(.*)$/);
    return {
      ip: d.query,
      cc: d.countryCode,
      country: d.country,
      region: d.regionName,
      city: d.city,
      isp: d.isp,
      org: d.org || (asn && asn[2]),
      asn: asn ? asn[1] : "",
      tz: d.timezone,
      source: "ip-api.com",
    };
  }

  // ipwho.is
  // { success, ip, country, country_code, region, city, timezone: { id },
  //   connection: { asn, org, isp } }
  if ("success" in d) {
    if (d.success !== true) return null;
    const c = d.connection || {};
    return {
      ip: d.ip,
      cc: d.country_code,
      country: d.country,
      region: d.region,
      city: d.city,
      isp: c.isp,
      org: c.org,
      asn: c.asn,
      tz: d.timezone && d.timezone.id,
      source: "ipwho.is",
    };
  }

  // api.ip.sb/geoip
  // { ip, country, country_code, region, city, isp, organization, asn,
  //   asn_organization, timezone }
  if ("ip" in d && ("country_code" in d || "asn" in d)) {
    return {
      ip: d.ip,
      cc: d.country_code,
      country: d.country,
      region: d.region,
      city: d.city,
      isp: d.isp,
      org: d.organization || d.asn_organization,
      asn: d.asn,
      tz: d.timezone,
      source: "ip.sb",
    };
  }

  return null;
}

/*
 * Classify unsuccessful API responses.
 *
 * limited:  rate limit / quota exceeded (HTTP 429/403 or a message saying so)
 * refused:  API answered but returned no usable location (e.g. reserved range)
 */
function failureKind(status, d) {
  if (status === 429 || status === 403) return "limited";

  if (d && typeof d === "object" && (d.status === "fail" || d.success === false)) {
    const message = String(d.message || "");
    return /\b(rate|limit|limited|quota|too many|exceeded?)\b/i.test(message)
      ? "limited"
      : "refused";
  }

  return null;
}

// "HKT Limited" + "HKT" -> "HKT Limited"; fall back to the ASN.
function provider(g) {
  const isp = (g.isp || "").trim();
  const org = (g.org || "").trim();

  if (isp && org) {
    const a = isp.toLowerCase();
    const b = org.toLowerCase();
    if (a.includes(b) || b.includes(a)) {
      return isp.length >= org.length ? isp : org;
    }
    return `${isp} / ${org}`;
  }

  return isp || org || asnText(g.asn);
}

function httpLine(status) {
  return status ? `HTTP ${status}` : "";
}

function main(status, body) {
  let data = null;
  try {
    data = JSON.parse(body || "");
  } catch (e) {
    data = null;
  }

  // 1. Successful HTTP response + recognized geo data.
  const g = status >= 200 && status < 300 ? normalize(data) : null;

  if (g) {
    const country = g.country || g.cc || TEXT.unknown;
    const who = provider(g) || TEXT.unknown;

    // The title is the most visible line in the node list, so it shows the
    // most distinguishing information: the city (or region). Several nodes
    // in one country (Los Angeles / San Jose / Seattle) would otherwise all
    // read "United States". City-states (Hong Kong, Singapore, Macau) where
    // the city equals the country show the country once.
    const place = String(g.city || g.region || "").trim();
    const sameAsCountry =
      !place || place.toLowerCase() === String(country).toLowerCase();

    $done({
      title: `${flag(g.cc)} ${sameAsCountry ? country : place}`,
      subtitle: sameAsCountry ? who : `${country} · ${who}`,
      ip: g.ip || "",
      description: [
        `${TEXT.ok} ✅`,
        `IP: ${g.ip || TEXT.unknown}`,
        clean(g.country, g.region, g.city) || TEXT.unknown,
        `ISP: ${g.isp || TEXT.unknown}`,
        g.asn ? `ASN: ${asnText(g.asn)} ${g.org || ""}`.trim() : "",
        g.tz ? `Time zone: ${g.tz}` : "",
        `API: ${g.source}`,
      ]
        .filter(Boolean)
        .join("\n"),
    });
    return;
  }

  // 2. The API responded, but reported a known failure.
  const kind = failureKind(status, data);
  if (kind) {
    $done({
      title: `✅ ${TEXT.ok}`,
      subtitle: kind === "limited" ? TEXT.limited : TEXT.refused,
      ip: (data && (data.query || data.ip)) || "",
      description: [
        kind === "limited" ? TEXT.limitedHint : TEXT.refusedHint,
        httpLine(status),
      ]
        .filter(Boolean)
        .join("\n"),
    });
    return;
  }

  // 3. The API responded, but the response was not recognized
  //    (e.g. an HTML error page). Still proof the request got through.
  $done({
    title: `✅ ${TEXT.ok}`,
    subtitle: TEXT.badData,
    ip: "",
    description: [TEXT.badDataHint, httpLine(status)].filter(Boolean).join("\n"),
  });
}

function noResponse() {
  $done({
    title: `❌ ${TEXT.noResponse}`,
    subtitle: TEXT.noResponse,
    ip: "",
    description: TEXT.noResponseHint,
  });
}

// Entry point. "Node OK" is only ever reported when an HTTP response
// actually arrived (status > 0); without one, the node may really be down.
const STATUS = Number((typeof $response !== "undefined" && $response && $response.statusCode) || 0);

if (!STATUS) {
  noResponse();
} else {
  try {
    main(STATUS, $response.body);
  } catch (e) {
    $done({
      title: `✅ ${TEXT.ok}`,
      subtitle: TEXT.badData,
      ip: "",
      description: [TEXT.badDataHint, httpLine(STATUS), String(e)]
        .filter(Boolean)
        .join("\n"),
    });
  }
}
