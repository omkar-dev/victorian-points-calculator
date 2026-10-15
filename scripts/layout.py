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
EXTRA = [("privacy/", "Privacy", "")]  # stamped like the rest, linked from the footer only

# Analytics and ads. Leave an ID empty to keep that service off; nothing is
# added to the pages until it is set. Cloudflare Web Analytics needs no code:
# Cloudflare injects it at the edge.
GA4_ID = "G-3FJECMFC01"          # Google Analytics 4 measurement ID, e.g. "G-ABC123XYZ9"
ADSENSE_CLIENT = ""  # AdSense publisher ID, e.g. "ca-pub-1234567890123456"
# No ads where people type in their own details. The calculators keep answers
# in the page address, and ad requests send that address to the ad network.
AD_FREE = {"", "skillselect-points/", "189-chances/", "my-journey/", "compare/", "404", "privacy/"}


def analytics(page):
    """Head tags for the configured services. Page addresses go to Google
    without the query string, so calculator answers are never sent."""
    tags = []
    if ADSENSE_CLIENT:
        tags.append(f'<meta name="google-adsense-account" content="{ADSENSE_CLIENT}">')
        if page not in AD_FREE:
            tags.append(f'<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ADSENSE_CLIENT}" crossorigin="anonymous"></script>')
    if GA4_ID:
        tags.append(f'<script async src="https://www.googletagmanager.com/gtag/js?id={GA4_ID}"></script>')
        tags.append("<script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}gtag('js',new Date());"
                    f"gtag('config','{GA4_ID}',{{page_location:location.origin+location.pathname}});</script>")
    return "<!-- analytics -->" + ("\n" + "\n".join(tags) + "\n" if tags else "") + "<!-- /analytics -->"


def privacy_google():
    """The privacy page's Google section, describing only the services that are on."""
    parts = []
    if GA4_ID:
        parts.append("<p>Google Analytics 4 measures which pages are visited and how people find the site. It sets cookies. "
                     "Page addresses are sent without their query string, so calculator answers aren’t included. "
                     'See <a href="https://policies.google.com/technologies/partner-sites" rel="noopener">how Google uses data from sites that use its services</a>.</p>')
    if ADSENSE_CLIENT:
        parts.append("<p>Google AdSense shows ads on some pages, never on the calculators. Google and its partners may use cookies to show ads "
                     'based on your visits to this and other sites. You can turn off personalised ads in <a href="https://adssettings.google.com" rel="noopener">Google’s ad settings</a>, '
                     'and visitors in some regions are asked for consent first.</p>')
    return "<!-- privacy-google -->" + ("\n      " + "\n      ".join(parts) + "\n" if parts else "") + "<!-- /privacy-google -->"


def stamp_head(text, page):
    if "<!-- analytics -->" not in text:
        text = text.replace("</head>", "<!-- analytics --><!-- /analytics -->\n</head>", 1)
    return stamp(text, "analytics", analytics(page))


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
    links = " · ".join(f'<a href="{pre}{p or "./"}">{"Victorian Points Test calculator" if p == "" else l}</a>' for p, l, _ in PAGES)
    guides = " · ".join(f'<a href="{pre}victorian-points-test/{slug}/">{name}</a>' for slug, name in
                        [("age-points", "VPT age points"), ("salary-points", "VPT salary points"), ("score-examples", "VPT score examples")])
    return f"""<!-- footer -->
    <footer class="site-foot">
      <p class="foot-links">{links}</p>
      <p class="foot-links">Guides: {guides}</p>
      <p>VPT Points is an independent, free project. It isn’t made by or connected to the Victorian Government, any state government or the Department of Home Affairs, and it isn’t migration advice. Figures come from official publications and can lag behind the latest round, so check the source links and talk to a registered migration agent before you act.</p>
      <p>Updated {int(UPDATED[8:])} October {UPDATED[:4]} · Your answers stay in your browser · <a href="{pre}privacy/">Privacy</a></p>
    </footer>
<!-- /footer -->"""


def stamp(text, tag, block):
    pat = re.compile(rf"<!-- {tag} -->.*?<!-- /{tag} -->", re.S)
    if not pat.search(text):
        raise SystemExit(f"missing <!-- {tag} --> markers")
    return pat.sub(lambda _: block, text)


def main():
    import build_pages  # occupation pages, VPT guides, pre-rendered tables, structured data
    guides, generated = build_pages.main(UPDATED)

    for path, _, _ in PAGES + EXTRA:
        f = ROOT / path / "index.html"
        if not f.exists():
            print("skip (missing)", f.relative_to(ROOT))
            continue
        t = f.read_text()
        t = stamp(t, "header", header(path))
        t = stamp(t, "footer", footer(path))
        t = stamp_head(t, path)
        if path == "privacy/":
            t = stamp(t, "privacy-google", privacy_google())
        f.write_text(t)
        print("ok", f.relative_to(ROOT))

    changed = 0
    for path, current in [(g, "") for g in guides] + [(o, "occupations/") for o in generated]:
        f = ROOT / path / "index.html"  # guides sit under the VPT, occupation pages under Occupations
        old = f.read_text()
        t = stamp_head(stamp(stamp(old, "header", header(path, current)), "footer", footer(path)), path)
        if t != old:
            f.write_text(t)
            changed += 1
    print(f"ok {len(guides)} guides and {len(generated)} occupation pages ({changed} changed)")

    for src in sorted((ROOT / "data").glob("*.json")):
        data = json.loads(src.read_text())
        src.with_suffix(".js").write_text(
            "// Generated by scripts/layout.py from " + src.name + " for pages opened from disk. Edit the JSON, not this.\n"
            "(window.VPT_DATA = window.VPT_DATA || {})[" + json.dumps(src.stem) + "] = "
            + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n"
        )
        print("data", src.with_suffix(".js").relative_to(ROOT))

    entries = [(p, "monthly" if p == "" else "weekly", "1.0" if p == "" else "0.8") for p, _, _ in PAGES if (ROOT / p / "index.html").exists()]
    entries += [(p, "yearly", "0.2") for p, _, _ in EXTRA]
    entries += [(p, "monthly", "0.8") for p in guides]
    entries += [(p, "monthly", "0.6") for p in generated]
    nf = ROOT / "404.html"
    nf.write_text(stamp_head(nf.read_text(), "404"))
    ads = ROOT / "ads.txt"
    if ADSENSE_CLIENT:
        ads.write_text(f"google.com, {ADSENSE_CLIENT.replace('ca-', '')}, DIRECT, f08c47fec0942fa0\n")
    elif ads.exists():
        ads.unlink()

    urls = "\n".join(
        f"  <url>\n    <loc>{SITE}{p}</loc>\n    <lastmod>{UPDATED}</lastmod>\n    <changefreq>{freq}</changefreq>\n    <priority>{prio}</priority>\n  </url>"
        for p, freq, prio in entries
    )
    (ROOT / "sitemap.xml").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}\n</urlset>\n'
    )


if __name__ == "__main__":
    main()
