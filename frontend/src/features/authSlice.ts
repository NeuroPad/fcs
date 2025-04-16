import { createAsyncThunk, createSlice } from '@reduxjs/toolkit';
import { api } from '../config/axiosConfig';
import { get, remove, set } from '../services/storage';

interface AuthState {
  isAuthenticated: boolean;
  token: string | null;
  isLoading: boolean;
  error: string | null;
}

const initialState: AuthState = {
  isAuthenticated: false,
  token: null,
  isLoading: false,
  error: null,
};

export const loginUser = createAsyncThunk(
  'auth/login',
  async (credential: any, { rejectWithValue }) => {
    try {
      // Generate dummy token
      const dummyToken = `${Date.now()}|${Math.random().toString(36).substring(2)}`;
      // Create dummy user data using email as name
      const dummyUser = {
        id: Math.floor(Math.random() * 1000), // Random ID
        name: credential.email,
        email: credential.email,
        email_verified_at: null,
        created_at: new Date().toISOString().slice(0, 19).replace('T', ' '),
        updated_at: new Date().toISOString().slice(0, 19).replace('T', ' '),
        deleted_at: null
      };
      
      const dummyResponse = {
        accessToken: dummyToken,
        token_type: 'Bearer',
        user: dummyUser
      };

      await set('token', dummyResponse.accessToken);
      await set('auth-user', dummyResponse.user);
      window.location.reload();
      return dummyResponse;
    } catch (error: any) {
      return rejectWithValue('Login failed');
    }
  }
);

export const registerUser = createAsyncThunk(
  'auth/register',
  async (credential: any, { rejectWithValue }) => {
    try {
      const response = await api.post('/auth/register', credential);
      return response.data.data;
    } catch (error: any) {
      return rejectWithValue(error.response.data.message);
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
        // Optionally, you can validate the token with your backend here
        // const response = await api.post('/auth/validate-token', { token });
        // return response.data.isValid;

        // For now, we'll just assume the presence of a token means the user is authenticated
        return true;
      }
      return false;
    } catch (error) {
      console.error('Failed to check auth status:', error);
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
      //window.location.reload();
    },
  },
  extraReducers(builder) {
    builder
      .addCase(loginUser.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(loginUser.fulfilled, (state) => {
        state.isLoading = false;
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
        if (!action.payload) {
          state.token = null;
        }
      })
      .addCase(checkAuthStatus.rejected, (state) => {
        state.isLoading = false;
        state.isAuthenticated = false;
        state.token = null;
      });
  },
});

export const { logout } = authSlice.actions;
export default authSlice.reducer;
