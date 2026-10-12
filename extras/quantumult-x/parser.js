/*
 * RuleNova Parser 1.0.0 - Quantumult X resource parser for rules and modules
 * https://github.com/harryheros/rulenova
 *
 * Converts rule lists and Surge modules into Quantumult X format.
 * It does NOT handle server (node) subscriptions.
 *
 * Usage ([general] section of Quantumult X):
 *   resource_parser_url=https://cdn.jsdelivr.net/gh/harryheros/rulenova@main/extras/quantumult-x/parser.js
 * then add opt-parser=true to a [filter_remote] or [rewrite_remote] entry.
 * Options go after "#" in the resource URL, joined with "&":
 *   https://example.com/list.txt#policy=Proxy&exclude=ads
 *
 * Input -> output
 *   Rule lists (Surge / Clash classical, Clash rule-provider YAML, domain
 *   sets, IP lists, hosts files, simple "||domain^" filters)  -> filter
 *   Surge modules (.sgmodule) and Quantumult X rewrite snippets -> rewrite
 *
 * Options
 *   policy=NAME             policy for every rule (default: the rule's own
 *                           policy, otherwise "proxy")
 *   include=a+b             keep only lines containing any keyword
 *   exclude=a+b             drop lines containing any keyword
 *   host-include=a+b        keep only MITM hostnames containing any keyword
 *   host-exclude=a+b        drop MITM hostnames containing any keyword
 *   replace=REGEX@TEXT+...  regex replace on every output line
 *   output=filter|rewrite   force the output type
 *   notify=1|0              always / never notify (default: only when
 *                           something was skipped)
 *   Keywords are case-insensitive. Write a literal "+" as %2B, "@" as %40,
 *   "&" as %26 and "#" as %23.
 *
 * Server (node) subscriptions are returned unchanged, so Quantumult X
 * parses them natively.
 *
 * Anything Quantumult X cannot express (PROCESS-NAME, logical rules, cron
 * scripts, ...) is skipped, never guessed; the notification lists it.
 *
 * Structure (enforced by sources/scripts/test_parser.js):
 *   1. $done() is called exactly once, at the top level, at the very end.
 *   2. Plain ES5 only. No eval, no network access, no storage.
 *   3. Every global name starts with __np_ (plus the $parser helper object).
 */

var __np_VERSION = "1.0.0";
var __np_NAME = "RuleNova Parser";

// Surge / Clash rule type -> Quantumult X filter type
var __np_RULE_TYPES = {
  "domain": "host",
  "domain-suffix": "host-suffix",
  "domain-keyword": "host-keyword",
  "domain-wildcard": "host-wildcard",
  "host": "host",
  "host-suffix": "host-suffix",
  "host-keyword": "host-keyword",
  "host-wildcard": "host-wildcard",
  "ip-cidr": "ip-cidr",
  "ip-cidr6": "ip6-cidr",
  "ip6-cidr": "ip6-cidr",
  "geoip": "geoip",
  "ip-asn": "ip-asn",
  "user-agent": "user-agent"
};

// Rule options that are not a policy name
var __np_RULE_OPTIONS = {
  "no-resolve": 1, "extended-matching": 1, "pre-matching": 1,
  "force-remote-dns": 1, "src": 1, "dst": 1
};

// Surge sections that have a Quantumult X equivalent
var __np_MODULE_SECTIONS = {
  "rule": 1, "url rewrite": 1, "map local": 1, "script": 1,
  "mitm": 1, "body rewrite": 1
};

function __np_trim(s) {
  return String(s).trim();
}

function __np_decode(s) {
  try { return decodeURIComponent(s); } catch (e) { return s; }
}

function __np_list(raw) {
  var out = [], parts, i, v;
  if (!raw) return out;
  parts = raw.split("+");
  for (i = 0; i < parts.length; i++) {
    v = __np_trim(__np_decode(parts[i]));
    if (v) out.push(v);
  }
  return out;
}

function __np_options(link) {
  var opts = {}, hash, pairs, i, eq, key, val;
  link = String(link || "");
  eq = link.indexOf("#");
  hash = eq < 0 ? "" : link.slice(eq + 1);
  pairs = hash.split("&");
  for (i = 0; i < pairs.length; i++) {
    if (!pairs[i]) continue;
    eq = pairs[i].indexOf("=");
    key = (eq < 0 ? pairs[i] : pairs[i].slice(0, eq)).toLowerCase();
    val = eq < 0 ? "" : pairs[i].slice(eq + 1);
    opts[key] = val;
  }
  return {
    policy: opts.policy ? __np_trim(__np_decode(opts.policy)) : "",
    include: __np_list(opts.include),
    exclude: __np_list(opts.exclude),
    hostInclude: __np_list(opts["host-include"]),
    hostExclude: __np_list(opts["host-exclude"]),
    replace: opts.replace || "",
    output: (opts.output || "").toLowerCase(),
    notify: opts.notify === undefined ? "" : opts.notify
  };
}

