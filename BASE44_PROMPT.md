# Property Scout — Base44 build prompt

> **How to use this file.** Copy everything from the line `--- START PROMPT ---`
> down to `--- END PROMPT ---` and paste it into Base44 as your app-creation
> prompt. It's long; if Base44 asks you to trim, paste **Section 1–4 first**
> (that builds a working app), then paste Sections 5–9 as follow-up messages to
> add scraping, exports and polish. Iterate — Base44 is conversational.

---

--- START PROMPT ---

Build an internal web app called **Property Scout**.

## 1. What the app is for

A South African health-tech company places small physical equipment inside
leased spaces. Staff need to find small rental units to let in a chosen town or
suburb, then phone the listing agents to book viewings. This app searches SA
property portals, filters the results down to units worth calling about, removes
duplicates, and produces a **call sheet** grouped by agency plus a spreadsheet.
It is an internal team tool (require login). Prioritise a working end-to-end flow
over visual polish. Use a clean, professional look: navy `#1f4e78` primary,
light-grey background, readable tables.

## 2. Data model (Entities)

Create these entities.

### Entity: `Listing`
One row per physical unit per source. (Base44's automatic `created_date` on this
record IS our "first seen" date — use it for listing-age tracking, see §6.)

- `source` (string) — e.g. "property24", "privateproperty", "pamgolding"
- `source_listing_id` (string)
- `dedupe_key` (string) — stable id = source + "::" + source_listing_id
- `url` (string)
- `title` (string)
- `property_type` (enum: retail, office, commercial, industrial, medical, residential, other)
- `monthly_rent` (number) — ZAR, whole rand; empty if Price-on-Application
- `rent_basis` (enum: incl_vat, excl_vat, unknown)
- `effective_rent_incl_vat` (number) — monthly_rent grossed up 15% if excl_vat
- `additional_costs` (string) — levies/rates/utilities as stated
- `size_sqm` (number) — floor area; empty if not extractable
- `size_confidence` (enum: stated, parsed_from_text, estimated, unknown)
- `address_raw` (string)
- `address_normalised` (string) — lowercased, no unit/shop numbers, street types abbreviated (for dedup)
- `suburb` (string)
- `city` (string)
- `province` (string)
- `agency_name` (string)
- `agent_name` (string)
- `agent_phone` (string)
- `agent_email` (string)
- `date_listed` (date) — genuine first-published date if the source states one
- `days_on_market` (number)
- `age_confidence` (enum: stated, first_seen, inferred, unknown)
- `availability_status` (enum: available, under_offer, let, coming_soon, unknown)
- `last_seen` (datetime) — most recent run that still saw it live
- `description` (string, long text)
- `image_url` (string)
- `duplicate_of` (string) — dedupe_key of the surviving record, if this is a duplicate
- `also_listed_by` (string) — semicolon list of other agencies listing the same unit
- `flags` (string) — semicolon list, e.g. "size_uncertain;price_on_application;vat_pushes_over_limit"
- `bucket` (enum: qualifying, age_unconfirmed, needs_verification, excluded) — where it lands after filtering
- `search_run_id` (string) — the SearchRun that produced it

### Entity: `SearchRun`
One record per search executed.
- `area` (string) — e.g. "East London, Eastern Cape"
- `radius_km` (number, optional)
- `max_rent` (number, default 12000)
- `min_size_sqm` (number, default 25)
- `max_age_days` (number, default 60)
- `include_residential` (boolean, default false)
- `status` (enum: running, complete, failed)
- `sources_queried` (string) — semicolon list
- `sources_blocked` (string) — semicolon list of blocked/skipped sources
- `count_qualifying` (number)
- `count_age_unconfirmed` (number)
- `count_needs_verification` (number)
- `count_dropped_since_last` (number)
- `report_json` (string, long text) — per-source stats: requests, found, passing, errors, blocked, duration

### Entity: `Source`
Registry of portals (so new agencies can be added without code changes).
Seed it with the rows in §5.
- `key` (string) — machine name
- `display_name` (string)
- `enabled` (boolean, default true)
- `base_url` (string)
- `commercial_search_template` (string) — URL template with `{slug}` placeholder
- `residential_search_template` (string)
- `detail_link_pattern` (string) — regex a detail-page URL must match
- `access_notes` (string) — how it's accessed, robots.txt notes
- `last_status` (enum: ok, blocked, zero, error, untested)

