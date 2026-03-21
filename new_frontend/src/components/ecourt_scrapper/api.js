import apiClient from '../../services/api';

const BASE = 'ecourts';

function sleep(ms) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

export function unwrapTerminalPayload(payload) {
  if (!payload) return null;
  if (payload.result) return payload.result;
  if (payload.data) return payload.data;
  return payload;
}

export async function waitForEcourtsJob(jobId, options = {}) {
  const {
    intervalMs = 2500,
    maxAttempts = 36,
  } = options;

  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    const response = await apiClient.get(`${BASE}/jobs/${jobId}/`);
    const payload = response.data || {};

    if (payload.status === 'completed') {
      return payload;
    }

    if (payload.status === 'failed') {
      throw new Error(payload.error || 'The scraper job failed.');
    }

    await sleep(intervalMs);
  }

  throw new Error('The scraper job timed out before completing.');
}

export async function resolveEcourtsResponse(response) {
  if (response?.status === 202 && response?.data?.job_id) {
    const jobPayload = await waitForEcourtsJob(response.data.job_id);
    return {
      jobId: response.data.job_id,
      fromJob: true,
      data: unwrapTerminalPayload(jobPayload),
    };
  }

  return {
    jobId: response?.data?.job_id || null,
    fromJob: false,
    data: unwrapTerminalPayload(response?.data),
  };
}

export const getReferenceSection = (section) => apiClient.get(`${BASE}/reference/${section}/`);
export const getHighCourts = () => apiClient.get(`${BASE}/court-structure/high-courts/`);
export const getDistrictStates = () => apiClient.get(`${BASE}/court-structure/district/states/`);
export const getDistricts = (stateName) => apiClient.get(`${BASE}/court-structure/district/states/${encodeURIComponent(stateName)}/districts/`);
export const getComplexes = (stateName, districtName) => apiClient.get(`${BASE}/court-structure/district/states/${encodeURIComponent(stateName)}/districts/${encodeURIComponent(districtName)}/complexes/`);
export const getCourtsByComplex = (stateName, districtName, complexId) => apiClient.get(`${BASE}/court-structure/district/states/${encodeURIComponent(stateName)}/districts/${encodeURIComponent(districtName)}/complexes/${encodeURIComponent(complexId)}/courts/`);

export const getCaseByCnr = (cnr) => apiClient.get(`${BASE}/case/${encodeURIComponent(cnr)}/`);
export const getCaseOrders = (cnr) => apiClient.get(`${BASE}/case/${encodeURIComponent(cnr)}/orders/`);

export const searchCases = (payload) => apiClient.post(`${BASE}/search/`, payload);
export const getCauseList = (params) => apiClient.get(`${BASE}/causelist/`, { params });
export const getCauseListDates = (params) => apiClient.get(`${BASE}/causelist/dates/`, { params });

export async function ensureCaseLoaded(cnr) {
  const response = await getCaseByCnr(cnr);
  return resolveEcourtsResponse(response);
}

export async function runCaseSearch(payload) {
  const response = await searchCases(payload);
  return resolveEcourtsResponse(response);
}

export async function runCauseListSearch(params) {
  const response = await getCauseList(params);
  return resolveEcourtsResponse(response);
}