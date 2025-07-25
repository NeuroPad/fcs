import { createAsyncThunk, createSlice, PayloadAction } from '@reduxjs/toolkit';
import axios from 'axios';
import { API_BASE_URL } from '../api/config';
import { get } from '../services/storage';

const BASE_URL = `${API_BASE_URL}/chat`;

interface ChatMessage {
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

export const createChat = createAsyncThunk(
  'chat/createChat',
  async ({ question, mode }: CreateChatPayload) => {
    try {
      const token = await get('token');
      const newSessionResponse = await axios.post(
        `${BASE_URL}/new`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      const sessionId = newSessionResponse.data.id;
      
      const askResponse = await fetch(`${API_BASE_URL}/chat/session/${sessionId}/ask?mode=${mode}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ text: question }),
      });
      
      const askData = await askResponse.json();
      
      // Parse the response content to extract answer, sources, and reasoning_nodes
      let assistantMessage: ChatMessage;
      try {
        const responseContent = JSON.parse(askData.response);
        assistantMessage = {
          role: 'assistant',
          content: responseContent.answer || 'No response received',
          sources: responseContent.sources || [],
          reasoning_nodes: responseContent.reasoning_nodes || []
        };
      } catch (parseError) {
        // Fallback if response parsing fails
        assistantMessage = {
          role: 'assistant',
          content: askData.response || 'No response received',
          sources: [],
          reasoning_nodes: []
        };
      }
      
      // Create user message
      const userMessage: ChatMessage = {
        role: 'user',
        content: question
      };
      
      return {
        messages: [userMessage, assistantMessage],
        chatId: sessionId,
        sessionId: sessionId,
      };
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to create chat';
      
      // Handle specific error types
      if (error.response?.status === 503) {
        throw "The AI service is temporarily unavailable. Please try again later.";
      } else if (error.response?.status === 429) {
        throw "Too many requests. Please wait a moment before trying again.";
      } else if (error.response?.status === 408) {
        throw "Request timeout. Please try again.";
      } else {
        throw errorMessage;
      }
    }
  }
);

export const getUserChats = createAsyncThunk(
  'chat/getUserChats',
  async () => {
    try {
      const token = await get('token');
      const response = await axios.get(`${BASE_URL}/sessions`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      return response.data;
    } catch (error: any) {
      throw error.response?.data?.detail || 'An error occurred';
    }
  }
);

export const getChatById = createAsyncThunk(
  'chat/getChatById',
  async (id: number) => {
    try {
      const token = await get('token');
      const response = await axios.get(`${BASE_URL}/session/${id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      return response.data;
    } catch (error: any) {
      throw error.response?.data?.detail || 'An error occurred';
    }
  }
);

export const sendMessage = createAsyncThunk(
  'chat/sendMessage',
  async ({ sessionId, message, mode }: SendMessagePayload) => {
    try {
      const token = await get('token');
      const askResponse = await fetch(`${API_BASE_URL}/chat/session/${sessionId}/ask?mode=${mode}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ text: message }),
      });
      
      const askData = await askResponse.json();
      
      // Parse the response content to extract answer, sources, and reasoning_nodes
      let assistantMessage: ChatMessage;
      try {
        const responseContent = JSON.parse(askData.response);
        assistantMessage = {
          role: 'assistant',
          content: responseContent.answer || 'No response received',
          sources: responseContent.sources || [],
          reasoning_nodes: responseContent.reasoning_nodes || []
        };
      } catch (parseError) {
        // Fallback if response parsing fails
        assistantMessage = {
          role: 'assistant',
          content: askData.response || 'No response received',
          sources: [],
          reasoning_nodes: []
        };
      }
      
      return {
        newMessage: assistantMessage,
        sessionId: sessionId
      };
    } catch (error: any) {
      throw error.response?.data?.detail || 'An error occurred';
    }
  }
);

export const deleteChat = createAsyncThunk(
  'chat/deleteChat',
  async (id: number) => {
    try {
      const token = await get('token');
      await axios.delete(`${BASE_URL}/session/${id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
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
      state.chatId = null;
    },
    addUserMessage: (state, action: PayloadAction<string>) => {
      state.selectedChat = [
        ...state.selectedChat,
        {
          role: 'user',
          content: action.payload,
        },
      ];
    },
  },
  extraReducers(builder) {
    builder
      .addCase(createChat.fulfilled, (state, action) => {
        // For new chats, if there's already a user message in state, append only the assistant message
        // Otherwise, use all messages from the response
        if (state.selectedChat.length > 0 && state.selectedChat[state.selectedChat.length - 1].role === 'user') {
          // Only add the assistant message (second message in the response)
          state.selectedChat = [...state.selectedChat, action.payload.messages[1]];
        } else {
          // Use all messages from the response
          state.selectedChat = action.payload.messages;
        }
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
        state.selectedChat = action.payload.messages || [];
        state.chatId = action.payload.id;
        state.error = null;
      })
      .addCase(getChatById.rejected, (state, action) => {
        state.selectedChat = [];
        state.error = action.error.message || null;
      })

      .addCase(sendMessage.fulfilled, (state, action) => {
        // Add the user message first if it's not already there
        const lastMessage = state.selectedChat[state.selectedChat.length - 1];
        if (!lastMessage || lastMessage.role !== 'user') {
          // This shouldn't happen with current flow, but adding as safety
          state.selectedChat = [...state.selectedChat, action.payload.newMessage];
        } else {
          // User message is already there, just add the assistant message
          state.selectedChat = [...state.selectedChat, action.payload.newMessage];
        }
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

export const { setMessages, addUserMessage } = chatSlice.actions;
export default chatSlice.reducer;