### Entity: `AppSetting`
Single-record config.
- `contact_email` (string) — sent in the honest User-Agent header
- `default_max_rent` (number, default 12000)
- `default_min_size_sqm` (number, default 25)
- `max_listing_age_days` (number, default 60)
- `request_delay_seconds` (number, default 2)
- `exclude_inferred_age_over_limit` (boolean, default true)
- `saved_areas` (string) — semicolon list, seed with "East London, Eastern Cape;Port Elizabeth, Eastern Cape;Jeffreys Bay, Eastern Cape"

## 3. Pages & UI

### Page: `Search` (home)
- Inputs: **Target area** (text with autocomplete from `AppSetting.saved_areas`),
  **Max rent** (default 12000), **Min size m²** (default 25), **Radius km**
  (optional), **Include residential units** (checkbox, default off), and a
  checkbox per enabled `Source`.
- Big **"Run Search"** button.
- **Live progress area**: as the search runs, show which source is being queried
  and how many results found so far ("Querying Property24 … 12 found"). Poll the
  running `SearchRun` / its Listings to update this.
- When done, redirect to the Results page for that run.

### Page: `Results`
- Header stats: qualifying / age-unconfirmed / needs-verification / dropped-since-
  last-run counts. Show any blocked sources in red.
- **Sortable results table** (sort by rent and size at minimum), columns:
  Section badge, Source, Agency, Agent, Phone, Email, Suburb, Type, Rent (show
  VAT basis; append "*" when `vat_pushes_over_limit` flag set), Size m² (prefix
  "~" when size_confidence ≠ stated), Days on market, Age confidence, Verified
  live (date), Title (links to original listing).
- Buttons: **Export Call Sheet**, **Export Spreadsheet (XLSX)**, **Download run
  report (JSON)**.

### Page: `Call Sheet` (printable)
A clean, **portrait A4, print-friendly** page the team works from:
- Cover block: area, date, filters applied, total qualifying, sources queried,
  sources blocked/skipped.
- **Grouped by agency** (one call covers several properties). Per agency: agency
  name, agent name, phone, email, then a table of that agency's matching
  properties — address, suburb, size m², rent, VAT basis, type, **days on
  market**, **verified live**, listing link. Sort properties within each agency
  by days-on-market, freshest first. Add blank columns: **Called (date)**,
  **Outcome**, **Viewing booked**.
- Section **"Age Unconfirmed"**: passed every other filter but age couldn't be
  established. Add the line: *"Ask the agent how long this has been on the
  market."*
- Section **"Needs Verification"**: matched area/type but unclear size or price
  (e.g. Price on Application).
- Section **"Dropped Since Last Run"**: previously-exported listings now let or
  withdrawn — "stop chasing these".
- A "Print / Save as PDF" button (use the browser print dialog styled for A4).

### Page: `Sources`
Table of `Source` records with enable/disable toggles, last status, and a
"Test source" button (runs the smoke test in §7). Allow adding a new source by
filling in the fields — no code change needed.

### Page: `Settings`
Edit the single `AppSetting` record.

## 4. Business logic — filters and routing

When a search runs, each raw listing becomes a `Listing`, then is routed into a
`bucket`:

1. **Availability** — exclude anything not currently on the market: exclude
   `under_offer`, `let`, `coming_soon`. Detect from status text: "under offer",
   "let", "leased", "no longer available", "sold", "pending", "coming soon",
   "waitlist". Treat "to let"/"to rent"/"available" as available. (Do not let
   the boilerplate phrase "to let" count as the negative word "let".)
2. **Property type** — keep only: retail, office, commercial, medical, other by
   default; include residential only if the toggle is on. Exclude industrial by
   default.
3. **Price unclear** (Price-on-Application / no rand figure) → `needs_verification`.
4. **Size unclear** (no extractable m²) → `needs_verification`. Never silently
   drop for missing size.
5. **Hard cut-offs** — exclude if `monthly_rent` > max_rent, or `size_sqm` <
   min_size.
