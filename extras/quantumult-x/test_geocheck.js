#!/usr/bin/env node
/*
 * Tests for GeoCheck.js — run with: node extras/quantumult-x/test_geocheck.js
 *
 * Covers every response type, and repeated evaluation in one shared JS
 * context (defensive: the script must not depend on a fresh global scope).
 */
const fs = require("fs"), vm = require("vm"), path = require("path");
const src = fs.readFileSync(path.join(__dirname, "GeoCheck.js"), "utf8");
const J = (o) => JSON.stringify(o);

const CASES = [
  ["ip.sb success", {statusCode:200, body:J({ip:"203.0.113.9",country:"Japan",country_code:"JP",region:"Tokyo",city:"Tokyo",isp:"IIJ",organization:"Internet Initiative Japan",asn:2497,timezone:"Asia/Tokyo"})},
    (o) => o.title === "🇯🇵 Tokyo" && o.subtitle === "IIJ" && /Org: Internet Initiative Japan/.test(o.description)],
  ["ip-api success", {statusCode:200, body:J({status:"success",country:"Hong Kong",countryCode:"HK",regionName:"Central and Western",city:"Hong Kong",isp:"HKT Limited",org:"HKT",as:"AS4760 HKT Limited",query:"203.0.113.10"})},
    (o) => o.title === "🇭🇰 Hong Kong" && o.subtitle === "HKT Limited" && o.ip === "203.0.113.10"],
  ["ipwho.is success", {statusCode:200, body:J({ip:"203.0.113.11",success:true,country:"Singapore",country_code:"SG",city:"Singapore",connection:{asn:16509,org:"Amazon.com",isp:"Amazon.com, Inc."},timezone:{id:"Asia/Singapore"}})},
    (o) => o.title === "🇸🇬 Singapore"],
  ["US city", {statusCode:200, body:J({ip:"198.51.100.7",country:"United States",country_code:"US",region:"California",city:"Los Angeles",isp:"Cloudflare",asn:13335})},
    (o) => o.title === "🇺🇸 Los Angeles" && o.subtitle === "Cloudflare" && /Country: United States/.test(o.description)],
  ["region only", {statusCode:200, body:J({ip:"198.51.100.8",country:"Germany",country_code:"DE",region:"Hesse",isp:"Hetzner"})},
    (o) => o.title === "🇩🇪 Hesse" && o.subtitle === "Hetzner"],
  ["minimal ip.sb", {statusCode:200, body:J({ip:"2001:db8::1",country_code:"US",asn:13335})},
    (o) => o.title === "🇺🇸 US" && o.subtitle === "AS13335"],
  ["HTTP 429", {statusCode:429, body:""},
    (o) => o.title === "✅ Node OK" && o.subtitle === "Geo service rate-limited" && /HTTP 429/.test(o.description)],
  ["200 + rate limit message", {statusCode:200, body:J({success:false,message:"rate limit exceeded"})},
    (o) => o.subtitle === "Geo service rate-limited"],
  ["'accurate' is not rate limiting", {statusCode:200, body:J({success:false,message:"No accurate location available"})},
    (o) => o.subtitle === "No location data"],
  ["reserved range", {statusCode:200, body:J({status:"fail",message:"reserved range",query:"10.0.0.1"})},
    (o) => o.subtitle === "No location data" && o.ip === "10.0.0.1"],
  ["HTML error page", {statusCode:502, body:"<html>Bad gateway</html>"},
    (o) => o.title === "✅ Node OK" && o.subtitle === "Invalid geo data"],
  ["empty body", {statusCode:200, body:""},
    (o) => o.subtitle === "Invalid geo data"],
  ["no $response", undefined,
    (o) => o.title.startsWith("❌")],
  ["status 0", {statusCode:0, body:""},
    (o) => o.title.startsWith("❌")],
];

let failed = 0;
function runIn(ctx, name, resp, check, label) {
  let out = null, calls = 0;
  if (resp === undefined) delete ctx.$response; else ctx.$response = resp;
  ctx.$done = (o) => { out = o; calls++; };
  try {
    vm.runInContext(src, ctx);
  } catch (e) {
    failed++; console.log(`FAIL ${label} ${name}: crashed — ${e.message}`); return;
  }
  // Composite subtitles blanked ip-api results in Quantumult X: keep them plain.
  if (out && /[·\/|]/.test(out.subtitle || "")) {
    failed++; console.log(`FAIL ${label} ${name}: composite subtitle "${out.subtitle}"`); return;
  }
  if (calls !== 1 || !check(out)) {
    failed++; console.log(`FAIL ${label} ${name}: ${out ? `${out.title} | ${out.subtitle}` : "$done not called"}`);
  }
}

// 1. Every case in a fresh context.
for (const [name, resp, check] of CASES) runIn(vm.createContext({}), name, resp, check, "[fresh]");

// 2. All cases, twice, in ONE shared context (the Quantumult X situation).
const shared = vm.createContext({});
for (let round = 1; round <= 2; round++) {
  for (const [name, resp, check] of CASES) runIn(shared, name, resp, check, `[shared #${round}]`);
}

const total = CASES.length * 3;
if (failed) { console.log(`\n${failed}/${total} checks FAILED`); process.exit(1); }
console.log(`All ${total} checks passed (${CASES.length} cases, fresh + shared context x2).`);
