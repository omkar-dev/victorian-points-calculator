#!/usr/bin/env python3
"""Generate the search layer of the site from data/*.json.

- One static page per skilled occupation at occupations/<ANZSCO>/ (cut-off
  history, EOIs, ceiling, visas, related occupations)
- Pre-rendered tables inside the data pages, so the numbers are in the HTML
  before JavaScript runs (the scripts replace them when they load)
- Structured data, Twitter cards and per-page preview images for every page
- 404.html, apple-touch-icon.png and site.webmanifest

Run through scripts/layout.py, which calls this first and then stamps the
shared header and footer into every page, generated ones included.
"""
import datetime
import hashlib
import html
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = "https://vptpoints.com/"
SKILLED = {"189", "190", "491"}
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]


def esc(s):
    return html.escape(str(s), quote=True)


def num(n, hidden="fewer than 20"):
    return hidden if n is None else f"{n:,}"


def long_date(iso):
    if not iso:
        return "–"
    y, m, *d = iso.split("-")
    return (f"{int(d[0])} " if d else "") + f"{MONTHS[int(m) - 1]} {y}"


def short_date(iso):
    return long_date(iso).replace("January", "Jan").replace("February", "Feb").replace("March", "Mar") \
        .replace("April", "Apr").replace("August", "Aug").replace("September", "Sep").replace("October", "Oct") \
        .replace("November", "Nov").replace("December", "Dec").replace("June", "Jun").replace("July", "Jul")


def load(name):
    return json.loads((ROOT / "data" / f"{name}.json").read_text())


def table(cols, rows, cls="data"):
    """cols: [(label, is_num)], rows: [[cell_html, ...]]."""
    head = "".join(f'<th scope="col" class="{"num" if n else ""}">{esc(l)}</th>' for l, n in cols)
    body = "".join("<tr>" + "".join(f'<td class="{"num" if cols[i][1] else ""}">{c}</td>' for i, c in enumerate(r)) + "</tr>"
                   for r in rows)
    return f'<table class="{cls}"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'


def stamp(text, name, block):
    pat = re.compile(rf"<!-- {re.escape(name)} -->.*?<!-- /{re.escape(name)} -->", re.S)
    if not pat.search(text):
        raise SystemExit(f"missing <!-- {name} --> markers")
    return pat.sub(lambda _: f"<!-- {name} -->{block}<!-- /{name} -->", text)


# ── Data ────────────────────────────────────────────────────────────────

class Data:
    def __init__(self):
        self.occ = load("occupations")
        self.rounds = load("rounds")
        self.eoi = load("eoi")
        self.ceil = load("ceilings")
        self.states = load("states")
        self.grants = load("grants")
        self.by = {}
        for o in self.occ["occupations"]:
            if not o.get("anzsco"):
                continue
            if o["anzsco"] in self.by:
                self.by[o["anzsco"]]["aka"].append(o["name"])
            else:
                self.by[o["anzsco"]] = dict(o, aka=[])
        self.eoi_by = {e["anzsco"]: e for e in self.eoi["byOccupation"] if e.get("anzsco")}
        self.hist = {}
        for h in self.rounds["byOccupation"]:
            if h.get("anzsco"):
                self.hist.setdefault(h["anzsco"], []).append(h)
        for v in self.hist.values():
            v.sort(key=lambda h: h["roundDate"])
        yr = (self.ceil.get("years") or [None])[0]
        self.ceil_fy = yr["fy"] if yr else None
        self.ceil_by = {c["unitGroup"]: c for c in (yr["rows"] if yr else [])}
        self.latest_round = max(r["date"] for r in self.rounds["rounds"])
        # Every code another page links to gets a page.
        codes = {c for c, o in self.by.items() if SKILLED & set(o["visas"])}
        codes |= set(self.hist) | set(self.eoi_by)
        self.pages = sorted(codes)
        for c in self.pages:
            if c not in self.by:  # in the EOI data but not on the occupation list
                e = self.eoi_by.get(c, {})
                self.by[c] = {"anzsco": c, "name": e.get("occupation", c), "lists": [], "visas": [], "assessor": None,
                              "skillLevel": None, "unitGroup": c[:4], "caveats": False, "aka": []}

    def cutoff(self, code):
        h = [x for x in self.hist.get(code, []) if x["subclass"] == "189" and (x["minPoints"] or 0) >= 65]
        return h[-1] if h else None


# ── Occupation pages ───────────────────────────────────────────────────

