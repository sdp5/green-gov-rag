export interface QueryRequest {
  query: string;
  region?: string;
  jurisdiction?: string;
  topics?: string[];
  max_sources?: number;
}

export interface SourceDocument {
  // Core fields
  title: string;
  source_url: string;
  excerpt?: string;
  relevance_score?: number;

  // Citation metadata (legal-grade citations)
  page_number?: number;
  page_range?: [number, number];
  section_title?: string;
  section_hierarchy?: string[];
  clause_reference?: string;
  deep_link?: string;
  citation?: string;

  // Document metadata
  jurisdiction?: string;
  category?: string;
  topic?: string;
  region?: string;

  // ESG & spatial metadata
  esg_metadata?: {
    frameworks?: string[];
    emission_scopes?: string[];
    greenhouse_gases?: string[];
    consolidation_method?: string;
    regulator?: string;
    reportable_under_nger?: boolean;
    [key: string]: unknown;
  };
  spatial_metadata?: {
    spatial_scope?: string;
    state?: string;
    lga_codes?: string[];
    lga_names?: string[];
    [key: string]: unknown;
  };
}

export interface TrustBreakdown {
  citation_score: number;
  authority_score: number;
  conflict_score: number;
  accuracy_score: number;
  warnings: string[];
}

export interface ConflictDetection {
  type: string;
  severity: string;
  resolution: string;
  details: string;
}

export interface QueryResponse {
  query: string;
  answer: string;
  sources: SourceDocument[];
  filters_applied: Record<string, unknown>;
  response_time_ms?: number;
  query_id?: number;

  // Phase 3: Trust & Compliance Features
  trust_score?: number;
  trust_confidence?: 'high' | 'medium' | 'low';
  trust_breakdown?: TrustBreakdown;
  conflicts_detected?: ConflictDetection[];
  hierarchy_explanation?: string;
  citation_warnings?: string[];
}

export interface FeedbackRequest {
  rating: number;
  feedback_text?: string;
}

export interface FeedbackResponse {
  success: boolean;
  message: string;
  query_id: number;
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
