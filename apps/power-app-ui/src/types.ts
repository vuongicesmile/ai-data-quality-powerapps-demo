export type Lifecycle = Record<string, boolean | number | string>;

export interface Asset {
  asset_key: string;
  file_name: string;
  provider: string;
  row_count: number;
  columns: string[];
  source_version: string;
}

export interface Dataset {
  dataset_key: string;
  dataset_id: string;
  dataset_name: string;
  provider: string;
  status: string;
  selected_asset_key?: string;
  assets: Asset[];
  lifecycle: Lifecycle;
  ingestion: Record<string, unknown>;
  silver: Record<string, SilverResult>;
  gold: Record<string, unknown>;
  approvals: Record<string, Approval>;
  manifest?: Record<string, unknown>;
}

export interface Profile {
  column_name: string;
  physical_type: string;
  semantic_type: string;
  row_count: number;
  null_count: number;
  null_percentage: number;
  distinct_count: number;
  duplicate_count: number;
}

export interface Rule {
  rule_id: string;
  column_name?: string;
  rule_type: string;
  description: string;
  status: string;
}

export interface RuleResult {
  rule_id: string;
  status: string;
  violation_count: number;
  evidence: Array<Record<string, unknown>>;
}

export interface ProfileResponse {
  asset_key: string;
  profiles: Profile[];
  quality: { score?: number; status?: string; dimensions?: Array<Record<string, unknown>> };
  rules: Rule[];
  rule_results: RuleResult[];
}

export interface Mapping {
  asset_key: string;
  status: string;
  target_table: string;
  business_key: string[];
  columns: Array<{ source: string; target: string; type: string; nullable: boolean }>;
}

export interface Approval {
  layer: string;
  decision: string;
  actor: string;
  recorded_at: string;
}

export interface SilverResult {
  table?: string;
  entity_set?: string;
  row_count?: number;
  valid_rows?: number;
  rejected_rows?: number;
  snapshot_hash?: string;
}

export interface GoldRecipe {
  recipe_id: string;
  status: string;
  source_asset: string;
  target_asset: string;
  version: number;
}

export interface Lineage {
  nodes: Array<{ id: string; label: string; status: string }>;
  edges: Array<{ from: string; to: string }>;
  activity: Array<{ event_id: string; action: string; status: string; detail: string; recorded_at: string }>;
}
