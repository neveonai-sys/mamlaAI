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

/** ~200-entry judge/member code list, used by the orders-by-judge modes. */
export const getCATJudges = () => apiClient.get(`${BASE}/judges/`);

// ─── Case Status Searches ────────────────────────────────────────────────────
// All 4 modes return { success, bench, cases: [...] }, each case row
// carrying a `detail_token` used by searchCATCaseDetail below.

export const searchCATByNumber = ({ bench, case_type, case_no, year }) =>
  apiClient.post(`${BASE}/case/by-number/`, { bench, case_type, case_no, year });

export const searchCATByDiary = ({ bench, diary_no, year }) =>
  apiClient.post(`${BASE}/case/by-diary/`, { bench, diary_no, year });

export const searchCATByParty = ({ bench, party_name, party_type }) =>
  apiClient.post(`${BASE}/case/by-party/`, { bench, party_name, party_type });

export const searchCATByAdvocate = ({ bench, advocate_name, advocate_type }) =>
  apiClient.post(`${BASE}/case/by-advocate/`, { bench, advocate_name, advocate_type });

/** Full case-detail drilldown — token comes from a search result's detail_token. */
export const searchCATCaseDetail = (token) =>
  apiClient.post(`${BASE}/case/detail/`, { token });

// ─── Cause List ───────────────────────────────────────────────────────────────

/** date must be dd-mm-yyyy */
export const getCATCauseList = ({ bench, date }) =>
  apiClient.post(`${BASE}/causelist/`, { bench, date });

// ─── Orders — Daily (5 modes) ─────────────────────────────────────────────────

export const getCATOrdersDailyByCase = ({ bench, case_type, case_no, year }) =>
  apiClient.post(`${BASE}/orders/daily/by-case/`, { bench, case_type, case_no, year });

export const getCATOrdersDailyByDiary = ({ bench, diary_no, year }) =>
  apiClient.post(`${BASE}/orders/daily/by-diary/`, { bench, diary_no, year });

export const getCATOrdersDailyByParty = ({ bench, party_name, party_type }) =>
  apiClient.post(`${BASE}/orders/daily/by-party/`, { bench, party_name, party_type });

/** from_date / to_date must be dd-mm-yyyy */
export const getCATOrdersDailyByDate = ({ bench, from_date, to_date }) =>
  apiClient.post(`${BASE}/orders/daily/by-date/`, { bench, from_date, to_date });

export const getCATOrdersDailyByJudge = ({ bench, judge_code }) =>
  apiClient.post(`${BASE}/orders/daily/by-judge/`, { bench, judge_code });

// ─── Orders — Final / Oral (4 modes) ──────────────────────────────────────────

export const getCATOrdersFinalByCase = ({ bench, case_type, case_no, year }) =>
  apiClient.post(`${BASE}/orders/final/by-case/`, { bench, case_type, case_no, year });

export const getCATOrdersFinalByDiary = ({ bench, diary_no, year }) =>
  apiClient.post(`${BASE}/orders/final/by-diary/`, { bench, diary_no, year });

/** from_date / to_date must be dd-mm-yyyy */
export const getCATOrdersFinalByDate = ({ bench, from_date, to_date }) =>
  apiClient.post(`${BASE}/orders/final/by-date/`, { bench, from_date, to_date });

export const getCATOrdersFinalByJudge = ({ bench, judge_code }) =>
  apiClient.post(`${BASE}/orders/final/by-judge/`, { bench, judge_code });

// ─── Judgments ────────────────────────────────────────────────────────────────

export const searchCATJudgments = ({ bench, query, from_year, to_year }) =>
  apiClient.post(`${BASE}/judgments/search/`, { bench, query, from_year, to_year });