6. **Age** (see §6) — `stated`/`first_seen` older than max_age → exclude;
   `inferred` older than max_age → exclude but count it; `unknown` →
   `age_unconfirmed` (never dropped); otherwise → `qualifying`.

**VAT rule:** SA commercial rent is often quoted excluding VAT (15%). Detect
incl/excl from text ("excl VAT", "plus VAT", "+VAT" → excl; "incl VAT" → incl).
Compute `effective_rent_incl_vat`. If rent is excl-VAT and the VAT-inclusive
figure exceeds max_rent while the stated figure does not, keep it but add the
flag `vat_pushes_over_limit` so the team sees the real number.

**Size rule:** Extract from free text — handle "approx 45m2", "45 sqm", "45 m²",
"45m² shop", "1,250 m2", "45.5 square metres". Use the **largest single**
figure; **never sum multiple units** to reach the threshold. Set
`size_confidence` (stated if a clean lone value, else parsed_from_text).

**Price rule:** Handle "R 12 000", "R12,000", "R12000 pm", "R12 000 p/m excl
VAT". "Price on Application"/"POA" → empty rent + `price_on_application` flag +
needs_verification.

**Deduplication:** Two listings are the same physical unit when
`address_normalised` is equal AND size within 5% AND rent within 10%. Keep the
record with the most complete agent contact details; set the others'
`duplicate_of` to the survivor and append their agency to the survivor's
`also_listed_by`. Only surviving records appear on the call sheet.

## 5. Sources to seed (`Source` entity)

Seed these, in this priority order, all enabled except where noted. `{slug}` is
the area town lowercased with spaces→hyphens (e.g. "east-london").

| key | display_name | base_url | notes |
|---|---|---|---|
| property24 | Property24 | https://www.property24.com | Largest inventory; commercial + to-rent sections |
| privateproperty | Private Property | https://www.privateproperty.co.za | Second-largest general portal |
| gumtree | Gumtree Property | https://www.gumtree.co.za | Independent landlords; may block bots |
| pamgolding | Pam Golding | https://www.pamgolding.co.za | Agency |
| century21 | Century 21 SA | https://www.century21.co.za | Agency |
| seeff | Seeff | https://www.seeff.com | Agency |
| remax | RE/MAX SA | https://www.remax.co.za | Agency |
| rawson | Rawson / Just Property | https://www.rawson.co.za | Agency |

## 6. Listing age (do this carefully)

Establish age in this order of trust and set `age_confidence` accordingly:
1. **stated** — a genuine first-published date the source exposes: a visible
   date, a JSON-LD `datePosted`/`datePublished` field, an `og:` meta tag, or the
   page's embedded JSON. Check the markup, not just visible text.
2. **first_seen** — the `created_date` of this Listing record in our own
   database (the earliest run that ever saw this `dedupe_key`). On the very first
   run this is today and unhelpful, but it becomes our most trustworthy signal
   over time. When re-seeing a listing, do **not** create a duplicate — update
   the existing record and keep its original `created_date`.
3. **inferred** — an "updated"/"refreshed" date (agents game these).
4. **unknown** — nothing at all → route to `age_unconfirmed`.

Compute `days_on_market` from the best available date. Show it on every row of
every output. Make max_age configurable (default 60).

## 7. Backend functions (scraping + orchestration)

Create backend functions. **Follow these source-access rules strictly** — they
are non-negotiable compliance requirements:

- Before scraping any domain, fetch and honour its **`robots.txt`**. If a path is
  disallowed, skip it and record the skip in the run report — never work around it.
- **Rate-limit**: minimum `request_delay_seconds` (default 2s) between requests
  to the same domain; exponential backoff on HTTP 429/503.
- Send an honest **User-Agent** identifying the tool and including
  `AppSetting.contact_email`, e.g. `PropertyScout/1.0 (+ops@company.co.za)`.
- **Never** solve CAPTCHAs, bypass paywalls, or defeat bot detection. If a
  source returns 403 or a bot wall, mark it **blocked** in the run report and
  continue with the other sources — one broken source must never fail the run.
- **Cache** raw fetched pages for 24h (store HTML + fetched-at in a `RawCache`
  entity keyed by URL) so re-runs don't re-hit the sites.

