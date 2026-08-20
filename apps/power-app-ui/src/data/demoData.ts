import type { DemoRule, ProfileRow, SourceAsset, TimelineEvent, ViewName } from "../ui/types";

export const viewTitles: Record<ViewName, string> = {
  workspace: "Workspace",
  ingestion: "Ingestion Runs",
  ingestion_detail: "Ingestion Runs",
  bronze: "Bronze",
  profiles: "Profiles",
  rules: "Rules & Evidence",
  bronze_approval: "Bronze Approval",
  mapping: "Mapping",
  silver: "Silver",
  gold: "Gold",
  activity: "Activity",
};

export const sourceAssets: SourceAsset[] = [
  { name: "TimerList_AllProject01", rows: 4831, columns: 28, hash: "a1b2c3d4e5f6...", capturedAt: "20/08 10:35", status: "CAPTURED" },
  { name: "TimerList_AllProject02", rows: 5102, columns: 28, hash: "b2c3d4e5f6a1...", capturedAt: "20/08 10:35", status: "CAPTURED" },
  { name: "TimerList_AllProject03", rows: 4950, columns: 28, hash: "c3d4e5f6a1b2...", capturedAt: "20/08 10:35", status: "CAPTURED" },
  { name: "TimerList_AllProject04", rows: 4599, columns: 28, hash: "d4e5f6a1b2c3...", capturedAt: "20/08 10:35", status: "CAPTURED" },
];

export const profileRows: ProfileRow[] = [
  { column: "ProjectName", detectedType: "string", semanticType: "Name", nullPercentage: 0, uniquePercentage: 72, min: "—", max: "—", quality: 95, issues: 12 },
  { column: "Customer", detectedType: "string", semanticType: "Organization", nullPercentage: 1.2, uniquePercentage: 18, min: "—", max: "—", quality: 93, issues: 24 },
  { column: "StartDate", detectedType: "datetime", semanticType: "Date", nullPercentage: 0.6, uniquePercentage: 61, min: "2022-01-04", max: "2026-08-18", quality: 96, issues: 9 },
  { column: "Budget", detectedType: "decimal", semanticType: "Currency", nullPercentage: 2.4, uniquePercentage: 44, min: "-500,000", max: "8,400,000", quality: 88, issues: 41 },
  { column: "Email", detectedType: "string", semanticType: "Email", nullPercentage: 3.1, uniquePercentage: 91, min: "—", max: "—", quality: 82, issues: 76 },
  { column: "Status", detectedType: "string", semanticType: "Category", nullPercentage: 0, uniquePercentage: 0.04, min: "—", max: "—", quality: 99, issues: 0 },
];

export const initialRules: DemoRule[] = [
  { id: "rule-email", name: "Email must be valid format", column: "Email", type: "REGEX", severity: "High", confidence: 96, violations: 76, description: "Column semantic type and samples indicate email addresses.", status: "PENDING" },
  { id: "rule-start", name: "StartDate cannot be empty", column: "StartDate", type: "NOT_NULL", severity: "High", confidence: 99, violations: 9, description: "Missing start dates prevent duration and schedule analysis.", status: "PENDING" },
  { id: "rule-budget", name: "Budget must be numeric and >= 0", column: "Budget", type: "RANGE", severity: "Medium", confidence: 92, violations: 41, description: "Negative budget values are outside the governed business range.", status: "PENDING" },
  { id: "rule-project", name: "Project name is required", column: "ProjectName", type: "NOT_NULL", severity: "High", confidence: 100, violations: 0, description: "Every project row requires a display name.", status: "APPROVED" },
  { id: "rule-status", name: "Status must use approved values", column: "Status", type: "ENUM", severity: "Medium", confidence: 100, violations: 0, description: "Status values follow the TimerApp lifecycle vocabulary.", status: "APPROVED" },
];

export const lifecycleEvents: TimelineEvent[] = [
  { time: "10:35", title: "Run created", description: "Triggered by Alex Dev" },
  { time: "10:35", title: "SharePoint source validated", description: "4 lists verified via Microsoft Graph" },
  { time: "10:36", title: "4 assets captured", description: "TimerList_AllProject01 to 04" },
  { time: "10:37", title: "Bronze snapshot persisted", description: "19,482 Bronze rows persisted to Dataverse" },
  { time: "10:38", title: "28 columns profiled", description: "FastAPI worker completed statistical analysis" },
  { time: "10:39", title: "3 AI rule suggestions generated", description: "AI Service analyzed profiling metrics", tone: "ai" },
  { time: "10:40", title: "Waiting for rule review", description: "Reviewer action required", tone: "warning" },
];

export const activityEvents: TimelineEvent[] = [
  { time: "10:45", title: "Bronze approved", description: "Actor: Maria Reviewer · Entity: Bronze Layer · Run: 8f3a1c7d" },
  { time: "10:42", title: "Email rule approved", description: "Actor: Alex Dev · Entity: Rule · Run: 8f3a1c7d" },
  { time: "10:39", title: "AI generated 3 rule suggestions", description: "Actor: AI Service · Entity: Rules · Run: 8f3a1c7d", tone: "ai" },
  { time: "10:37", title: "Profiling completed", description: "Actor: Worker · Entity: Profiles · Run: 8f3a1c7d" },
  { time: "10:36", title: "Bronze snapshot captured", description: "Actor: System · Entity: Bronze Layer · Run: 8f3a1c7d" },
  { time: "10:35", title: "Ingestion started", description: "Actor: Alex Dev · Entity: Run 8f3a1c7d" },
];

export const mappingRows = [
  ["ProjectName", "project_name", "Text", "Required"],
  ["Customer", "customer_name", "Text", "Required"],
  ["StartDate", "start_date", "Date only", "Required"],
  ["Budget", "budget", "Decimal", "Nullable"],
  ["Email", "contact_email", "Text", "Nullable"],
  ["Status", "project_status", "Choice", "Required"],
] as const;

export const silverAccepted = [
  ["Cloud Migration", "Samsung", "2024-05-10", "1,200,000", "TimerList_AllProject01", "VALID"],
  ["Network Upgrade", "LG", "2024-06-14", "840,000", "TimerList_AllProject02", "VALID"],
  ["Data Platform", "Intel", "2024-07-03", "2,100,000", "TimerList_AllProject03", "VALID"],
] as const;

export const runRows = [
  ["8f3a1c7d", "20/08/2026 10:35", "4", "19,482", "WAITING_REVIEW", "75%", "Alex Dev"],
  ["7a2b9c8e", "19/08/2026 14:20", "4", "19,450", "COMPLETED", "100%", "System"],
  ["6c1d8e9f", "18/08/2026 09:15", "4", "0", "FAILED", "20%", "Alex Dev"],
] as const;