// ---------------------------------------------------------------- notes

function __np_newNotes() {
  return { converted: 0, hosts: 0, skipped: {}, skippedTotal: 0, warnings: {} };
}

function __np_skip(notes, what) {
  notes.skipped[what] = (notes.skipped[what] || 0) + 1;
  notes.skippedTotal++;
}

function __np_warn(notes, what) {
  notes.warnings[what] = (notes.warnings[what] || 0) + 1;
}

function __np_summary(notes, kind) {
  var parts = [], keys, i;
  keys = Object.keys(notes.skipped).sort();
  for (i = 0; i < keys.length; i++) parts.push(keys[i] + " x" + notes.skipped[keys[i]]);
  var text = "Converted " + notes.converted + " " + kind + " line(s)" +
    (notes.hosts ? " and " + notes.hosts + " MITM hostname(s)." : ".");
  if (parts.length) text += "\nSkipped (not supported by Quantumult X): " + parts.join(", ");
  keys = Object.keys(notes.warnings).sort();
  parts = [];
  for (i = 0; i < keys.length; i++) parts.push(keys[i] + " x" + notes.warnings[keys[i]]);
  if (parts.length) text += "\nCheck: " + parts.join(", ");
  return text;
}

// ---------------------------------------------------------------- tokenizing

// Split "a, b, c" on commas, keeping commas inside quotes.
function __np_splitCsv(line) {
  var out = [], cur = "", q = "", i, c;
  if (line.indexOf("\"") < 0 && line.indexOf("'") < 0) {
    out = line.split(",");
    for (i = 0; i < out.length; i++) out[i] = __np_trim(out[i]);
    return out;
  }
  for (i = 0; i < line.length; i++) {
    c = line.charAt(i);
    if (q) {
      if (c === q) q = ""; else cur += c;
    } else if (c === "\"" || c === "'") {
      q = c;
    } else if (c === ",") {
      out.push(__np_trim(cur)); cur = "";
    } else {
      cur += c;
    }
  }
  out.push(__np_trim(cur));
  return out;
}

// Split on whitespace. A token wrapped in matching quotes ("a b" or 'a b')
// is one token without the quotes; a quote whose partner is not at the end
// of a token ("ad":true) is kept as part of the text.
function __np_splitWords(line) {
  var out = [], i = 0, n = line.length, c, end, j;
  while (i < n) {
    while (i < n && /\s/.test(line.charAt(i))) i++;
    if (i >= n) break;
    c = line.charAt(i);
    end = -1;
    if (c === "\"" || c === "'") {
      j = line.indexOf(c, i + 1);
      if (j > 0 && (j + 1 === n || /\s/.test(line.charAt(j + 1)))) end = j;
    }
    if (end > 0) {
      out.push(line.slice(i + 1, end));
      i = end + 1;
    } else {
      j = i;
      while (j < n && !/\s/.test(line.charAt(j))) j++;
      out.push(line.slice(i, j));
      i = j;
    }
  }
  return out;
}

// "key=value, key2="v, 2"" -> {key: value, key2: "v, 2"}; a comma only ends
// a value when the next item looks like "key=" (regex patterns contain commas).
function __np_keyValues(text) {
  var out = {}, parts = text.split(/,\s*(?=[A-Za-z][A-Za-z0-9-]*\s*=)/), i, eq, k, v;
  for (i = 0; i < parts.length; i++) {
    eq = parts[i].indexOf("=");
    if (eq < 0) continue;
    k = __np_trim(parts[i].slice(0, eq)).toLowerCase();
    v = __np_trim(parts[i].slice(eq + 1));
    if (v.length >= 2 && (v.charAt(0) === "\"" || v.charAt(0) === "'") && v.charAt(v.length - 1) === v.charAt(0)) {
      v = v.slice(1, -1);
    }
    out[k] = v;
  }
  return out;
}

function __np_isComment(line) {
  return line === "" || /^(#|;|\/\/|!)/.test(line);
}

// ---------------------------------------------------------------- rules

function __np_isIPv4(s) {
  var m = /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})(\/(\d{1,2}))?$/.exec(s);
  if (!m) return false;
  for (var i = 1; i <= 4; i++) if (+m[i] > 255) return false;
  return m[6] === undefined || +m[6] <= 32;
}

