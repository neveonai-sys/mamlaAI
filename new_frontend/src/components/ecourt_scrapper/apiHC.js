/**
 * API client for the High Court eCourts scraper backend.
 *
 * Backend prefix: /api/ecourts/v2/hc/
 * Django proxies these to the HC FastAPI scraper on :8001.
 *
 * Note: Django views accept JSON bodies (POST) or query params (GET).
 * The HC FastAPI scraper itself is GET-only — the translation happens in Django.
 */
import apiClient from '../../services/api';

const BASE = 'ecourts/v2/hc';

// ─── Info / Health ────────────────────────────────────────────────────────────

export const getHCHealth = () => apiClient.get(`${BASE}/health/`);

/**
 * Returns all supported High Courts and their bench slugs + labels.
 * Shape: { hc_slug: { name, benches: { bench_slug: "Bench Label", ... } }, ... }
 */
export const getHCCourts = () => apiClient.get(`${BASE}/courts/`);

// ─── Metadata ────────────────────────────────────────────────────────────────

export const getHCPoliceStations = (hc, bench) =>
  apiClient.get(`${BASE}/meta/police-stations/`, { params: { hc, bench } });

export const getHCCourtNumbers = (hc, bench) =>
  apiClient.get(`${BASE}/meta/court-numbers/`, { params: { hc, bench } });

// ─── Case Lookup ─────────────────────────────────────────────────────────────

/**
 * Full case detail by CNR. HC/bench auto-detected from prefix.
 * Returns HCCaseDetail with hearing history, orders, linked cases, etc.
 */
export const searchHCCnr = (cino) =>
  apiClient.get(`${BASE}/case/cnr/${encodeURIComponent(cino.trim().toUpperCase())}/`);

// ─── Case Status Searches ────────────────────────────────────────────────────

export const searchHCParty = ({ hc, bench, name, year, status }) =>
  apiClient.post(`${BASE}/case/party/`, { hc, bench, name, year, status: status || 'Both' });

export const searchHCAdvocate = ({ hc, bench, query, status }) =>
  apiClient.post(`${BASE}/case/advocate/`, { hc, bench, query, status: status || 'Both' });

export const searchHCBarCode = ({ hc, bench, bar_code, status }) =>
  apiClient.post(`${BASE}/case/bar-code/`, { hc, bench, bar_code, status: status || 'Both' });

export const searchHCFiling = ({ hc, bench, filing_number, year, case_type }) =>
  apiClient.post(`${BASE}/case/filing/`, { hc, bench, filing_number, year, case_type });

export const searchHCFir = ({ hc, bench, police_station, status, fir_number, fir_year }) =>
  apiClient.post(`${BASE}/case/fir/`, { hc, bench, police_station, status, fir_number, fir_year });

// ─── Court Orders ─────────────────────────────────────────────────────────────

export const searchHCOrdersByParty = ({ hc, bench, name, year }) =>
  apiClient.post(`${BASE}/orders/search/`, { hc, bench, name, year });

/**
 * date_from / date_to must be YYYY-MM-DD
 */
export const searchHCOrdersByCourt = ({ hc, bench, judge_code, date_from, date_to }) =>
  apiClient.post(`${BASE}/orders/by-court/`, { hc, bench, judge_code, date_from, date_to });

/**
 * date_from / date_to must be DD-MM-YYYY (different from by-court!)
 */
export const searchHCOrdersByDate = ({ hc, bench, date_from, date_to }) =>
  apiClient.post(`${BASE}/orders/by-date/`, { hc, bench, date_from, date_to });

// ─── Cause List ───────────────────────────────────────────────────────────────

/**
 * list_date is optional (defaults to today on the scraper side). Format: DD-MM-YYYY.
 */
export const fetchHCCauseList = ({ hc, bench, list_date }) =>
  apiClient.post(`${BASE}/causelist/`, { hc, bench, list_date });

// ─── PDF Proxy ────────────────────────────────────────────────────────────────

/**
 * Download an HC order PDF proxied through our backend.
 * The HC portal requires a valid PHPSESSID cookie; the FastAPI scraper injects it.
 * Returns an Axios response with responseType: 'blob'.
 * Usage:
 *   const resp = await downloadHCOrderPdf(docUrl);
 *   const objUrl = URL.createObjectURL(new Blob([resp.data], { type: 'application/pdf' }));
 *   window.open(objUrl, '_blank');
 */
export const downloadHCOrderPdf = (pdf_url) =>
  apiClient.get(`${BASE}/order-pdf/`, { params: { pdf_url }, responseType: 'blob' });

export const downloadHCCauseListPdf = (pdf_url) =>
  apiClient.get(`${BASE}/causelist-pdf/`, { params: { pdf_url }, responseType: 'blob' });
