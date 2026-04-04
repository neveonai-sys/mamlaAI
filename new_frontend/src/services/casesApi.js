/**
 * Cases API — all calls to /api/cases/
 * Uses the shared apiClient (auth header + base URL already configured).
 */
import apiClient from './api';

const BASE = 'cases';

// ── Cases ──────────────────────────────────────────────────────────────────

export function createCase(payload) {
  return apiClient.post(`${BASE}/create/`, payload);
}

export function listCases(params = {}) {
  return apiClient.get(`${BASE}/list/`, { params });
}

export function getCase(caseId) {
  return apiClient.get(`${BASE}/${caseId}/`);
}

export function updateCase(caseId, payload) {
  return apiClient.patch(`${BASE}/${caseId}/update/`, payload);
}

export function closeCase(caseId, payload) {
  return apiClient.post(`${BASE}/${caseId}/close/`, payload);
}

export function getCaseTimeline(caseId) {
  return apiClient.get(`${BASE}/${caseId}/timeline/`);
}

// ── Hearing notes ──────────────────────────────────────────────────────────

export function createHearingNote(caseId, payload) {
  return apiClient.post(`${BASE}/${caseId}/hearing-notes/`, payload);
}

export function listHearingNotes(caseId) {
  return apiClient.get(`${BASE}/${caseId}/hearing-notes/list/`);
}

export function getHearingNote(caseId, noteId) {
  return apiClient.get(`${BASE}/${caseId}/hearing-notes/${noteId}/`);
}

export function updateHearingNote(caseId, noteId, payload) {
  return apiClient.patch(`${BASE}/${caseId}/hearing-notes/${noteId}/update/`, payload);
}

// ── Case notes ─────────────────────────────────────────────────────────────

export function createCaseNote(caseId, payload) {
  return apiClient.post(`${BASE}/${caseId}/notes/`, payload);
}

export function listCaseNotes(caseId) {
  return apiClient.get(`${BASE}/${caseId}/notes/list/`);
}

export function updateCaseNote(caseId, noteId, payload) {
  return apiClient.patch(`${BASE}/${caseId}/notes/${noteId}/update/`, payload);
}

export function deleteCaseNote(caseId, noteId) {
  return apiClient.delete(`${BASE}/${caseId}/notes/${noteId}/delete/`);
}

// ── Case tasks ─────────────────────────────────────────────────────────────

export function createCaseTask(caseId, payload) {
  return apiClient.post(`${BASE}/${caseId}/tasks/`, payload);
}

export function listCaseTasks(caseId, params = {}) {
  return apiClient.get(`${BASE}/${caseId}/tasks/list/`, { params });
}

export function updateCaseTask(caseId, taskId, payload) {
  return apiClient.patch(`${BASE}/${caseId}/tasks/${taskId}/update/`, payload);
}

export function deleteCaseTask(caseId, taskId) {
  return apiClient.delete(`${BASE}/${caseId}/tasks/${taskId}/delete/`);
}

// ─── Agents (/api/agents/) ────────────────────────────────────────────────

const AGENTS = 'agents';

export function runCaseIntakeAgent(payload) {
  return apiClient.post(`${AGENTS}/case-intake/`, payload);
}

export function runDocumentIntelAgent(caseId, documentIds) {
  return apiClient.post(`${AGENTS}/document-intel/`, { case_id: caseId, document_ids: documentIds });
}

export function runHearingPrepAgent(caseId, hearingDate, purpose, opts = {}) {
  return apiClient.post(`${AGENTS}/hearing-prep/`, {
    case_id: caseId,
    hearing_date: hearingDate,
    purpose,
    ...opts,
  });
}

export function runPostHearingAgent(caseId, hearingNotesId, outcomeText, nextDate = '') {
  return apiClient.post(`${AGENTS}/post-hearing/`, {
    case_id: caseId,
    hearing_notes_id: hearingNotesId,
    outcome_text: outcomeText,
    next_date: nextDate,
  });
}

export function runDraftContextAgent(caseId, draftType, documentIds = []) {
  return apiClient.post(`${AGENTS}/draft-context/`, {
    case_id: caseId,
    draft_type: draftType,
    document_ids: documentIds,
  });
}

export function runCaseClosureAgent(caseId, resolutionType, resolutionSummary) {
  return apiClient.post(`${AGENTS}/case-closure/`, {
    case_id: caseId,
    resolution_type: resolutionType,
    resolution_summary: resolutionSummary,
  });
}

export function listCalendarEventsByCase(caseId, upcoming = true) {
  return apiClient.get('calendar/events/', { params: { case_id: caseId, upcoming: upcoming ? 'true' : undefined, page_size: 500 } });
}
