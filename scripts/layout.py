#!/usr/bin/env python3
"""Stamp the shared header and footer into every page, rebuild sitemap.xml,
and write data/*.js copies of data/*.json (pages opened from disk can't fetch JSON).

The site is plain static HTML with no build step to serve it. This script only
keeps the navigation identical across pages. Run it after adding a page or
changing the nav or any data file:  python3 scripts/layout.py
"""
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = "https://vptpoints.com/"
UPDATED = "2026-10-15"

# (path, nav label, short description). The VIC Points Test always comes first.
PRIMARY = [
    ("", "VIC Points Test", "Score your Victoria 190/491 ROI out of 950"),
    ("skillselect-points/", "Points calculator", "Federal 189, 190 and 491 points test"),
    ("189-chances/", "189 chances", "Compare your points with the latest cut-offs"),
    ("rounds/", "Invitation rounds", "Every round, cut-off and trend"),
    ("occupations/", "Occupations", "Search lists, cut-offs and ceilings"),
    ("state-nominations/", "State nominations", "190 and 491 places by state"),
]
MORE = [
    ("compare/", "Compare occupations", "Side by side, up to four"),
    ("my-journey/", "Journey tracker", "Track an EOI from lodgement"),
    ("eoi-pool/", "EOI pool", "Who is waiting, by points and occupation"),
    ("visa-grants/", "Visa grants", "Program places and grants by visa"),
    ("occupation-ceilings/", "Occupation ceilings", "Caps on 189 and 491 family invitations"),
]
PAGES = PRIMARY + MORE


def header(page, current=None):
    pre = "../" * page.count("/")
    current = page if current is None else current

    def link(path, label, desc=None):
        cur = ' aria-current="page"' if path == current else ""
        cls = ' class="vic"' if path == "" else ""
        sub = f"<small>{desc}</small>" if desc else ""
        return f'<a href="{pre}{path or "./"}"{cls}{cur}>{label}{sub}</a>'

    prim = "\n      ".join(link(p, l) for p, l, _ in PRIMARY)
    more = "\n          ".join(link(p, l, d) for p, l, d in MORE)
    more_cur = " is-current" if any(p == current for p, _, _ in MORE) else ""
    return f"""<!-- header -->
<div class="wrap">
  <header class="top">
    <a class="brand" href="{pre or './'}" aria-label="VPT Points home">
      <svg width="30" height="30" viewBox="0 0 32 32" aria-hidden="true"><rect width="32" height="32" rx="9" fill="var(--leaf)"/><path d="M9 10l7 13 7-13" fill="none" stroke="var(--sun)" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"/></svg>
      VPT Points
    </a>
    <button class="nav-toggle" type="button" aria-expanded="false" aria-controls="site-nav">Menu</button>
    <nav class="site-nav" id="site-nav" aria-label="Main">
      {prim}
      <div class="more">
        <button class="more-btn{more_cur}" type="button" aria-expanded="false">More</button>
        <div class="more-list">
          {more}
        </div>
      </div>
    </nav>
  </header>
</div>
<!-- /header -->"""


def footer(page):
    pre = "../" * page.count("/")
    links = " · ".join(f'<a href="{pre}{p or "./"}">{l}</a>' for p, l, _ in PAGES)
    return f"""<!-- footer -->
    <footer class="site-foot">
      <p class="foot-links">{links}</p>
      <p>VPT Points is an independent, free project. It isn’t made by or connected to the Victorian Government, any state government or the Department of Home Affairs, and it isn’t migration advice. Figures come from official publications and can lag behind the latest round, so check the source links and talk to a registered migration agent before you act.</p>
      <p>Updated {int(UPDATED[8:])} October {UPDATED[:4]} · Your answers stay in your browser.</p>
    </footer>
<!-- /footer -->"""


def stamp(text, tag, block):
    pat = re.compile(rf"<!-- {tag} -->.*?<!-- /{tag} -->", re.S)
    if not pat.search(text):
        raise SystemExit(f"missing <!-- {tag} --> markers")
    return pat.sub(lambda _: block, text)


def main():
    import build_pages  # occupation pages, pre-rendered tables, structured data
    generated = build_pages.main(UPDATED)

    for path, _, _ in PAGES:
        f = ROOT / path / "index.html"
        if not f.exists():
            print("skip (missing)", f.relative_to(ROOT))
            continue
        t = f.read_text()
        t = stamp(t, "header", header(path))
        t = stamp(t, "footer", footer(path))
        f.write_text(t)
        print("ok", f.relative_to(ROOT))

    changed = 0
    for path in generated:  # occupation pages sit under Occupations in the nav
        f = ROOT / path / "index.html"
        old = f.read_text()
        t = stamp(stamp(old, "header", header(path, "occupations/")), "footer", footer(path))
        if t != old:
            f.write_text(t)
            changed += 1
    print(f"ok {len(generated)} occupation pages ({changed} changed)")

    for src in sorted((ROOT / "data").glob("*.json")):
        data = json.loads(src.read_text())
        src.with_suffix(".js").write_text(
            "// Generated by scripts/layout.py from " + src.name + " for pages opened from disk. Edit the JSON, not this.\n"
            "(window.VPT_DATA = window.VPT_DATA || {})[" + json.dumps(src.stem) + "] = "
            + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n"
        )
        print("data", src.with_suffix(".js").relative_to(ROOT))

    entries = [(p, "monthly" if p == "" else "weekly", "1.0" if p == "" else "0.8") for p, _, _ in PAGES if (ROOT / p / "index.html").exists()]
    entries += [(p, "monthly", "0.6") for p in generated]
    urls = "\n".join(
        f"  <url>\n    <loc>{SITE}{p}</loc>\n    <lastmod>{UPDATED}</lastmod>\n    <changefreq>{freq}</changefreq>\n    <priority>{prio}</priority>\n  </url>"
        for p, freq, prio in entries
    )
    (ROOT / "sitemap.xml").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}\n</urlset>\n'
    )


if __name__ == "__main__":
    main()
