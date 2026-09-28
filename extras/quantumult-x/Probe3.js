// RuleNova Probe3 - runs GeoCheck's full logic, captures its result, and
// reports it in the plain format that Probe.js proved Quantumult X displays.
var __trace = [];
var __out = null;
function __capture(o) { __out = o; __trace.push("captured"); }
function __ascii(s) { return String(s || "").replace(/[^\x20-\x7e]/g, "?"); }
__trace.push("start");
__trace.push("console:" + (typeof console !== "undefined" && console && typeof console.log));
try {
/*
 * RuleNova GeoCheck - Quantumult X geo_location_checker script
 * https://github.com/harryheros/rulenova
 *
 * Usage ([general] section of Quantumult X):
 *   geo_location_checker=http://ip-api.com/json/?lang=en, https://cdn.jsdelivr.net/gh/harryheros/rulenova@main/extras/quantumult-x/GeoCheck.js
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
 *   http://ip-api.com/json/    recommended - best city coverage, 45 requests/min per IP
 *   https://api.ip.sb/geoip    HTTPS, 100 requests/min per IP, often no city data
 *   https://ipwho.is/          1,000 requests/day per IP
 *
 * Compatibility: written in plain ES5 (var, function, string concatenation).
 * Quantumult X's script engine rejects parts of modern syntax; a script it
 * cannot parse never runs at all, which shows up as a blank result.
 * test_geocheck.js enforces ES5 syntax.
 *
 * License: same as the RuleNova repository.
 */

(function () {
  var VERSION = "1.4.0";

  var TEXT = {
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
    unknown: "Unknown"
  };

  // Diagnostics go to the Quantumult X log.
  function log(msg) {
    try {
      if (typeof console !== "undefined" && console.log) {
        console.log("[GeoCheck " + VERSION + "] " + msg);
      }
    } catch (e) {}
  }

  function str(v) {
    return v === undefined || v === null ? "" : String(v).replace(/^\s+|\s+$/g, "");
  }

  function lower(v) {
    return str(v).toLowerCase();
  }

  function contains(haystack, needle) {
    return haystack.indexOf(needle) !== -1;
  }

  // Country code -> flag emoji, built from UTF-16 surrogate pairs
  // (regional indicator symbols U+1F1E6.. = 0xD83C 0xDDE6..).
  function flag(cc) {
    var c = str(cc).toUpperCase();
    if (!/^[A-Z]{2}$/.test(c)) return "\uD83C\uDFF3\uFE0F"; // white flag
    return (
      String.fromCharCode(0xd83c, 0xdde6 + c.charCodeAt(0) - 65) +
      String.fromCharCode(0xd83c, 0xdde6 + c.charCodeAt(1) - 65)
    );
  }

  function asnText(asn) {
    var a = str(asn);
    return a ? "AS" + a.replace(/^AS/i, "") : "";
  }

  // Normalize supported API responses into one common structure.
  // Returns null when the response does not represent a successful lookup.
  function normalize(d) {
    if (!d || typeof d !== "object") return null;

    // ip-api.com
    // { status, query, country, countryCode, regionName, city, isp, org, as, timezone }
    if ("status" in d && "query" in d) {
      if (d.status !== "success") return null;
      var m = str(d.as).match(/^AS(\d+)\s*(.*)$/);
      return {
        ip: d.query,
        cc: d.countryCode,
        country: d.country,
        region: d.regionName,
        city: d.city,
        isp: d.isp,
        org: d.org || (m ? m[2] : ""),
        asn: m ? m[1] : "",
        tz: d.timezone,
        source: "ip-api.com"
      };
    }

    // ipwho.is
    // { success, ip, country, country_code, region, city, timezone: { id },
    //   connection: { asn, org, isp } }
    if ("success" in d) {
      if (d.success !== true) return null;
      var c = d.connection || {};
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
        source: "ipwho.is"
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
        source: "ip.sb"
      };
    }

    return null;
  }

  // Classify unsuccessful API responses.
  //   limited:  rate limit / quota exceeded (HTTP 429/403 or a message saying so)
  //   refused:  API answered but returned no usable location (e.g. reserved range)
  function failureKind(status, d) {
    if (status === 429 || status === 403) return "limited";
    if (d && typeof d === "object" && (d.status === "fail" || d.success === false)) {
      return /\b(rate|limit|limited|quota|too many|exceeded?)\b/i.test(str(d.message))
        ? "limited"
        : "refused";
    }
    return null;
  }

  // One plain provider name ("HKT Limited" + "HKT" -> "HKT Limited");
  // the organisation, if different, is listed in the details.
  function provider(g) {
    var isp = str(g.isp);
    var org = str(g.org);
    if (isp && org) {
      var a = isp.toLowerCase();
      var b = org.toLowerCase();
      if (contains(a, b) || contains(b, a)) {
        return isp.length >= org.length ? isp : org;
      }
      return isp;
    }
    return isp || org || asnText(g.asn);
  }

  function httpLine(status) {
    return status ? "HTTP " + status : "";
  }

  function lines(arr) {
    var out = [];
    for (var i = 0; i < arr.length; i++) {
      if (arr[i]) out.push(arr[i]);
    }
    return out.join("\n");
  }

  function main(status, body) {
    var data = null;
    try {
      data = JSON.parse(body || "");
    } catch (e) {
      data = null;
    }

    // 1. Successful HTTP response + recognized geo data.
    var g = status >= 200 && status < 300 ? normalize(data) : null;

    if (g) {
      var country = str(g.country) || str(g.cc) || TEXT.unknown;
      var place = str(g.city) || str(g.region) || country;
      var org = str(g.org);

      // Title: flag + city. Subtitle: one plain name (composite subtitles
      // are avoided for Quantumult X).
      __capture({
        title: flag(g.cc) + " " + place,
        subtitle: provider(g) || TEXT.unknown,
        ip: str(g.ip),
        description: lines([
          "Status: " + TEXT.ok,
          "IP: " + (str(g.ip) || TEXT.unknown),
          "Country: " + country,
          str(g.region) ? "Region: " + str(g.region) : "",
          str(g.city) ? "City: " + str(g.city) : "",
          "ISP: " + (str(g.isp) || TEXT.unknown),
          org && lower(org) !== lower(g.isp) ? "Org: " + org : "",
          g.asn ? "ASN: " + asnText(g.asn) : "",
          str(g.tz) ? "Time zone: " + str(g.tz) : "",
          "API: " + g.source,
          "GeoCheck " + VERSION
        ])
      });
      return;
    }

    // 2. The API responded, but reported a known failure.
    var kind = failureKind(status, data);
    if (kind) {
      __capture({
        title: "\u2705 " + TEXT.ok,
        subtitle: kind === "limited" ? TEXT.limited : TEXT.refused,
        ip: (data && str(data.query || data.ip)) || "",
        description: lines([
          kind === "limited" ? TEXT.limitedHint : TEXT.refusedHint,
          httpLine(status),
          "GeoCheck " + VERSION
        ])
      });
      return;
    }

    // 3. The API responded, but the response was not recognized
    //    (e.g. an HTML error page). Still proof the request got through.
    __capture({
      title: "\u2705 " + TEXT.ok,
      subtitle: TEXT.badData,
      ip: "",
      description: lines([TEXT.badDataHint, httpLine(status), "GeoCheck " + VERSION])
    });
  }

  // Entry point. "Node OK" is only ever reported when an HTTP response
  // actually arrived (status > 0); without one, the node may really be down.
  var hasResponse = typeof $response !== "undefined" && $response;
  var STATUS = Number((hasResponse && $response.statusCode) || 0);
  var BODY = hasResponse && $response.body ? String($response.body) : "";

  log("status=" + STATUS + " body=" + (BODY ? BODY.slice(0, 160) : "(none)"));

  if (!STATUS) {
    __capture({
      title: "\u274C " + TEXT.noResponse,
      subtitle: TEXT.noResponse,
      ip: "",
      description: TEXT.noResponseHint + "\nGeoCheck " + VERSION
    });
    return;
  }

  try {
    main(STATUS, BODY);
  } catch (e) {
    log("error: " + (e && e.stack ? e.stack : e));
    __capture({
      title: "\u2705 " + TEXT.ok,
      subtitle: TEXT.badData,
      ip: "",
      description: lines([TEXT.badDataHint, httpLine(STATUS), String(e), "GeoCheck " + VERSION])
    });
  }
})();

  __trace.push("logic-finished");
} catch (__e) {
  __trace.push("ERROR:" + __e);
}
$done({
  title: "P3 " + (__out ? __ascii(__out.title) : "no-output"),
  subtitle: "P3 " + (__out ? __ascii(__out.subtitle) : "no-output"),
  ip: __out && __out.ip ? String(__out.ip) : "",
  description: "PROBE 3\ntrace: " + __trace.join(" > ") +
    "\nwould-title: " + (__out ? __ascii(__out.title) : "-") +
    "\nwould-subtitle: " + (__out ? __ascii(__out.subtitle) : "-") +
    "\nwould-description:\n" + (__out ? __ascii(__out.description) : "-")
});
