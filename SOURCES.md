# SOURCES.md — data-source access & compliance

Property Scout follows strict source-access rules. This file documents, per
source, the access method chosen and the compliance behaviour the tool enforces.

## Compliance behaviour enforced in code (all sources)

These are implemented in `property_scout/adapters/base.py` and apply to every
adapter automatically — an individual adapter cannot opt out:

| Rule | Where | Behaviour |
|---|---|---|
| **robots.txt respected** | `PoliteClient.allowed()` | `robots.txt` is fetched once per domain, cached, and consulted before every request via `urllib.robotparser`. A disallowed path is **skipped** and logged to the run report (`skipped_paths`); it is never worked around. |
| **Rate limiting** | `PoliteClient._respect_delay()` | Minimum `request_delay_seconds` (default **2 s**) between requests to the same domain, tracked per host across all adapters sharing the client. |
| **Backoff** | `PoliteClient.get()` | HTTP 429 / 503 trigger exponential backoff (2 → 4 → 8 → 16 s, up to 5 attempts). |
| **Honest User-Agent** | `Config.user_agent()` | `PropertyScout/1.0 (internal rental-sourcing tool; +<contact_email>)` — identifies the tool and a contact address read from `config.yaml`. |
| **No bot-defeating** | `PoliteClient.get()` | CAPTCHAs / paywalls / bot walls are **never** solved. A 403 or CAPTCHA-looking body raises `SourceBlocked`; the adapter is marked `BLOCKED` in the run report and the run continues with other sources. |
| **Caching** | `PoliteClient._read_cache()` | Raw responses are cached on disk for `cache_ttl_hours` (default **24 h**) so re-runs do not re-hit the sites. |

## Access method per source

The **preferred access order** for every source is: official API → partner
feed → XML/RSS → sitemap → HTML pages. None of the SA portals below expose a
free public API for listing search, so the tool uses their **public HTML search
and detail pages**, and mines the **structured data already embedded in those
pages** (JSON-LD `RealEstateListing`/`Offer`, Open Graph meta tags, and embedded
state blobs) in preference to scraping rendered text. This keeps the footprint
to ordinary page views.

| # | Source | Adapter | Access method | Notes |
|---|---|---|---|---|
| 1 | Property24 | `property24.py` | Public `/commercial-property-to-rent/<area>` + `/to-rent/<area>` search pages → detail pages; JSON-LD + `datePosted` mined for price/size/date/agent. | No public API; rich JSON-LD on detail pages. Largest inventory. |
| 2 | Private Property | `generic.py` | Public commercial/residential to-rent search → detail pages; JSON-LD. | Second-largest general portal. |
| 3 | Gumtree Property | `generic.py` | Public property-to-rent category pages → ad detail pages. | Often carries independent landlords. Gumtree is aggressive about bot detection — expect occasional `BLOCKED`. |
| 4 | Pam Golding | `generic.py` | Public property-to-rent results → property-details pages; JSON-LD. | Agency site. |
| 5 | Century 21 SA | `generic.py` | Public to-let results pages → detail pages. | Agency site. |
| 6 | Seeff | `generic.py` | Public commercial/residential to-let results → detail pages. | Agency site. |
| 7 | RE/MAX SA | `generic.py` | Public to-let listing pages → detail pages. | Agency site. |
| 8 | Rawson / Just Property | `generic.py` | Public property-to-rent pages → detail pages. | Agency sites. |

## robots.txt verification

The tool reads each domain's `robots.txt` **live at run time** and obeys it. The
search-result and listing-detail paths used above are the sites' public,
indexable pages (they appear in Google), which is the category `robots.txt`
normally permits while disallowing internal/admin/search-API paths — and the
tool's `allowed()` check enforces whatever the live file actually says.

> **Important:** the environment this repository was built in blocks outbound
> access to the property portals at the network-egress layer (organisation
> policy), so the live `robots.txt` contents could **not** be captured here and
> pasted in verbatim. Before the first production run, run the tool from an
> unrestricted network and check the run report's `skipped_paths` for each
> source; those are the paths the live `robots.txt` disallowed. Do not remove or
> weaken the `allowed()` check to reach a disallowed path.

## When a source is blocked

If a source starts returning 403s or CAPTCHA walls, it is reported as `BLOCKED`
(console + JSON run report) and the run continues. Do **not** attempt to defeat
the block. Options: reduce frequency, contact the site for a data-sharing
arrangement/API, or disable that source in `config.yaml`.
