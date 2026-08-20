export type ViewName =
  | "workspace"
  | "ingestion"
  | "ingestion_detail"
  | "bronze"
  | "profiles"
  | "rules"
  | "bronze_approval"
  | "mapping"
  | "silver"
  | "gold"
  | "activity";

export type Role = "Administrator" | "Operator";
export type RuleStatus = "PENDING" | "APPROVED" | "REJECTED";
export type RuleFilter = "pending" | "approved" | "rejected" | "all";
export type Layer = "Bronze" | "Silver" | "Gold";
export type DrawerName = "evidence" | "payload" | null;
export type DialogName = "run" | "approve" | "reject-rule" | "edit-rule" | "profile" | "ai-recipe" | null;

export interface SourceAsset {
  name: string;
  rows: number;
  columns: number;
  hash: string;
  capturedAt: string;
  status: "CAPTURED";
}

export interface ProfileRow {
  column: string;
  detectedType: string;
  semanticType: string;
  nullPercentage: number;
  uniquePercentage: number;
  min: string;
  max: string;
  quality: number;
  issues: number;
}

export interface DemoRule {
  id: string;
  name: string;
  column: string;
  type: string;
  severity: "High" | "Medium" | "Low";
  confidence: number;
  violations: number;
  description: string;
  status: RuleStatus;
}

export interface TimelineEvent {
  time: string;
  title: string;
  description: string;
  tone?: "brand" | "warning" | "ai";
}

export interface ChatMessage {
  id: number;
  sender: "bot" | "user";
  text: string;
  suggestions?: Array<{ label: string; view: ViewName }>;
}
