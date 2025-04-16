import { configureStore } from '@reduxjs/toolkit';
import authReducer from '../features/authSlice';
import controlReducer from '../features/controlSlice';
import userReducer from '../features/userSlice';
import chatReducer from '../features/chatSlice';
import themeReducer from '../features/themeSlice';


export const store = configureStore({
  reducer: {
    auth: authReducer,
    user: userReducer,
    control: controlReducer,
    chat: chatReducer,
    theme: themeReducer,
  },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
