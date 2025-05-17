import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { api } from '../config/axiosConfig';
import { API_BASE_URL } from '../api/config';
import { Document, DocumentState } from '../types/document';

// Define return type and error handling
export const fetchDocuments = createAsyncThunk<Document[], void, { rejectValue: string }>(
  'documents/fetchDocuments',
  async (_, { rejectWithValue }) => {
    try {
      const response = await api.get(`${API_BASE_URL}/documents/`);
      return response.data.documents;
    } catch (error) {
      return rejectWithValue('Failed to fetch documents');
    }
  }
);

// Export these async thunks
export const uploadDocument = createAsyncThunk(
  'documents/uploadDocument',
  async (file: File, { rejectWithValue }) => {
    try {
      const formData = new FormData();
      formData.append('files', file);
      const response = await api.post(`${API_BASE_URL}/files/upload-files`, formData);
      return response.data; // Adjust based on your API response
    } catch (error) {
      return rejectWithValue('Failed to upload document');
    }
  }
);

export const processDocument = createAsyncThunk(
  'documents/processDocument',
  async (documentId: number, { rejectWithValue }) => {
    try {
      const response = await api.post(`${API_BASE_URL}/rag/index-document/${documentId}`);
      return response.data; // Adjust based on your API response
    } catch (error) {
      return rejectWithValue('Failed to process document');
    }
  }
);

export const indexDocument = createAsyncThunk(
  'documents/indexDocument',
  async (documentId: number, { rejectWithValue }) => {
    try {
      // Assuming indexDocument uses the same endpoint as processDocument for RAG indexing
      const response = await api.post(`${API_BASE_URL}/rag/index-document/${documentId}`);
      return response.data; // Adjust based on your API response
    } catch (error) {
      return rejectWithValue('Failed to index document');
    }
  }
);

export const deleteDocument = createAsyncThunk(
  'documents/deleteDocument',
  async (documentId: number, { rejectWithValue }) => {
    try {
      // Corrected endpoint to use the documents API
      const response = await api.delete(`${API_BASE_URL}/documents/${documentId}`);
      return response.data; // Adjust based on your API response
    } catch (error) {
      return rejectWithValue('Failed to delete document');
    }
  }
);

export const processPendingDocuments = createAsyncThunk<
  any, // Assuming the fulfilled payload type is not strictly defined yet
  void,
  { rejectValue: string } // Explicitly define the reject value type as string
>(
  'documents/processPendingDocuments',
  async (_, { rejectWithValue }) => {
    try {
      const response = await api.post(`${API_BASE_URL}/rag/process-pending`);
      return response.data; // Adjust based on your API response
    } catch (error) {
      // Ensure the error payload is a string
      const errorMessage = (error as any).response?.data?.detail || (error as any).message || 'Failed to process pending documents';
      return rejectWithValue(errorMessage);
    }
  }
);


const initialState: DocumentState = {
  documents: [],
  isLoading: false,
  error: null
};

const documentSlice = createSlice({
  name: 'documents',
  initialState,
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchDocuments.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchDocuments.fulfilled, (state, action) => {
        state.isLoading = false;
        state.documents = action.payload;
        state.error = null;
      })
      .addCase(fetchDocuments.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload || 'An error occurred';
      })
      .addCase(processPendingDocuments.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(processPendingDocuments.fulfilled, (state, action) => {
        state.isLoading = false;
        // Optionally refetch documents after successful processing
        // state.documents = action.payload; // Or update based on response
        state.error = null;
      })
      .addCase(processPendingDocuments.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload || 'An error occurred during pending document processing';
      });
  }
});

export default documentSlice.reducer;