import apiClient from './client';

export interface Document {
  document_id: string;
  filename: string;
  content_type: string;
  file_size: number;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  created_at: string;
  user_id?: string;
}

export interface DocumentListResponse {
  documents: Document[];
  total: number;
  limit: number;
  offset: number;
}

export interface UploadDocumentResponse {
  document_id: string;
  filename: string;
  content_type: string;
  file_size: number;
  status: string;
  created_at: string;
}

export const documentsApi = {
  uploadDocument: async (
    file: File,
    onProgress?: (progress: number) => void
  ): Promise<UploadDocumentResponse> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post('/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(progress);
        }
      },
    });

    return response.data;
  },

  listDocuments: async (
    limit: number = 50,
    offset: number = 0
  ): Promise<DocumentListResponse> => {
    const response = await apiClient.get('/documents/', {
      params: { limit, offset },
    });
    return response.data;
  },

  getDocument: async (documentId: string): Promise<Document> => {
    const response = await apiClient.get(`/documents/${documentId}`);
    return response.data;
  },

  deleteDocument: async (documentId: string): Promise<void> => {
    await apiClient.delete(`/documents/${documentId}`);
  },
};
