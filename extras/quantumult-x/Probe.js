// RuleNova GeoCheck probe — minimal diagnostic for Quantumult X.
// Deliberately written in the most conservative style (var only, no modern
// syntax). The details view shows the raw API response, so no log is needed.
var status = (typeof $response !== "undefined" && $response) ? $response.statusCode : "none";
var body = (typeof $response !== "undefined" && $response && $response.body) ? String($response.body) : "";
var obj = {};
try { obj = JSON.parse(body); } catch (e) { obj = {}; }
var place = obj.city || obj.regionName || obj.region || obj.country || "no-city";
$done({
  title: "PROBE " + place,
  subtitle: "status " + status,
  ip: obj.query || obj.ip || "",
  description: "PROBE 1\nstatus: " + status + "\nbody: " + body.slice(0, 300)
});
