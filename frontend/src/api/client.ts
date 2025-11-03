import axios from 'axios';
import { API_URL } from '../config/env';
import type { FeedbackRequest, FeedbackResponse, CoverageInfo } from '../types/api';
import { getOrCreateSessionId } from '../utils/session';

const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export default apiClient;

// API functions
export const queryAPI = {
  execute: async (query: string, filters: Record<string, unknown>) => {
    // Include session_id for user-specific query history
    const session_id = getOrCreateSessionId();
    const response = await apiClient.post('/query', {
      query,
      session_id,
      ...filters
    });
    return response.data;
  },
  submitFeedback: async (queryId: number, feedback: FeedbackRequest): Promise<FeedbackResponse> => {
    const response = await apiClient.post(`/query/${queryId}/feedback`, feedback);
    return response.data;
  },
};

export const documentsAPI = {
  list: async (params: Record<string, unknown>) => {
    const response = await apiClient.get('/documents', { params });
    return response.data;
  },
  getById: async (id: string) => {
    const response = await apiClient.get(`/documents/${id}`);
    return response.data;
  },
};

export const analyticsAPI = {
  getStats: async () => {
    const response = await apiClient.get('/analytics/stats');
    return response.data;
  },
};

export const mapAPI = {
  getLGAs: async () => {
    const response = await apiClient.get('/map/lgas');
    return response.data;
  },
};

export const coverageAPI = {
  getLGACoverage: async (lgaCode?: string, lgaName?: string): Promise<CoverageInfo> => {
    const params: Record<string, string> = {};
    if (lgaCode) params.lga_code = lgaCode;
    if (lgaName) params.lga_name = lgaName;
    const response = await apiClient.get('/lga-coverage', { params });
    return response.data;
  },
};
