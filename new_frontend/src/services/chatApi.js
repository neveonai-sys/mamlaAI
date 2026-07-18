/**
 * MamlaAI Chat API — all calls to /api/brain/v2/
 * The unified multi-agent chat surface. Uses the shared apiClient (auth cookie /
 * bearer + base URL already configured).
 *
 * Phase 0 is non-streaming (`sendChat`). The SSE streaming client
 * (`streamChat` via EventSource) lands in Phase 1.
 */
import { Capacitor } from '@capacitor/core';
import { Preferences } from '@capacitor/preferences';
import apiClient, { NATIVE_TOKEN_KEY } from './api';

const BASE = 'brain/v2';

async function _authHeaders() {
  const headers = { 'Content-Type': 'application/json' };
  if (Capacitor.isNativePlatform()) {
    const { value } = await Preferences.get({ key: NATIVE_TOKEN_KEY });
    if (value) headers['Authorization'] = `Bearer ${value}`;
  }
  return headers;
}

export function createSession(payload = {}) {
  return apiClient.post(`${BASE}/sessions/`, payload);
}

export function listSessions(params = {}) {
  return apiClient.get(`${BASE}/sessions/list/`, { params });
}

export function getMessages(sessionId) {
  return apiClient.get(`${BASE}/sessions/${sessionId}/messages/`);
}

export function renameSession(sessionId, title) {
  return apiClient.patch(`${BASE}/sessions/${sessionId}/`, { title });
}

export function deleteSession(sessionId) {
  return apiClient.delete(`${BASE}/sessions/${sessionId}/`);
}

/** Per-tier token/credit usage breakdown for the Wallet page. */
export function getUsageSummary() {
  return apiClient.get(`${BASE}/usage-summary/`);
}

/** Live sections for a chat-created draft (re-sync the in-chat canvas). */
export function getDraftSections(draftSessionId) {
  return apiClient.get(`${BASE}/drafts/${draftSessionId}/sections/`);
}

/** Write-through one edited section from the in-chat canvas. */
export function updateDraftSection(draftSessionId, section) {
  return apiClient.post(`${BASE}/drafts/${draftSessionId}/section/`, {
    section_id: section.section_id,
    section_name: section.section_name,
    content: section.content,
  });
}

export function uploadDoc(sessionId, file) {
  const form = new FormData();
  form.append('file', file);
  return apiClient.post(`${BASE}/sessions/${sessionId}/upload/`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
}

/**
 * Send one chat turn.
 * @param {string} sessionId
 * @param {string} text
 * @param {{ model_level?: 'low'|'medium'|'high', premium?: boolean }} opts
 */
export function sendChat(sessionId, text, opts = {}) {
  return apiClient.post(`${BASE}/sessions/${sessionId}/chat/`, {
    text,
    model_level: opts.model_level || 'medium',
    premium: !!opts.premium,
  });
}

/**
 * Stream one chat turn as Server-Sent Events.
 *
 * Our endpoint is POST (it carries the message + model selection), so we use
 * fetch()'s streaming body instead of EventSource (which is GET-only) and parse
 * the SSE frames by hand.
 *
 * @param {object} handlers { onToolCall, onToolResult, onToken, onCitation, onDone, onError }
 * @returns {Promise<void>} resolves when the stream ends
 */
export async function streamChat(sessionId, text, opts = {}, handlers = {}) {
  const url = `${apiClient.defaults.baseURL}${BASE}/sessions/${sessionId}/chat/stream/`;
  let resp;
  try {
    resp = await fetch(url, {
      method: 'POST',
      credentials: Capacitor.isNativePlatform() ? 'omit' : 'include',
      headers: await _authHeaders(),
      body: JSON.stringify({
        text,
        model_level: opts.model_level || 'medium',
        premium: !!opts.premium,
      }),
    });
  } catch (e) {
    handlers.onError && handlers.onError('Network error. Please retry.');
    return;
  }
  if (!resp.ok || !resp.body) {
    handlers.onError && handlers.onError(`Request failed (${resp.status})`);
    return;
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  const dispatch = (evt) => {
    switch (evt.type) {
      case 'tool_call':   handlers.onToolCall && handlers.onToolCall(evt); break;
      case 'tool_result': handlers.onToolResult && handlers.onToolResult(evt); break;
      case 'token':       handlers.onToken && handlers.onToken(evt.text || ''); break;
      case 'citation':    handlers.onCitation && handlers.onCitation(evt); break;
      case 'done':        handlers.onDone && handlers.onDone(evt); break;
      case 'error':       handlers.onError && handlers.onError(evt.message || 'Error'); break;
      default: break;
    }
  };

  // eslint-disable-next-line no-constant-condition
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let idx;
    while ((idx = buffer.indexOf('\n\n')) !== -1) {
      const frame = buffer.slice(0, idx);
      buffer = buffer.slice(idx + 2);
      for (const line of frame.split('\n')) {
        if (!line.startsWith('data:')) continue;
        const payload = line.slice(5).trim();
        if (!payload) continue;
        try { dispatch(JSON.parse(payload)); } catch (_) { /* ignore partial */ }
      }
    }
  }
}
