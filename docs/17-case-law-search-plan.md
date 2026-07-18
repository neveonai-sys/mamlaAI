# 17 — Add "Search Case Law" mode to Citation Search

> **Status:** 🚧 IMPLEMENTED, NEEDS LIVE VERIFICATION — code is in; the load-bearing assumption (captcha solved once per session, pagination reuses it) has not been confirmed against a live run, and the in-process session store assumes a single-worker scraper deployment (see Verification section).
> Last updated: 2026-07-12

---

## TL;DR

The existing Citation Search (`new_frontend/src/components/citations/CitationSearch.jsx`) only verifies a citation you already know and returns a single "best" result. Typing a research-style query like "land dispute" silently runs an exact-**phrase** search and returns one arbitrary top row — nothing like the real scr.sci.gov.in experience (broad `search_opt=ANY` search, thousands of paginated/filterable results). This plan adds a second **"Search Case Law"** mode on the same page with full filter parity and real pagination, built so pagination doesn't require a paid CAPTCHA solve on every page turn.

## Context

Citation Search is backed by:
- `scrapping_codes_ecourt/sc_citation_scraper.py` — the actual scraper (`ESCRClient`, `classify_citation`, `CaptchaSolver`, `CitationCache`, FastAPI `lookup_citation` route)
- `Legalv1/ecourt_scrapped/citation_views.py` + `Legalv1/ecourt_scrapped/services/citation_client.py` — Django proxy layer with a persistent Redis cache (30-day TTL, keyed by SHA256 of the raw citation text)
- `Legalv1/ai_draft/citation_grounding.py` — reuses the same single-result lookup to ground AI-drafted citations
- `new_frontend/src/components/citations/CitationSearch.jsx` — single text box, single-result card UI