def occupation_page(D, code, updated):
    o = D.by[code]
    name = o["name"]
    e = D.eoi_by.get(code, {})
    c = D.ceil_by.get(o.get("unitGroup") or code[:4])
    hist = [h for h in D.hist.get(code, []) if (h["minPoints"] or 0) >= 65]
    h189 = [h for h in hist if h["subclass"] == "189"]
    cut = D.cutoff(code)
    visas = o["visas"]
    on189 = "189" in visas
    lists = o["lists"]

    # Plain sentences built only from the data.
    facts = []
    if lists:
        facts.append(f"{esc(name)} (ANZSCO {code}) is on the {' and '.join(esc(l) for l in lists)} "
                     f"{'list' if len(lists) == 1 else 'lists'}" +
                     (f" and can be used for subclass {', '.join(v for v in visas if v in SKILLED)} skilled visas." if SKILLED & set(visas) else "."))
    if o.get("assessor"):
        facts.append(f"Skills are assessed by {esc(o['assessor'])}.")
    if cut:
        s = f"In the {long_date(cut['roundDate'])} SkillSelect round, the lowest score invited for {esc(name)} was <strong>{cut['minPoints']} points</strong>."
        if cut["roundDate"] != D.latest_round:
            s += f" It wasn’t among the occupations invited in the latest round on {long_date(D.latest_round)}."
        facts.append(s)
    elif on189:
        facts.append(f"No subclass 189 invitations have gone to {esc(name)} in the rounds published since July 2023.")
    elif SKILLED & set(visas):
        facts.append(f"{esc(name)} isn’t on the MLTSSL, so subclass 189 isn’t available. State or territory nomination (subclass 190 or 491) may be.")
    if e:
        facts.append(f"As at {long_date(D.eoi['asAt'])}, {num(e.get('submitted189'))} EOIs were waiting for subclass 189, "
                     f"{num(e.get('submitted190'))} for 190 and {num(e.get('submitted491'))} for 491.")
    if c:
        left = f"{c['remaining189']:,}" if c.get("remaining189") is not None else ("none" if c.get("remaining189Raw") == "-" else esc(c.get("remaining189Raw") or "–"))
        facts.append(f"It belongs to the {esc(c['name'])} group ({c['unitGroup']}), with a {D.ceil_fy} occupation ceiling of "
                     f"{c['ceiling']:,} places and {left} left for subclass 189 after 2024–25 grants.")

    title = f"{name} ({code}): 189 Cut-off, EOIs and Visa Options"
    if len(title) > 62:
        title = f"{name} ({code}): 189 Cut-off and EOIs"
    desc_bits = []
    if cut:
        desc_bits.append(f"Latest 189 cut-off for {name}: {cut['minPoints']} points ({short_date(cut['roundDate'])}).")
    elif on189:
        desc_bits.append(f"{name}: no 189 invitations since July 2023.")
    else:
        desc_bits.append(f"{name} (ANZSCO {code}): visa options and EOIs.")
    if e.get("submitted189") is not None:
        desc_bits.append(f"{e['submitted189']:,} EOIs waiting for 189.")
    if SKILLED & set(visas):
        desc_bits.append("Visas: " + ", ".join(v for v in visas if v in SKILLED) + ".")
    if o.get("assessor"):
        desc_bits.append(f"Assessor: {o['assessor']}.")
    desc = ""
    for b in desc_bits:
        if len(desc) + len(b) + 1 > 158:
            break
        desc = (desc + " " + b).strip()

    hist_rows = [[short_date(h["roundDate"]), "189" if h["subclass"] == "189" else "491 family", str(h["minPoints"])]
                 for h in reversed(hist)]
    eoi_rows = [[f"Subclass {k}", num(e.get(f"submitted{k}"), "under 20")] for k in ("189", "190", "491")] if e else []

    group = sorted((x for x in D.pages if x != code and x[:4] == code[:4]), key=lambda x: D.by[x]["name"])
    if len(group) < 3:
        group += sorted((x for x in D.pages if x != code and x[:3] == code[:3] and x not in group), key=lambda x: D.by[x]["name"])
    related = group[:12]

    faqs = []
    if cut:
        faqs.append((f"What is the 189 cut-off for {name}?",
                     f"The lowest score invited for {name} (ANZSCO {code}) was {cut['minPoints']} points in the {long_date(cut['roundDate'])} SkillSelect round."))
    elif on189:
        faqs.append((f"What is the 189 cut-off for {name}?",
                     f"{name} hasn’t been invited in any subclass 189 round published since July 2023, so there is no recent cut-off."))
    if e.get("submitted189") is not None:
        faqs.append((f"How many EOIs are there for {name}?",
                     f"As at {long_date(D.eoi['asAt'])} there were {e['submitted189']:,} EOIs for subclass 189, "
                     f"{num(e.get('submitted190'))} for 190 and {num(e.get('submitted491'))} for 491. EOIs are counted, not people."))
    if o.get("assessor"):
        faqs.append((f"Who assesses {name}?", f"{o['assessor']} assesses skills for {name} (ANZSCO {code})."))

    url = f"{SITE}occupations/{code}/"
    graph = [
        {"@type": "WebPage", "@id": url, "url": url, "name": title, "description": desc, "dateModified": updated,
         "inLanguage": "en-AU", "isPartOf": {"@id": SITE + "#website"}, "breadcrumb": {"@id": url + "#breadcrumb"},
         "about": {"@id": url + "#occupation"}},
        {"@type": "BreadcrumbList", "@id": url + "#breadcrumb", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE},
            {"@type": "ListItem", "position": 2, "name": "Occupations", "item": SITE + "occupations/"},
            {"@type": "ListItem", "position": 3, "name": name, "item": url}]},
        {"@type": "Occupation", "@id": url + "#occupation", "name": name,
         "occupationalCategory": {"@type": "CategoryCode", "codeValue": code, "inCodeSet": "ANZSCO"},
         "description": re.sub("<[^>]+>", "", " ".join(facts[:2]))},
    ]
    if faqs:
        graph.append({"@type": "FAQPage", "@id": url + "#faq", "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faqs]})
    ld = json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False)

    chart = ""
    if len(h189) >= 2:
        data = json.dumps({"labels": [short_date(h["roundDate"][:7]) for h in h189],
                           "tips": [short_date(h["roundDate"]) for h in h189],
                           "values": [h["minPoints"] for h in h189]})
        chart = f"""<div class="panel"><h3 class="sub">189 cut-off by round</h3><div id="hist"></div></div>
<script>window.OCC_HIST = {data};</script>"""

    pills = "".join(f'<span class="pill">{esc(l)}</span>' for l in lists) + \
        "".join(f'<span class="pill sun">Subclass {esc(v)}</span>' for v in visas if v in SKILLED)
    stats = [
        ("Latest 189 cut-off", f"{cut['minPoints']} pts" if cut else ("Not invited" if on189 else "Not on 189"),
         short_date(cut["roundDate"]) + " round" if cut else ("Since July 2023" if on189 else "Not on the MLTSSL")),
        ("EOIs waiting · 189", num(e.get("submitted189"), "under 20") if e else "–",
         f"190: {num(e.get('submitted190'), 'under 20')} · 491: {num(e.get('submitted491'), 'under 20')}" if e else "No EOI data"),
        (f"Ceiling {D.ceil_fy or ''}".strip(), f"{c['ceiling']:,}" if c else "–", esc(c["name"]) if c else "No ceiling listed"),
    ]
    stat_html = "".join(f'<div class="stat"><span class="lbl">{l}</span><span class="val">{v}</span><span class="sub2">{s}</span></div>'
                        for l, v, s in stats)
    rel_html = "".join(f'<a class="tool" href="../{x}/"><h3>{esc(D.by[x]["name"])}</h3><p class="code">{x}</p></a>' for x in related)
    faq_html = "".join(f"<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>" for q, a in faqs)

    return f"""<!DOCTYPE html>
<html lang="en-AU">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} | VPT Points</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{url}">
<meta name="theme-color" content="#1d5a44" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#0e1613" media="(prefers-color-scheme: dark)">
<meta name="color-scheme" content="light dark">
<meta property="og:type" content="article">
<meta property="og:site_name" content="VPT Points">
<meta property="og:locale" content="en_AU">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{SITE}assets/og/occupations.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(title)}">
<meta name="twitter:description" content="{esc(desc)}">
<meta name="twitter:image" content="{SITE}assets/og/occupations.png">
<link rel="icon" href="../../favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="../../apple-touch-icon.png">
<link rel="manifest" href="../../site.webmanifest">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="preload" as="style" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700;12..96,800&family=Instrument+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@500&display=swap" onload="this.onload=null;this.rel='stylesheet'">
<noscript><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700;12..96,800&family=Instrument+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@500&display=swap"></noscript>
<link rel="stylesheet" href="../../assets/site.css">
<script type="application/ld+json">{ld}</script>
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<!-- header -->
<!-- /header -->

<main id="main">
  <div class="wrap">
    <nav class="crumbs" aria-label="Breadcrumb"><a href="../../">Home</a> › <a href="../">Occupations</a> › <span aria-current="page">{esc(name)}</span></nav>
    <div class="page-hero">
      <span class="kicker"><i></i>ANZSCO {code}</span>
      <h1>{esc(name)}</h1>
      <div>{pills}</div>
    </div>

    <section class="block" aria-label="Key numbers"><div class="stats">{stat_html}</div></section>

    <section class="block" aria-labelledby="sum-h">
      <h2 id="sum-h">Summary</h2>
      <div class="prose">{"".join(f"<p>{f}</p>" for f in facts)}</div>
      <div class="actions" style="margin-top:12px">
        {f'<a class="btn primary" style="text-decoration:none" href="../../189-chances/?occ={code}">Check 189 chances</a>' if on189 else ''}
        <a class="btn" style="text-decoration:none" href="../../compare/?codes={code}">Compare with others</a>
        <a class="btn" style="text-decoration:none" href="../../">Victorian Points Test</a>
      </div>
    </section>

    <section class="block" aria-labelledby="hist-h">
      <h2 id="hist-h">Cut-off history</h2>
      {chart}
      {f'<div class="scroll" style="margin-top:16px">{table([("Round", False), ("Visa", False), ("Lowest score invited", True)], hist_rows)}</div>' if hist_rows else f'<p class="muted">No invitations for {esc(name)} in the subclass 189 or 491 family rounds published since July 2023.</p>'}
    </section>

    {f'<section class="block" aria-labelledby="eoi-h"><h2 id="eoi-h">EOIs waiting</h2><p class="muted small">Submitted EOIs as at {long_date(D.eoi["asAt"])}. EOIs are counted, not people. Home Affairs hides counts under 20.</p><div class="scroll" style="max-width:520px">{table([("Visa", False), ("EOIs", True)], eoi_rows)}</div></section>' if eoi_rows else ''}

    <section class="block" aria-labelledby="vic-h">
      <h2 id="vic-h">Applying in Victoria?</h2>
      <p class="prose">Victoria ranks subclass 190 and 491 Registrations of Interest with the Victorian Points Test, scored out of 950. Check Victoria’s current eligibility for {esc(name)} on Live in Melbourne before you apply, then <a href="../../">work out your VPT score</a>.</p>
    </section>

    {f'<section class="block" aria-labelledby="faq-h"><h2 id="faq-h">Questions</h2><div class="faq">{faq_html}</div></section>' if faqs else ''}

    {f'<section class="block" aria-labelledby="rel-h"><h2 id="rel-h">Related occupations</h2><div class="tools">{rel_html}</div></section>' if related else ''}

    <p class="source">Sources: Home Affairs skilled occupation list and invitation rounds, the SkillSelect EOI dashboard and occupation ceilings ({D.ceil_fy}, released under FOI). Checked {long_date(updated)}.</p>
<!-- footer -->
<!-- /footer -->
  </div>
</main>

<script src="../../assets/site.js"></script>
{'''<script>
(function () {
  var h = window.OCC_HIST, el = document.getElementById("hist");
  function draw() { VPT.chart(el, { title: "189 cut-off by round", type: "line", height: 220, yMin: 60, unit: "points", labels: h.labels, tipLabels: h.tips,
    series: [{ name: "Lowest score invited", color: "var(--leaf)", values: h.values }] }); }
  draw(); VPT.onResize(draw);
})();
</script>''' if chart else ''}
</body>
</html>
"""


# ── Pre-rendered blocks for the data pages ────────────────────────────

def occ_link(D, code, name=None, prefix="../"):
    if code and code in D.by and code in D.pages:
        return f'<a href="{prefix}occupations/{code}/">{esc(name or D.by[code]["name"])}</a>'
    return esc(name or code or "–")


def prerenders(D):
    r = D.rounds
    rounds = sorted(r["rounds"], key=lambda x: x["date"], reverse=True)
    latest = rounds[0]
    out = {}

    out["rounds-stats"] = "".join(
        f'<div class="stat"><span class="lbl">{l}</span><span class="val">{v}</span><span class="sub2">{s}</span></div>' for l, v, s in [
            ("Latest round", short_date(latest["date"]), f"Program year {latest['fy']}"),
            ("189 invitations", num((latest.get("invitations") or {}).get("189"), "–"), "In the latest round"),
            ("Lowest 189 cut-off", f"{(latest.get('minPoints') or {}).get('189')} pts", "Across all occupations"),
        ])
    out["rounds-table"] = table(
        [("Date", False), ("Year", False), ("189 invited", True), ("491F invited", True), ("189 min pts", True), ("Tie-break (189 / 491F)", False)],
        [[short_date(x["date"]), x["fy"], num((x.get("invitations") or {}).get("189"), "–"), num((x.get("invitations") or {}).get("491F"), "–"),
          num((x.get("minPoints") or {}).get("189"), "–"), esc(f"{(x.get('tieBreak') or {}).get('189') or '–'} / {(x.get('tieBreak') or {}).get('491F') or '–'}")] for x in rounds])
    last = [h for h in r["byOccupation"] if h["roundDate"] == latest["date"]]
    out["rounds-occ"] = table([("Occupation", False), ("ANZSCO", False), ("Visa", False), ("Min points", True)],
                              [[occ_link(D, h.get("anzsco"), h["occupation"]), f'<span class="code">{esc(h.get("anzsco") or "–")}</span>', esc(h["subclass"]), str(h["minPoints"])]
                               for h in sorted(last, key=lambda h: (-(h["minPoints"] or 0), h["occupation"]))])

    occs = sorted((D.by[c] for c in D.by), key=lambda o: o["name"])
    out["occ-list"] = table([("Occupation", False), ("ANZSCO", False), ("Lists", False), ("Assessor", False), ("189 cut-off", True), ("189 EOIs", True)],
                            [[occ_link(D, o["anzsco"], o["name"]), f'<span class="code">{o["anzsco"]}</span>', " ".join(f'<span class="pill">{esc(l)}</span>' for l in o["lists"]),
                              esc(o.get("assessor") or "–"), str(D.cutoff(o["anzsco"])["minPoints"]) if D.cutoff(o["anzsco"]) else "–",
                              num((D.eoi_by.get(o["anzsco"]) or {}).get("submitted189"), "–")] for o in occs])

    yr = (D.ceil.get("years") or [None])[0]
    if yr:
        out["ceilings"] = table([("Occupation group", False), ("Code", False), ("Tier", True), ("Ceiling", True), ("2024–25 grants", True), ("Left", True)],
                                [[esc(c["name"]), f'<a class="code" href="../occupations/?q={c["unitGroup"]}">{c["unitGroup"]}</a>', str(c.get("tier") or "–"), f'{c["ceiling"]:,}',
                                  num(c.get("grantsPY2425"), esc(c.get("grantsPY2425Raw") or "–")),
                                  num(c.get("remaining189"), "None left" if c.get("remaining189Raw") == "-" else esc(c.get("remaining189Raw") or "–"))]
                                 for c in sorted(yr["rows"], key=lambda c: -c["ceiling"])])

    e = D.eoi
    out["eoi-stats"] = "".join(f'<div class="stat"><span class="lbl">Subclass {t["subclass"]} · submitted</span><span class="val">{t["submitted"]:,}</span>'
                               f'<span class="sub2">As at {short_date(e["asAt"])}</span></div>' for t in e["totals"] if t.get("submitted") is not None)
    out["eoi"] = table([("Occupation", False), ("ANZSCO", False), ("189", True), ("190", True), ("491", True)],
                       [[occ_link(D, x.get("anzsco"), x["occupation"]), f'<span class="code">{esc(x.get("anzsco"))}</span>',
                         num(x.get("submitted189"), "–"), num(x.get("submitted190"), "–"), num(x.get("submitted491"), "–")]
                        for x in sorted(e["byOccupation"], key=lambda x: -(x.get("submitted189") or 0))])

    names = {"VIC": "Victoria", "NSW": "New South Wales", "QLD": "Queensland", "SA": "South Australia", "WA": "Western Australia",
             "TAS": "Tasmania", "ACT": "Australian Capital Territory", "NT": "Northern Territory"}
    order = list(names)
    alloc = [a for a in D.states["allocations"] if a.get("published") is not False]
    alloc = sorted(alloc, key=lambda a: a["fy"], reverse=True)[0] if alloc else None
    if alloc:
        rows = sorted(alloc["states"], key=lambda s: order.index(s["state"].upper()) if s["state"].upper() in order else 99)
        out["alloc"] = f'<p class="small muted" style="margin:12px 14px 0">{alloc["fy"]}</p>' + table(
            [("State", False), ("190", True), ("491", True), ("Total", True)],
            [[esc(names.get(s["state"].upper(), s["state"])), num(s.get("190"), "–"), num(s.get("491"), "–"),
              num((s.get("190") or 0) + (s.get("491") or 0) if s.get("190") is not None or s.get("491") is not None else None, "–")] for s in rows])
    out["states"] = "".join(
        f'<div class="panel state-card"><h3>{esc(names.get(s["state"].upper(), s["state"]))}<span class="pill">{esc(s["state"].upper())}</span></h3>'
        f'<p>{esc(s.get("summary", ""))}</p>' + (f'<a href="{esc(s["url"])}" rel="noopener">Official {esc(s["state"].upper())} page →</a>' if s.get("url") else "") + "</div>"
        for s in sorted(D.states.get("statesInfo", []), key=lambda s: order.index(s["state"].upper()) if s["state"].upper() in order else 99))

    plan = sorted(D.grants.get("planning", []), key=lambda p: p["fy"])
    streams = []
    for p in plan:
        for s in p.get("streams", []):
            if s["name"] not in streams:
                streams.append(s["name"])
    out["plan"] = table([("Stream", False)] + [(p["fy"], True) for p in plan],
                        [[esc(n)] + [num(next((s["places"] for s in p.get("streams", []) if s["name"] == n), None), "–") for p in plan] for n in streams] +
                        [["Whole program"] + [num(p.get("total"), "–") for p in plan]])

    cut_rows = []
    for code in D.pages:
        c = D.cutoff(code)
        if c:
            cut_rows.append((D.by[code]["name"], code, c))
    out["cutoffs"] = table([("Occupation", False), ("ANZSCO", False), ("Round", False), ("189 cut-off", True)],
                           [[occ_link(D, code, n), f'<span class="code">{code}</span>', short_date(c["roundDate"]), f'{c["minPoints"]} pts'] for n, code, c in sorted(cut_rows)])

    top = sorted((c for c in D.pages if (D.eoi_by.get(c) or {}).get("submitted189")), key=lambda c: -D.eoi_by[c]["submitted189"])[:12]
    out["home-guides"] = '<div class="tools">' + "".join(
        f'<a class="tool" href="occupations/{c}/"><h3>{esc(D.by[c]["name"])}</h3><p>' +
        (f'189 cut-off {D.cutoff(c)["minPoints"]} · ' if D.cutoff(c) else "") + f'{D.eoi_by[c]["submitted189"]:,} EOIs for 189</p></a>' for c in top) + "</div>"
    return out


# ── Structured data, cards and preview images for the main pages ──────

PAGES = {
    "": dict(name="Victorian Points Test calculator", og="vpt", kicker="Victoria · 190 and 491", line="Score your ROI out of 950"),
    "skillselect-points/": dict(name="SkillSelect points calculator", og="points", kind="app", kicker="189 · 190 · 491", line="Federal points and the 65-point pass mark"),
    "189-chances/": dict(name="189 chances", og="chances", kind="app", kicker="Subclass 189", line="Your points against the latest cut-off"),
    "rounds/": dict(name="Invitation rounds", og="rounds", kind="dataset", data="rounds", kicker="SkillSelect", line="Every 189 and 491 round since 2023"),
    "occupations/": dict(name="Occupations", og="occupations", kind="dataset", data="occupations", kicker="ANZSCO", line="Cut-offs, EOIs and ceilings by occupation", search=True),
    "state-nominations/": dict(name="State nominations", og="states", kind="dataset", data="states", kicker="190 and 491", line="Places for every state, Victoria first"),
    "compare/": dict(name="Compare occupations", og="compare", kind="app", kicker="Side by side", line="Up to four occupations compared"),
    "my-journey/": dict(name="Journey tracker", og="journey", kind="app", kicker="EOI to grant", line="Track every step, privately"),
    "eoi-pool/": dict(name="EOI pool", og="eoi", kind="dataset", data="eoi", kicker="SkillSelect EOIs", line="Who is waiting, by points and occupation"),
    "visa-grants/": dict(name="Visa grants", og="grants", kind="dataset", data="grants", kicker="Migration Program", line="Places and grants by visa and year"),
    "occupation-ceilings/": dict(name="Occupation ceilings", og="ceilings", kind="dataset", data="ceilings", kicker="2025–26", line="Caps on 189 and 491 family invitations"),
}


def faqs_from(html_text):
    out = []
    for q, a in re.findall(r"<details[^>]*><summary>(.*?)</summary><p>(.*?)</p></details>", html_text, re.S):
        out.append({"@type": "Question", "name": re.sub("<[^>]+>", "", q).strip(),
                    "acceptedAnswer": {"@type": "Answer", "text": re.sub("<[^>]+>", "", a).strip()}})
    return out


def seo_block(path, text, D, updated):
    meta = PAGES[path]
    url = SITE + path
    title = html.unescape(re.search(r"<title>(.*?)</title>", text, re.S).group(1))
    desc = html.unescape(re.search(r'<meta name="description" content="([^"]*)"', text).group(1))
    img = f"{SITE}assets/og/{meta['og']}.png"
    graph = []
    if path == "":
        graph.append({"@type": "WebSite", "@id": SITE + "#website", "url": SITE, "name": "VPT Points",
                      "potentialAction": {"@type": "SearchAction",
                                          "target": {"@type": "EntryPoint", "urlTemplate": SITE + "occupations/?q={search_term_string}"},
                                          "query-input": "required name=search_term_string"}})
    else:
        graph.append({"@type": "WebPage", "@id": url, "url": url, "name": title, "description": desc, "dateModified": updated,
                      "inLanguage": "en-AU", "isPartOf": {"@id": SITE + "#website"}, "breadcrumb": {"@id": url + "#breadcrumb"},
                      "primaryImageOfPage": img})
        graph.append({"@type": "BreadcrumbList", "@id": url + "#breadcrumb", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE},
            {"@type": "ListItem", "position": 2, "name": meta["name"], "item": url}]})
    if meta.get("kind") == "app":
        graph.append({"@type": "WebApplication", "@id": url + "#app", "name": meta["name"], "url": url, "description": desc,
                      "applicationCategory": "UtilitiesApplication", "operatingSystem": "Any", "isAccessibleForFree": True,
                      "offers": {"@type": "Offer", "price": "0", "priceCurrency": "AUD"}})
    if meta.get("kind") == "dataset":
        src = load(meta["data"])
        graph.append({"@type": "Dataset", "@id": url + "#dataset", "name": f"{meta['name']} (Australian skilled migration)", "url": url,
                      "description": desc, "dateModified": src.get("updated") or updated, "inLanguage": "en-AU",
                      "isAccessibleForFree": True, "creator": {"@type": "Organization", "name": "VPT Points", "url": SITE},
                      "isBasedOn": [s["url"] for s in src.get("sources", []) if isinstance(s, dict) and s.get("url")][:5],
                      "spatialCoverage": "Australia",
                      "distribution": {"@type": "DataDownload", "encodingFormat": "application/json", "contentUrl": f"{SITE}data/{meta['data']}.json"}})
    faq = faqs_from(text) if path != "" else []  # the home page carries its own FAQPage
    if faq:
        graph.append({"@type": "FAQPage", "@id": url + "#faq", "mainEntity": faq})
    ld = json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False)
    tags = [f'<script type="application/ld+json">{ld}</script>']
    if 'name="twitter:card"' not in text.split("<!-- seo -->")[0]:
        tags += ['<meta name="twitter:card" content="summary_large_image">',
                 f'<meta name="twitter:title" content="{esc(title)}">',
                 f'<meta name="twitter:description" content="{esc(desc)}">',
                 f'<meta name="twitter:image" content="{img}">']
    tags += ['<meta property="og:image:width" content="1200">', '<meta property="og:image:height" content="630">',
             '<meta property="og:locale" content="en_AU">']
    prefix = "../" * path.count("/")
    tags += [f'<link rel="apple-touch-icon" href="{prefix}apple-touch-icon.png">', f'<link rel="manifest" href="{prefix}site.webmanifest">']
    return "\n" + "\n".join(tags) + "\n"


