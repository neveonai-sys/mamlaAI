// Deprecated helper surface: this file reflects the older direct-API-shaped
// eCourts screens. New work should target the scraper-first terminal flow
// under src/components/ecourt_scrapper and the scraper runtime at /api/ecourts/.

import apiClient from '../../../services/api';

const BASE = 'ecourts';

export function unwrapEcourtsPayload(response) {
  return response?.data?.data ?? response?.data ?? null;
}

export const getCaseByCnr = (cnr) => apiClient.get(`${BASE}/case/${cnr}/`);

export const refreshCase = (cnr) => apiClient.post(`${BASE}/case/${cnr}/refresh/`);

export const getCaseOrders = (cnr) => apiClient.get(`${BASE}/case/${cnr}/orders/`);

export const downloadOrder = (cnr, index) =>
  apiClient.get(`${BASE}/case/${cnr}/orders/${index}/download/`, {
    responseType: 'blob',
  });

export const searchEcourts = ({
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
  apiClient.post(`${BASE}/search/`, {
    search_type: searchType,
    query,
    page,
    page_size: pageSize,
    ...(courtCodes ? { court_codes: courtCodes } : {}),
    ...(caseStatuses ? { case_statuses: caseStatuses } : {}),
    ...(caseTypes ? { case_types: caseTypes } : {}),
    ...(filingDateFrom ? { filing_date_from: filingDateFrom } : {}),
    ...(filingDateTo ? { filing_date_to: filingDateTo } : {}),
  });

export const getCauseList = (params) => apiClient.get(`${BASE}/causelist/`, { params });

export const getCauseListDates = (params) => apiClient.get(`${BASE}/causelist/dates/`, { params });

export const getCourtStructure = () => apiClient.get(`${BASE}/court-structure/`);

export const getStates = () => apiClient.get(`${BASE}/court-structure/states/`);

export const getDistricts = (stateCode) =>
  apiClient.get(`${BASE}/court-structure/states/${stateCode}/districts/`);

export const getComplexes = (stateCode, districtCode) =>
  apiClient.get(`${BASE}/court-structure/states/${stateCode}/districts/${districtCode}/complexes/`);

export const getCourts = (stateCode, districtCode, complexCode) =>
  apiClient.get(`${BASE}/court-structure/states/${stateCode}/districts/${districtCode}/complexes/${complexCode}/courts/`);

export const getHighCourts = () => apiClient.get(`${BASE}/court-structure/high-courts/`);

export const getEcourtsDefaults = (section) => apiClient.get(`${BASE}/defaults/${section}/`);
