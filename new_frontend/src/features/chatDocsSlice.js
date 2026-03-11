import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  selectedDocs: [],
  currentSessionId: null,
  sessions: [],
  messages: [],
  matter: {},
};

const chatDocsSlice = createSlice({
  name: 'chatDocs',
  initialState,
  reducers: {
    setSelectedDocs(state, action) {
      state.selectedDocs = action.payload;
    },
    addSelectedDoc(state, action) {
      const nextId = action.payload.doc_id || action.payload.id;
      const exists = state.selectedDocs.find((d) => (d.doc_id || d.id) === nextId);
      if (!exists) state.selectedDocs.push(action.payload);
    },
    removeSelectedDoc(state, action) {
      state.selectedDocs = state.selectedDocs.filter((d) => (d.doc_id || d.id) !== action.payload);
    },
    setMatter(state, action) {
      state.matter = action.payload;
    },
    setSessions(state, action) {
      state.sessions = action.payload;
    },
    setCurrentSession(state, action) {
      state.currentSessionId = action.payload;
    },
    setMessages(state, action) {
      state.messages = action.payload;
    },
    appendMessage(state, action) {
      state.messages.push(action.payload);
    },
    resetChatDocs(state) {
      state.selectedDocs = [];
      state.currentSessionId = null;
      state.sessions = [];
      state.messages = [];
      state.matter = {};
    },
  },
});

export const {
  setSelectedDocs,
  addSelectedDoc,
  removeSelectedDoc,
  setMatter,
  setSessions,
  setCurrentSession,
  setMessages,
  appendMessage,
  resetChatDocs,
} = chatDocsSlice.actions;
export default chatDocsSlice.reducer;
