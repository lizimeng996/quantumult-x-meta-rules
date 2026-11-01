#!/usr/bin/env python3
"""Build Meta / Muse rule sets for Quantumult X and Loon from upstream sources.

Usage: python3 scripts/build.py   (writes QuantumultX/*.list and Loon/*.list)
Only the standard library is used.
"""
import ipaddress
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "quantumult-x-meta-rules-builder"}

V2FLY = "https://raw.githubusercontent.com/v2fly/domain-list-community/master/data/{}"
BM7 = "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/QuantumultX/{0}/{0}.list"
MUSE_SOURCES = {
    "juner922/muse-loon-rules": "https://raw.githubusercontent.com/juner922/muse-loon-rules/main/MuseAI.list",
    "Tartarus2014/Loon-Script": "https://raw.githubusercontent.com/Tartarus2014/Loon-Script/master/Rule/Other/Muse.lsr",
    "VPSDance/ai-proxy-rules": "https://raw.githubusercontent.com/VPSDance/ai-proxy-rules/main/rules/quantumult-x/meta-ai.list",
    "zhbcn/Rules": "https://raw.githubusercontent.com/zhbcn/Rules/main/Ruleset/QuantumultX/AI/Muse.list",
}
BM7_LISTS = ["Facebook", "Instagram", "Whatsapp", "Threads"]
# Meta-owned ASNs (RIPEstat holder names: FACEBOOK, FACEBOOK-OFFNET, FACEBOOK-CORP)
META_ASNS = [32934, 63293, 54115]

# Always present in Muse.list (Muse + Meta AI + Meta account login essentials).
MUSE_CORE = [
    ("HOST-SUFFIX", "muse.ai"), ("HOST-SUFFIX", "museai.com"),
    ("HOST-SUFFIX", "meta.ai"), ("HOST-SUFFIX", "meta.com"), ("HOST-SUFFIX", "atmeta.com"),
    ("HOST-SUFFIX", "metaaivm.com"), ("HOST-SUFFIX", "metaaiusercontent.com"),
    ("HOST-SUFFIX", "llama.com"), ("HOST-SUFFIX", "llamameta.net"),
    ("HOST-SUFFIX", "facebook.com"), ("HOST-SUFFIX", "facebook.net"), ("HOST-SUFFIX", "fb.com"),
    ("HOST-SUFFIX", "fbcdn.net"), ("HOST-SUFFIX", "fbsbx.com"),
    ("HOST-SUFFIX", "instagram.com"), ("HOST-SUFFIX", "cdninstagram.com"),
    ("HOST-SUFFIX", "whatsapp.com"), ("HOST-SUFFIX", "whatsapp.net"),
]
# Extra domains not (yet) in upstream lists.
EXTRA = [("HOST-SUFFIX", "fb.me"), ("HOST-SUFFIX", "metacdn.com")]

# Never emit these (too broad / not Meta-owned / fake-IP artefacts).
BAD_KEYWORDS = {"meta", "fb", "ig", "wa"}
DROP_SUFFIX = {"bintray.com"}  # JFrog, not Meta (blackmatrix7 Whatsapp list)
FAKE_NETS = [ipaddress.ip_network(n) for n in ("198.18.0.0/15", "10.0.0.0/8", "172.16.0.0/12",
                                               "192.168.0.0/16", "127.0.0.0/8", "100.64.0.0/10",
                                               "0.0.0.0/8", "fc00::/7", "fe80::/10", "::1/128")]
DOMAIN_RE = re.compile(r"^(?=.{1,253}$)([a-z0-9_]([a-z0-9_-]{0,61}[a-z0-9_])?\.)+[a-z0-9-]{2,63}$")
KEYWORD_RE = re.compile(r"^[a-z0-9._-]{3,}$")
TYPE_MAP = {"DOMAIN": "HOST", "DOMAIN-SUFFIX": "HOST-SUFFIX", "DOMAIN-KEYWORD": "HOST-KEYWORD",
            "HOST": "HOST", "HOST-SUFFIX": "HOST-SUFFIX", "HOST-KEYWORD": "HOST-KEYWORD",
            "IP-CIDR": "IP-CIDR", "IP6-CIDR": "IP6-CIDR", "IP-CIDR6": "IP6-CIDR", "IP-ASN": "IP-ASN"}


def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", "replace")


