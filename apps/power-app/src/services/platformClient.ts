import type { Dataset, GoldRecipe, Lineage, Mapping, ProfileResponse } from "../types";

export interface PlatformGateway {
  getDataset(datasetKey: string): Promise<Dataset>;
  startIngestion(datasetKey: string): Promise<Record<string, unknown>>;
  discover(datasetKey: string): Promise<Record<string, unknown>>;
  profile(datasetKey: string): Promise<ProfileResponse>;
  selectAsset(datasetKey: string, assetKey: string): Promise<Dataset>;
  getProfiles(datasetKey: string, assetKey: string): Promise<ProfileResponse>;
  approveAllRules(datasetKey: string): Promise<Record<string, unknown>>;
  executeRules(datasetKey: string): Promise<Record<string, unknown>>;
  reviewRule(datasetKey: string, ruleId: string, decision: string): Promise<Record<string, unknown>>;
  getMapping(datasetKey: string, assetKey: string): Promise<Mapping>;
  approveAllMappings(datasetKey: string): Promise<Record<string, unknown>>;
  approveLayer(datasetKey: string, layer: string): Promise<Record<string, unknown>>;
  runSilver(datasetKey: string): Promise<Record<string, unknown>>;
  listGoldRecipes(datasetKey: string): Promise<GoldRecipe[]>;
  createGoldRecipe(datasetKey: string, sourceAsset: string): Promise<GoldRecipe>;
  reviewGoldRecipe(datasetKey: string, recipeId: string): Promise<GoldRecipe>;
  runGold(datasetKey: string, recipeId: string): Promise<Record<string, unknown>>;
  getLineage(datasetKey: string): Promise<Lineage>;
}

class HttpPlatformGateway implements PlatformGateway {
  private readonly baseUrl = `${import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"}/api/v1/datasets`;

  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      ...options,
      headers: { Accept: "application/json", ...(options.body ? { "Content-Type": "application/json" } : {}), ...options.headers },
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload?.error?.message || payload?.detail || "Platform request failed");
    return payload as T;
  }

  getDataset = (key: string) => this.request<Dataset>(`/${key}`);
  startIngestion = (key: string) => this.request<Record<string, unknown>>(`/${key}/ingestion-runs`, { method: "POST", body: JSON.stringify({ force: false }) });
  discover = (key: string) => this.request<Record<string, unknown>>(`/${key}/discover`, { method: "POST" });
  profile = (key: string) => this.request<ProfileResponse>(`/${key}/profile`, { method: "POST" });
  selectAsset = (key: string, assetKey: string) => this.request<Dataset>(`/${key}/assets/select`, { method: "POST", body: JSON.stringify({ asset_key: assetKey }) });
  getProfiles = (key: string, assetKey: string) => this.request<ProfileResponse>(`/${key}/profiles?asset_key=${encodeURIComponent(assetKey)}`);
  approveAllRules = (key: string) => this.request<Record<string, unknown>>(`/${key}/rules/approve-all`, { method: "POST", body: JSON.stringify({ actor: "power-app-user" }) });
  executeRules = (key: string) => this.request<Record<string, unknown>>(`/${key}/rules/execute`, { method: "POST" });
  reviewRule = (key: string, ruleId: string, decision: string) => this.request<Record<string, unknown>>(`/${key}/rules/${ruleId}/review`, { method: "POST", body: JSON.stringify({ decision, actor: "power-app-user" }) });
  getMapping = (key: string, assetKey: string) => this.request<Mapping>(`/${key}/mappings/${assetKey}`);
  approveAllMappings = (key: string) => this.request<Record<string, unknown>>(`/${key}/mappings/approve-all`, { method: "POST", body: JSON.stringify({ actor: "power-app-user" }) });
  approveLayer = (key: string, layer: string) => this.request<Record<string, unknown>>(`/${key}/approvals/${layer}`, { method: "POST", body: JSON.stringify({ decision: "APPROVED", actor: "power-app-user", reason: "Reviewed in Power Apps" }) });
  runSilver = (key: string) => this.request<Record<string, unknown>>(`/${key}/silver/run`, { method: "POST" });
  listGoldRecipes = (key: string) => this.request<GoldRecipe[]>(`/${key}/gold/recipes`);
  createGoldRecipe = (key: string, sourceAsset: string) => this.request<GoldRecipe>(`/${key}/gold/recipes`, { method: "POST", body: JSON.stringify({ target_asset: "quality_summary", source_asset: sourceAsset, dimensions: [], measures: [], actor: "power-app-user" }) });
  reviewGoldRecipe = (key: string, recipeId: string) => this.request<GoldRecipe>(`/${key}/gold/recipes/${recipeId}/review`, { method: "POST", body: JSON.stringify({ decision: "APPROVED", actor: "power-app-user" }) });
  runGold = (key: string, recipeId: string) => this.request<Record<string, unknown>>(`/${key}/gold/run`, { method: "POST", body: JSON.stringify({ recipe_id: recipeId }) });
  getLineage = (key: string) => this.request<Lineage>(`/${key}/lineage`);
}

let gateway: PlatformGateway = new HttpPlatformGateway();

/** Register the generated custom-connector service during Power Apps initialization. */
export function registerPowerAppsGateway(powerAppsGateway: PlatformGateway): void {
  gateway = powerAppsGateway;
}

export function platformClient(): PlatformGateway {
  return gateway;
}
