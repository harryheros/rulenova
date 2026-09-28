/*
 * RuleNova GeoCheck — Quantumult X geo_location_checker script
 * https://github.com/harryheros/rulenova
 *
 * Usage ([general] section of Quantumult X):
 *   geo_location_checker=http://ip-api.com/json/?lang=en, https://cdn.jsdelivr.net/gh/harryheros/rulenova@main/extras/quantumult-x/GeoCheck.js
 *
 * Supported API responses:
 *   http://ip-api.com/json/    recommended — best city coverage, 45 requests/min per IP
 *   https://api.ip.sb/geoip    HTTPS, 100 requests/min per IP
 *   https://ipwho.is/          1,000 requests/day per IP
 *
 * License: same as the RuleNova repository.
 */

(function () {
  "use strict";

  var VERSION = "1.5.0";

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

  /*
   * 安全生成國旗 Emoji：
   * 優先使用原生 String.fromCodePoint，若不支援或異常則降級為文字標籤 [SG]，
   * 避免原生 UI 橋接層因代理對解析失敗而觸發全空白崩潰。
   */
  function flag(cc) {
    var c = str(cc).toUpperCase();
    if (!/^[A-Z]{2}$/.test(c)) return "🏳️";
    try {
      if (typeof String.fromCodePoint === "function") {
        var code1 = 0x1f1e6 + c.charCodeAt(0) - 65;
        var code2 = 0x1f1e6 + c.charCodeAt(1) - 65;
        return String.fromCodePoint(code1, code2);
      }
    } catch (e) {}
    return "[" + c + "]";
  }

  function asnText(asn) {
    var a = str(asn);
    return a ? "AS" + a.replace(/^AS/i, "") : "";
  }

  /*
   * 歸一化 API 回應數據
   */
  function normalize(d) {
    if (!d || typeof d !== "object") return null;

    // ip-api.com
    if ("status" in d && "query" in d) {
      if (d.status !== "success") return null;
      var m = str(d.as).match(/^AS(\d+)\s*(.*)$/);
      return {
        ip: d.query,
        cc: d.countryCode,
        country: d.country,
        // 優先取 regionName，若為空（如部分城市國家）則降級使用 region 代碼
        region: str(d.regionName) || str(d.region),
        city: d.city,
        isp: d.isp,
        org: d.org || (m ? m[2] : ""),
        asn: m ? m[1] : "",
        tz: d.timezone,
        source: "ip-api.com"
      };
    }

    // ipwho.is
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

  function failureKind(status, d) {
    if (status === 429 || status === 403) return "limited";
    if (d && typeof d === "object" && (d.status === "fail" || d.success === false)) {
      return /\b(rate|limit|limited|quota|too many|exceeded?)\b/i.test(str(d.message))
        ? "limited"
        : "refused";
    }
    return null;
  }

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

    var g = status >= 200 && status < 300 ? normalize(data) : null;

    if (g) {
      var country = str(g.country) || str(g.cc) || TEXT.unknown;
      // 城市國家相容逐級降級：city -> region -> country
      var place = str(g.city) || str(g.region) || country;
      var org = str(g.org);

      $done({
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

    var kind = failureKind(status, data);
    if (kind) {
      $done({
        title: "✅ " + TEXT.ok,
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

    $done({
      title: "✅ " + TEXT.ok,
      subtitle: TEXT.badData,
      ip: "",
      description: lines([TEXT.badDataHint, httpLine(status), "GeoCheck " + VERSION])
    });
  }

  var hasResponse = typeof $response !== "undefined" && $response;
  var STATUS = Number((hasResponse && $response.statusCode) || 0);
  var BODY = hasResponse && $response.body ? String($response.body) : "";

  log("status=" + STATUS + " body=" + (BODY ? BODY.slice(0, 160) : "(none)"));

  if (!STATUS) {
    $done({
      title: "❌ " + TEXT.noResponse,
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
    $done({
      title: "✅ " + TEXT.ok,
      subtitle: TEXT.badData,
      ip: "",
      description: lines([TEXT.badDataHint, httpLine(STATUS), String(e), "GeoCheck " + VERSION])
    });
  }
})();
