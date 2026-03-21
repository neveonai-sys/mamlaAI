// Deprecated helper surface: legacy frontend_webpack eCourts integration.
// Keep only as historical reference while the active app moves to the
// scraper-first terminal flow and drops the retired partner API path.

import AxiosInstance from '../common/AxiosInstance';

const BASE = 'ecourts';

// ── Case ────────────────────────────────────────────────────────────

export const getCaseByCnr = (cnr) =>
  AxiosInstance.get(`${BASE}/case/${cnr}/`);

export const refreshCase = (cnr) =>
  AxiosInstance.post(`${BASE}/case/${cnr}/refresh/`);

export const getCaseOrders = (cnr) =>
  AxiosInstance.get(`${BASE}/case/${cnr}/orders/`);

export const downloadOrder = (cnr, idx) =>
  AxiosInstance.get(`${BASE}/case/${cnr}/orders/${idx}/download/`, {
    responseType: 'blob',
  });

// ── Search ──────────────────────────────────────────────────────────

export const searchCases = ({
  searchType = 'general',
  query,
  page = 1,
  pageSize = 20,
  courtCodes,
  caseStatuses,
  caseTypes,
  filingDateFrom,
  filingDateTo,
} = {}) =>
  AxiosInstance.post(`${BASE}/search/`, {
    search_type: searchType,
    query,
    page,
    page_size: pageSize,
    ...(courtCodes && { court_codes: courtCodes }),
    ...(caseStatuses && { case_statuses: caseStatuses }),
    ...(caseTypes && { case_types: caseTypes }),
    ...(filingDateFrom && { filing_date_from: filingDateFrom }),
    ...(filingDateTo && { filing_date_to: filingDateTo }),
  });

// ── Cause List ──────────────────────────────────────────────────────

export const getCauseList = (params) =>
  AxiosInstance.get(`${BASE}/causelist/`, { params });

export const getCauseListDates = (params) =>
  AxiosInstance.get(`${BASE}/causelist/dates/`, { params });

// ── Court Structure (FREE) ──────────────────────────────────────────

export const getCourtStructure = () =>
  AxiosInstance.get(`${BASE}/court-structure/`);

export const getStates = () =>
  AxiosInstance.get(`${BASE}/court-structure/states/`);

export const getDistricts = (stateCode) =>
  AxiosInstance.get(`${BASE}/court-structure/states/${stateCode}/districts/`);

export const getComplexes = (stateCode, districtCode) =>
  AxiosInstance.get(
    `${BASE}/court-structure/states/${stateCode}/districts/${districtCode}/complexes/`
  );

export const getCourts = (stateCode, districtCode, complexCode) =>
  AxiosInstance.get(
    `${BASE}/court-structure/states/${stateCode}/districts/${districtCode}/complexes/${complexCode}/courts/`
  );

export const getHighCourts = () =>
  AxiosInstance.get(`${BASE}/court-structure/high-courts/`);

// ── Default / pre-populated results ────────────────────────────────

/**
 * GET /api/ecourts/defaults/<section>/
 * Returns server-side pre-populated results for a section's landing page
 * (populated daily/weekly by Celery Beat tasks, stored in MongoDB).
 * section: 'cases' | 'lawyers' | 'litigants'
 * Response: { status: 'success'|'empty', refreshed_at, data }
 */
export const getEcourtsDefaults = (section) =>
  AxiosInstance.get(`${BASE}/defaults/${section}/`);
