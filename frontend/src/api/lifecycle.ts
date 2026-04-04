import apiClient from './client';
import type {
  LifecycleSummary,
  LGALifecycleResponse,
  DocumentHistoryResponse,
  RegisterDocumentRequest,
  RegisterDocumentResponse,
  ReplaceDocumentResponse,
} from '../types/lifecycle';

// All admin lifecycle endpoints live under /api/admin/...
// apiClient.baseURL is already set to API_URL (e.g. http://localhost:8000/api)

export const lifecycleAPI = {
  getSummary: async (): Promise<LifecycleSummary> => {
    const response = await apiClient.get('/admin/lifecycle/summary');
    return response.data;
  },

  getByLGA: async (lifecycleState?: string): Promise<LGALifecycleResponse> => {
    const params: Record<string, string> = {};
    if (lifecycleState && lifecycleState !== 'all') {
      params.lifecycle_state = lifecycleState;
    }
    const response = await apiClient.get('/admin/lifecycle/documents/by-lga', { params });
    return response.data;
  },

  getHistory: async (fileId: string): Promise<DocumentHistoryResponse> => {
    const response = await apiClient.get(`/admin/lifecycle/documents/${fileId}/history`);
    return response.data;
  },

  replace: async (fileId: string, newUrl: string): Promise<ReplaceDocumentResponse> => {
    const response = await apiClient.post(
      `/admin/lifecycle/documents/${fileId}/replace`,
      { new_url: newUrl }
    );
    return response.data;
  },

  markSuperseded: async (fileId: string): Promise<{ status: string }> => {
    const response = await apiClient.post(
      `/admin/lifecycle/documents/${fileId}/mark-superseded`
    );
    return response.data;
  },

  register: async (body: RegisterDocumentRequest): Promise<RegisterDocumentResponse> => {
    const response = await apiClient.post('/admin/documents', body);
    return response.data;
  },
};