def og_images():
    """1200×630 preview cards in the site's colours. Rebuilt only when their text changes."""
    from PIL import Image, ImageDraw, ImageFont
    out = ROOT / "assets" / "og"
    out.mkdir(parents=True, exist_ok=True)
    font = "/System/Library/Fonts/Avenir Next.ttc"

    def f(size, idx):
        try:
            return ImageFont.truetype(font, size, index=idx)
        except OSError:
            return ImageFont.load_default()

    cards = [(m["og"], m["name"], m["kicker"], m["line"]) for m in PAGES.values()]
    cards.append(("occupations", "Occupation guides", "ANZSCO", "Cut-off history, EOIs and ceilings"))
    seen = set()
    for key, title, kicker, line in cards:
        if key in seen:
            continue
        seen.add(key)
        dst = out / f"{key}.png"
        sig = hashlib.sha1(f"{title}|{kicker}|{line}|v2".encode()).hexdigest()[:10]
        sigf = out / f".{key}.sig"
        if dst.exists() and sigf.exists() and sigf.read_text() == sig:
            continue
        im = Image.new("RGB", (1200, 630), "#f4f6f1")
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((70, 70, 150, 150), 24, fill="#1d5a44")
        d.line([(93, 98), (110, 128), (127, 98)], fill="#f2b81f", width=9, joint="curve")
        d.text((172, 88), "VPT Points", font=f(40, 2), fill="#13261f")
        d.rounded_rectangle((70, 210, 70 + 26 + d.textlength(kicker, font=f(30, 5)) + 26, 262), 26, fill="#e1ece4")
        d.text((96, 216), kicker, font=f(30, 5), fill="#1d5a44")
        words, lines, cur = title.split(), [], ""
        big = f(92, 2)
        for w in words:
            if d.textlength((cur + " " + w).strip(), font=big) > 1060:
                lines.append(cur); cur = w
            else:
                cur = (cur + " " + w).strip()
        lines.append(cur)
        y = 290
        for i, l in enumerate(lines[:2]):
            d.text((70, y), l, font=big, fill="#13261f")
            if i == len(lines[:2]) - 1:
                w = d.textlength(l, font=big)
                d.rectangle((70, y + 104, 70 + w, y + 116), fill="#f2b81f")
            y += 104
        d.text((70, 540), line, font=f(36, 5), fill="#56675f")
        d.text((1130, 548), "vptpoints.com", font=f(28, 5), fill="#56675f", anchor="ra")
        im.save(dst, optimize=True)
        sigf.write_text(sig)