Functions to create:

- `runSearch(searchRunId)` — orchestrates: for each enabled selected source,
  build the search URL from its template + slug, fetch the results page, extract
  detail-page links matching `detail_link_pattern`, fetch each detail page,
  extract fields (below), upsert Listings (dedupe on `dedupe_key`, preserve
  `created_date`), then dedupe/route/count and update the SearchRun. Update
  progress as it goes so the Search page can show it live.
- **Field extraction via InvokeLLM** — this is the robust part. For each detail
  page, pass the page's main text/HTML to Base44's **InvokeLLM** integration with
  a JSON response schema matching the `Listing` fields, asking it to extract:
  title, monthly rent + whether incl/excl VAT + Price-on-Application, size in m²
  (single unit only, never summed) + confidence, property type, full address +
  suburb/city/province, agency name, agent name/phone/email, any stated
  listing/updated date, and availability status. This handles the messy,
  inconsistent SA listing formats far better than fixed selectors. Also try to
  read a `datePosted` from JSON-LD in the raw HTML first (more reliable than
  visible text).
- `recheckPreviousExports(area)` — re-fetch the URLs of the previous run's
  exported listings; if a listing now 404s, redirects to search, or shows
  let/under-offer, mark it `let`, update `last_seen`, and add it to "Dropped
  Since Last Run".
- `smokeTest(sourceKey)` — hit the source once for a known area and report
  ok / zero / blocked / error into `Source.last_status`, so you find out when a
  site changes its layout.

## 8. Exports

- **Spreadsheet**: export all listings (one row, every field) as **XLSX**
  (generate server-side in a backend function using a spreadsheet library) with a
  **Summary** tab — count and median rent by suburb, count by agency, count by
  property type. Provide XLSX; a CSV fallback is fine if XLSX is hard.
- **Call Sheet**: the printable `Call Sheet` page above; "Save as PDF" via the
  browser print dialog. (If a server-side DOCX/PDF library is available, offer a
  DOCX download too — otherwise print-to-PDF is acceptable.)
- **Run report**: the `SearchRun.report_json` (per-source requests, found,
  passing, errors, blocked, duration), downloadable as JSON and shown on Results.

## 9. Build order

1. Entities (`Listing`, `SearchRun`, `Source`, `AppSetting`, `RawCache`) + seed
   `Source` and `AppSetting`.
2. Search page + `runSearch` backend function against **Property24 only**, using
   InvokeLLM extraction — get one source working end to end with live progress.
3. Filtering/routing + dedup + Results page + Call Sheet page.
4. XLSX export + run report.
5. Remaining sources one at a time; `smokeTest`; Sources page.
6. `recheckPreviousExports` + "Dropped Since Last Run".
7. Settings page, login/auth, final polish.

**Definition of done:** entering "East London, Eastern Cape" with max rent 12000
and min size 25 produces a call sheet grouped by agency (with phone numbers and
listing links) and a spreadsheet with the same data, without manual steps.

--- END PROMPT ---

---

## Notes for you (do NOT paste — this is guidance for you, not Base44)

- **Scraping is the hard part in any no-code tool.** Base44 backend functions can
  `fetch()` pages, but some SA portals (Gumtree especially) actively block
  automated access, and heavy JavaScript-rendered sites may return little usable
  HTML to a plain fetch. Expect to iterate on the sources one at a time. Property24
  and the agency sites (which embed JSON-LD) are the most likely to work; treat
  the harder ones as "best effort, may be BLOCKED".
- **The InvokeLLM extraction approach** (Section 7) is what makes this feasible in
  Base44 — it turns messy listing text into your structured schema without
  fragile regex. It costs LLM calls per listing, so keep runs scoped to one area.
- **First-seen tracking is free** in Base44 because every record has a
  `created_date` — the prompt tells it to reuse that and never duplicate records.
- If Base44 struggles with the whole thing at once, build in the order in Section
  9, pasting one section per message.
- The original Python version of this app (fuller compliance, tested parsers,
  DOCX export, CLI) lives in the `property_scout/` folder of this repo — useful as
  a reference for exact parsing rules if Base44's output needs tightening.
