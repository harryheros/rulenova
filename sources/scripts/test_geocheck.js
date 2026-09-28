#!/usr/bin/env node
/*
 * Tests for extras/quantumult-x/GeoCheck.js
 *   node sources/scripts/test_geocheck.js
 *
 * 1. Structure rules learned the hard way on Quantumult X (behaviour tests in
 *    Node passed for every broken version, so structure is checked directly):
 *      - $done() is called exactly once, at the top level (never inside a
 *        function or IIFE) - otherwise Quantumult X shows a blank result
 *      - plain ES5 syntax only
 *      - every top-level name starts with __gc_
 * 2. Behaviour for every response type, in fresh and shared JS contexts.
 */
const fs = require("fs"), vm = require("vm"), path = require("path");
const { execFileSync } = require("child_process");

const FILE = path.join(__dirname, "..", "..", "extras", "quantumult-x", "GeoCheck.js");
const src = fs.readFileSync(FILE, "utf8");
let failed = 0;
const fail = (msg) => { failed++; console.log("FAIL " + msg); };

// ---- 1. structure (AST via the acorn parser bundled with Node, ES5 mode)
let ast;
try {
  ast = JSON.parse(execFileSync(process.execPath, ["--expose-internals", "-e",
    'const acorn = require("internal/deps/acorn/acorn/dist/acorn");' +
    'process.stdout.write(JSON.stringify(acorn.parse(require("fs").readFileSync(process.argv[1], "utf8"), { ecmaVersion: 5 })));',
    FILE], { stdio: ["ignore", "pipe", "pipe"], maxBuffer: 64 * 1024 * 1024 }).toString());
} catch (e) {
  const line = String(e.stderr || e.message).split("\n").find((l) => /SyntaxError|reserved|Unexpected/.test(l)) || e.message;
  fail("not plain ES5 syntax: " + line.trim());
}

if (ast) {
  const doneCalls = [];
  (function walk(node, fnDepth) {
    if (!node || typeof node.type !== "string") return;
    const isFn = /Function/.test(node.type);
    if (node.type === "CallExpression" && node.callee.type === "Identifier" && node.callee.name === "$done") {
      doneCalls.push({ fnDepth, line: src.slice(0, node.start).split("\n").length });
    }
    for (const key of Object.keys(node)) {
      const v = node[key];
      if (Array.isArray(v)) v.forEach((c) => walk(c, fnDepth + (isFn ? 1 : 0)));
      else if (v && typeof v.type === "string") walk(v, fnDepth + (isFn ? 1 : 0));
    }
  })(ast, 0);

  if (doneCalls.length !== 1) fail(`$done() must appear exactly once, found ${doneCalls.length} (lines ${doneCalls.map((c) => c.line).join(", ")})`);
  doneCalls.filter((c) => c.fnDepth > 0).forEach((c) => fail(`$done() on line ${c.line} is inside a function - it must be at the top level`));

  for (const stmt of ast.body) {
    const names = stmt.type === "FunctionDeclaration" ? [stmt.id.name]
      : stmt.type === "VariableDeclaration" ? stmt.declarations.map((d) => d.id.name) : [];
    names.filter((n) => !n.startsWith("__gc_")).forEach((n) => fail(`top-level name "${n}" must start with __gc_`));
  }
}

