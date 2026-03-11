const TTL_MS = 30 * 60 * 1000;

function cacheKey(section) {
  return `ecourts_src_v1_${section}`;
}

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
      })
    );
  } catch {
    // Ignore sessionStorage failures.
  }
}

export function loadSearchCache(section, query, page, filters) {
  try {
    const raw = sessionStorage.getItem(cacheKey(section));
    if (!raw) return null;
    const cached = JSON.parse(raw);
    if (!cached || Date.now() - cached.ts > TTL_MS) return null;
    if (cached.query !== (query || '').trim()) return null;
    if (cached.page !== page) return null;
    if (JSON.stringify(cached.filters || {}) !== JSON.stringify(filters || {})) return null;
    return cached.results;
  } catch {
    return null;
  }
}

export function loadLastSearchCache(section) {
  try {
    const raw = sessionStorage.getItem(cacheKey(section));
    if (!raw) return null;
    const cached = JSON.parse(raw);
    if (!cached || Date.now() - cached.ts > TTL_MS) return null;
    return {
      query: cached.query,
      page: cached.page,
      filters: cached.filters,
      results: cached.results,
    };
  } catch {
    return null;
  }
}
