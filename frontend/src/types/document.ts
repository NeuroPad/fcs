export interface Document {
  id: number;
  filename: string;
  created_at: string;
  file_size: number;
  status: string;
  isProcessed: boolean;
  knowledgeBaseIndexed: boolean;
  is_indexed: boolean;
  path: string;
  type: string;
}

export interface DocumentState {
  documents: Document[];
  isLoading: boolean;
  error: string | null;
}