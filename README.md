# VPT Points: Victorian Points Test and skilled visa tools

A free static site for Australian skilled migration, led by the Victorian Points Test (VPT) calculator for Victoria's subclass 190 and 491 nomination.

Live: https://vptpoints.com/

## Pages

| Path | What it does |
|---|---|
| `/` | Victorian Points Test calculator (2026–27 tables, out of 950) |
| `/skillselect-points/` | Federal points test for 189, 190 and 491 |
| `/189-chances/` | Your points against the latest 189 cut-off for your occupation |
| `/rounds/` | Every 189 / 491 family round since July 2023, cut-offs by occupation, movers |
| `/occupations/` | Search the skilled occupation list, with per-occupation detail |
| `/state-nominations/` | 190 / 491 allocations by state (Victoria first) and how each state selects |
| `/compare/` | Up to four occupations side by side |
| `/my-journey/` | EOI-to-grant tracker kept in the browser (localStorage) |
| `/eoi-pool/` | SkillSelect EOI counts by visa, points and occupation |
| `/visa-grants/` | Migration Program planning levels and grants |
| `/occupation-ceilings/` | 2025–26 occupation ceilings |

## Data

Everything in `data/` comes from official sources (Home Affairs, the SkillSelect EOI dashboard, state migration sites, an FOI release for ceilings). Each file lists its sources and the date it was checked, and each page shows them. Refresh the JSON after each invitation round.

## Editing

No build step is needed to serve the site. Shared styles and helpers live in `assets/`. The header, footer and `sitemap.xml` are stamped into every page by:

```
python3 scripts/layout.py
```

Run it after adding a page, changing the navigation or editing anything in `data/`. It also writes `data/*.js` copies of the JSON, so pages work when opened straight from disk (`file://`), where browsers block `fetch()`.

## Tests

End-to-end tests use [Velocity](https://github.com/omkar-dev/velocity)'s web platform:

```
python3 tests/velocity/serve.py &          # no-cache server on :8765
velocity run tests/velocity/desktop.yaml   # 32 tests, every page
velocity run tests/velocity/mobile.yaml    # 8 tests at 390 px
```

Not affiliated with the Victorian Government, any state government or the Department of Home Affairs.
