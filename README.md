# Property Scout

An internal tool for sourcing small rental units across South African property
portals and agency sites, then handing your team a ready-to-work **call sheet**.

Give it a town or suburb; it searches Property24, Private Property, Gumtree, Pam
Golding, Century 21, Seeff, RE/MAX and Rawson/Just Property, applies your hard
filters (rent, size, availability, listing age), deduplicates the same unit
listed by multiple agents, and exports a DOCX call sheet grouped by agency plus
an XLSX spreadsheet.

---

## What it filters for

- **Rent** ≤ R12 000/month (configurable). VAT basis (incl/excl) is detected and
  a listing is flagged when its excl-VAT rent exceeds the limit once VAT is added.
- **Size** ≥ 25 m² as a **single contiguous unit** (never summed across units).
  Listings with no extractable size go to a *Needs Verification* section, not the bin.
- **Availability** — excludes sold / let / under-offer / pending / coming-soon /
  waitlist. A previously-seen listing that 404s or redirects to search is marked
  let and reported under *Dropped Since Last Run*.
- **Listing age** < 60 days (configurable), using stated dates → our own
  first-seen tracking → inferred "updated" dates, in that order of trust.
  Listings we can't date go to an *Age Unconfirmed* section so the team can ask
  the agent — they are never silently dropped.

---

## Install

Requires **Python 3.11+**.

```bash
git clone <this repo>
cd medwave-agent

python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

`selectolax`/`BeautifulSoup` handle static pages. Playwright is only needed if a
source ever requires JS rendering; it is commented out in `requirements.txt`.
If you enable it: `pip install playwright==1.49.1 && playwright install chromium`.

Edit `config.yaml` — at minimum set `contact_email` (it is sent in the honest
User-Agent on every request).

---

## Run the web UI

```bash
python -m property_scout serve            # http://127.0.0.1:8000
```

Open the page, enter an area (max-rent 12000 and min-size 25 are pre-filled),
tick the sources and *Run Search*. You'll see live progress ("querying
Property24 …"), then a sortable results table and buttons:

- **Export Call Sheet (DOCX)**
- **Export Spreadsheet (XLSX)**
- **Run report (JSON)**

---

## Run from the command line

```bash
python -m property_scout search \
    --area "East London, Eastern Cape" \
    --max-rent 12000 --min-size 25 \
    --out ./exports/
```

Options: `--radius <km>`, `--include-residential`, `--sources property24,seeff`
(subset), `--config path/to/config.yaml`.

This is the *definition of done*: it writes a DOCX call sheet grouped by agency
(with phone numbers and listing links), an XLSX with the same data plus a summary
tab, and a JSON run report — no manual intervention.

Schedule it with cron for saved areas, e.g.:

```cron
0 6 * * 1  cd /path/to/medwave-agent && .venv/bin/python -m property_scout search --area "East London, Eastern Cape"
```

---

## Outputs

- **Call sheet (`call_sheet_<area>_<runid>.docx`)** — the primary deliverable.
  Cover block (area, date, filters, source status), qualifying listings **grouped
  by agency** and sorted freshest-first, with blank **Called / Outcome / Viewing
  booked** columns, then *Age Unconfirmed*, *Needs Verification* and *Dropped
  Since Last Run* sections. Portrait A4, printable.
- **Spreadsheet (`property_scout_<area>_<runid>.xlsx`)** — one row per listing
  (all model fields) plus a **Summary** tab (count & median rent by suburb, count
  by agency, count by property type) and a *Dropped Since Last* tab.
- **Run report (`run_report_<area>_<runid>.json`)** + console summary — per
  source: requests made, listings found, listings passing, errors, blocked
  status, duration.

---

## How listing age works (important)

SA portals are inconsistent about dates, so age is established in this order:

1. **Stated date** — a genuine first-published date from JSON-LD
   (`datePosted`/`datePublished`), an `og:`/meta tag, or the embedded page state.
   `age_confidence = "stated"`.
2. **First-seen tracking** — every listing ID seen on every run is persisted in
   SQLite; `date_first_seen` is the earliest run that saw it. Useless on the very
   first run, but becomes the most trustworthy signal over time.
   `age_confidence = "first_seen"`.
3. **Inferred** — an "updated"/"refreshed" date (agents game these).
   `age_confidence = "inferred"`.

Filtering: `stated`/`first_seen` older than the limit are excluded; `inferred`
older than the limit are excluded but **counted** in the report; `unknown` are
routed to *Age Unconfirmed*, never dropped.

**Run it regularly from day one** — first-seen tracking only pays off once there
is history.

---

## Adding a new agency adapter (worked example)

Adapters are pluggable — one class per source, registered in a config file, no
core changes needed. Most sites fit the generic pattern; you only declare URLs
and a link regex.

**1. Add a class** (in `property_scout/adapters/generic.py`, or a new module):

```python
from .generic import GenericPortalAdapter
import re