def icons_and_extras(updated):
    from PIL import Image, ImageDraw
    im = Image.new("RGBA", (180, 180), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, 179, 179), 40, fill="#1d5a44")
    d.line([(50, 56), (90, 128), (130, 56)], fill="#f2b81f", width=18, joint="curve")
    im.save(ROOT / "apple-touch-icon.png", optimize=True)
    (ROOT / "site.webmanifest").write_text(json.dumps({
        "name": "VPT Points", "short_name": "VPT Points", "start_url": "/", "display": "standalone",
        "background_color": "#f4f6f1", "theme_color": "#1d5a44",
        "icons": [{"src": "/apple-touch-icon.png", "sizes": "180x180", "type": "image/png"},
                  {"src": "/favicon.svg", "sizes": "any", "type": "image/svg+xml"}]}, indent=2) + "\n")


NOT_FOUND = """<!DOCTYPE html>
<html lang="en-AU">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Page not found | VPT Points</title>
<meta name="robots" content="noindex">
<meta name="color-scheme" content="light dark">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="/assets/site.css">
</head>
<body>
<main id="main">
  <div class="wrap">
    <div class="page-hero" style="padding-block:64px 24px">
      <span class="kicker"><i></i>404</span>
      <h1>That page isn’t here</h1>
      <p class="lede">The link may be old, or the occupation code may have changed. These will get you back on track.</p>
    </div>
    <div class="tools">
      <a class="tool feature" href="/"><h3>Victorian Points Test</h3><p>Score your Victoria 190 or 491 ROI out of 950.</p><span class="go">Open the calculator →</span></a>
      <a class="tool" href="/occupations/"><h3>Occupations</h3><p>Search by name or ANZSCO code.</p><span class="go">Find an occupation →</span></a>
      <a class="tool" href="/rounds/"><h3>Invitation rounds</h3><p>Every 189 and 491 round and cut-off.</p><span class="go">See the rounds →</span></a>
      <a class="tool" href="/skillselect-points/"><h3>Points calculator</h3><p>Federal points for 189, 190 and 491.</p><span class="go">Calculate points →</span></a>
    </div>
  </div>
</main>
</body>
</html>
"""


