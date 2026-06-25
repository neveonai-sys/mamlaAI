import { configureStore } from '@reduxjs/toolkit';
import userReducer from './features/userSlice';
import chatDocsReducer from './features/chatDocsSlice';
import entitlementsReducer from './features/entitlementsSlice';
import uiReducer from './features/uiSlice';

export const store = configureStore({
  reducer: {
    user: userReducer,
    chatDocs: chatDocsReducer,
    entitlements: entitlementsReducer,
    ui: uiReducer,
  },
});

export default store;