class AcmePropsAdapter(GenericPortalAdapter):
    name = "acme"                       # must match the config.yaml key
    display_name = "Acme Props"
    base_url = "https://www.acmeprops.co.za"
    # {slug} is the area, e.g. "east-london"
    commercial_search_templates = [
        "{base}/to-rent/commercial/{slug}",
    ]
    residential_search_templates = [
        "{base}/to-rent/{slug}",
    ]
    # Regex a detail-page URL must match (used to pick links off the results page)
    detail_link_re = re.compile(r"/to-rent/[\w/-]+/\d{4,}")
```

The generic base already extracts price, size, VAT, address, dates, agent
contacts and availability from JSON-LD + Open Graph + visible text. Override
`parse_detail()` only if the site is unusual.

**2. Register it** (in `property_scout/adapters/__init__.py`):

```python
from .generic import AcmePropsAdapter
REGISTRY["acme"] = AcmePropsAdapter
```

or, from a plugin, at import time:

```python
from property_scout.adapters import register
register("acme", AcmePropsAdapter)
```

**3. Enable it** in `config.yaml`:

```yaml
sources:
  acme:
    enabled: true
```

**4. Smoke-test it:**

```bash
python -m property_scout smoke --area "East London, Eastern Cape" --sources acme
```

A completely bespoke source can instead subclass `BaseAdapter` directly and
implement `search(area, max_rent, min_size_sqm, radius_km, include_residential)
-> list[RawListing]`.

---

## Troubleshooting — a source returns zero results

Run the smoke test to see which source is affected:

```bash
python -m property_scout smoke --area "East London, Eastern Cape"
```

| Symptom | Likely cause | Fix |
|---|---|---|
| One source `ZERO`, others fine | The site changed its HTML → the `detail_link_re` no longer matches, or the search URL slug format changed. | Open the site's results page, copy a real listing URL, update `detail_link_re` / `*_search_templates` for that adapter. |
| `BLOCKED` | 403 / CAPTCHA / bot wall. | Do **not** try to bypass it. Lower frequency, disable the source in `config.yaml`, or pursue an official feed. See `SOURCES.md`. |
| Everything `ZERO` | Network egress blocked, or the area slug is wrong. | Check connectivity; try the plain town name (`"East London"`). |
| `skipped_paths` populated | `robots.txt` disallowed the path. | Expected and correct — the tool obeys `robots.txt`. |
| Stale results | 24 h response cache. | Delete the `.cache/` directory (path from `config.yaml`) to force a fresh fetch. |

Logs are written to `logs/property_scout.log` (path configurable).

---

## Testing

```bash
pip install -r requirements.txt
python -m pytest -q
```

The suite covers the fragile parts — size / price / VAT / address parsers, the
deduplication engine, listing-age logic, and Property24 detail-page parsing
against saved HTML fixtures (`tests/fixtures/`). The **adapter smoke test**
(`python -m property_scout smoke`) tells you when a live site changes its layout.

---

## Project layout

```
property_scout/
  config.py          config.yaml loader
  models.py          RawListing + canonical Listing
  parsers.py         size / price / VAT / address / type / availability
  age.py             listing-age determination
  dedup.py           cross-source deduplication
  db.py              SQLite: listings, first-seen, export history
  pipeline.py        orchestration: search → parse → filter → dedupe → route
  smoke.py           adapter smoke test
  adapters/          base + polite HTTP client + one class per source
  exporters/         DOCX call sheet, XLSX, JSON run report
  web/               FastAPI app + single-page UI
config.yaml
requirements.txt
SOURCES.md           per-source access method & robots.txt compliance
tests/
```

---

## A note on this environment

The portals are reached over the public internet. If you run this where outbound
access to those domains is blocked (e.g. a locked-down CI/sandbox), every source
will report `BLOCKED`/`ZERO` — that's the network, not the tool. Run it from a
normal network for live results. The pipeline, parsers, dedup, exporters and web
UI are fully exercised offline by the test suite.
