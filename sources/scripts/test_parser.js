#!/usr/bin/env node
/*
 * Tests for extras/quantumult-x/parser.js
 *   node sources/scripts/test_parser.js
 *
 * 1. Structure: plain ES5, $done() exactly once at the top level, global
 *    names prefixed __np_ (plus $parser), no eval / network / storage APIs,
 *    and the three $parser option-editor functions work in isolation.
 * 2. Behaviour: every supported input format and option, run the way
 *    Quantumult X runs it ($resource in, $done out), in fresh and shared
 *    JS contexts.
 */
const fs = require("fs"), vm = require("vm"), path = require("path");
const { execFileSync } = require("child_process");

const ROOT = path.join(__dirname, "..", "..");
const FILE = path.join(ROOT, "extras", "quantumult-x", "parser.js");
let failed = 0, passed = 0;
const fail = (msg) => { failed++; console.log("FAIL " + msg); };
const check = (ok, msg) => { if (ok) passed++; else fail(msg); };

if (!fs.existsSync(FILE)) {
  fail("extras/quantumult-x/parser.js is missing");
  process.exit(1);
}
const src = fs.readFileSync(FILE, "utf8");

// ---- 1. structure ---------------------------------------------------------
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

const helperSrc = {};
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
  check(doneCalls.length === 1, `$done() must appear exactly once, found ${doneCalls.length}`);
  doneCalls.filter((c) => c.fnDepth > 0).forEach((c) => fail(`$done() on line ${c.line} is inside a function`));

  for (const stmt of ast.body) {
    const names = stmt.type === "FunctionDeclaration" ? [stmt.id.name]
      : stmt.type === "VariableDeclaration" ? stmt.declarations.map((d) => d.id.name) : [];
    names.filter((n) => !n.startsWith("__np_") && n !== "$parser").forEach((n) => fail(`top-level name "${n}" must start with __np_`));
    // collect "$parser.x = function () {...}" for the isolation test
    if (stmt.type === "ExpressionStatement" && stmt.expression.type === "AssignmentExpression"
        && stmt.expression.left.type === "MemberExpression" && stmt.expression.left.object.name === "$parser") {
      helperSrc[stmt.expression.left.property.name] = src.slice(stmt.expression.right.start, stmt.expression.right.end);
    }
  }
}
for (const banned of [/\beval\s*\(/, /\bnew\s+Function\b/, /\$task\b/, /\$prefs\b/, /\$httpClient\b/]) {
  check(!banned.test(src), `source must not use ${banned}`);
}

// Quantumult X runs the three option-editor functions on their own: rebuild
// $parser from just their source, with nothing else from the script.
for (const name of ["hashSchema", "hashToUI", "uiToHash"]) check(helperSrc[name], `$parser.${name} is missing`);
if (helperSrc.hashSchema && helperSrc.hashToUI && helperSrc.uiToHash) {
  const iso = vm.createContext({});
  try {
    vm.runInContext("var $parser = {};" + ["hashSchema", "hashToUI", "uiToHash"]
      .map((n) => `$parser.${n} = ${helperSrc[n]};`).join("\n"), iso);
    const schema = vm.runInContext("$parser.hashSchema()", iso);
    const keys = [].concat(...schema.sections.map((g) => g.items.map((i) => i.key)));
    check(schema.version === 1 && keys.join() === "policy,include,exclude,replace,host-include,host-exclude,output,notify",
      "hashSchema keys: " + keys.join());
    const ui = vm.runInContext('$parser.hashToUI("policy=My%20Proxy&include=ads+a%2Bb&replace=x%2By@z+q@r&custom=1")', iso);
    const vals = {};
    ui.sections.forEach((g) => g.items.forEach((i) => { vals[i.key] = i.value; }));
    check(vals.policy === "My Proxy", "hashToUI decodes text: " + vals.policy);
    check(JSON.stringify(vals.include) === '["ads","a+b"]', "hashToUI splits tags: " + JSON.stringify(vals.include));
    check(vals.replace === "x%2By@z+q@r", "hashToUI keeps replace raw: " + vals.replace);
    check(ui.unknown === "custom=1", "hashToUI keeps unknown options: " + ui.unknown);
    check(vm.runInContext('$parser.hashToUI("").sections.length', iso) === 0, "hashToUI empty hash");
    iso.values = { policy: "My Proxy", include: ["ads", "a+b"], replace: "x%2By@z+q@r&", output: "", __unknown: "custom=1" };
    const hash = vm.runInContext("$parser.uiToHash(values)", iso);
    check(hash === "policy=My%20Proxy&include=ads+a%2Bb&replace=x%2By@z+q@r%26&custom=1", "uiToHash: " + hash);
  } catch (e) {
    fail("option editor functions are not self-contained: " + e.message);
  }
}

// ---- 2. behaviour --------------------------------------------------------
function run(ctx, content, link) {
  let out = null, calls = 0;
  const notes = [];
  ctx.$resource = { content, link };
  ctx.$done = (o) => { out = o; calls++; };
  ctx.$notify = (t, s, b) => notes.push([t, s, b]);
  try { vm.runInContext(src, ctx); } catch (e) { return { crash: e.message, notes }; }
  return { out, calls, notes };
}

const lines = (o) => (o && o.content ? o.content.trim().split("\n").filter((l) => !l.startsWith("#")) : []);
const L = (...a) => a.join("\n");

const MODULE = L(
  "#!name=Sample",
  "#!arguments=Mode:block,Host:api.example.com",
  "[General]",
  "force-http-engine-hosts = %APPEND% x.example.com",
  "[Rule]",
  "DOMAIN,ads.example.com,REJECT",
  "URL-REGEX,^https?://ad\\.example\\.com/,REJECT",
  "URL-REGEX,^https?://pic\\.example\\.com/,REJECT-TINYGIF",
  "URL-REGEX,^https?://x\\.example\\.com/,DIRECT",
  "[URL Rewrite]",
  "^https?://old\\.example\\.com/(.*) https://new.example.com/$1 302",
  "^https?://moved\\.example\\.com/ https://new.example.com/ 307",
  "^https?://ads\\.example\\.com - reject",
  "^https?://h\\.example\\.com https://x.example.com header",
  "[Map Local]",
  '^https?://a\\.example\\.com/config data-type=json data="{}" status-code=200',
  '^https?://b\\.example\\.com/list data-type=json data="[]"',
  "^https?://c\\.example\\.com/gif data-type=tiny-gif status-code=200",
  '^https?://d\\.example\\.com/e data=""',
  '^https?://e\\.example\\.com/f data="https://example.com/y.json"',
  "[Script]",
  "resp = type=http-response,pattern=^https?://{{{Host}}}/v(1|2){1,3},requires-body=1,max-size=0,script-path=https://cdn.example.com/a.js,argument=mode={{{Mode}}}",
  "req = type=http-request,pattern=^https?://api\\.example\\.com/login,script-path=https://cdn.example.com/b.js",
  'job = type=cron,cronexp="0 8 * * *",script-path=https://cdn.example.com/c.js',
  "bin = type=http-response,pattern=^https?://bin\\.example\\.com,requires-body=1,binary-body-mode=1,script-path=https://cdn.example.com/e.js",
  "local = type=http-response,pattern=^https?://l\\.example\\.com,script-path=local.js",
  "http-response ^https?://legacy\\.example\\.com/x requires-body=1,script-path=https://cdn.example.com/d.js",
  "[Body Rewrite]",
  'http-response ^https?://f\\.example\\.com/api "ad":true "ad":false "vip":0 "vip":1',
  "http-response-jq ^https?://g\\.example\\.com/api 'del(.ads)'",
  "http-response ^https?://s\\.example\\.com/api \"a b\" c",
  "[Header Rewrite]",
  "^https?://x header-del Cookie",
  "[MITM]",
  "hostname = %APPEND% {{{Host}}}, *.example.com, -safe.example.com, *.example.com",
  "[Panel]",
  "p = title=x"
);

const CASES = [
  ["Surge / Clash classical list", L(
    "# comment", "// comment", "; comment", "",
    "DOMAIN-SUFFIX,Google.com,Proxy", "DOMAIN,a.com", "DOMAIN-KEYWORD,track",
    "DOMAIN-WILDCARD,*.w?.com,DIRECT",
    "IP-CIDR,1.1.1.0/24,DIRECT,no-resolve", "IP-CIDR6,2001:db8::/32,no-resolve",
    "IP-CIDR,8.8.8.8,REJECT-DROP", "IP-ASN,AS13335,Proxy", "GEOIP,CN,DIRECT", "USER-AGENT,Foo*,REJECT",
    "PROCESS-NAME,x,DIRECT", "AND,((DOMAIN,a.com),(DST-PORT,443)),REJECT", "MATCH,DIRECT",
    "DOMAIN-SUFFIX,google.com"),
    "https://example.com/list.txt",
    (r) => lines(r.out).join("|") === [
      "host-suffix, google.com, proxy", "host, a.com, proxy", "host-keyword, track, proxy",
      "host-wildcard, *.w?.com, direct", "ip-cidr, 1.1.1.0/24, direct", "ip6-cidr, 2001:db8::/32, proxy",
      "ip-cidr, 8.8.8.8/32, reject", "ip-asn, 13335, proxy", "geoip, CN, direct", "user-agent, Foo*, reject",
    ].join("|") && r.notes.length === 1 && /PROCESS-NAME x1/.test(r.notes[0][2]) && /AND \(logical rule\) x1/.test(r.notes[0][2]) && /MATCH x1/.test(r.notes[0][2])],

  ["policy option overrides every rule", L("DOMAIN,a.com,DIRECT", "IP-CIDR,10.0.0.0/8,REJECT", "b.com"),
    "https://example.com/list.txt#policy=My%20Group",
    (r) => lines(r.out).join("|") === "host, a.com, My Group|ip-cidr, 10.0.0.0/8, My Group|host, b.com, My Group"],

  ["Clash rule-provider YAML (domain behavior)", L(
    "payload:", "  - '+.a.com'", '  - ".b.com"', "  - c.com", "  - '*.d.com'  # comment", "  # skipped comment"),
    "https://example.com/a.yaml",
    (r) => lines(r.out).join("|") === "host-suffix, a.com, proxy|host-wildcard, *.b.com, proxy|host, c.com, proxy|host-wildcard, *.d.com, proxy"
      && r.notes.length === 0],

  ["Clash rule-provider YAML (classical + ipcidr)", L(
    "# header", "payload:", "  - DOMAIN-SUFFIX,a.com", "  - 'IP-CIDR,10.0.0.0/8,no-resolve'", "  - '192.168.0.0/16'", "  - '2001:db8::/48'"),
    "https://example.com/b.yaml#policy=LAN",
    (r) => lines(r.out).join("|") === "host-suffix, a.com, LAN|ip-cidr, 10.0.0.0/8, LAN|ip-cidr, 192.168.0.0/16, LAN|ip6-cidr, 2001:db8::/48, LAN"],

  ["Surge domain set", L(".a.com", "b.com", "+.c.com", "*.d.com", "invalid_line here"),
    "https://example.com/set.txt",
    (r) => lines(r.out).join("|") === "host-suffix, a.com, proxy|host, b.com, proxy|host-suffix, c.com, proxy|host-wildcard, *.d.com, proxy"
      && /unrecognized x1/.test(r.notes[0][2])],

  ["IP list", L("1.2.3.4", "10.0.0.0/8", "2001:db8::1", "999.1.1.1"),
    "https://example.com/ip.txt",
    (r) => lines(r.out).join("|") === "ip-cidr, 1.2.3.4/32, proxy|ip-cidr, 10.0.0.0/8, proxy|ip6-cidr, 2001:db8::1/128, proxy"
      && /unrecognized x1/.test(r.notes[0][2])],

  ["custom policy names keep their case; built-ins are lower-cased", L("DOMAIN,a.com,Streaming", "DOMAIN,b.com,PROXY", "DOMAIN,c.com,DIRECT"),
    "https://example.com/l.txt",
    (r) => lines(r.out).join("|") === "host, a.com, Streaming|host, b.com, proxy|host, c.com, direct"],

  ["hosts file and simple filter list -> reject", L(
    "127.0.0.1 localhost", "0.0.0.0 ads.example.com", "::1 ip6-localhost", "||track.example.com^",
    "! comment", "@@||ok.example.com^", "||x.example.com^$third-party"),
    "https://example.com/hosts",
    (r) => lines(r.out).join("|") === "host, ads.example.com, reject|host-suffix, track.example.com, reject"
      && /filter-list syntax x2/.test(r.notes[0][2])],

  ["CRLF, BOM and duplicates", "﻿DOMAIN,a.com\r\nDOMAIN,A.com,Proxy\r\nDOMAIN-SUFFIX,a.com\r\n",
    "https://example.com/crlf.txt",
    (r) => lines(r.out).join("|") === "host, a.com, proxy|host-suffix, a.com, proxy"],

  ["include / exclude keywords (case-insensitive)", L("DOMAIN,ads.a.com", "DOMAIN,b.com", "DOMAIN,ADS.c.com", "DOMAIN,ads.keep.com"),
    "https://example.com/l.txt#include=ads&exclude=KEEP",
    (r) => lines(r.out).join("|") === "host, ads.a.com, proxy|host, ads.c.com, proxy"],

  ["replace with %2B and invalid regex", L("DOMAIN,a.com,Media"),
    "https://example.com/l.txt#replace=Media@Media%2BTV+(@x&notify=1",
    (r) => lines(r.out).join("|") === "host, a.com, Media+TV" && /invalid replace regex ignored x1/.test(r.notes[0][2])],

  ["Surge module -> rewrite", MODULE, "https://example.com/sample.sgmodule",
    (r) => lines(r.out).join("|") === [
      "^https?://ad\\.example\\.com/ url reject",
      "^https?://pic\\.example\\.com/ url reject-img",
      "^https?://old\\.example\\.com/(.*) url 302 https://new.example.com/$1",
      "^https?://moved\\.example\\.com/ url 307 https://new.example.com/",
      "^https?://ads\\.example\\.com url reject",
      "^https?://a\\.example\\.com/config url reject-dict",
      "^https?://b\\.example\\.com/list url reject-array",
      "^https?://c\\.example\\.com/gif url reject-img",
      "^https?://d\\.example\\.com/e url reject-200",
      "^https?://api.example.com/v(1|2){1,3} url script-response-body https://cdn.example.com/a.js",
      "^https?://api\\.example\\.com/login url script-request-header https://cdn.example.com/b.js",
      "^https?://legacy\\.example\\.com/x url script-response-body https://cdn.example.com/d.js",
      '^https?://f\\.example\\.com/api url response-body "ad":true response-body "ad":false',
      '^https?://f\\.example\\.com/api url response-body "vip":0 response-body "vip":1',
      "^https?://g\\.example\\.com/api url jsonjq-response-body 'del(.ads)'",
      "hostname = api.example.com, *.example.com, -safe.example.com",
    ].join("|") && [
      "URL Rewrite header x1", "Map Local with custom data x1", "Script type=cron x1", "Script binary-body-mode x1",
      "Script (no pattern or remote script-path) x1", "Body Rewrite with spaces or empty text x1",
      "[Header Rewrite] section x1", "[Panel] section x1", "URL-REGEX without REJECT x1",
      "rules in a rewrite resource (use output=filter) x1", "script argument not passed x1",
    ].every((s) => r.notes.length === 1 && r.notes[0][2].indexOf(s) >= 0)],

  ["module with output=filter keeps the [Rule] section", MODULE, "https://example.com/sample.sgmodule#output=filter&policy=AdBlock",
    (r) => lines(r.out).join("|") === "host, ads.example.com, AdBlock"],

  ["module options: exclude, host-exclude, replace, notify=0", MODULE,
    "https://example.com/sample.sgmodule#exclude=old+legacy&host-include=example&host-exclude=safe&replace=cdn%5C.example@mirror.example&notify=0",
    (r) => {
      const l = lines(r.out);
      return l.length === 14 && !l.some((x) => /old|legacy/.test(x)) && l.indexOf("^https?://api\\.example\\.com/login url script-request-header https://mirror.example.com/b.js") >= 0
        && l[l.length - 1] === "hostname = api.example.com, *.example.com" && r.notes.length === 0;
    }],

  ["Quantumult X rewrite snippet passes through", L(
    "hostname = a.example.com, b.example.com",
    "^https?://a\\.example\\.com/ad url reject",
    "^https?://b\\.example\\.com/x url script-response-body https://cdn.example.com/x.js"),
    "https://example.com/qx.snippet#host-exclude=b.example",
    (r) => lines(r.out).join("|") === "^https?://a\\.example\\.com/ad url reject|^https?://b\\.example\\.com/x url script-response-body https://cdn.example.com/x.js|hostname = a.example.com"
      && r.notes.length === 0],

  ["Quantumult X filter lines are normalised", L("host-suffix, a.com, Streaming", "ip-cidr, 10.0.0.0/8, direct, force-cellular", "geoip, cn, direct, via-interface=%TUN%", "DOMAIN,b.com,DIRECT,force-cellular"),
    "https://example.com/qx.list",
    (r) => lines(r.out).join("|") === "host-suffix, a.com, Streaming|ip-cidr, 10.0.0.0/8, direct, force-cellular|geoip, cn, direct, via-interface=%TUN%|host, b.com, direct"],

  ["empty resource -> error", "  \n ", "https://example.com/empty.txt",
    (r) => r.out.error && /empty/.test(r.out.error) && !r.out.content],

  ["nothing convertible -> error with reasons", L("PROCESS-NAME,a,DIRECT", "SRC-IP,1.1.1.1,DIRECT"),
    "https://example.com/l.txt",
    (r) => r.out.error && /nothing to convert/.test(r.out.error) && /PROCESS-NAME x1/.test(r.out.error) && r.notes.length === 1],

  ["module with only rules -> error points to output=filter", L("#!name=x", "[Rule]", "DOMAIN,a.com,REJECT"),
    "https://example.com/m.sgmodule",
    (r) => r.out.error && /output=filter/.test(r.out.error)],

  ["no notification when nothing is skipped", L("DOMAIN,a.com"), "https://example.com/l.txt",
    (r) => r.notes.length === 0],

  ["notify=1 always notifies", L("DOMAIN,a.com"), "https://example.com/l.txt#notify=1",
    (r) => r.notes.length === 1 && /Converted 1 filter line/.test(r.notes[0][2]) && r.notes[0][1] === "l.txt"],

  ["node subscription (links) passes through untouched", L("vmess://eyJhZGQiOiJ4In0=", "ss://YWVzOnB3@1.2.3.4:8388#HK", "trojan://pw@example.com:443?sni=a#JP"),
    "https://example.com/sub",
    (r) => r.out.content === L("vmess://eyJhZGQiOiJ4In0=", "ss://YWVzOnB3@1.2.3.4:8388#HK", "trojan://pw@example.com:443?sni=a#JP") && r.notes.length === 0],

  ["node subscription (base64 / Quantumult X / Clash) passes through", "c3M6Ly9ZV1Z6T25CM0AxLjIuMy40Ojg4ODgjSEsKdm1lc3M6Ly9leUpoWkdRaU9pSjRJbjA9",
    "https://example.com/sub2",
    (r) => r.out.content === "c3M6Ly9ZV1Z6T25CM0AxLjIuMy40Ojg4ODgjSEsKdm1lc3M6Ly9leUpoWkdRaU9pSjRJbjA9"
      && run(vm.createContext({}), "shadowsocks=1.2.3.4:443, method=aes-128-gcm, password=x, tag=A", "https://x/s").out.content.indexOf("shadowsocks=") === 0
      && run(vm.createContext({}), L("port: 7890", "proxies:", "  - {name: a, type: ss}"), "https://x/c.yaml").out.content.indexOf("port: 7890") === 0],

  ["output header line", L("DOMAIN,a.com"), "https://example.com/l.txt",
    (r) => /^# RuleNova Parser \d+\.\d+\.\d+ - filter, 1 line\(s\)\n/.test(r.out.content)],
];

function runAll(ctx, label) {
  for (const [name, content, link, ok] of CASES) {
    const r = run(ctx, content, link);
    if (r.crash) { fail(`${label} ${name}: crashed - ${r.crash}`); continue; }
    if (r.calls !== 1) { fail(`${label} ${name}: $done called ${r.calls} times`); continue; }
    if (r.out.content !== undefined && typeof r.out.content !== "string") { fail(`${label} ${name}: content is not a string`); continue; }
    let good = false;
    try { good = ok(r); } catch (e) { good = false; }
    if (good) passed++;
    else fail(`${label} ${name}\n  got: ${JSON.stringify(r.out)}\n  notes: ${JSON.stringify(r.notes)}`);
  }
}

runAll(vm.createContext({}), "[fresh]");
const shared = vm.createContext({});
runAll(shared, "[shared #1]");
runAll(shared, "[shared #2]");

// no $resource at all (e.g. the script is loaded outside a resource refresh)
{
  let out = null;
  const ctx = vm.createContext({ $done: (o) => { out = o; } });
  try { vm.runInContext(src, ctx); check(out && out.error, "no $resource -> error"); }
  catch (e) { fail("no $resource: crashed - " + e.message); }
}

if (failed) { console.log(`\n${failed} check(s) FAILED, ${passed} passed`); process.exit(1); }
console.log(`parser.js: structure OK (ES5, one top-level $done, __np_ names, isolated option editor); ${passed} checks passed.`);
