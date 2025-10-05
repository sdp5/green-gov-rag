import { create } from 'zustand';
import type { QueryResponse } from '../types/api';

interface QueryState {
  query: string;
  filters: {
    region?: string;
    jurisdiction?: string;
    topics?: string[];
  };
  results: QueryResponse | null;
  isLoading: boolean;

  setQuery: (query: string) => void;
  setFilters: (filters: Partial<QueryState['filters']>) => void;
  setResults: (results: QueryResponse | null) => void;
  setLoading: (loading: boolean) => void;
  reset: () => void;
}

export const useQueryStore = create<QueryState>((set) => ({
  query: '',
  filters: {},
  results: null,
  isLoading: false,

  setQuery: (query) => set({ query }),
  setFilters: (filters) => set((state) => ({
    filters: { ...state.filters, ...filters }
  })),
  setResults: (results) => set({ results, isLoading: false }),
  setLoading: (isLoading) => set({ isLoading }),
  reset: () => set({ query: '', filters: {}, results: null, isLoading: false }),
}));