def parse_rules(text):
    """Parse Surge/Loon/QX style rule lines -> list of (TYPE, value)."""
    out = []
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip() if not line.lstrip().startswith("#") else ""
        if not line or line.startswith(("//", ";")):
            continue
        parts = [p.strip() for p in line.split(",")]
        t = TYPE_MAP.get(parts[0].upper())
        if t and len(parts) >= 2:
            out.append((t, parts[1].lower()))
    return out


def v2fly_domains(name, seen=None):
    """Resolve a v2fly domain-list-community entry (with include:) -> list of (TYPE, value)."""
    seen = seen if seen is not None else set()
    if name in seen:
        return []
    seen.add(name)
    out = []
    for raw in fetch(V2FLY.format(name)).splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        val = line.split()[0]  # drop @attrs
        if val.startswith("include:"):
            out += v2fly_domains(val[8:].split("@")[0], seen)
        elif val.startswith("full:"):
            out.append(("HOST", val[5:].lower()))
        elif val.startswith("keyword:"):
            out.append(("HOST-KEYWORD", val[8:].lower()))
        elif val.startswith("regexp:"):
            continue  # QX has no regex host rule
        else:
            out.append(("HOST-SUFFIX", val.removeprefix("domain:").lower()))
    return out


def asn_prefixes(asn):
    url = f"https://stat.ripe.net/data/announced-prefixes/data.json?resource=AS{asn}&sourceapp=quantumult-x-meta-rules"
    data = json.loads(fetch(url))["data"]["prefixes"]
    return [ipaddress.ip_network(p["prefix"], strict=False) for p in data]


def valid(rule):
    t, v = rule
    if t in ("HOST", "HOST-SUFFIX"):
        return bool(DOMAIN_RE.match(v)) and v not in DROP_SUFFIX and not any(v.endswith("." + d) for d in DROP_SUFFIX)
    if t == "HOST-KEYWORD":
        return bool(KEYWORD_RE.match(v)) and v not in BAD_KEYWORDS
    if t in ("IP-CIDR", "IP6-CIDR"):
        try:
            n = ipaddress.ip_network(v, strict=False)
        except ValueError:
            return False
        if (t == "IP-CIDR") != (n.version == 4):
            return False
        return not any(n.version == f.version and n.overlaps(f) for f in FAKE_NETS)
    if t == "IP-ASN":
        return v.isdigit()
    return False


def normalise(rules):
    """Dedupe; drop HOST/HOST-SUFFIX already covered by a parent HOST-SUFFIX."""
    rules = {r for r in rules if valid(r)}
    suffixes = {v for t, v in rules if t == "HOST-SUFFIX"}

    def covered(v, self_suffix):
        labels = v.split(".")
        start = 1 if self_suffix else 0
        return any(".".join(labels[i:]) in suffixes for i in range(start, len(labels) - 1))

    out = []
    for t, v in rules:
        if t == "HOST-SUFFIX" and covered(v, True):
            continue
        if t == "HOST" and covered(v, False):
            continue
        out.append((t, v))
    return out


ORDER = {"HOST": 0, "HOST-SUFFIX": 1, "HOST-KEYWORD": 2, "IP-CIDR": 3, "IP6-CIDR": 4, "IP-ASN": 5}


def sort_key(r):
    t, v = r
    if t in ("IP-CIDR", "IP6-CIDR"):
        n = ipaddress.ip_network(v)
        return (ORDER[t], n.network_address.packed, n.prefixlen)
    if t == "IP-ASN":
        return (ORDER[t], int(v))
    return (ORDER[t], v)


def header(name, desc, rules, sources):
    counts = {}
    for t, _ in rules:
        counts[t] = counts.get(t, 0) + 1
    lines = [f"# NAME: {name}", f"# DESC: {desc}",
             "# REPO: https://github.com/lizimeng996/quantumult-x-meta-rules",
             f"# UPDATED: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}"]
    lines += [f"# {t}: {counts[t]}" for t in sorted(counts, key=ORDER.get)]
    lines += [f"# TOTAL: {len(rules)}", "# SOURCES: " + ", ".join(sources), "#"]
    return lines


def write_qx(path, name, desc, rules, sources):
    body = [f"{t},{v},{name}" for t, v in rules]
    path.write_text("\n".join(header(name, desc, rules, sources) + body) + "\n")