function __np_isIPv6(s) {
  var m = /^([0-9a-fA-F:.]+)(\/(\d{1,3}))?$/.exec(s);
  if (!m || m[1].indexOf(":") < 0 || !/[0-9a-fA-F]/.test(m[1])) return false;
  return m[3] === undefined || +m[3] <= 128;
}

function __np_isDomain(s) {
  // labels separated by dots, not an (invalid) IP address
  return /^[a-z0-9_*?-]+(\.[a-z0-9_*?-]+)+\.?$/i.test(s) && !/^[\d.]+$/.test(s);
}

function __np_policyOf(fields, start, opts) {
  var i, f, low;
  if (opts.policy) return opts.policy;
  for (i = start; i < fields.length; i++) {
    f = fields[i];
    low = f.toLowerCase();
    if (!f || __np_RULE_OPTIONS[low]) continue;
    if (low === "direct") return "direct";
    if (/^reject/.test(low)) return "reject";
    if (low === "proxy") return "proxy";
    return f;
  }
  return "proxy";
}

// Domain from a domain-set / payload entry -> [type, value] or null.
// clashStyle: in Clash, ".a.com" means subdomains only; in Surge it also
// matches a.com itself.
function __np_domainEntry(entry, clashStyle) {
  var d = entry.toLowerCase();
  if (d.indexOf("+.") === 0) {
    d = d.slice(2);
    return __np_isDomain(d) ? ["host-suffix", d] : null;
  }
  if (d.charAt(0) === ".") {
    d = d.slice(1);
    if (!__np_isDomain(d)) return null;
    return clashStyle ? ["host-wildcard", "*." + d] : ["host-suffix", d];
  }
  if (!__np_isDomain(d)) return null;
  if (/[*?]/.test(d)) return ["host-wildcard", d];
  return ["host", d.replace(/\.$/, "")];
}

// "TYPE,value[,policy][,options]" -> Quantumult X filter line, or null
function __np_convertTypedRule(line, opts, notes) {
  var fields, type, qxType, value;
  fields = __np_splitCsv(line);
  type = fields[0].toLowerCase();
  qxType = __np_RULE_TYPES[type];
  if (!qxType) {
    if (/^(and|or|not)$/.test(type)) __np_skip(notes, fields[0].toUpperCase() + " (logical rule)");
    else __np_skip(notes, fields[0].toUpperCase());
    return null;
  }
  value = fields[1] || "";
  if (!value) { __np_skip(notes, "empty value"); return null; }
  if (qxType === "ip-cidr" || qxType === "ip6-cidr") {
    if (__np_isIPv4(value)) qxType = "ip-cidr";
    else if (__np_isIPv6(value)) qxType = "ip6-cidr";
    else { __np_skip(notes, "invalid IP"); return null; }
    if (value.indexOf("/") < 0) value += qxType === "ip-cidr" ? "/32" : "/128";
  } else if (qxType === "ip-asn") {
    value = value.replace(/^as/i, "");
    if (!/^\d+$/.test(value)) { __np_skip(notes, "invalid ASN"); return null; }
  } else if (qxType.indexOf("host") === 0) {
    value = value.toLowerCase();
  }
  // Quantumult X's own interface options (force-cellular, via-interface=...)
  var extra = "", i;
  if (type === qxType) {
    for (i = 3; i < fields.length; i++) {
      if (/^(force-cellular|multi-interface(-balance)?|via-interface=\S+)$/i.test(fields[i])) extra += ", " + fields[i];
    }
  }
  return qxType + ", " + value + ", " + __np_policyOf(fields, 2, opts) + extra;
}

