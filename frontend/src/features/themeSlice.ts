import { createAsyncThunk, createSlice, PayloadAction } from '@reduxjs/toolkit';
import { get, set } from '../services/storage';

interface ThemeState {
  isDarkMode: boolean;
}

const initialState: ThemeState = {
  isDarkMode: localStorage.getItem('darkMode') === 'true', // Load initial state from localStorage
};

export const loadDarkMode = createAsyncThunk('theme/loadDarkMode', async () => {
  const storedValue = await get('darkMode');
  return storedValue === true;
});

const themeSlice = createSlice({
  name: 'theme',
  initialState,
  reducers: {
    toggleDarkMode(state, action: PayloadAction<boolean>) {
      state.isDarkMode = action.payload;
      set('darkMode', action.payload); // Save the dark mode preference in storage
      document.body.classList.toggle('dark', action.payload); // Toggle dark mode class
    },
  },
  extraReducers: (builder) => {
    builder.addCase(loadDarkMode.fulfilled, (state, action) => {
      state.isDarkMode = action.payload;
      document.body.classList.toggle('dark', action.payload); // Apply the dark mode on load
    });
  },
});

export const { toggleDarkMode } = themeSlice.actions;
export default themeSlice.reducer;
