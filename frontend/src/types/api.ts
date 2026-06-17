export interface User {
  id: number;
  username: string;
  display_name: string;
  is_active: boolean;
  roles: string[];
  permissions: string[];
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface DocumentItem {
  id: number;
  title: string;
  file_name: string;
  file_type: string;
  business_type: string;
  source_type: string;
  product_id?: string | null;
  competitor_id?: string | null;
  industry_id?: string | null;
  trust_level: number;
  permission_scope: string;
  version: number;
  storage_path: string;
  status: string;
  uploaded_by?: number | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentListResponse {
  items: DocumentItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface DocumentDetail extends DocumentItem {
  versions: Array<{
    id: number;
    version: number;
    file_name: string;
    storage_path: string;
    file_size: number;
    checksum: string;
    created_at: string;
  }>;
  ingestion_jobs: Array<{
    id: number;
    job_type: string;
    status: string;
    error_message?: string | null;
    created_at: string;
  }>;
  chunks: Array<{
    id: number;
    chunk_index: number;
    title_path: string;
    content: string;
    page_number?: number | null;
    sheet_name?: string | null;
    token_count: number;
    vector_status: string;
    metadata_json: Record<string, unknown>;
    created_at: string;
  }>;
}

export interface Product {
  id: number;
  name: string;
  model?: string | null;
  category?: string | null;
  description?: string | null;
  status: string;
  confidence_level: number;
}

export interface EvidenceItem {
  id?: number | null;
  citation_code: string;
  group_name: string;
  source_type: string;
  document_id?: number | null;
  chunk_id?: number | null;
  content: string;
  quote?: string | null;
  score: number;
  trust_level: number;
  metadata_json: Record<string, unknown>;
}

export interface AnalysisStep {
  id: number;
  task_id: number;
  step_name: string;
  status: string;
  input_json: Record<string, unknown>;
  output_json: Record<string, unknown>;
  error_message?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
}

export interface AnalysisTask {
  id: number;
  task_type: string;
  product_id?: number | null;
  product_name_input?: string | null;
  product_model_input?: string | null;
  target_industry_id?: number | null;
  competitor_ids: number[];
  user_question?: string | null;
  analysis_goals: string[];
  output_format: string;
  status: string;
  current_step?: string | null;
  result_json: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  steps: AnalysisStep[];
}
