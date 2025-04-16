import { createAsyncThunk, createSlice, PayloadAction } from '@reduxjs/toolkit';
import axios from 'axios';
import { API_BASE_URL } from '../api/config';

// Define the base URL for the API
const BASE_URL = `${API_BASE_URL}/chat`;

interface ChatMessage {
  role: string;
  content: string;
  images?: string[]; // Array of image URLs
  sources?: string[]; // Array of source links
  created_at?: string;
}

interface ChatSession {
  id: number;
  created_at: string;
  messages: ChatMessage[];
}

interface ChatState {
  chats: ChatSession[] | null;
  selectedChat: ChatMessage[];
  error: string | null;
  chatId: number | null;
}

const initialState: ChatState = {
  chats: null,
  selectedChat: [],
  error: null,
  chatId: null,
};


interface SendMessagePayload {
  sessionId: string;
  message: string;
  mode: 'normal' | 'graph' | 'combined';
}

interface CreateChatPayload {
  question: string;
  mode: 'normal' | 'graph' | 'combined';
}
// Create a new chat session
export const createChat = createAsyncThunk(
  'chat/createChat',
  async ({ question, mode }: CreateChatPayload) => {
    try {
      // First create a new chat session
      const newSessionResponse = await axios.post(`${BASE_URL}/new`);
      const sessionId = newSessionResponse.data.id;

      // Then send the question
      const response = await fetch(`${API_BASE_URL}/chat/session/${sessionId}/ask?mode=${mode}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text: question }),
      });

      // Get the updated chat session
      const sessionResponse = await axios.get(`${BASE_URL}/session/${sessionId}`);

      return {
        messages: sessionResponse.data.messages,
        chatId: sessionId,
      };
    } catch (error: any) {
      throw error.response?.data?.detail || 'An error occurred';
    }
  }
);

// Get all chat sessions
export const getUserChats = createAsyncThunk(
  'chat/getUserChats',
  async () => {
    try {
      const response = await axios.get(`${BASE_URL}/sessions`);
      return response.data;
    } catch (error: any) {
      throw error.response?.data?.detail || 'An error occurred';
    }
  }
);

// Get chat by ID
export const getChatById = createAsyncThunk(
  'chat/getChatById',
  async (id: number) => {
    try {
      const response = await axios.get(`${BASE_URL}/session/${id}`);
      return response.data;
    } catch (error: any) {
      throw error.response?.data?.detail || 'An error occurred';
    }
  }
);

// Send a message in existing chat
export const sendMessage = createAsyncThunk(
  'chat/sendMessage',
  async ({ sessionId, message, mode }: SendMessagePayload) => {
    try {
    const response = await fetch(`${API_BASE_URL}/chat/session/${sessionId}/ask?mode=${mode}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ text: message }),
    });

      // Get updated session
      const sessionResponse = await axios.get(`${BASE_URL}/session/${sessionId}`);
      return sessionResponse.data;
    } catch (error: any) {
      throw error.response?.data?.detail || 'An error occurred';
    }
  }
);

// Add this new thunk after the other thunks
export const deleteChat = createAsyncThunk(
  'chat/deleteChat',
  async (id: number) => {
    try {
      await axios.delete(`${BASE_URL}/session/${id}`);
      return id;
    } catch (error: any) {
      throw error.response?.data?.detail || 'An error occurred';
    }
  }
);

export const chatSlice = createSlice({
  name: 'chat',
  initialState,
  reducers: {
    setMessages: (state, action: PayloadAction<ChatMessage[]>) => {
      state.selectedChat = action.payload;
      state.chatId= null;
    },
  },
  extraReducers(builder) {
    builder
      .addCase(createChat.fulfilled, (state, action) => {
        state.selectedChat = action.payload.messages;
        state.chatId = action.payload.chatId;
        state.error = null;
      })
      .addCase(createChat.rejected, (state, action) => {
        state.error = action.error.message || null;
      })

      .addCase(getUserChats.fulfilled, (state, action) => {
        state.chats = action.payload.sort((a: ChatSession, b: ChatSession) =>
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        );
        state.error = null;
      })
      .addCase(getUserChats.rejected, (state, action) => {
        state.chats = null;
        state.error = action.error.message || null;
      })

      .addCase(getChatById.fulfilled, (state, action) => {
        state.selectedChat = action.payload.messages;
        state.chatId = action.payload.id;
        state.error = null;
      })
      .addCase(getChatById.rejected, (state, action) => {
        state.selectedChat = [];
        state.error = action.error.message || null;
      })

      .addCase(sendMessage.fulfilled, (state, action) => {
        state.selectedChat = action.payload.messages;
        state.error = null;
      })
      .addCase(sendMessage.rejected, (state, action) => {
        state.error = action.error.message || null;
      })
      .addCase(deleteChat.fulfilled, (state, action) => {
        state.chats = state.chats?.filter(chat => chat.id !== action.payload) || null;
        if (state.chatId === action.payload) {
          state.selectedChat = [];
          state.chatId = null;
        }
        state.error = null;
      })
      .addCase(deleteChat.rejected, (state, action) => {
        state.error = action.error.message || null;
      });
  },
});

export const { setMessages } = chatSlice.actions;
export default chatSlice.reducer;