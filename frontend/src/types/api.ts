export interface QueryRequest {
  query: string;
  region?: string;
  jurisdiction?: string;
  topics?: string[];
  max_sources?: number;
}

export interface SourceDocument {
  title: string;
  source_url: string;
  excerpt?: string;
  relevance_score?: number;
  jurisdiction?: string;
  topic?: string;
  region?: string;
}

export interface QueryResponse {
  query: string;
  answer: string;
  sources: SourceDocument[];
  filters_applied: Record<string, unknown>;
  response_time_ms?: number;
}

export interface Document {
  id: string;
  title: string;
  source_url: string;
  jurisdiction: string;
  topic: string;
  region?: string;
  category?: string;
  status: string;
  chunk_count: number;
  created_at: string;
  processed_at?: string;
  summary?: string;
}

export interface DocumentListResponse {
  documents: Document[];
  total: number;
  limit: number;
  offset: number;
}

export interface AnalyticsStats {
  total_documents: number;
  total_queries: number;
  avg_response_time_ms?: number;
  documents_by_jurisdiction: Array<{ name: string; count: number }>;
  documents_by_topic: Array<{ name: string; count: number }>;
  documents_by_region: Array<{ name: string; count: number }>;
}
