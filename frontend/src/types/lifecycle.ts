// TypeScript types mirroring backend lifecycle Pydantic schemas
// backend/green_gov_rag/api/schemas/lifecycle.py

export type LifecycleState =
  | 'detect'
  | 'fetch'
  | 'chunk'
  | 'embed'
  | 'available_for_search'
  | 'url_dead'
  | 'mark_superseded'
  | 'removed_from_search';

export interface LifecycleSummary {
  detect: number;
  fetch: number;
  chunk: number;
  embed: number;
  available_for_search: number;
  url_dead: number;
  mark_superseded: number;
  removed_from_search: number;
  total_files: number;
  total_sources: number;
  last_monitoring_run: string | null; // ISO datetime
}

export interface LifecycleDocumentEntry {
  file_id: string;
  source_id: string;
  title: string;
  jurisdiction: string;
  topic: string;
  lga_names: string[];
  applies_to_all_lgas: boolean;
  file_url: string;
  lifecycle_state: LifecycleState;
  lifecycle_transitioned_at: string | null;
  http_status_code: number | null;
  http_last_checked_at: string | null;
  superseded_by_url: string | null;
}

export interface LGADocumentGroup {
  lga_name: string;
  documents: LifecycleDocumentEntry[];
}

export interface LGALifecycleResponse {
  groups: LGADocumentGroup[];
  total_lgas: number;
  total_files: number;
}

export interface LifecycleEventEntry {
  id: number;
  from_state: LifecycleState;
  to_state: LifecycleState;
  triggered_by: string;
  http_status: number | null;
  run_id: string | null;
  details: Record<string, unknown> | null;
  created_at: string; // ISO datetime
}

export interface DocumentHistoryResponse {
  file_id: string;
  events: LifecycleEventEntry[];
}

export interface RegisterDocumentRequest {
  title: string;
  source_url: string;
  download_urls: string[];
  jurisdiction: string;
  category: string;
  topic: string;
  region?: string;
  esg_metadata?: Record<string, unknown>;
  spatial_metadata?: {
    spatial_scope?: string;
    state?: string | null;
    lga_codes?: string[];
    lga_names?: string[];
    applies_to_all_lgas?: boolean;
    applies_to_point?: boolean;
  };
}

export interface RegisterDocumentResponse {
  source_id: string;
  file_ids: string[];
  lifecycle_state: string;
  message: string;
}

export interface ReplaceDocumentResponse {
  status: string;
  superseded_file_id: string;
  new_file_id: string;
  new_url: string;
  message: string;
}
