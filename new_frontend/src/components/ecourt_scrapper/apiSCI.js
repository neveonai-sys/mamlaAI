/**
 * API client for the Supreme Court of India (SCI) case-search backend.
 *
 * Backend prefix: /api/ecourts/v2/sci/
 * Django proxies these to the SCI FastAPI scraper (mounted at /sci).
 */
import apiClient from '../../services/api';

const BASE = 'ecourts/v2/sci';

// ─── Info / Metadata ──────────────────────────────────────────────────────────

export const getSCIHealth = () => apiClient.get(`${BASE}/health/`);

export const getSCICaseTypes = () => apiClient.get(`${BASE}/case-types/`);

export const getSCIJudges = () => apiClient.get(`${BASE}/judges/`);

// ─── Case Status Searches ────────────────────────────────────────────────────

export const searchSCIByNumber = ({ case_type, case_no, case_year }) =>
  apiClient.post(`${BASE}/case/by-number/`, { case_type, case_no, case_year });

export const searchSCIByDiary = ({ diary_no, diary_year }) =>
  apiClient.post(`${BASE}/case/by-diary/`, { diary_no, diary_year });

/**
 * year, party_type ('any'|'P' Petitioner|'R' Respondent), and party_status
 * ('P' Pending|'D' Disposed) are all required by the portal's own form —
 * confirmed live, omitting any of them gets rejected server-side.
 */
export const searchSCIByParty = ({ party_name, year, party_type, party_status }) =>
  apiClient.post(`${BASE}/case/by-party/`, { party_name, year, party_type, party_status });

export const searchSCIByAor = ({ aor_code, year }) =>
  apiClient.post(`${BASE}/case/by-aor/`, { aor_code, year });

export const searchSCIByCnr = ({ cnr_no }) =>
  apiClient.post(`${BASE}/case/by-cnr/`, { cnr_no });

// ─── Case Status — Court cascade (Court → State → Bench → Case Type) ────────

export const getSCICaseStatusCourtStates = (court) =>
  apiClient.get(`${BASE}/case-status-court/states/`, { params: { court } });

export const getSCICaseStatusCourtBenches = (court, state) =>
  apiClient.get(`${BASE}/case-status-court/benches/`, { params: { court, state } });

export const getSCICaseStatusCourtCaseTypes = (court, state, bench) =>
  apiClient.get(`${BASE}/case-status-court/case-types/`, { params: { court, state, bench } });

export const searchSCIByCourt = ({ court, state, bench, case_type, case_no, year, listing_date }) =>
  apiClient.post(`${BASE}/case/by-court/`, { court, state, bench, case_type, case_no, year, listing_date });

/**
 * Case-detail drill-down — no CAPTCHA involved on the backend, so this
 * resolves in well under a second (unlike the search endpoints above).
 * tab_name defaults to the main Case Details tab; other known values:
 * argument_transcripts, indexing, earlier_court_details, tagged_matters, listing_dates.
 */
export const getSCICaseDetails = (diary_no, diary_year, tab_name) =>
  apiClient.get(`${BASE}/case/details/`, { params: { diary_no, diary_year, tab_name } });

// ─── Cause List ───────────────────────────────────────────────────────────────

export const getSCICauseListToday = () => apiClient.get(`${BASE}/causelist/today/`);

export const getSCICauseListTomorrow = () => apiClient.get(`${BASE}/causelist/tomorrow/`);

/** date must be DD-MM-YYYY */
export const getSCICauseListByDate = (date) =>
  apiClient.post(`${BASE}/causelist/by-date/`, { date });

/**
 * Full-filter cause list search — list_type ('daily'|'other'), search_by
 * ('all_courts'|'court'|'judge'|'aor_code'|'party_name') plus its matching
 * sub-field, causelist_type, listing_date OR listing_date_from/to (used when
 * causelist_type === 'weekly'), and msb ('main'|'suppli'|'both').
 */
export const searchSCICauseListFull = (filters) =>
  apiClient.post(`${BASE}/causelist/search/`, filters);

// ─── Daily Orders ─────────────────────────────────────────────────────────────

export const searchSCIOrdersByCase = ({ case_type, case_no, case_year }) =>
  apiClient.post(`${BASE}/orders/by-case/`, { case_type, case_no, case_year });

export const searchSCIOrdersByDiary = ({ diary_no, diary_year }) =>
  apiClient.post(`${BASE}/orders/by-diary/`, { diary_no, diary_year });

/** from_date / to_date must be DD-MM-YYYY */
export const searchSCIOrdersByRopDate = ({ from_date, to_date }) =>
  apiClient.post(`${BASE}/orders/by-rop-date/`, { from_date, to_date });

export const searchSCIOrdersFreeText = ({ search_text, from_date, to_date }) =>
  apiClient.post(`${BASE}/orders/free-text/`, { search_text, from_date, to_date });

// ─── Judgments ────────────────────────────────────────────────────────────────

export const searchSCIJudgmentsByCase = ({ case_type, case_no, case_year }) =>
  apiClient.post(`${BASE}/judgments/by-case/`, { case_type, case_no, case_year });

export const searchSCIJudgmentsByParty = ({ party_name }) =>
  apiClient.post(`${BASE}/judgments/by-party/`, { party_name });

/** from_date / to_date must be DD-MM-YYYY */
export const searchSCIJudgmentsByDate = ({ from_date, to_date }) =>
  apiClient.post(`${BASE}/judgments/by-date/`, { from_date, to_date });

export const searchSCIJudgmentsByDiary = ({ diary_no, year }) =>
  apiClient.post(`${BASE}/judgments/by-diary/`, { diary_no, year });

/** from_date / to_date must be DD-MM-YYYY, max 30-day range (portal-enforced) */
export const searchSCIJudgmentsByJudge = ({ judge, from_date, to_date }) =>
  apiClient.post(`${BASE}/judgments/by-judge/`, { judge, from_date, to_date });

/** from_date / to_date must be DD-MM-YYYY, max 30-day range (portal-enforced) */
export const searchSCIJudgmentsFreeText = ({ search_text, from_date, to_date }) =>
  apiClient.post(`${BASE}/judgments/free-text/`, { search_text, from_date, to_date });

// ─── Office Reports ───────────────────────────────────────────────────────────

export const searchSCIOfficeReportByCase = ({ case_type, case_no, case_year }) =>
  apiClient.post(`${BASE}/office-report/by-case/`, { case_type, case_no, case_year });

export const searchSCIOfficeReportByDiary = ({ diary_no, diary_year }) =>
  apiClient.post(`${BASE}/office-report/by-diary/`, { diary_no, diary_year });

// ─── Document / PDF ───────────────────────────────────────────────────────────

/**
 * Download an SCI document PDF proxied through our backend.
 * Returns an Axios response with responseType: 'blob'.
 * Usage:
 *   const resp = await downloadSCIPdf(doc_url);
 *   const objUrl = URL.createObjectURL(new Blob([resp.data], { type: 'application/pdf' }));
 *   window.open(objUrl, '_blank');
 */
export const downloadSCIPdf = (doc_url) =>
  apiClient.post(`${BASE}/document/pdf/`, { doc_url }, { responseType: 'blob' });
