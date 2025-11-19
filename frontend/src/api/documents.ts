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
};

