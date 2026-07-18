/**
 * API client for the Central Administrative Tribunal (CAT) case-search backend.
 *
 * Backend prefix: /api/ecourts/v2/cat/
 * Django proxies these to the CAT FastAPI scraper (mounted at /cat).
 *
 * CAT has no CAPTCHA and returns direct, stable PDF URLs inline in the JSON
 * response — there is no download/blob helper here (unlike SCI/DC), render
 * the returned `pdf_url` as a plain <a href target="_blank"> link.
 */
import apiClient from '../../services/api';

const BASE = 'ecourts/v2/cat';

// ─── Info / Metadata ──────────────────────────────────────────────────────────

export const getCATHealth = () => apiClient.get(`${BASE}/health/`);

export const getCATBenches = () => apiClient.get(`${BASE}/benches/`);

export const getCATCaseTypes = () => apiClient.get(`${BASE}/case-types/`);

// ─── Case Status Searches ────────────────────────────────────────────────────

export const searchCATByNumber = ({ bench, case_type, case_no, year }) =>
  apiClient.post(`${BASE}/case/by-number/`, { bench, case_type, case_no, year });

export const searchCATByDiary = ({ bench, diary_no, year }) =>
  apiClient.post(`${BASE}/case/by-diary/`, { bench, diary_no, year });

export const searchCATByParty = ({ bench, party_name, party_type }) =>
  apiClient.post(`${BASE}/case/by-party/`, { bench, party_name, party_type });

export const searchCATByAdvocate = ({ bench, advocate_name, advocate_type }) =>
  apiClient.post(`${BASE}/case/by-advocate/`, { bench, advocate_name, advocate_type });

// ─── Cause List ───────────────────────────────────────────────────────────────

/** date must be dd-mm-yyyy */
export const getCATCauseList = ({ bench, date }) =>
  apiClient.post(`${BASE}/causelist/`, { bench, date });

// ─── Orders ───────────────────────────────────────────────────────────────────

/** date must be dd-mm-yyyy */
export const getCATOrdersDaily = ({ bench, date }) =>
  apiClient.post(`${BASE}/orders/daily/`, { bench, date });

export const getCATOrdersFinal = ({ bench, case_type, case_no, year }) =>
  apiClient.post(`${BASE}/orders/final/`, { bench, case_type, case_no, year });

// ─── Judgments ────────────────────────────────────────────────────────────────

export const searchCATJudgments = ({ bench, query, from_year, to_year }) =>
  apiClient.post(`${BASE}/judgments/search/`, { bench, query, from_year, to_year });
