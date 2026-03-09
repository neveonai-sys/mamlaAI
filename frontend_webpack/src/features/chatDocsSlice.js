import { createSlice } from '@reduxjs/toolkit';

const initial = {
  selectedDocs: [],   // {id, name}
  currentSessionId: null,
  sessions: [],       // list in left rail
  messages: [],       // for current session
  matter: { personal: 'N', caseid: [], clientid: [] }
};

const slice = createSlice({
  name: 'chatdocs',
  initialState: initial,
  reducers: {
    setSelectedDocs: (s, a) => { s.selectedDocs = a.payload; },
    addSelectedDoc: (s, a) => { if (!s.selectedDocs.find(d => d.id === a.payload.id)) s.selectedDocs.push(a.payload); },
    removeSelectedDoc: (s, a) => { s.selectedDocs = s.selectedDocs.filter(d => d.id !== a.payload); },
    setMatter: (s, a) => { s.matter = a.payload; },
    setSessions: (s, a) => { s.sessions = a.payload; },
    setCurrentSession: (s, a) => { s.currentSessionId = a.payload; s.messages = []; },
    setMessages: (s, a) => { s.messages = a.payload; },
    appendMessage: (s, a) => { s.messages.push(a.payload); },
    resetChatDocs: () => initial
  }
});

export const {
  setSelectedDocs, addSelectedDoc, removeSelectedDoc, setMatter, setSessions,
  setCurrentSession, setMessages, appendMessage, resetChatDocs
} = slice.actions;

export default slice.reducer;
