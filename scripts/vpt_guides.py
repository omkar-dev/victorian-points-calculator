"""Victorian Points Test guide pages, built from the calculator's own tables.

The numbers are parsed out of index.html, so a guide can never disagree with
the calculator. Called from build_pages.main().
"""
import json
import re

from build_pages import ICON_TAGS, ROOT, SITE, esc, table

FONTS = ("https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700;12..96,800"
         "&family=Instrument+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@500&display=swap")
GUIDES = [("victorian-points-test/age-points/", "Age points", "Every year from 18 to 44."),
          ("victorian-points-test/salary-points/", "Salary points", "All 19 Victorian earnings bands."),
          ("victorian-points-test/score-examples/", "Score examples", "Eight profiles, fully worked.")]
OFFICIAL = "https://liveinmelbourne.vic.gov.au/migrate/skilled-migration-visas/vpt"


def vpt_tables():
    """AGE, SALARY and CHOICES as the calculator defines them."""
    js = (ROOT / "index.html").read_text()
    age = {int(k): int(v) for k, v in re.findall(r"(\d+): (\d+)", re.search(r"var AGE = \{(.*?)\};", js).group(1))}
    lo, hi, pts = re.search(r"for \(var a = (\d+); a <= (\d+); a\+\+\) AGE\[a\] = (\d+);", js).groups()
    for a in range(int(lo), int(hi) + 1):
        age[a] = int(pts)
    salary = [(int(a), int(b)) for a, b in re.findall(r"\[(\d+),(\d+)\]", re.search(r"var SALARY = \[(.*?)\];", js).group(1))]
    choices = {}
    block = re.search(r"var CHOICES = \{(.*?)\n  \};", js, re.S).group(1)
    for key, body in re.findall(r'(\w+): \{ label: "[^"]+", def: "[^"]+", options: \[(.*?)\] \}', block, re.S):
        choices[key] = [dict(v=v, label=l, pts=int(n)) for v, l, n in
                        re.findall(r'\{ v: "([^"]+)", label: "([^"]+)"(?:, sub: "[^"]*")?, pts: (\d+) \}', body)]
    return age, salary, choices


def salary_pts(salary, v):
    for floor, p in salary:
        if v >= floor:
            return p
    return 0


def shell(path, title, desc, body, graph):
    pre = "../" * path.count("/")
    url = SITE + path
    ld = json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False)
    img = f"{SITE}assets/og/vpt.png"
    return f"""<!DOCTYPE html>
<html lang="en-AU">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
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
<meta property="og:image" content="{img}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(title)}">
<meta name="twitter:description" content="{esc(desc)}">
<meta name="twitter:image" content="{img}">
<link rel="icon" href="{pre}favicon.svg" type="image/svg+xml">
{ICON_TAGS.format(p=pre)}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="preload" as="style" href="{FONTS}" onload="this.onload=null;this.rel='stylesheet'">
<noscript><link rel="stylesheet" href="{FONTS}"></noscript>
<link rel="stylesheet" href="{pre}assets/site.css">
<script type="application/ld+json">{ld}</script>
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<!-- header -->
<!-- /header -->

<main id="main">
  <div class="wrap">
{body}
<!-- footer -->
<!-- /footer -->
  </div>
</main>

<script src="{pre}assets/site.js"></script>
</body>
</html>
"""


