import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  blockingCount: 0,
  message: 'Working...'
};

const uiSlice = createSlice({
  name: 'ui',
  initialState,
  reducers: {
    beginBlocking: (state, action) => {
      state.blockingCount += 1;
      if (action.payload?.message) {
        state.message = action.payload.message;
      }
    },
    stopBlocking: (state) => {
      state.blockingCount = Math.max(0, state.blockingCount - 1);
      if (state.blockingCount === 0) {
        state.message = initialState.message;
      }
    },
  },
});

export const { beginBlocking, stopBlocking } = uiSlice.actions;
export default uiSlice.reducer;