// One rule line -> Quantumult X filter line, or null (skip reason recorded).
function __np_convertRule(line, opts, notes, clashStyle) {
  var fields, type, qxType, value, m, c = line.charAt(0);

  if (c !== "|" && c !== "@" && line.indexOf(",") > 0) return __np_convertTypedRule(line, opts, notes);

  // hosts file: "0.0.0.0 ads.example.com"
  m = /^(0\.0\.0\.0|127\.0\.0\.1|::1?|::)\s+(\S+)/.exec(line);
  if (m) {
    if (/^(localhost|local|broadcasthost|ip6-\w+|0\.0\.0\.0)$/i.test(m[2])) return null;
    if (!__np_isDomain(m[2])) { __np_skip(notes, "unrecognized"); return null; }
    return "host, " + m[2].toLowerCase() + ", " + (opts.policy || "reject");
  }

  // simple filter list: "||ads.example.com^"
  m = /^\|\|([a-z0-9_.-]+)\^$/i.exec(line);
  if (m) {
    if (!__np_isDomain(m[1])) { __np_skip(notes, "unrecognized"); return null; }
    return "host-suffix, " + m[1].toLowerCase() + ", " + (opts.policy || "reject");
  }
  if (/^(@@|\|)/.test(line)) {
    __np_skip(notes, "filter-list syntax");
    return null;
  }

  if (__np_isIPv4(line)) {
    return "ip-cidr, " + (line.indexOf("/") < 0 ? line + "/32" : line) + ", " + (opts.policy || "proxy");
  }
  if (__np_isIPv6(line)) {
    return "ip6-cidr, " + (line.indexOf("/") < 0 ? line + "/128" : line) + ", " + (opts.policy || "proxy");
  }

  var d = __np_domainEntry(line, clashStyle);
  if (d) return d[0] + ", " + d[1] + ", " + (opts.policy || "proxy");

  __np_skip(notes, "unrecognized");
  return null;
}

function __np_ruleKey(line) {
  var f = line.split(", ");
  return f[0] + "," + f[1];
}

