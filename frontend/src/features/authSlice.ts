import { createAsyncThunk, createSlice } from '@reduxjs/toolkit';
import axios from 'axios';
import { API_BASE_URL } from '../api/config';
import { get, remove, set } from '../services/storage';

interface AuthState {
  isAuthenticated: boolean;
  token: string | null;
  isLoading: boolean;
  error: string | null;
  user: any | null;
}

const initialState: AuthState = {
  isAuthenticated: false,
  token: null,
  isLoading: false,
  error: null,
  user: null,
};

export const loginUser = createAsyncThunk(
  'auth/login',
  async (credential: { email: string; password: string }, { rejectWithValue }) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/auth/login`, credential);
      const { access_token, token_type, user } = response.data;
      await set('token', access_token);
      await set('auth-user', user);
      return { access_token, token_type, user };
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || 'Login failed');
    }
  }
);

export const registerUser = createAsyncThunk(
  'auth/register',
  async (credential: { email: string; password: string; name: string; role: string }, { rejectWithValue }) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/auth/register`, credential);
      return response.data;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || 'Registration failed');
    }
  }
);

export const getTokenFromStorage = createAsyncThunk(
  'auth/getTokenFromStorage',
  async (_, { rejectWithValue }) => {
    try {
      const token = await get('token');
      return token;
    } catch (error) {
      return rejectWithValue('Failed to retrieve token');
    }
  }
);

export const checkAuthStatus = createAsyncThunk(
  'auth/checkStatus',
  async (_, { dispatch }) => {
    try {
      const token = await get('token');
      if (token) {
        return true;
      }
      return false;
    } catch (error) {
      return false;
    }
  }
);

export const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    logout(state) {
      remove('token');
      remove('auth-user');
      state.isAuthenticated = false;
      state.token = null;
      state.user = null;
    },
  },
  extraReducers(builder) {
    builder
      .addCase(loginUser.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(loginUser.fulfilled, (state, action) => {
        state.isLoading = false;
        state.isAuthenticated = true;
        state.token = action.payload.access_token;
        state.user = action.payload.user;
      })
      .addCase(loginUser.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      });

    builder
      .addCase(registerUser.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(registerUser.fulfilled, (state) => {
        state.isLoading = false;
      })
      .addCase(registerUser.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      });

    builder
      .addCase(getTokenFromStorage.pending, (state) => {
        state.isLoading = true;
      })
      .addCase(getTokenFromStorage.fulfilled, (state, action) => {
        state.isLoading = false;
        if (action.payload) {
          state.isAuthenticated = true;
          state.token = action.payload;
        } else {
          state.isAuthenticated = false;
          state.token = null;
        }
      });

    builder
      .addCase(checkAuthStatus.pending, (state) => {
        state.isLoading = true;
      })
      .addCase(checkAuthStatus.fulfilled, (state, action) => {
        state.isLoading = false;
        state.isAuthenticated = action.payload;
      });
  },
});

export const { logout } = authSlice.actions;
export default authSlice.reducer;
