import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  firstname: '',
  lastname: '',
  email: '',
  user_type: '',  // 'Lawyer' | 'Client' | 'Paralegal'
  isAuthenticated: null, // null = unknown, true = auth'd, false = not auth'd
  sessions: [],
};

const userSlice = createSlice({
  name: 'user',
  initialState,
  reducers: {
    setUser(state, action) {
      const { firstname, lastname, email, user_type, sessions } = action.payload;
      state.firstname = firstname ?? '';
      state.lastname = lastname ?? '';
      state.email = email ?? '';
      state.user_type = user_type ?? '';
      state.isAuthenticated = true;
      state.sessions = sessions ?? [];
    },
    clearUser(state) {
      state.firstname = '';
      state.lastname = '';
      state.email = '';
      state.user_type = '';
      state.isAuthenticated = false;
      state.sessions = [];
    },
  },
});

export const { setUser, clearUser } = userSlice.actions;
export default userSlice.reducer;