// ---- 2. behaviour
const J = (o) => JSON.stringify(o);
const CASES = [
  ["ip-api success", {statusCode:200, body:J({status:"success",country:"United States",countryCode:"US",regionName:"California",city:"Los Angeles",isp:"Cloudflare, Inc.",org:"Cloudflare",as:"AS13335 Cloudflare, Inc.",query:"198.51.100.7",timezone:"America/Los_Angeles"})},
    (o) => o.title === "🇺🇸 Los Angeles" && o.subtitle === "Cloudflare, Inc." && o.ip === "198.51.100.7" && /Country: United States/.test(o.description) && /GeoCheck \d+\.\d+\.\d+/.test(o.description)],
  ["ip-api city-state", {statusCode:200, body:J({status:"success",country:"Hong Kong",countryCode:"HK",regionName:"Central and Western",city:"Hong Kong",isp:"HKT Limited",org:"HKT",as:"AS4760 HKT Limited",query:"203.0.113.10"})},
    (o) => o.title === "🇭🇰 Hong Kong" && o.subtitle === "HKT Limited"],
  ["ip-api empty city -> region", {statusCode:200, body:J({status:"success",country:"Germany",countryCode:"DE",regionName:"Hesse",city:"",isp:"Hetzner",query:"198.51.100.8"})},
    (o) => o.title === "🇩🇪 Hesse"],
  ["ip.sb success", {statusCode:200, body:J({ip:"203.0.113.9",country:"Japan",country_code:"JP",region:"Tokyo",city:"Tokyo",isp:"IIJ",organization:"Internet Initiative Japan",asn:2497,timezone:"Asia/Tokyo"})},
    (o) => o.title === "🇯🇵 Tokyo" && o.subtitle === "IIJ" && /Org: Internet Initiative Japan/.test(o.description)],
  ["ip.sb without city -> country", {statusCode:200, body:J({ip:"203.0.113.12",country:"Singapore",country_code:"SG",isp:"Amazon"})},
    (o) => o.title === "🇸🇬 Singapore"],
  ["ipwho.is success", {statusCode:200, body:J({ip:"203.0.113.11",success:true,country:"Singapore",country_code:"SG",city:"Singapore",connection:{asn:16509,org:"Amazon.com",isp:"Amazon.com, Inc."},timezone:{id:"Asia/Singapore"}})},
    (o) => o.title === "🇸🇬 Singapore"],
  ["minimal ip.sb", {statusCode:200, body:J({ip:"2001:db8::1",country_code:"US",asn:13335})},
    (o) => o.title === "🇺🇸 US" && o.subtitle === "AS13335"],
  ["HTTP 429", {statusCode:429, body:""},
    (o) => o.title === "✅ Node OK" && o.subtitle === "Geo service rate-limited" && /HTTP 429/.test(o.description)],
  ["200 + quota message", {statusCode:200, body:J({success:false,message:"You've hit the monthly limit"})},
    (o) => o.subtitle === "Geo service rate-limited"],
  ["'accurate' is not rate limiting", {statusCode:200, body:J({success:false,message:"No accurate location available"})},
    (o) => o.subtitle === "No location data"],
  ["reserved range", {statusCode:200, body:J({status:"fail",message:"reserved range",query:"10.0.0.1"})},
    (o) => o.subtitle === "No location data" && o.ip === "10.0.0.1"],
  ["HTML error page", {statusCode:502, body:"<html>Bad gateway</html>"},
    (o) => o.title === "✅ Node OK" && o.subtitle === "Invalid geo data" && /HTTP 502/.test(o.description)],
  ["no $response", undefined, (o) => o.title === "❌ No response"],
  ["status 0", {statusCode:0, body:""}, (o) => o.title === "❌ No response"],
];

function run(ctx, name, resp, check, label) {
  let out = null, calls = 0;
  if (resp === undefined) delete ctx.$response; else ctx.$response = resp;
  ctx.$done = (o) => { out = o; calls++; };
  try { vm.runInContext(src, ctx); } catch (e) { return fail(`${label} ${name}: crashed - ${e.message}`); }
  if (calls !== 1) return fail(`${label} ${name}: $done called ${calls} times`);
  for (const k of ["title", "subtitle", "ip", "description"]) {
    if (typeof out[k] !== "string") return fail(`${label} ${name}: ${k} is not a string`);
  }
  if (/[·\/|]/.test(out.subtitle)) return fail(`${label} ${name}: composite subtitle "${out.subtitle}"`);
  if (!check(out)) fail(`${label} ${name}: got "${out.title}" | "${out.subtitle}"`);
}

for (const [name, resp, check] of CASES) run(vm.createContext({}), name, resp, check, "[fresh]");
const shared = vm.createContext({});
for (let round = 1; round <= 2; round++) for (const [name, resp, check] of CASES) run(shared, name, resp, check, `[shared #${round}]`);

if (failed) { console.log(`\n${failed} check(s) FAILED`); process.exit(1); }
console.log(`GeoCheck: structure OK (ES5, one top-level $done, __gc_ names); ${CASES.length * 3} behaviour checks passed.`);
