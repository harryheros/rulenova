/*
 * RuleNova GeoCheck 1.0.0 - Quantumult X geo_location_checker script
 * https://github.com/harryheros/rulenova
 *
 * Usage ([general] section of Quantumult X):
 *   geo_location_checker=http://ip-api.com/json/?lang=en, https://cdn.jsdelivr.net/gh/harryheros/rulenova@main/extras/quantumult-x/GeoCheck.js
 *
 * What it shows:
 *   - location data       flag + city, ISP (details: IP, country, region, ASN, time zone)
 *   - API rate limiting   "Node OK" - the request got through, the API refused it
 *   - missing location    "Node OK" - the API answered without location data
 *   - invalid response    "Node OK" - the API answered in an unknown format
 *   - no response         nothing came back through the node
 *
 *   The lookup is sent THROUGH each node, from the node's exit IP. Shared
 *   exit IPs often hit free geo API limits; other scripts then show nothing,
 *   which looks exactly like a dead node. Any HTTP response proves the node
 *   forwarded the request, so GeoCheck reports it as OK.
 *
 * Supported API responses (switch the URL, keep this script):
 *   http://ip-api.com/json/?lang=en   recommended - best city coverage, 45 req/min per IP
 *   https://api.ip.sb/geoip           HTTPS, 100 req/min per IP, often no city data
 *   https://ipwho.is/                 1,000 req/day per IP
 *
 * Structure rules (verified on Quantumult X; enforced by test_geocheck.js):
 *   1. $done() is called exactly once, at the top level, at the very end.
 *      The logic only builds a result object. Calling $done() from inside
 *      a function (or an IIFE) left the result blank in Quantumult X.
 *   2. Plain ES5 only (var, function, string concatenation).
 *   3. Every global name starts with __gc_ to avoid clashing with the host.
 *
 * License: same as the RuleNova repository.
 */

var __gc_VERSION = "1.0.0";

var __gc_TEXT = {
  ok: "Node OK",
  limited: "Geo service rate-limited",
  limitedHint: "Node is reachable. The request passed through this node, but the geo service rate-limited the lookup. This is common with shared exit IPs and recovers automatically.",
  refused: "No location data",
  refusedHint: "Node is reachable. The request passed through this node, but the geo service returned no location data for this IP.",
  badData: "Invalid geo data",
  badDataHint: "Node is reachable. The geo service responded, but the response format was not recognized.",
  noResponse: "No response",
  noResponseHint: "No HTTP response came back from the geo service through this node. The node may be down, or the geo service unreachable from it.",
  unknown: "Unknown"
};

var __gc_out = null;
var __gc_hasResponse = typeof $response !== "undefined" && $response;
var __gc_status = Number((__gc_hasResponse && $response.statusCode) || 0);
var __gc_body = __gc_hasResponse && $response.body ? String($response.body) : "";

// ---------------------------------------------------------------- helpers

function __gc_str(v) {
  return v === undefined || v === null ? "" : String(v).replace(/^\s+|\s+$/g, "");
}

function __gc_lower(v) {
  return __gc_str(v).toLowerCase();
}

// Country code -> flag emoji (regional indicators as UTF-16 surrogate pairs).
function __gc_flag(cc) {
  var c = __gc_str(cc).toUpperCase();
  if (!/^[A-Z]{2}$/.test(c)) return "\uD83C\uDFF3\uFE0F"; // white flag
  return String.fromCharCode(0xd83c, 0xdde6 + c.charCodeAt(0) - 65) +
    String.fromCharCode(0xd83c, 0xdde6 + c.charCodeAt(1) - 65);
}

function __gc_asn(asn) {
  var a = __gc_str(asn);
  return a ? "AS" + a.replace(/^AS/i, "") : "";
}

// One plain provider name ("HKT Limited" + "HKT" -> "HKT Limited").
function __gc_provider(g) {
  var isp = __gc_str(g.isp);
  var org = __gc_str(g.org);
  if (isp && org) {
    var a = isp.toLowerCase();
    var b = org.toLowerCase();
    if (a.indexOf(b) !== -1 || b.indexOf(a) !== -1) {
      return isp.length >= org.length ? isp : org;
    }
    return isp;
  }
  return isp || org || __gc_asn(g.asn);
}

// Normalize the supported API formats into one structure, or null if the
// response is not a successful lookup.
function __gc_normalize(d) {
  if (!d || typeof d !== "object") return null;

  // ip-api.com: { status, query, country, countryCode, regionName, city, isp, org, as, timezone }
  if ("status" in d && "query" in d) {
    if (d.status !== "success") return null;
    var m = __gc_str(d.as).match(/^AS(\d+)\s*(.*)$/);
    return {
      ip: d.query, cc: d.countryCode, country: d.country,
      region: d.regionName, city: d.city,
      isp: d.isp, org: d.org || (m ? m[2] : ""), asn: m ? m[1] : "",
      tz: d.timezone, source: "ip-api.com"
    };
  }

  // ipwho.is: { success, ip, country, country_code, region, city, timezone: { id }, connection: { asn, org, isp } }
  if ("success" in d) {
    if (d.success !== true) return null;
    var c = d.connection || {};
    return {
      ip: d.ip, cc: d.country_code, country: d.country,
      region: d.region, city: d.city,
      isp: c.isp, org: c.org, asn: c.asn,
      tz: d.timezone && d.timezone.id, source: "ipwho.is"
    };
  }

  // api.ip.sb/geoip: { ip, country, country_code, region, city, isp, organization, asn, asn_organization, timezone }
  if ("ip" in d && ("country_code" in d || "asn" in d)) {
    return {
      ip: d.ip, cc: d.country_code, country: d.country,
      region: d.region, city: d.city,
      isp: d.isp, org: d.organization || d.asn_organization, asn: d.asn,
      tz: d.timezone, source: "ip.sb"
    };
  }

  return null;
}