**Key finding that shapes the design**: a live browser request captured against `https://scr.sci.gov.in/scrsearch/?p=pdf_search/home/` (the real site's results/pagination data source) contains **no `captcha` field at all**, even for a fully-formed `search_opt=ANY` search POST. This means the real site validates the captcha once (via a separate `?p=pdf_search/checkCaptcha` call, visible in network logs) and relies on the session cookie for all subsequent `home/` calls — including pagination.

Our scraper doesn't exploit this today: `ESCRClient.search()` (`sc_citation_scraper.py:418-455`) calls `_solve_and_verify_captcha()` (a paid CapSolver + local-OCR solve, lines 354-416) on *every* call, and the FastAPI handler constructs a brand-new `ESCRClient`/`httpx.AsyncClient` per request (line 656), so cookies never survive between requests. Fixing that is the core backend change that makes real pagination affordable.

## Backend changes

**1. Session-aware `ESCRClient` (`scrapping_codes_ecourt/sc_citation_scraper.py`)**

- Add `search_structured(filters: dict, iDisplayStart=0, iDisplayLength=10)` alongside the existing `search(parsed: ParsedCitation)` — same POST/parsing logic (reuse `_parse_rows`, lines 493-562) but driven by a general filter dict, with `iDisplayStart`/`iDisplayLength` parameterized instead of hardcoded (`"0"`/`"10"`, line 434). Read `iTotalRecords`/`iTotalDisplayRecords` from `payload["reportrow"]` (currently discarded — only `aaData` is read, line 490) and return them.
- Keep the `httpx.AsyncClient` (cookies + `app_token`) alive across page requests instead of constructing a fresh `ESCRClient` per call, so follow-up pages can skip `_solve_and_verify_captcha()` — mirroring the real site's own behavior.
- Add a short-lived in-process session store (dict keyed by generated `session_id` → `{client, app_token, expires_at}`, TTL ~10 min, similar to the existing `CitationCache` in-process dedupe pattern at lines 602-614). First case-search call solves the captcha once and returns `session_id`; page requests reuse it, falling back to a fresh solve if the session is missing/expired.
- **Caveat to verify before shipping**: in-memory session storage only works cleanly on a single-process/single-worker deployment. If the scraper runs multi-worker/multi-replica, this needs sticky routing or Redis-backed session state — check actual deployment topology first.

**2. New FastAPI routes** (same router area as `lookup_citation`, `sc_citation_scraper.py:621`):
- `POST /api/ecourts/v2/case-search/search` — full filter payload + `page`/`page_size` → `{session_id, results, total_records, total_display_records}`.
- `POST /api/ecourts/v2/case-search/page` — `{session_id, page}` → reuses the stored session, no fresh captcha solve on the happy path.

**3. Django proxy layer**
- `Legalv1/ecourt_scrapped/services/citation_client.py`: add `search_case_law(filters, page, session_id=None)`, same thin-proxy pattern as `lookup_citation` (lines 24-38).
- `Legalv1/ecourt_scrapped/citation_views.py` + `urls.py` (lines 61-63): add a `case-search/` POST view. New cache key hashing the full filter set **and** page number (distinct from the existing `_cache_key(citation)`, lines 52-54). Long TTL is fine for cached *results* (decided cases are immutable) but `session_id` must **not** be cached at the Django layer — it's ephemeral, cookie-bound state.

**4. Filter set** (all field names already exist as named, currently-empty fields in `search()`'s payload, `sc_citation_scraper.py:432-454` — nothing new to invent server-side):
- Search mode: `search_opt` (Phrase / Any / All — currently hardcoded to `"PHRASE"`)
- Keyword: `search_txt1`
- Party names: `pet_res` (petitioner), `pet_res1` (respondent)
- Date range: `from_date`, `to_date`
- Judge name: `judge_name` / `judge_txt`
- Act & Section: `act` / `act_txt`, `section_txt`
- Case number/year: `case_no`, `case_year`
- SCR reference: `citation_yr`, `citation_vol`, `citation_supl` ("OR Supl" — currently never populated, a real gap today), `citation_page`
- Neutral citation: `neu_cit_year`, `neu_no`
- `fcourt_type` stays hardcoded `"3"` — this portal only searches Supreme Court Reports, not a real user-facing filter.

## Frontend changes

`new_frontend/src/components/citations/`:
- Mode toggle at the top of the page: "Verify Citation" (current single-box behavior, unchanged) vs. "Search Case Law" (new).
- New filter panel covering the fields above, grouped (Keyword + mode radio / Parties / SCR & Neutral citation / Date & Judge/Act).
- New results-list with true pagination — mirror the existing pattern in `new_frontend/src/components/ecourts/CaseSearch.jsx` (page/pageSize/`total_pages`, prev/next, `useSearchParams`, `useSearchCache` keyed by `(section, query, page, filters)` — already supports arbitrary `page`/`filters`, just unused by today's single-box `CitationSearch.jsx`).
- Track `session_id` in component state (not URL) between page navigations within one search — "next page" hits the cheap `/case-search/page` route; changing any filter starts a new session via `/case-search/search`.

## Related small fix

- Existing citation-lookup `match_count` (`sc_citation_scraper.py:681`) is `len(results)` from a single hardcoded 10-row page, not a true total — mislabeled. Leave "Verify Citation" behavior otherwise unchanged; rename/drop this field once "Search Case Law" has a real `total_records` to show instead.

## Click-to-resolve PDF (added after initial implementation)

Matching the real site's per-row Split view / HTML view / Flip view / PDF buttons (resolved on click, not preloaded for all rows), each result now carries opaque `pdf_ref_path`/`pdf_ref_year`/`pdf_ref_val` fields from `_parse_rows()`. Clicking a result calls a new `POST /case-search/resolve` route, which reuses the session's `ESCRClient` (no fresh captcha in the common case, same as pagination) and opens the resolved PDF in a new tab. `ESCRClient.resolve_pdf_url()` was updated to also respect `_session_verified` — as a side effect, this also fixes the existing single-citation `/lookup` flow, which was previously solving the captcha *twice* per request (once in `search()`, once in `resolve_pdf_url()`), doubling its failure surface. Django caches resolved PDF URLs independent of `session_id` (keyed by `path`/`year`/`val`), since a decided case's PDF is stable and shareable across sessions/users.

## Verification

- Backend: call `/case-search/search` with `search_opt=ANY`, keyword "land dispute", confirm `total_records` is in the thousands (matching the real site's `iTotalRecords`), not 10.
- Confirm pagination cost: call `/case-search/page` for page 2 right after `/case-search/search` and verify (logs/timing) it does **not** trigger a new CapSolver solve — this is the load-bearing assumption from the browser trace and must be confirmed against the live portal.
- Frontend: switch to "Search Case Law", run a keyword search, page through results, apply filters (e.g. date range + judge name).
- Confirm "Verify Citation" mode is untouched and still works for a known citation like `2024 INSC 45`.