def main(updated):
    D = Data()
    occ_dir = ROOT / "occupations"
    keep = set(D.pages)
    for d in occ_dir.iterdir():  # drop pages for codes no longer in the data
        if d.is_dir() and re.fullmatch(r"\d{6}", d.name) and d.name not in keep:
            for f in d.iterdir():
                f.unlink()
            d.rmdir()
    for code in D.pages:
        p = occ_dir / code / "index.html"
        p.parent.mkdir(exist_ok=True)
        new = occupation_page(D, code, updated)
        old = p.read_text() if p.exists() else ""
        # Keep the stamped header/footer from the last run so unchanged pages stay unchanged.
        for tag in ("header", "footer"):
            m = re.search(rf"<!-- {tag} -->.*?<!-- /{tag} -->", old, re.S)
            if m:
                new = re.sub(rf"<!-- {tag} -->.*?<!-- /{tag} -->", lambda _: m.group(0), new, flags=re.S)
        if new != old:
            p.write_text(new)

    blocks = prerenders(D)
    targets = {"rounds/index.html": ["rounds-stats", "rounds-table", "rounds-occ"], "occupations/index.html": ["occ-list"],
               "occupation-ceilings/index.html": ["ceilings"], "eoi-pool/index.html": ["eoi-stats", "eoi"],
               "state-nominations/index.html": ["alloc", "states"], "visa-grants/index.html": ["plan"],
               "189-chances/index.html": ["cutoffs"], "index.html": ["home-guides"]}
    for f, names in targets.items():
        p = ROOT / f
        t = p.read_text()
        for n in names:
            t = stamp(t, f"pre:{n}", blocks.get(n, ""))
        p.write_text(t)

    for path, meta in PAGES.items():
        p = ROOT / path / "index.html"
        t = p.read_text()
        t = re.sub(r'<meta property="og:image" content="[^"]*">', f'<meta property="og:image" content="{SITE}assets/og/{meta["og"]}.png">', t, count=1)
        t = re.sub(r'<meta name="twitter:image" content="[^"]*">', f'<meta name="twitter:image" content="{SITE}assets/og/{meta["og"]}.png">', t, count=1)
        t = stamp(t, "seo", seo_block(path, t, D, updated))
        p.write_text(t)

    og_images()
    icons_and_extras(updated)
    (ROOT / "404.html").write_text(NOT_FOUND)
    print(f"built {len(D.pages)} occupation pages, {len(blocks)} pre-rendered blocks, SEO for {len(PAGES)} pages")
    return [f"occupations/{c}/" for c in D.pages]


if __name__ == "__main__":
    main(datetime.date.today().isoformat())