// Rule lines (plain text or Clash YAML) -> filter lines
function __np_convertRules(lines, opts, notes) {
  var out = [], seen = {}, yaml = false, inPayload = false, i, line, r, k;
  for (i = 0; i < lines.length; i++) {
    if (lines[i].charAt(0) === "p" && /^payload\s*:\s*$/.test(lines[i])) { yaml = true; break; }
  }
  for (i = 0; i < lines.length; i++) {
    line = __np_trim(lines[i]);
    if (yaml) {
      if (/^payload\s*:\s*$/.test(line)) { inPayload = true; continue; }
      if (/^[A-Za-z_][\w-]*\s*:/.test(lines[i])) { inPayload = false; continue; }
      if (!inPayload || line.indexOf("- ") !== 0 && line !== "-") continue;
      line = __np_trim(line.slice(1));
      line = line.replace(/\s+#.*$/, "");
      if (/^(['"]).*\1$/.test(line)) line = line.slice(1, -1);
      line = __np_trim(line);
    } else {
      if (/^\[.*\]$/.test(line)) continue;
    }
    if (__np_isComment(line)) continue;
    r = __np_convertRule(line, opts, notes, yaml);
    if (!r) continue;
    k = __np_ruleKey(r);
    if (seen[k]) continue;
    seen[k] = 1;
    out.push(r);
  }
  return out;
}

// ---------------------------------------------------------------- modules

function __np_moduleArguments(lines) {
  var args = {}, i, m, parts, j, eq;
  for (i = 0; i < lines.length; i++) {
    m = /^#!arguments\s*=\s*(.*)$/i.exec(__np_trim(lines[i]));
    if (!m) continue;
    parts = __np_splitCsv(m[1]);
    for (j = 0; j < parts.length; j++) {
      eq = parts[j].indexOf(":");
      if (eq > 0) args[__np_trim(parts[j].slice(0, eq))] = __np_trim(parts[j].slice(eq + 1)).replace(/^(['"])(.*)\1$/, "$2");
    }
  }
  return args;
}

function __np_applyArguments(text, args) {
  return text.replace(/\{\{\{\s*([^}\s]+)\s*\}\}\}/g, function (all, name) {
    return Object.prototype.hasOwnProperty.call(args, name) ? args[name] : all;
  });
}

function __np_rejectType(policy) {
  var p = policy.toLowerCase();
  if (p === "reject-tinygif" || p === "reject-img") return "reject-img";
  if (p === "reject-dict") return "reject-dict";
  if (p === "reject-array") return "reject-array";
  if (p === "reject-200") return "reject-200";
  if (/^reject/.test(p)) return "reject";
  return "";
}

function __np_isUrl(s) {
  return /^https?:\/\/\S+$/i.test(s);
}

function __np_urlRewrite(line, notes) {
  var w = __np_splitWords(line), type;
  if (w.length < 2) { __np_skip(notes, "URL Rewrite (malformed)"); return null; }
  type = (w[2] || "header").toLowerCase();
  if (type === "302" || type === "307") {
    if (!w[1] || w[1] === "-") { __np_skip(notes, "URL Rewrite (malformed)"); return null; }
    return w[0] + " url " + type + " " + w[1];
  }
  if (type === "reject") return w[0] + " url reject";
  __np_skip(notes, "URL Rewrite " + type);
  return null;
}

function __np_mapLocal(line, notes) {
  var sp = line.search(/\s/), pattern, kv, dataType, data, status;
  if (sp < 0) { __np_skip(notes, "Map Local (malformed)"); return null; }
  pattern = line.slice(0, sp);
  kv = __np_keyValues(__np_trim(line.slice(sp)).replace(/\s+(?=[A-Za-z][A-Za-z0-9-]*=)/g, ", "));
  dataType = (kv["data-type"] || "text").toLowerCase();
  data = kv.data === undefined ? "" : __np_trim(kv.data);
  status = kv["status-code"] || "200";
  if (dataType === "tiny-gif") return pattern + " url reject-img";
  if (status === "200" && dataType === "json" && data === "{}") return pattern + " url reject-dict";
  if (status === "200" && dataType === "json" && data === "[]") return pattern + " url reject-array";
  if (status === "200" && data === "" && !kv.header) return pattern + " url reject-200";
  if (status === "404" && data === "" && !kv.header) return pattern + " url reject";
  __np_skip(notes, "Map Local with custom data");
  return null;
}

function __np_script(line, notes) {
  var eq = line.indexOf("="), kv, type, body, kind, path, m;
  // older form: "http-response ^https://a\.com requires-body=1,script-path=..."
  m = /^(http-request|http-response)\s+(\S+)\s+(.*)$/i.exec(line);
  if (m) {
    kv = __np_keyValues(m[3]);
    kv.type = m[1];
    kv.pattern = m[2];
  } else {
    if (eq < 0) { __np_skip(notes, "Script (malformed)"); return null; }
    kv = __np_keyValues(line.slice(eq + 1));
  }
  type = (kv.type || "").toLowerCase();
  if (type !== "http-request" && type !== "http-response") {
    __np_skip(notes, "Script type=" + (type || "?"));
    return null;
  }
  path = kv["script-path"] || "";
  if (!kv.pattern || !__np_isUrl(path)) { __np_skip(notes, "Script (no pattern or remote script-path)"); return null; }
  if (/^(1|true)$/i.test(kv["binary-body-mode"] || "")) { __np_skip(notes, "Script binary-body-mode"); return null; }
  body = /^(1|true)$/i.test(kv["requires-body"] || "");
  kind = "script-" + (type === "http-request" ? "request" : "response") + (body ? "-body" : "-header");
  if (kv.argument) __np_warn(notes, "script argument not passed");
  return kv.pattern + " url " + kind + " " + path;
}

function __np_bodyRewrite(line, notes) {
  var w = __np_splitWords(line), type, out = [], i, side;
  type = (w[0] || "").toLowerCase();
  if (!/^http-(request|response)(-jq)?$/.test(type) || w.length < 3) {
    __np_skip(notes, "Body Rewrite (malformed)");
    return out;
  }
  side = type.indexOf("request") > 0 ? "request" : "response";
  if (/-jq$/.test(type)) {
    out.push(w[1] + " url jsonjq-" + side + "-body '" + w.slice(2).join(" ").replace(/'/g, "\\'") + "'");
    return out;
  }
  if ((w.length - 2) % 2 !== 0) { __np_skip(notes, "Body Rewrite (malformed)"); return out; }
  for (i = 2; i < w.length; i += 2) {
    if (/\s/.test(w[i]) || /\s/.test(w[i + 1]) || w[i] === "" || w[i + 1] === "") {
      __np_skip(notes, "Body Rewrite with spaces or empty text");
      continue;
    }
    out.push(w[1] + " url " + side + "-body " + w[i] + " " + side + "-body " + w[i + 1]);
  }
  return out;
}

function __np_addHosts(hosts, seen, list) {
  var parts = list.replace(/%(APPEND|INSERT)%/gi, "").split(","), i, h;
  for (i = 0; i < parts.length; i++) {
    h = __np_trim(parts[i]).toLowerCase();
    if (h && !seen[h]) { seen[h] = 1; hosts.push(h); }
  }
}

// Surge module / Quantumult X rewrite snippet -> {rewrites, hosts, rules}
function __np_convertModule(lines, opts, notes) {
  var res = { rewrites: [], hosts: [], rules: [] };
  var seen = {}, hostSeen = {}, section = "", args = __np_moduleArguments(lines);
  var i, line, m, r, low, parts, f, rej;

  function add(x) {
    if (x && !seen[x]) { seen[x] = 1; res.rewrites.push(x); }
  }

  for (i = 0; i < lines.length; i++) {
    line = __np_trim(__np_applyArguments(lines[i], args));
    m = /^\[(.+)\]$/.exec(line);
    if (m) {
      section = m[1].toLowerCase();
      if (!__np_MODULE_SECTIONS[section] && section !== "general" && section !== "host") {
        __np_skip(notes, "[" + m[1] + "] section");
      }
      continue;
    }
    if (__np_isComment(line)) continue;

    if (section === "") {
      // Quantumult X rewrite snippet: pass through.
      m = /^hostname\s*=\s*(.*)$/i.exec(line);
      if (m) { __np_addHosts(res.hosts, hostSeen, m[1]); continue; }
      if (/\s(url|url-and-header)\s/.test(" " + line + " ")) { add(line); continue; }
      __np_skip(notes, "unrecognized");
      continue;
    }
    if (section === "mitm") {
      m = /^hostname\s*=\s*(.*)$/i.exec(line);
      if (m) __np_addHosts(res.hosts, hostSeen, m[1]);
      else __np_skip(notes, "MITM " + line.split("=")[0]);
    } else if (section === "url rewrite") {
      add(__np_urlRewrite(line, notes));
    } else if (section === "map local") {
      add(__np_mapLocal(line, notes));
    } else if (section === "script") {
      add(__np_script(line, notes));
    } else if (section === "body rewrite") {
      parts = __np_bodyRewrite(line, notes);
      for (r = 0; r < parts.length; r++) add(parts[r]);
    } else if (section === "rule") {
      f = __np_splitCsv(line);
      low = f[0].toLowerCase();
      if (low === "url-regex") {
        rej = __np_rejectType(f[2] || "");
        if (rej && f[1]) add(f[1] + " url " + rej);
        else __np_skip(notes, "URL-REGEX without REJECT");
      } else {
        res.rules.push(line);
      }
    }
  }
  return res;
}

// ---------------------------------------------------------------- options

function __np_keywordFilter(lines, include, exclude) {
  var out = [], i, low, j, keep;
  if (!include.length && !exclude.length) return lines;
  for (i = 0; i < lines.length; i++) {
    low = lines[i].toLowerCase();
    keep = include.length === 0;
    for (j = 0; j < include.length && !keep; j++) if (low.indexOf(include[j].toLowerCase()) >= 0) keep = true;
    for (j = 0; j < exclude.length && keep; j++) if (low.indexOf(exclude[j].toLowerCase()) >= 0) keep = false;
    if (keep) out.push(lines[i]);
  }
  return out;
}

function __np_replacers(raw, notes) {
  var out = [], parts = raw ? raw.split("+") : [], i, p, at;
  for (i = 0; i < parts.length; i++) {
    if (!parts[i]) continue;
    at = parts[i].indexOf("@");
    if (at <= 0) { __np_warn(notes, "replace option ignored (use REGEX@TEXT)"); continue; }
    try {
      p = new RegExp(__np_decode(parts[i].slice(0, at)), "g");
      out.push([p, __np_decode(parts[i].slice(at + 1))]);
    } catch (e) {
      __np_warn(notes, "invalid replace regex ignored");
    }
  }
  return out;
}

function __np_applyReplace(lines, reps) {
  var out = [], i, j, s;
  if (!reps.length) return lines;
  for (i = 0; i < lines.length; i++) {
    s = lines[i];
    for (j = 0; j < reps.length; j++) s = s.replace(reps[j][0], reps[j][1]);
    s = __np_trim(s);
    if (s) out.push(s);
  }
  return out;
}

// ---------------------------------------------------------------- main

function __np_isModule(lines) {
  var i, l, c;
  for (i = 0; i < lines.length; i++) {
    l = lines[i];
    c = l.charAt(0);
    if (c === "#" || c === "[" || c === "h" || c === "H" || c === " " || c === "\t") l = __np_trim(l);
    c = l.charAt(0);
    if (c === "#" && /^#!(name|desc|arguments|system|category)\s*=/i.test(l)) return true;
    if (c === "[" && /^\[(url rewrite|script|mitm|map local|rule|body rewrite|header rewrite|general|host)\]$/i.test(l)) return true;
    if ((c === "h" || c === "H") && /^hostname\s*=/i.test(l)) return true;
    if (l.indexOf(" url") > 0 && /^\S+\s+url(-and-header)?\s+\S/.test(l) && !/,/.test(l.split(/\s/)[0])) return true;
  }
  return false;
}

// Server (node) subscriptions are not converted: they are returned as they
// are, so Quantumult X parses them itself. Quantumult X allows only one
// resource parser, and this keeps node subscriptions working when it is set.
function __np_isServerList(lines) {
  var i, l, n = 0, hits = 0;
  for (i = 0; i < lines.length && n < 50; i++) {
    l = lines[i].trim();
    if (!l || l.charAt(0) === "#" || l.charAt(0) === ";") continue;
    n++;
    if (/^(ss|ssr|vmess|vless|trojan|hysteria2?|hy2|tuic|anytls|socks5?|https?):\/\/[^\s]*[@#?]/i.test(l) && !/^https?:/i.test(l)) hits++;
    else if (/^(shadowsocks|vmess|vless|trojan|http|socks5|anytls)\s*=\s*[^,\s]+:\d+\s*,/i.test(l)) hits++;
    else if (/^(proxies|proxy-groups)\s*:/.test(l)) return true;
  }
  if (n === 1 && /^[A-Za-z0-9+\/=_-]{40,}$/.test(lines.join("").replace(/\s/g, ""))) return true; // base64 subscription
  return hits > 0 && hits * 2 >= n;
}

// Pure conversion: returns {content} or {error}, plus notes and kind.
function __np_convert(content, link) {
  var opts = __np_options(link), notes = __np_newNotes();
  var text = String(content || "").replace(/^﻿/, "");
  var lines = text.split(/\r?\n/), kind, out, mod, reps, hosts, header;

  if (!__np_trim(text)) return { error: __np_NAME + ": the resource is empty", notes: notes, kind: "" };
  if (__np_isServerList(lines)) return { content: content, notes: notes, kind: "server", passThrough: true };

  kind = opts.output === "filter" || opts.output === "rewrite" ? opts.output : (__np_isModule(lines) ? "rewrite" : "filter");
  reps = __np_replacers(opts.replace, notes);

  if (kind === "rewrite") {
    mod = __np_convertModule(lines, opts, notes);
    if (mod.rules.length) {
      notes.skipped["rules in a rewrite resource (use output=filter)"] = mod.rules.length;
      notes.skippedTotal += mod.rules.length;
    }
    out = __np_applyReplace(__np_keywordFilter(mod.rewrites, opts.include, opts.exclude), reps);
    hosts = __np_keywordFilter(mod.hosts, opts.hostInclude, opts.hostExclude);
    notes.converted = out.length;
    notes.hosts = hosts.length;
    if (hosts.length) out.push("hostname = " + hosts.join(", "));
  } else {
    if (__np_isModule(lines)) {
      mod = __np_convertModule(lines, opts, __np_newNotes());
      lines = mod.rules;
    }
    out = __np_applyReplace(__np_keywordFilter(__np_convertRules(lines, opts, notes), opts.include, opts.exclude), reps);
    notes.converted = out.length;
  }

  if (!out.length) {
    return { error: __np_NAME + ": nothing to convert. " + __np_summary(notes, kind), notes: notes, kind: kind };
  }
  header = "# " + __np_NAME + " " + __np_VERSION + " - " + kind + ", " + notes.converted + " line(s)";
  return { content: header + "\n" + out.join("\n") + "\n", notes: notes, kind: kind };
}

function __np_main() {
  var r, link, name, want;
  if (typeof $resource === "undefined" || !$resource) {
    return { error: __np_NAME + ": no resource" };
  }
  link = String($resource.link || "");
  try {
    r = __np_convert($resource.content, link);
  } catch (e) {
    return { error: __np_NAME + " " + __np_VERSION + " failed: " + (e && e.message ? e.message : e) };
  }
  want = __np_options(link).notify;
  if (typeof $notify === "function" && !r.passThrough && want !== "0" && (want === "1" || r.notes.skippedTotal > 0 || r.error)) {
    name = link.split("#")[0].split("?")[0].split("/").pop() || "resource";
    $notify(__np_NAME, __np_decode(name), r.error ? r.error : __np_summary(r.notes, r.kind));
  }
  return r.error ? { error: r.error } : { content: r.content };
}

// ---------------------------------------------------------------- option editor
// Quantumult X 1.5.6 (build 918)+ shows these options as a form. The three
// functions are run on their own, so they must not use anything above.

var $parser = typeof $parser === "object" && $parser ? $parser : {};

$parser.hashSchema = function () {
  return {
    version: 1,
    sections: [
      {
        type: "group",
        title: "Rules",
        description: "Keywords are case-insensitive and match the converted line.",
        items: [
          { type: "text", key: "policy", label: "Policy",
            description: "Policy for every rule. Default: the rule's own policy, otherwise proxy.",
            placeholder: "proxy" },
          { type: "tags", key: "include", label: "Include",
            description: "Keep only lines containing any of these keywords.", placeholder: "keyword" },
          { type: "tags", key: "exclude", label: "Exclude",
            description: "Drop lines containing any of these keywords.", placeholder: "keyword" },
          { type: "text", key: "replace", label: "Replace",
            description: "REGEX@TEXT, several joined with +. Write a literal + as %2B and @ as %40.",
            placeholder: "pattern@text" }
        ]
      },
      {
        type: "group",
        title: "Rewrite",
        items: [
          { type: "tags", key: "host-include", label: "Keep hostnames",
            description: "Keep only MITM hostnames containing any of these keywords.", placeholder: "keyword" },
          { type: "tags", key: "host-exclude", label: "Drop hostnames",
            description: "Drop MITM hostnames containing any of these keywords.", placeholder: "keyword" }
        ]
      },
      {
        type: "group",
        title: "Other",
        items: [
          { type: "select", key: "output", label: "Output",
            options: [
              { label: "Automatic", value: "" },
              { label: "Filter", value: "filter" },
              { label: "Rewrite", value: "rewrite" }
            ] },
          { type: "select", key: "notify", label: "Notifications",
            options: [
              { label: "When something is skipped", value: "" },
              { label: "Always", value: "1" },
              { label: "Never", value: "0" }
            ] }
        ]
      }
    ]
  };
};

$parser.hashToUI = function (hash) {
  function dec(s) { try { return decodeURIComponent(s); } catch (e) { return s; } }
  var schema = $parser.hashSchema(), items = {}, values = {}, unknown = [], sections = [];
  var pairs = String(hash || "").split("&"), i, eq, k, v;
  if (!hash) return { version: 1, sections: [], unknown: "" };
  for (i = 0; i < schema.sections.length; i++) {
    for (k = 0; k < schema.sections[i].items.length; k++) items[schema.sections[i].items[k].key] = 1;
  }
  for (i = 0; i < pairs.length; i++) {
    if (!pairs[i]) continue;
    eq = pairs[i].indexOf("=");
    k = eq < 0 ? pairs[i] : pairs[i].slice(0, eq);
    v = eq < 0 ? "" : pairs[i].slice(eq + 1);
    if (items[k.toLowerCase()]) values[k.toLowerCase()] = v; else unknown.push(pairs[i]);
  }
  for (i = 0; i < schema.sections.length; i++) {
    var g = schema.sections[i], picked = [];
    for (k = 0; k < g.items.length; k++) {
      var it = g.items[k];
      if (!Object.prototype.hasOwnProperty.call(values, it.key)) continue;
      var c = JSON.parse(JSON.stringify(it)), raw = values[it.key];
      if (it.type === "tags") {
        c.value = [];
        var parts = raw.split("+");
        for (var p = 0; p < parts.length; p++) if (parts[p]) c.value.push(dec(parts[p]));
      } else if (it.type === "text" && it.key === "replace") {
        c.value = raw;
      } else {
        c.value = dec(raw);
      }
      picked.push(c);
    }
    if (picked.length) sections.push({ type: "group", title: g.title, description: g.description, items: picked });
  }
  return { version: 1, sections: sections, unknown: unknown.join("&") };
};

$parser.uiToHash = function (values) {
  function enc(s) { return encodeURIComponent(String(s)); }
  var order = ["policy", "include", "exclude", "replace", "host-include", "host-exclude", "output", "notify"];
  var parts = [], i, k, v, list, j;
  values = values || {};
  for (i = 0; i < order.length; i++) {
    k = order[i];
    if (!Object.prototype.hasOwnProperty.call(values, k)) continue;
    v = values[k];
    if (v === null || v === undefined || v === "") continue;
    if (Object.prototype.toString.call(v) === "[object Array]") {
      list = [];
      for (j = 0; j < v.length; j++) if (String(v[j]) !== "") list.push(enc(v[j]));
      if (list.length) parts.push(k + "=" + list.join("+"));
    } else if (k === "replace") {
      // keep "+" (pair separator) and "@"; only escape what breaks the hash
      parts.push(k + "=" + String(v).replace(/&/g, "%26").replace(/#/g, "%23"));
    } else {
      parts.push(k + "=" + enc(v));
    }
  }
  if (values.__unknown) parts.push(values.__unknown);
  return parts.join("&");
};

var __np_result = __np_main();
if (typeof $done === "function") $done(__np_result);
