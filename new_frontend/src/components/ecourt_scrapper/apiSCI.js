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

// ─── Case Status Searches ────────────────────────────────────────────────────

export const searchSCIByNumber = ({ case_type, case_no, case_year }) =>
  apiClient.post(`${BASE}/case/by-number/`, { case_type, case_no, case_year });

export const searchSCIByDiary = ({ diary_no, diary_year }) =>
  apiClient.post(`${BASE}/case/by-diary/`, { diary_no, diary_year });

export const searchSCIByParty = ({ party_name, year }) =>
  apiClient.post(`${BASE}/case/by-party/`, { party_name, year });

export const searchSCIByAor = ({ aor_code, year }) =>
  apiClient.post(`${BASE}/case/by-aor/`, { aor_code, year });

// ─── Cause List ───────────────────────────────────────────────────────────────

export const getSCICauseListToday = () => apiClient.get(`${BASE}/causelist/today/`);

export const getSCICauseListTomorrow = () => apiClient.get(`${BASE}/causelist/tomorrow/`);

/** date must be DD-MM-YYYY */
export const getSCICauseListByDate = (date) =>
  apiClient.post(`${BASE}/causelist/by-date/`, { date });

// ─── Daily Orders ─────────────────────────────────────────────────────────────

export const searchSCIOrdersByCase = ({ case_type, case_no, case_year }) =>
  apiClient.post(`${BASE}/orders/by-case/`, { case_type, case_no, case_year });

export const searchSCIOrdersByDiary = ({ diary_no, diary_year }) =>
  apiClient.post(`${BASE}/orders/by-diary/`, { diary_no, diary_year });

// ─── Judgments ────────────────────────────────────────────────────────────────

export const searchSCIJudgmentsByCase = ({ case_type, case_no, case_year }) =>
  apiClient.post(`${BASE}/judgments/by-case/`, { case_type, case_no, case_year });

export const searchSCIJudgmentsByParty = ({ party_name }) =>
  apiClient.post(`${BASE}/judgments/by-party/`, { party_name });

/** from_date / to_date must be DD-MM-YYYY */
export const searchSCIJudgmentsByDate = ({ from_date, to_date }) =>
  apiClient.post(`${BASE}/judgments/by-date/`, { from_date, to_date });

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
