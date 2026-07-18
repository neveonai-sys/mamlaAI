/**
 * Supreme Court citation lookup API client.
 *
 * Backend: Legalv1/ecourt_scrapped/citation_views.py, mounted at
 * /api/ecourts/v2/citations/ (same Django app that proxies the DC/HC
 * eCourts scrapers, extended with a third FastAPI sub-app at /sc).
 */
import apiClient from '../../services/api';

const BASE = 'ecourts/v2/citations';

export function unwrapCitationPayload(response) {
  return response?.data ?? null;
}

export const lookupCitation = (citation) =>
  apiClient.post(`${BASE}/lookup/`, { citation });

export const citationHealthCheck = () => apiClient.get(`${BASE}/health/`);

// "Search Case Law" mode — filtered, paginated multi-result search, distinct
// from lookupCitation's single-best-match citation verification above.
export const searchCaseLaw = (filters, page = 1, pageSize = 10) =>
  apiClient.post(`${BASE}/case-search/search/`, { filters, page, page_size: pageSize });

export const searchCaseLawPage = (sessionId, page, pageSize = 10) =>
  apiClient.post(`${BASE}/case-search/page/`, { session_id: sessionId, page, page_size: pageSize });

export const resolveCaseSearchPdf = (sessionId, { path, year, val, ncDisplay }) =>
  apiClient.post(`${BASE}/case-search/resolve/`, {
    session_id: sessionId, path, year, val, nc_display: ncDisplay || '',
  });
