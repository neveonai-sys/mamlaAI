/**
 * API client for the new eCourts v2 backend (ecourt_scrapped Django app).
 *
 * Backend prefix: /api/ecourts/v2/
 * Proxied through Django → FastAPI scraper on :3000
 *
 * All dropdown endpoints are cached in MongoDB by the backend.
 * All search/resolve endpoints call the scraper live.
 */
import apiClient from '../../services/api';

const BASE = 'ecourts/v2';

// ─── Dropdown / Master Data (cached) ─────────────────────────────────────────

export const getStates = () => apiClient.get(`${BASE}/states/`);

export const getDistricts = (stateCode) =>
  apiClient.post(`${BASE}/districts/`, { state_code: stateCode });

export const getComplexes = (stateCode, distCode) =>
  apiClient.post(`${BASE}/complexes/`, { state_code: stateCode, dist_code: distCode });

export const getEstablishments = (stateCode, distCode, courtComplexCode) =>
  apiClient.post(`${BASE}/establishments/`, {
    state_code: stateCode,
    dist_code: distCode,
    court_complex_code: courtComplexCode,
  });

export const getCourts = (stateCode, distCode, courtComplexCode, estCode) =>
  apiClient.post(`${BASE}/courts/`, {
    state_code: stateCode,
    dist_code: distCode,
    court_complex_code: courtComplexCode,
    est_code: estCode,
  });

export const getPoliceStations = (stateCode, distCode, courtComplexCode, estCode) =>
  apiClient.post(`${BASE}/police-stations/`, {
    state_code: stateCode,
    dist_code: distCode,
    court_complex_code: courtComplexCode,
    est_code: estCode,
  });

export const getOrderCaseTypes = (stateCode, distCode, courtComplexCode, estCode) =>
  apiClient.post(`${BASE}/order-case-types/`, {
    state_code: stateCode,
    dist_code: distCode,
    court_complex_code: courtComplexCode,
    est_code: estCode,
  });

export const getOrderCourtNumbers = (stateCode, distCode, courtComplexCode, estCode) =>
  apiClient.post(`${BASE}/order-court-numbers/`, {
    state_code: stateCode,
    dist_code: distCode,
    court_complex_code: courtComplexCode,
    est_code: estCode,
  });

// ─── Flow A: Direct Case Lookup ──────────────────────────────────────────────

export const cnrSearch = (cnrNumber) =>
  apiClient.post(`${BASE}/cnr/search/`, { cnr_number: cnrNumber });

export const caseByCino = (cino) =>
  apiClient.post(`${BASE}/case/by-cino/`, { cino });

// ─── Shared Resolvers ────────────────────────────────────────────────────────

export const caseFromUrl = (viewHistoryUrl) =>
  apiClient.post(`${BASE}/case/from-url/`, { view_history_url: viewHistoryUrl });

export const caseHistory = (params) =>
  apiClient.post(`${BASE}/case/history/`, params);

/**
 * Unified case detail resolver.
 * Pass view_history_url, cino, or cnr_number (tries in that order).
 */
export const caseDetail = (params) =>
  apiClient.post(`${BASE}/case/detail/`, params);

/**
 * Download court order PDF.
 * Pass the pdf_params object from interim_orders.
 */
export const orderPdf = (pdfParams) =>
  apiClient.post(`${BASE}/case/order-pdf/`, pdfParams, { responseType: 'blob' });

// ─── Flow B: Cause List ──────────────────────────────────────────────────────

export const causelistFetch = (params) =>
  apiClient.post(`${BASE}/causelist/fetch/`, params);

// ─── Flow C: Case Status Search ──────────────────────────────────────────────

export const casestatusByParty = (params) =>
  apiClient.post(`${BASE}/casestatus/by-party/`, params);

export const casestatusByFiling = (params) =>
  apiClient.post(`${BASE}/casestatus/by-filing/`, params);

export const casestatusByAdvocate = (params) =>
  apiClient.post(`${BASE}/casestatus/by-advocate/`, params);

export const casestatusByFir = (params) =>
  apiClient.post(`${BASE}/casestatus/by-fir/`, params);

// ─── Flow D: Court Orders Search ─────────────────────────────────────────────

export const courtorderByParty = (params) =>
  apiClient.post(`${BASE}/courtorder/by-party/`, params);

export const courtorderByCaseNumber = (params) =>
  apiClient.post(`${BASE}/courtorder/by-case-number/`, params);

export const courtorderByCourtNumber = (params) =>
  apiClient.post(`${BASE}/courtorder/by-court-number/`, params);

export const courtorderByOrderDate = (params) =>
  apiClient.post(`${BASE}/courtorder/by-order-date/`, params);

// ─── Health ──────────────────────────────────────────────────────────────────

export const scraperHealth = () => apiClient.get(`${BASE}/health/`);
