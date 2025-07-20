import { createAsyncThunk, createSlice, PayloadAction } from '@reduxjs/toolkit';
import axios from 'axios';
import { API_BASE_URL } from '../api/config';
import { get } from '../services/storage';

const BASE_URL = `${API_BASE_URL}/chat`;

interface ChatMessage {
  id?: string;
  role: string;
  content: string;
  images?: string[];
  sources?: string[];
  reasoning_nodes?: Array<{
    uuid: string;
    name: string;
    salience?: number;
    confidence?: number;
    summary?: string;
    node_type?: string;
    used_in_context?: string;
  }>;
  created_at?: string;
  isOptimistic?: boolean;
  isError?: boolean;
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
  isTyping: boolean;
  isLoading: boolean;
  messageCache: Map<string, ChatMessage[]>;
}

const initialState: ChatState = {
  chats: null,
  selectedChat: [],
  error: null,
  chatId: null,
  isTyping: false,
  isLoading: false,
  messageCache: new Map(),
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

// Optimistic message sending with immediate UI updates
export const sendMessageOptimistic = createAsyncThunk(
  'chat/sendMessageOptimistic',
  async ({ sessionId, message, mode }: SendMessagePayload, { dispatch, rejectWithValue }) => {
    const tempId = `temp_${Date.now()}`;
    
    try {
      // Add user message immediately (optimistic update)
      dispatch(addUserMessageOptimistic({ content: message, id: tempId }));
      
      // Add typing indicator
      dispatch(setTyping(true));
      
      const token = await get('token');
      
      // Send request with timeout
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout
      
      const response = await fetch(`${API_BASE_URL}/chat/session/${sessionId}/ask?mode=${mode}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ text: message }),
        signal: controller.signal,
      });
      
      clearTimeout(timeoutId);
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const errorMessage = errorData.detail || `HTTP error! status: ${response.status}`;
        
        // Handle specific error types
        if (response.status === 503) {
          throw new Error("The AI service is temporarily unavailable. Please try again later.");
        } else if (response.status === 429) {
          throw new Error("Too many requests. Please wait a moment before trying again.");
        } else if (response.status === 408) {
          throw new Error("Request timeout. Please try again.");
        } else {
          throw new Error(errorMessage);
        }
      }
      
      // Get updated session data
      const sessionResponse = await axios.get(`${BASE_URL}/session/${sessionId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      
      // Remove optimistic message and add real messages
      dispatch(removeOptimisticMessage(tempId));
      
      return {
        messages: sessionResponse.data.messages,
        sessionId,
      };
    } catch (error: any) {
      // Mark optimistic message as error
      dispatch(markMessageAsError(tempId));
      
      if (error.name === 'AbortError') {
        return rejectWithValue('Request timeout - please try again');
      }
      
      return rejectWithValue(error.response?.data?.detail || error.message || 'An error occurred');
    } finally {
      dispatch(setTyping(false));
    }
  }
);

// Cached chat retrieval
export const getChatByIdCached = createAsyncThunk(
  'chat/getChatByIdCached',
  async (id: number, { getState }) => {
    const state = getState() as { chat: ChatState };
    const cacheKey = `chat_${id}`;
    
    // Check cache first
    if (state.chat.messageCache.has(cacheKey)) {
      return {
        messages: state.chat.messageCache.get(cacheKey)!,
        id,
        fromCache: true,
      };
    }
    
    try {
      const token = await get('token');
      const response = await axios.get(`${BASE_URL}/session/${id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      
      return {
        messages: response.data.messages,
        id: response.data.id,
        fromCache: false,
      };
    } catch (error: any) {
      throw error.response?.data?.detail || 'An error occurred';
    }
  }
);

// Optimized chat creation
export const createChatOptimized = createAsyncThunk(
  'chat/createChatOptimized',
  async ({ question, mode }: CreateChatPayload, { dispatch }) => {
    try {
      const token = await get('token');
      
      // Create session
      const newSessionResponse = await axios.post(
        `${BASE_URL}/new`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      const sessionId = newSessionResponse.data.id;
      
      // Send first message and get the updated session
      await dispatch(sendMessageOptimistic({
        sessionId: sessionId.toString(),
        message: question,
        mode,
      }));
      
      // Get the updated session to return messages
      const sessionResponse = await axios.get(
        `${BASE_URL}/session/${sessionId}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      return {
        sessionId,
        messages: sessionResponse.data.messages || [],
      };
    } catch (error: any) {
      throw error.response?.data?.detail || 'An error occurred';
    }
  }
);

// Batch load user chats with pagination
export const getUserChatsOptimized = createAsyncThunk(
  'chat/getUserChatsOptimized',
  async ({ limit = 20, offset = 0 }: { limit?: number; offset?: number } = {}) => {
    try {
      const token = await get('token');
      const response = await axios.get(`${BASE_URL}/sessions?limit=${limit}&offset=${offset}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      return response.data;
    } catch (error: any) {
      throw error.response?.data?.detail || 'An error occurred';
    }
  }
);

export const optimizedChatSlice = createSlice({
  name: 'optimizedChat',
  initialState,
  reducers: {
    setMessages: (state, action: PayloadAction<ChatMessage[]>) => {
      state.selectedChat = action.payload;
      state.error = null;
    },
    
    addUserMessageOptimistic: (state, action: PayloadAction<{ content: string; id: string }>) => {
      const optimisticMessage: ChatMessage = {
        id: action.payload.id,
        role: 'user',
        content: action.payload.content,
        created_at: new Date().toISOString(),
        isOptimistic: true,
      };
      state.selectedChat.push(optimisticMessage);
    },
    
    removeOptimisticMessage: (state, action: PayloadAction<string>) => {
      state.selectedChat = state.selectedChat.filter(
        message => message.id !== action.payload
      );
    },
    
    markMessageAsError: (state, action: PayloadAction<string>) => {
      const messageIndex = state.selectedChat.findIndex(
        message => message.id === action.payload
      );
      if (messageIndex !== -1) {
        state.selectedChat[messageIndex].isError = true;
        state.selectedChat[messageIndex].isOptimistic = false;
      }
    },
    
    setTyping: (state, action: PayloadAction<boolean>) => {
      state.isTyping = action.payload;
    },
    
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.isLoading = action.payload;
    },
    
    clearError: (state) => {
      state.error = null;
    },
    
    updateMessageCache: (state, action: PayloadAction<{ key: string; messages: ChatMessage[] }>) => {
      state.messageCache.set(action.payload.key, action.payload.messages);
    },
    
    clearCache: (state) => {
      state.messageCache.clear();
    },
    
    retryFailedMessage: (state, action: PayloadAction<string>) => {
      const messageIndex = state.selectedChat.findIndex(
        message => message.id === action.payload
      );
      if (messageIndex !== -1) {
        state.selectedChat[messageIndex].isError = false;
        state.selectedChat[messageIndex].isOptimistic = true;
      }
    },
  },
  
  extraReducers(builder) {
    builder
      // Optimistic message sending
      .addCase(sendMessageOptimistic.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(sendMessageOptimistic.fulfilled, (state, action) => {
        // Remove any optimistic messages and replace with real ones
        state.selectedChat = state.selectedChat.filter(msg => !msg.isOptimistic);
        state.selectedChat = action.payload.messages;
        state.isLoading = false;
        state.error = null;
        
        // Update cache
        const cacheKey = `chat_${action.payload.sessionId}`;
        state.messageCache.set(cacheKey, action.payload.messages);
      })
      .addCase(sendMessageOptimistic.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      })
      
      // Cached chat retrieval
      .addCase(getChatByIdCached.fulfilled, (state, action) => {
        state.selectedChat = action.payload.messages;
        state.chatId = action.payload.id;
        state.error = null;
        
        // Update cache if not from cache
        if (!action.payload.fromCache) {
          const cacheKey = `chat_${action.payload.id}`;
          state.messageCache.set(cacheKey, action.payload.messages);
        }
      })
      .addCase(getChatByIdCached.rejected, (state, action) => {
        state.error = action.error.message || null;
      })
      
      // Optimized chat creation
      .addCase(createChatOptimized.fulfilled, (state, action) => {
        state.selectedChat = action.payload.messages;
        state.chatId = action.payload.sessionId;
        state.error = null;
      })
      .addCase(createChatOptimized.rejected, (state, action) => {
        state.error = action.error.message || null;
      })
      
      // Optimized user chats
      .addCase(getUserChatsOptimized.fulfilled, (state, action) => {
        state.chats = action.payload.sort((a: ChatSession, b: ChatSession) =>
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        );
        state.error = null;
      })
      .addCase(getUserChatsOptimized.rejected, (state, action) => {
        state.chats = null;
        state.error = action.error.message || null;
      });
  },
});

export const {
  setMessages,
  addUserMessageOptimistic,
  removeOptimisticMessage,
  markMessageAsError,
  setTyping,
  setLoading,
  clearError,
  updateMessageCache,
  clearCache,
  retryFailedMessage,
} = optimizedChatSlice.actions;

export default optimizedChatSlice.reducer;

// This slice extends the existing chat functionality with optimizations
// It should be integrated with the existing chat slice or replace it