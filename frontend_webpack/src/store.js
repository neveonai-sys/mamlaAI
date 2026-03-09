// src/store.js
import { configureStore } from '@reduxjs/toolkit';
import userReducer from './features/userSlice';
import chatDocsReducer from './features/chatDocsSlice';

export const store = configureStore({
    reducer: {
        user: userReducer,
        chatdocs: chatDocsReducer,
    },
});