LOON_MAP = {"HOST": "DOMAIN", "HOST-SUFFIX": "DOMAIN-SUFFIX", "HOST-KEYWORD": "DOMAIN-KEYWORD",
            "IP-CIDR": "IP-CIDR", "IP6-CIDR": "IP-CIDR6", "IP-ASN": "IP-ASN"}


def write_loon(path, name, desc, rules, sources):
    body = []
    for t, v in rules:
        s = f"{LOON_MAP[t]},{v}"
        if t in ("IP-CIDR", "IP6-CIDR", "IP-ASN"):
            s += ",no-resolve"
        body.append(s)
    path.write_text("\n".join(header(name, desc, rules, sources) + body) + "\n")


QX_LINE = re.compile(r"^(HOST|HOST-SUFFIX|HOST-KEYWORD|IP-CIDR|IP6-CIDR|IP-ASN),[^,\s]+,[A-Za-z0-9_-]+$")


def validate_qx_file(path):
    bad = []
    for i, line in enumerate(path.read_text().splitlines(), 1):
        if not line or line.startswith("#"):
            continue
        parts = line.split(",")
        if not QX_LINE.match(line) or not valid((parts[0], parts[1])):
            bad.append(f"{path.name}:{i}: {line}")
    return bad


def main():
    sources = []
    muse = list(MUSE_CORE)
    for name, url in MUSE_SOURCES.items():
        try:
            muse += parse_rules(fetch(url))
            sources.append(name)
        except Exception as e:  # upstream outage must not wipe our list
            print(f"WARN: {name}: {e}", file=sys.stderr)
    # v2fly "meta" top-level (non-include) entries are Meta AI / Muse / account domains
    meta_direct = [r for r in v2fly_domains("meta", seen={"facebook", "facebook-dev", "instagram",
                                                        "messenger", "oculus", "threads", "whatsapp"})]
    muse += meta_direct
    full = list(muse) + EXTRA + v2fly_domains("meta")
    sources.append("v2fly/domain-list-community")

    for n in BM7_LISTS:
        try:
            full += [r for r in parse_rules(fetch(BM7.format(n)))
                     if r[0] in ("HOST", "HOST-SUFFIX")]  # IPs come from RIPEstat, keywords dropped
        except Exception as e:
            print(f"WARN: blackmatrix7 {n}: {e}", file=sys.stderr)
    sources.append("blackmatrix7/ios_rule_script")

    nets = []
    for asn in META_ASNS:
        nets += asn_prefixes(asn)
        full.append(("IP-ASN", str(asn)))
    sources.append("RIPEstat (AS" + "/AS".join(map(str, META_ASNS)) + ")")
    for v in (4, 6):
        for n in ipaddress.collapse_addresses([x for x in nets if x.version == v]):
            full.append(("IP-CIDR" if v == 4 else "IP6-CIDR", str(n)))

    muse_rules = sorted(normalise(muse), key=sort_key)
    full_rules = sorted(normalise(full), key=sort_key)
    # sanity: never publish a suspiciously small list
    if len(full_rules) < 300 or len(muse_rules) < 15:
        sys.exit(f"ERROR: too few rules (full={len(full_rules)}, muse={len(muse_rules)})")

    (ROOT / "QuantumultX").mkdir(exist_ok=True)
    (ROOT / "Loon").mkdir(exist_ok=True)
    write_qx(ROOT / "QuantumultX/Meta.list", "Meta", "Muse + Meta AI + all Meta services/accounts + Meta IP ranges", full_rules, sources)
    write_qx(ROOT / "QuantumultX/Muse.list", "Muse", "Muse + Meta AI + Meta account login essentials", muse_rules, sources)
    write_loon(ROOT / "Loon/Meta.list", "Meta", "Muse + Meta AI + all Meta services/accounts + Meta IP ranges", full_rules, sources)
    write_loon(ROOT / "Loon/Muse.list", "Muse", "Muse + Meta AI + Meta account login essentials", muse_rules, sources)

    bad = validate_qx_file(ROOT / "QuantumultX/Meta.list") + validate_qx_file(ROOT / "QuantumultX/Muse.list")
    if bad:
        sys.exit("INVALID LINES:\n" + "\n".join(bad))
    print(f"OK: Meta.list={len(full_rules)} Muse.list={len(muse_rules)}")


if __name__ == "__main__":
    main()
