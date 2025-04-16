import { createAsyncThunk, createSlice, PayloadAction } from '@reduxjs/toolkit';
import { IUser } from '../interfaces/user';
import { get } from '../services/storage';

interface UserState {
  user: IUser | null;
  status: string;
}

const initialState: UserState = {
  user: null,
  status: 'loading',
};

export const getUserDataFromStorage = createAsyncThunk(
  'user/getUserDataFromStorage',
  async (_, { rejectWithValue }) => {
    try {
      const user = await get('auth-user');
      return user;
    } catch (error) {
      return rejectWithValue('Failed to retrieve token');
    }
  }
);

const userSlice = createSlice({
  name: 'user',
  initialState,
  reducers: {},
  extraReducers(builder) {
    builder
      .addCase(getUserDataFromStorage.pending, (state) => {
        state.status = 'loading';
      })
      .addCase(
        getUserDataFromStorage.fulfilled,
        (state, action: PayloadAction<IUser | null>) => {
          state.status = 'succeeded';
          state.user = action.payload;
        }
      )
      .addCase(getUserDataFromStorage.rejected, (state) => {
        state.status = 'failed';
        state.user = null;
      });
  },
});

export default userSlice.reducer;
