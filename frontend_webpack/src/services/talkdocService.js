import axiosInstance from '../components/common/AxiosInstance.jsx';
import { secureLocalStorage, secureSessionStorage } from '../utils/securityUtils';

const TalkDocService = {
  async uploadDocument(file, title) {
    const formData = new FormData();
    formData.append('file', file);
    if (title) formData.append('title', title);

    const res = await axiosInstance.post('/talkdoc/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data; // { doc_id, chunk_count, title }
  },

  async startSession(title, docIds) {
    const res = await axiosInstance.post('/talkdoc/start-session', {
      title,
      doc_ids: docIds,
    });
    return res.data; // { session_id, doc_count, title }
  },

  async chat(sessionId, message, useLLM, meta = {}) {
    const body = { session_id: sessionId, message };
    if (typeof useLLM === 'boolean') body.use_llm = useLLM;
    if (meta.promptId) body.prompt_id = meta.promptId;
    if (typeof meta.promptText === 'string') body.prompt_text = meta.promptText;
    if (meta.docIds && Array.isArray(meta.docIds)) body.doc_ids = meta.docIds; // Add document IDs for RAG
    
    const res = await axiosInstance.post('/talkdoc/chat', body);
    return res.data; // { answer, citations }
  },

  // Streaming chat via fetch + SSE text/event-stream
  // options: { useLLM?: boolean, signal?: AbortSignal, promptId?: string, promptText?: string, docIds?: string[] }
  async *chatStream(sessionId, message, options = {}) {
    const { useLLM, signal, promptId, promptText, docIds } = options;
    const base = axiosInstance.defaults.baseURL?.replace(/\/$/, '') || '';
    const url = `${base}/talkdoc/chat-stream`;
    const token = secureLocalStorage.getItem('authToken') || secureSessionStorage.getItem('authToken');
    const headers = {
      'Content-Type': 'application/json',
      // Use */* so DRF content negotiation doesn't 406 on text/event-stream
      'Accept': '*/*',
    };
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const body = { session_id: sessionId, message };
    if (typeof useLLM === 'boolean') body.use_llm = useLLM;
    if (promptId) body.prompt_id = promptId;
    if (typeof promptText === 'string') body.prompt_text = promptText;
    if (docIds && Array.isArray(docIds)) body.doc_ids = docIds; // Add document IDs for RAG

    let resp;
    try {
      resp = await fetch(url, {
        method: 'POST',
        headers,
        body: JSON.stringify(body),
        credentials: 'include',
        signal,
      });
    } catch (e) {
      // aborted fetch
      if (signal?.aborted) return; // silent end
      throw e;
    }

    if (!resp.ok || !resp.body) {
      const text = await resp.text().catch(() => '');
      throw new Error(text || `Streaming request failed: ${resp.status}`);
    }

    const reader = resp.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buf = '';
    while (true) {
      let result;
      try {
        result = await reader.read();
      } catch (e) {
        // read aborted
        if (signal?.aborted) break;
        throw e;
      }
      const { done, value } = result;
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      let idx;
      // SSE events are separated by double newlines
      while ((idx = buf.indexOf('\n\n')) !== -1) {
        const raw = buf.slice(0, idx);
        buf = buf.slice(idx + 2);
        // Extract lines starting with 'data: '
        const lines = raw.split(/\n/);
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const payload = line.slice(6);
            // Unescape newlines
            const token = payload.replace(/\\n/g, '\n');
            yield token;
          }
        }
      }
    }
    // Flush remaining buffer if any
    if (buf.trim()) {
      const lines = buf.split(/\n/);
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const payload = line.slice(6);
          const token = payload.replace(/\\n/g, '\n');
          yield token;
        }
      }
    }
  },

  async listSessions() {
    const res = await axiosInstance.get('/talkdoc/sessions');
    return res.data; // { sessions }
  },

  async listFiles() {
    const res = await axiosInstance.get('/talkdoc/files');
    return res.data; // { files }
  },

  async reindexFile(docId) {
    const res = await axiosInstance.post(`/talkdoc/file/${docId}/reindex`);
    return res.data; // { ok, reindexed }
  },

  // Test document processing manually
  async testDocumentProcessing(docId) {
    const res = await axiosInstance.post('/talkdoc/test-processing', { doc_id: docId });
    return res.data;
  },

  // Test imports
  async testImports() {
    const res = await axiosInstance.post('/talkdoc/test-imports');
    return res.data;
  },

  async deleteFile(docId) {
    const res = await axiosInstance.post(`/talkdoc/file/${docId}/delete`);
    return res.data; // { ok }
  },

  async getSession(sessionId) {
    const res = await axiosInstance.get(`/talkdoc/session/${sessionId}`);
    return res.data; // { session, messages }
  },

  async getSessionDocuments(sessionId) {
    return axiosInstance.get(`/talkdoc/session/${sessionId}`).then(res => res.data?.session?.doc_ids || []);
  },

  async addDocumentToSession(sessionId, docId) {
    return axiosInstance.get(`/talkdoc/session/${sessionId}`).then(res => {
      const currentDocIds = res.data?.session?.doc_ids || [];
      if (!currentDocIds.includes(docId)) {
        return axiosInstance.post(`/talkdoc/session/${sessionId}/update`, {
          doc_ids: [...currentDocIds, docId]
        });
      }
      return Promise.resolve({ data: { ok: true } });
    });
  },

  async updateSession(sessionId, payload) {
    return axiosInstance.post(`/talkdoc/session/${sessionId}/update`, payload);
  },

  async deleteSession(sessionId) {
    const res = await axiosInstance.post(`/talkdoc/session/${sessionId}/delete`);
    return res.data; // { ok }
  },

  async getPrompts() {
    const res = await axiosInstance.get('/talkdoc/prompts');
    return res.data; // { prompts }
  },
};

export default TalkDocService;
