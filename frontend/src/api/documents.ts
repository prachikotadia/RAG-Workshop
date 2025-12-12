import { api } from './client';

export type DocumentStatus = 'UPLOADING' | 'INDEXING' | 'READY' | 'FAILED';

export interface Document {
  id: number;
  user_id: number;
  title: string;
  original_filename: string;
  status: DocumentStatus;
  num_chunks: number;
  created_at: string;
  updated_at: string;
}

export interface ChunkContent {
  document_id: number;
  document_title: string;
  chunk_index: number;
  text: string;
  highlighted_text?: string;
  token_count: number;
  metadata: Record<string, any>;
}

export const documentsApi = {
  upload: async (files: File[]): Promise<Document[]> => {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', file);
    });
    return api.postFormData<Document[]>('/documents/upload', formData);
  },

  list: async (): Promise<Document[]> => {
    return api.get<Document[]>('/documents');
  },

  get: async (id: number): Promise<Document> => {
    return api.get<Document>(`/documents/${id}`);
  },

  delete: async (id: number): Promise<void> => {
    return api.delete<void>(`/documents/${id}`);
  },

  getChunkContent: async (documentId: number, chunkIndex: number, query?: string): Promise<ChunkContent> => {
    const params = query ? `?query=${encodeURIComponent(query)}` : '';
    return api.get<ChunkContent>(`/documents/${documentId}/chunk/${chunkIndex}${params}`);
  },

  getRelatedDocuments: async (documentId: number, limit: number = 5): Promise<Array<{ document: Document; similarity: number }>> => {
    return api.get<Array<{ document: Document; similarity: number }>>(`/documents/${documentId}/related?limit=${limit}`);
  },

  search: async (query: string, documentId?: number, limit: number = 50): Promise<{
    query: string;
    results: Array<{
      document_id: number;
      document_title: string;
      chunk_id: number;
      chunk_index: number;
      text: string;
      highlighted_text: string;
      relevance_score: number;
    }>;
    total_results: number;
  }> => {
    const params = new URLSearchParams({ query, limit: limit.toString() });
    if (documentId) {
      params.append('document_id', documentId.toString());
    }
    return api.get(`/documents/search?${params.toString()}`);
  },

  cleanupStuck: async (maxAgeMinutes: number = 5): Promise<{ message: string; fixed_count: number }> => {
    return api.post<{ message: string; fixed_count: number }>(`/documents/cleanup-stuck?max_age_minutes=${maxAgeMinutes}`);
  },
};