def graph(path, title, desc, crumb, faqs, updated):
    url = SITE + path
    g = [{"@type": "Article", "@id": url + "#article", "headline": title, "description": desc, "url": url,
          "inLanguage": "en-AU", "datePublished": "2026-10-15", "dateModified": updated, "image": f"{SITE}assets/og/vpt.png",
          "author": {"@type": "Organization", "name": "VPT Points", "url": SITE},
          "publisher": {"@id": SITE + "#organization"}, "isPartOf": {"@id": SITE + "#website"},
          "mainEntityOfPage": url, "about": {"@type": "Thing", "name": "Victorian Points Test"}},
         {"@type": "BreadcrumbList", "@id": url + "#breadcrumb", "itemListElement": [
             {"@type": "ListItem", "position": 1, "name": "Victorian Points Test calculator", "item": SITE},
             {"@type": "ListItem", "position": 2, "name": crumb, "item": url}]},
         {"@type": "FAQPage", "@id": url + "#faq", "mainEntity": [
             {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faqs]}]
    return g


def crumbs(name):
    return (f'    <nav class="crumbs" aria-label="Breadcrumb"><a href="../../">Victorian Points Test</a> › '
            f'<span aria-current="page">{esc(name)}</span></nav>')


def hero(h1, lede):
    return f"""    <div class="page-hero">
      <span class="kicker"><i></i>Victorian Points Test · 2026–27</span>
      <h1>{h1}</h1>
      <p class="lede">{lede}</p>
    </div>"""


def faq_section(topic, faqs):
    items = "".join(f"<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>" for q, a in faqs)
    return f'    <section class="block" aria-labelledby="faq-h"><h2 id="faq-h">Questions about VPT {topic}</h2><div class="faq">{items}</div></section>'


def more(current):
    cards = ['<a class="tool" href="../../"><h3>VPT calculator</h3><p>Score your ROI out of 950.</p><span class="go">Calculate →</span></a>']
    for p, n, d in GUIDES:
        if p != current:
            cards.append(f'<a class="tool" href="../../{p}"><h3>{n}</h3><p>{d}</p><span class="go">Read →</span></a>')
    return f'    <section class="block" aria-labelledby="more-h"><h2 id="more-h">More on the Victorian Points Test</h2><div class="tools">{"".join(cards)}</div></section>'


def source(note="From the 2026–27 Victorian Points Test tables the calculator uses."):
    return f'    <p class="source">{note} Check Victoria’s official guidelines on <a href="{OFFICIAL}" rel="noopener">Live in Melbourne</a> before you lodge.</p>'


def age_page(age, updated):
    path = GUIDES[0][0]
    top = max(age.values())
    full = [a for a in range(18, 45) if age[a] == top]
    late = sorted({age[a - 1] - age[a] for a in range(41, 45)})
    mid = sorted({age[a - 1] - age[a] for a in range(31, 41)})
    rows = []
    for a in range(18, 46):
        p, prev = age.get(a, 0), age.get(a - 1)
        chg = "" if a == 18 else ("no change" if p == prev else (f"+{p - prev}" if p > prev else f"−{prev - p}"))
        rows.append([f'<a href="../../?age={a}">{a if a < 45 else "45 or older"}</a>', str(p), chg])
    faqs = [
        ("How many VPT points do I get for my age?",
         f"Ages {full[0]} to {full[-1]} score the maximum {top} points. Age 18 scores {age[18]} and 19 scores {age[19]}. "
         f"From 30 the points fall every year, to {age[40]} at 40 and {age[44]} at 44."),
        ("How many points do I lose at each birthday?",
         f"From 31 to 40 each birthday costs {' or '.join(map(str, mid))} points. From 41 to 44 each one costs {' or '.join(map(str, late))}, "
         "so lodging before a birthday matters most in your forties."),
        ("Do I get VPT age points at 45?",
         "No. Age 45 scores 0, and you also need to be under 45 for the federal subclass 190 and 491 points test."),
    ]
    title = "Victorian Points Test Age Points 2026–27 (18 to 44)"
    desc = (f"VPT age points for every year from 18 to 44. Ages {full[0]}–{full[-1]} score {top}; from 30 you lose "
            f"points at each birthday, down to {age[44]} at 44.")
    body = "\n".join([
        crumbs("Age points"),
        hero("VPT age points for every year",
             f"Age is the biggest factor in the Victorian Points Test, worth up to {top} of the 950 points. For 2026–27 "
             "Victoria scores age year by year instead of in five-year bands, so every birthday after 29 changes your score."),
        f"""    <section class="block" aria-labelledby="t-h">
      <div class="block-head"><div><h2 id="t-h">Age points table</h2><p>Select an age to open the calculator with it filled in.</p></div></div>
      <div class="scroll" style="max-width:600px;max-height:none">{table([("Age", False), ("VPT points", True), ("Change from a year younger", True)], rows)}</div>
    </section>""",
        f"""    <section class="block prose" aria-labelledby="k-h">
      <h2 id="k-h">What the table means</h2>
      <p>Everyone aged {full[0]} to {full[-1]} gets the full {top} points, so there’s no advantage to being 22 rather than 29. Ages 18 and 19 score a little less: {age[18]} and {age[19]}.</p>
      <p>From 30 the score drops each year: {age[30]} at 30, {age[35]} at 35 and {age[40]} at 40. After 40 the steps get bigger, {' or '.join(map(str, late))} points a year, falling to {age[44]} at 44. At 45 the score is 0.</p>
      <p>Use your age on the day you lodge or update your Registration of Interest. If a birthday is close, lodging before it keeps the higher score.</p>
    </section>""",
        faq_section("age points", faqs), more(path), source()])
    return path, shell(path, title, desc, body, graph(path, title, desc, "Age points", faqs, updated))


def salary_page(salary, updated):
    path = GUIDES[1][0]
    bands = sorted(salary)
    rows = [[f'<a href="../../?salary={bands[0][0] - 5000}">Under ${bands[0][0]:,}</a>', "0"]]
    for i, (floor, p) in enumerate(bands):
        rng = f"${floor:,} or more" if i + 1 == len(bands) else f"${floor:,} to ${bands[i + 1][0] - 1:,}"
        rows.append([f'<a href="../../?salary={floor}">{rng}</a>', str(p)])
    steps = sorted({bands[i + 1][1] - bands[i][1] for i in range(len(bands) - 1)})
    lo_f, lo_p, hi_f, hi_p = bands[0][0], bands[0][1], bands[-1][0], bands[-1][1]
    faqs = [
        ("How many VPT points do I get for my salary?",
         f"Victorian earnings score from {lo_p} points at ${lo_f:,} to the full {hi_p} at ${hi_f:,} or more, in {len(bands)} bands of $5,000. Under ${lo_f:,} scores 0."),
        ("What salary counts for the Victorian Points Test?",
         "Your yearly salary before tax, without super, from your current skilled employment in Victoria. If you work outside Victoria, salary scores 0."),
        ("How much is each $5,000 band worth?",
         f"Each band adds {' or '.join(map(str, steps))} points, so a pay rise that moves you up one band adds about 8 points."),
    ]
    title = "Victorian Points Test Salary Points 2026–27"
    desc = (f"VPT salary points for 2026–27: {len(bands)} bands of $5,000, from {lo_p} points at ${lo_f // 1000}k to {hi_p} "
            f"at ${hi_f // 1000}k or more, and what salary counts.")
    body = "\n".join([
        crumbs("Salary points"),
        hero("VPT salary points by earnings band",
             f"Victorian salary is worth up to {hi_p} of the 950 points. For 2026–27 it’s scored in {len(bands)} bands of $5,000, "
             "so even a modest pay rise can lift your score."),
        f"""    <section class="block" aria-labelledby="t-h">
      <div class="block-head"><div><h2 id="t-h">Salary points table</h2><p>Yearly salary before tax, without super. Select a band to open the calculator with it filled in.</p></div></div>
      <div class="scroll" style="max-width:600px;max-height:none">{table([("Yearly salary in Victoria", False), ("VPT points", True)], rows)}</div>
    </section>""",
        f"""    <section class="block prose" aria-labelledby="k-h">
      <h2 id="k-h">What the table means</h2>
      <p>Points start at ${lo_f:,} with {lo_p} points and rise by {' or '.join(map(str, steps))} every $5,000, reaching the maximum {hi_p} at ${hi_f:,}. Anything above that still scores {hi_p}.</p>
      <p>Only current skilled employment in Victoria counts. If you’re offshore or earn under ${lo_f:,}, this factor is 0, and age, English and experience carry your score.</p>
    </section>""",
        faq_section("salary points", faqs), more(path), source()])
    return path, shell(path, title, desc, body, graph(path, title, desc, "Salary points", faqs, updated))


PROFILES = [
    ("Recent graduate, offshore", 24, "competent", 75000, "1", "bachelor", "1", "no"),
    ("Engineer with Superior English", 27, "superior", 75000, "3", "masters", "1", "no"),
    ("Nurse working in Melbourne", 29, "proficient", 95000, "2", "bachelor", "1", "no"),
    ("Accountant with a skilled partner", 30, "superior", 120000, "3", "bachelor", "1", "yes"),
    ("Mid-career software developer", 32, "proficient", 110000, "6", "bachelor", "1", "no"),
    ("Senior specialist", 35, "superior", 135000, "8", "masters", "1", "yes"),
    ("Tradesperson in Victoria", 29, "proficient", 95000, "2", "other", "23", "no"),
    ("Experienced manager at 40", 40, "proficient", 170000, "8", "phd", "1", "no"),
]


def examples_page(age, salary, ch, updated):
    path = GUIDES[2][0]
    pick = lambda k, v: next(o for o in ch[k] if o["v"] == v)
    cards, totals = [], []
    for name, a, en, sal, ex, q, sk, pa in PROFILES:
        parts = [("Age", str(a), age.get(a, 0)),
                 ("English", pick("english", en)["label"], pick("english", en)["pts"]),
                 ("Victorian salary", "Under $80,000" if sal < salary[-1][0] else f"${sal:,}", salary_pts(salary, sal)),
                 ("Experience", pick("experience", ex)["label"], pick("experience", ex)["pts"]),
                 ("Qualification", pick("qualification", q)["label"], pick("qualification", q)["pts"]),
                 ("Skill level", pick("skill", sk)["label"], pick("skill", sk)["pts"]),
                 ("Partner points", "Yes" if pa == "yes" else "No", pick("partner", pa)["pts"])]
        total = sum(p for _, _, p in parts)
        totals.append((name, total))
        link = f"../../?age={a}&salary={sal}&english={en}&experience={ex}&qualification={q}&skill={sk}&partner={pa}"
        cards.append(f"""<div class="panel"><h3 style="margin:0 0 4px">{esc(name)}</h3>
        <p class="muted small" style="margin:0 0 10px">Total <strong style="color:var(--ink);font-size:20px">{total}</strong> of 950 · {round(total / 9.5)}% of the maximum</p>
        {table([("Factor", False), ("Answer", False), ("Points", True)], [[f, esc(v), str(p)] for f, v, p in parts])}
        <p style="margin:12px 0 0"><a href="{esc(link)}">Open this profile in the calculator →</a></p></div>""")
    hi_name, hi = max(totals, key=lambda t: t[1])
    lo_name, lo = min(totals, key=lambda t: t[1])
    faqs = [
        ("What is a good Victorian Points Test score?",
         "There is no pass mark. Victoria ranks Registrations of Interest against each other and invites the highest scorers in each occupation group, "
         "so a good score depends on who else is in the pool for your occupation."),
        ("What is the highest possible VPT score?",
         "950: age 300, English 200, Victorian salary 150, experience 100, qualification 100, skill level 50 and partner 50."),
        ("Which change raises a VPT score the most?",
         "English. Moving up one level, from Competent to Proficient or from Proficient to Superior, adds 100 points, more than any other single change."),
    ]
    title = "Victorian Points Test Examples 2026–27: 8 Worked Scores"
    desc = (f"Eight worked Victorian Points Test examples for 2026–27, scoring {lo} to {hi} out of 950, with every factor "
            "broken down. Open any profile in the calculator.")
    body = "\n".join([
        crumbs("Score examples"),
        hero("VPT score examples, worked out",
             f"Eight realistic profiles scored with the 2026–27 tables, from {lo} to {hi} out of 950. Each shows how every factor "
             "adds up, and opens in the calculator so you can change one answer and see the difference."),
        f"""    <section class="block" aria-labelledby="t-h">
      <h2 id="t-h">The profiles</h2>
      <div class="grid-2" style="margin-top:16px">{"".join(cards)}</div>
    </section>""",
        f"""    <section class="block prose" aria-labelledby="k-h">
      <h2 id="k-h">What the examples show</h2>
      <p>The highest score here, {hi} for the {esc(hi_name[0].lower() + hi_name[1:])}, comes from Superior English, long experience and partner points. The lowest, {lo} for the {esc(lo_name[0].lower() + lo_name[1:])}, has Competent English and no Victorian salary.</p>
      <p>Age and English make up half of the 950 points. Salary only counts for skilled work in Victoria, so offshore applicants rely on English and experience.</p>
    </section>""",
        faq_section("scores", faqs), more(path),
        source("Scored with the 2026–27 Victorian Points Test tables the calculator uses. These are illustrations, not predictions of an invitation.")])
    return path, shell(path, title, desc, body, graph(path, title, desc, "Score examples", faqs, updated))


def pages(updated):
    age, salary, ch = vpt_tables()
    return dict([age_page(age, updated), salary_page(salary, updated), examples_page(age, salary, ch, updated)])
