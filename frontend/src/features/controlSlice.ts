import { createSlice } from '@reduxjs/toolkit';

// We won't be using the bookmark from Redux state and localStorage in this code;
// instead, refer to the services/storage.ts to see the code using Ionic's Preferences API for managing bookmarks.

interface ControlState {
  // interface
  bookmarkedQuestions: any[] | null;
}

const initialState: ControlState = {
  // init state
  bookmarkedQuestions: null,
};

export const controlSlice = createSlice({
  name: 'control',
  initialState,
  reducers: {
    setBookmark(state, action) {
      state.bookmarkedQuestions = action.payload;
      localStorage.setItem('bookmark', JSON.stringify(action.payload));
    },
    getBookmarksFromStorage(state) {
      const bookmark = localStorage.getItem('bookmark');
      if (bookmark) {
        state.bookmarkedQuestions = JSON.parse(bookmark);
      }
    },
  },
});

export const { setBookmark, getBookmarksFromStorage } = controlSlice.actions;
export default controlSlice.reducer;
