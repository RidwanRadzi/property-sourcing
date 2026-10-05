# Property Sourcing

Finds Malaysian property projects/developments that still have **unsold
developer units** — leads for a sourcing/outreach business — by scraping
multiple sources, and publishes the results as a GitHub Pages listing site.

Standalone project: no shared code or process with `~/rental-gap-scraper` or
TEDUH. All scrapers run on this Mac's residential IP, so each is deliberately
paced (small page caps, delays between requests) to avoid tripping a
rate-limit/block that would also hurt the other scrapers on this machine.

**Live site:** https://ridwanradzi.github.io/property-sourcing/

## What counts as a lead

Two signal types, per source:

- **`developer_listed_project`** — structured signal. PropertyGuru and
  iProperty (both run the same REA Group platform) embed `isDeveloperListing`
  / `listerType == 'developer'` on listings where the developer itself is the
  lister, rather than an agent or owner. These are projects with developer
  stock still being actively sold.
- **`new_launch_unsold`** — NuProp is a new-launch marketing platform; every
  project on it is, by the site's purpose, still being sold by its developer.
  Cards with an explicit "Sold Out"/"Fully Sold" badge are filtered out.
- **`keyword_match`** — text signal. Listing titles / search snippets
  containing phrases like "developer unit", "VP unit", "direct from
  developer", "unsold unit" (see `common/keywords.py` for the full list).
  Used against PropertyGuru + iProperty keyword search and generic web search.

## Structure

```
common/
  keywords.py   — shared developer-unit keyword list
  models.py     — Lead record + cross-source dedupe (by URL)
scrapers/
  propertyguru.py  — structured + keyword signals, sale & rent
  nuprop.py        — new-launch project cards per state
  iproperty.py     — same platform as PropertyGuru, structured + keyword
  web_search.py    — DuckDuckGo HTML search, no API key
run_all.py      — runs every scraper, dedupes, writes docs/data/leads.json
docs/
  index.html    — GitHub Pages site, reads ./data/leads.json client-side
  data/leads.json — committed snapshot of the latest scrape
```

## Running it

```bash
pip install -r requirements.txt
python3 run_all.py
```

This overwrites `docs/data/leads.json`. Commit and push that file to update
the live site (no CI/build step — GitHub Pages serves `docs/` directly).

You can also run a single source during development, e.g.:

```bash
python3 -m scrapers.nuprop
```

## Known limitations

- **iProperty** occasionally 502s on specific paths (confirmed
  `/new-property-launches/` 502s consistently even after retries — looked
  like a dead route, not a rate limit); the `freetext` search path used here
  works reliably instead.
- **Web search** is the noisiest, lowest-precision source — DuckDuckGo
  results include aggregators, news, and forum posts, not just primary
  listings. Treat `web_search` leads as a starting point to verify manually,
  not a confirmed signal the way the other three sources are.
- **Developer websites** (individual developer company sites) are not
  scraped directly in v1 — there's no generalizable pattern across dozens of
  different developer sites. The keyword web-search pass is the current
  stand-in; a future pass could add specific developers' sites one at a time
  as `scrapers/developer_sites/<name>.py` modules if particular developers
  turn out to be worth tracking individually.
- No scheduling/automation yet — `run_all.py` is run manually. Could be
  wired to a GitHub Actions cron job to auto-refresh `leads.json`, but that
  would run scrapes from GitHub's IP ranges rather than this Mac's, which
  changes the blocking-risk profile and wasn't part of this pass.