// "limited": HTTP 429/403 or a message about limits / quota.
// "refused": the API answered but has no location (e.g. reserved range).
function __gc_failureKind(status, d) {
  if (status === 429 || status === 403) return "limited";
  if (d && typeof d === "object" && (d.status === "fail" || d.success === false)) {
    return /\b(rate|limit|limited|quota|too many|exceeded?)\b/i.test(__gc_str(d.message)) ? "limited" : "refused";
  }
  return null;
}

// Join the non-empty entries of a list with newlines.
function __gc_lines(list) {
  var out = [];
  for (var i = 0; i < list.length; i++) {
    if (list[i]) out.push(list[i]);
  }
  return out.join("\n");
}

function __gc_statusLine() {
  return __gc_status ? "HTTP " + __gc_status : "";
}

// ---------------------------------------------------------------- build the result

try {
  if (!__gc_status) {
    __gc_out = {
      title: "\u274C " + __gc_TEXT.noResponse,
      subtitle: __gc_TEXT.noResponse,
      ip: "",
      description: __gc_lines([__gc_TEXT.noResponseHint, "GeoCheck " + __gc_VERSION])
    };
  } else {
    var __gc_data = null;
    try {
      __gc_data = JSON.parse(__gc_body || "");
    } catch (e) {
      __gc_data = null;
    }

    var __gc_g = __gc_status >= 200 && __gc_status < 300 ? __gc_normalize(__gc_data) : null;
    var __gc_kind = __gc_g ? null : __gc_failureKind(__gc_status, __gc_data);

    if (__gc_g) {
      var __gc_country = __gc_str(__gc_g.country) || __gc_str(__gc_g.cc) || __gc_TEXT.unknown;
      var __gc_place = __gc_str(__gc_g.city) || __gc_str(__gc_g.region) || __gc_country;
      var __gc_org = __gc_str(__gc_g.org);

      __gc_out = {
        title: __gc_flag(__gc_g.cc) + " " + __gc_place,
        subtitle: __gc_provider(__gc_g) || __gc_TEXT.unknown,
        ip: __gc_str(__gc_g.ip),
        description: __gc_lines([
          "Status: " + __gc_TEXT.ok,
          "IP: " + (__gc_str(__gc_g.ip) || __gc_TEXT.unknown),
          "Country: " + __gc_country,
          __gc_str(__gc_g.region) ? "Region: " + __gc_str(__gc_g.region) : "",
          __gc_str(__gc_g.city) ? "City: " + __gc_str(__gc_g.city) : "",
          "ISP: " + (__gc_str(__gc_g.isp) || __gc_TEXT.unknown),
          __gc_org && __gc_lower(__gc_org) !== __gc_lower(__gc_g.isp) ? "Org: " + __gc_org : "",
          __gc_g.asn ? "ASN: " + __gc_asn(__gc_g.asn) : "",
          __gc_str(__gc_g.tz) ? "Time zone: " + __gc_str(__gc_g.tz) : "",
          "API: " + __gc_g.source,
          "GeoCheck " + __gc_VERSION
        ])
      };
    } else if (__gc_kind) {
      __gc_out = {
        title: "\u2705 " + __gc_TEXT.ok,
        subtitle: __gc_kind === "limited" ? __gc_TEXT.limited : __gc_TEXT.refused,
        ip: (__gc_data && __gc_str(__gc_data.query || __gc_data.ip)) || "",
        description: __gc_lines([
          __gc_kind === "limited" ? __gc_TEXT.limitedHint : __gc_TEXT.refusedHint,
          __gc_statusLine(),
          "GeoCheck " + __gc_VERSION
        ])
      };
    } else {
      __gc_out = {
        title: "\u2705 " + __gc_TEXT.ok,
        subtitle: __gc_TEXT.badData,
        ip: "",
        description: __gc_lines([__gc_TEXT.badDataHint, __gc_statusLine(), "GeoCheck " + __gc_VERSION])
      };
    }
  }
} catch (__gc_err) {
  __gc_out = {
    title: "\u26A0\uFE0F Script error",
    subtitle: String(__gc_err && __gc_err.message ? __gc_err.message : __gc_err),
    ip: "",
    description: __gc_lines([
      String(__gc_err && __gc_err.stack ? __gc_err.stack : __gc_err),
      __gc_statusLine(),
      "GeoCheck " + __gc_VERSION
    ])
  };
}

// ---------------------------------------------------------------- the one and only $done

if (typeof $done !== "undefined") {
  $done({
    title: String((__gc_out && __gc_out.title) || __gc_TEXT.unknown),
    subtitle: String((__gc_out && __gc_out.subtitle) || ""),
    ip: String((__gc_out && __gc_out.ip) || ""),
    description: String((__gc_out && __gc_out.description) || "")
  });
}
