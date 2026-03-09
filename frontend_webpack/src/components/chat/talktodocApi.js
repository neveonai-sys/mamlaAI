import AxiosInstance from '../common/AxiosInstance';

export const listDocs = (params) => AxiosInstance.get('talkdoc/docs', { params });
export const uploadDoc = (formData) =>
  AxiosInstance.post('talkdoc/docs/upload', formData, { headers: { 'Content-Type': 'multipart/form-data' }});

export const createSession = (payload) => AxiosInstance.post('talkdoc/sessions', payload);
export const listSessions = (params) => AxiosInstance.get('talkdoc/sessions/list', { params });
export const getMessages = (id) => AxiosInstance.get(`talkdoc/sessions/${id}/messages`);
export const sendMessage = (id, text) => AxiosInstance.post(`talkdoc/sessions/${id}/message`, { text });
export const deleteSession = (id) => AxiosInstance.delete(`talkdoc/sessions/${id}`);
export const modifySessionDocs = (id, body) => AxiosInstance.post(`talkdoc/sessions/${id}/docs`, body);
export async function renameSession(sessionId, title) {
  return await AxiosInstance.post(`/talkdoc/rename_session/${sessionId}`, { title });
}
