import { configureStore } from '@reduxjs/toolkit';
import authReducer from '../features/authSlice';
import controlReducer from '../features/controlSlice';
import userReducer from '../features/userSlice';
import chatReducer from '../features/chatSlice';
import optimizedChatReducer from '../features/optimizedChatSlice';
import themeReducer from '../features/themeSlice';
import documentReducer from '../features/documentSlice';
import { setupAxiosInterceptors } from '../config/axiosConfig';

export const store = configureStore({
  reducer: {
    auth: authReducer,
    user: userReducer,
    control: controlReducer,
    chat: chatReducer,
    optimizedChat: optimizedChatReducer,
    theme: themeReducer,
    documents: documentReducer,
  },
});

setupAxiosInterceptors(store);

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
