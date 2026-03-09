/**
 * Client-side sessionStorage cache for eCourts search results.
 *
 * Why sessionStorage (not localStorage)?
 *   - Clears when the tab closes → no stale legal data across sessions.
 *   - Synchronous read → instant result restore on back-navigation, zero API call.
 *
 * Cache key: one slot per section (cases / lawyers / litigants).
 * Stores the most recent query + page + filters + results.
 * TTL: 30 minutes. After that the next identical query re-fetches.
 *
 * Back-navigation flow:
 *   1. Search fires → on success → saveSearchCache(...)
 *   2. User clicks CaseCard → /ecourts/case/XXX
 *   3. Browser back → search component remounts with same URL params
 *   4. doSearch checks cache → hit → setResults(cached), no API call.
 */

const TTL_MS = 30 * 60 * 1000; // 30 minutes

function cacheKey(section) {
  return `ecourts_src_v1_${section}`;
}

/**
 * Persist search results to sessionStorage.
 * @param {string}  section   'cases' | 'lawyers' | 'litigants'
 * @param {string}  query
 * @param {number}  page
 * @param {object}  filters   plain object (will be JSON-compared on lookup)
 * @param {*}       results   whatever the API returns (case_list, total, etc.)
 */
export function saveSearchCache(section, query, page, filters, results) {
  try {
    sessionStorage.setItem(
      cacheKey(section),
      JSON.stringify({
        query: (query || '').trim(),
        page,
        filters: filters || {},
        results,
        ts: Date.now(),
      }),
    );
  } catch {
    // Quota exceeded or private-browsing restriction — silently ignore.
  }
}

/**
 * Retrieve cached results for an exact query+page+filters match.
 * Returns null on miss, expiry, or mismatch.
 */
export function loadSearchCache(section, query, page, filters) {
  try {
    const raw = sessionStorage.getItem(cacheKey(section));
    if (!raw) return null;
    const c = JSON.parse(raw);
    if (!c || Date.now() - c.ts > TTL_MS) return null;
    if (c.query !== (query || '').trim()) return null;
    if (c.page !== page) return null;
    if (JSON.stringify(c.filters || {}) !== JSON.stringify(filters || {})) return null;
    return c.results;
  } catch {
    return null;
  }
}

/**
 * Load the last cached entry for a section regardless of query/page.
 * Used to preload results when a search page is opened with no active query
 * (e.g. clicking a feature card from the eCourts home page).
 * Returns { query, page, results } or null.
 */
export function loadLastSearchCache(section) {
  try {
    const raw = sessionStorage.getItem(cacheKey(section));
    if (!raw) return null;
    const c = JSON.parse(raw);
    if (!c || Date.now() - c.ts > TTL_MS) return null;
    return { query: c.query, page: c.page, filters: c.filters, results: c.results };
  } catch {
    return null;
  }
}
