import { useCallback, useEffect, useMemo, useState } from "react";
import { LineageRail } from "./components/LineageRail";
import { platformClient } from "./services/platformClient";
import type { Dataset, GoldRecipe, Lineage, Mapping, ProfileResponse, Rule } from "./types";

const datasetKey = "ecommerce-v1";
const tabs = ["Workspace", "Profiles", "Rules", "Mapping", "Silver", "Gold", "Lineage"] as const;
type Tab = typeof tabs[number];

function Status({ value }: { value?: string }) {
  const normalized = String(value || "pending").toLowerCase();
  return <span className={`status status-${normalized}`}>{normalized.replaceAll("_", " ")}</span>;
}

function ActionButton({ children, onClick, disabled, tone = "primary" }: { children: React.ReactNode; onClick: () => void; disabled?: boolean; tone?: "primary" | "quiet" | "danger" }) {
  return <button className={`button button-${tone}`} disabled={disabled} onClick={onClick}>{children}</button>;
}

export function App() {
  const client = useMemo(() => platformClient(), []);
  const [tab, setTab] = useState<Tab>("Workspace");
  const [dataset, setDataset] = useState<Dataset>();
  const [profiles, setProfiles] = useState<ProfileResponse>();
  const [mapping, setMapping] = useState<Mapping>();
  const [recipes, setRecipes] = useState<GoldRecipe[]>([]);
  const [lineage, setLineage] = useState<Lineage>();
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const selectedAsset = dataset?.selected_asset_key || dataset?.assets?.[0]?.asset_key;

  const refresh = useCallback(async () => {
    const next = await client.getDataset(datasetKey);
    setDataset(next);
    setLineage(await client.getLineage(datasetKey));
    const asset = next.selected_asset_key || next.assets?.[0]?.asset_key;
    if (asset && Boolean(next.lifecycle.profiled)) {
      setProfiles(await client.getProfiles(datasetKey, asset));
      setMapping(await client.getMapping(datasetKey, asset));
      setRecipes(await client.listGoldRecipes(datasetKey));
    }
  }, [client]);

  useEffect(() => { refresh().catch((reason) => setError(String(reason.message || reason))); }, [refresh]);

  async function run(label: string, action: () => Promise<unknown>) {
    setBusy(label); setError(""); setNotice("");
    try {
      await action();
      setNotice(`${label} completed`);
      await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    } finally {
      setBusy("");
    }
  }

  async function chooseAsset(assetKey: string) {
    await run("Select asset", () => client.selectAsset(datasetKey, assetKey));
  }

  const progress = Number(dataset?.lifecycle.progress || 0);
  const violationCount = profiles?.rule_results.reduce((sum, result) => sum + result.violation_count, 0) || 0;
  const latestRecipe = recipes.at(-1);

  return <div className="app-shell">
    <header className="topbar">
      <div className="brand-mark" aria-hidden="true"><span /><span /><span /></div>
      <div className="brand-copy"><strong>AI Data Quality</strong><small>Microsoft data platform control room</small></div>
      <div className="topbar-meta"><span>Environment</span><strong>Development</strong></div>
      <Status value={dataset?.status} />
    </header>

    <main>
      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">Dataset / {datasetKey}</p>
          <h1>Turn source files into<br /><em>governed evidence.</em></h1>
          <p className="hero-description">One review surface for SharePoint ingestion, Bronze profiling, rule decisions, and approved Silver and Gold outputs.</p>
        </div>
        <div className="hero-gauge" style={{ "--progress": `${progress * 3.6}deg` } as React.CSSProperties}>
          <div><strong>{progress}%</strong><span>workflow complete</span></div>
        </div>
      </section>

      <LineageRail lineage={lineage} />

      {(error || notice || busy) && <section className={`message ${error ? "message-error" : "message-info"}`} role="status">
        <span className={busy ? "pulse" : "message-dot"} />
        <div><strong>{error ? "Action blocked" : busy ? `${busy} in progress` : "Workflow updated"}</strong><p>{error || notice || "Waiting for the platform operation to finish."}</p></div>
      </section>}

      <nav className="tabs" aria-label="Dataset workflow">
        {tabs.map((item) => <button key={item} className={tab === item ? "active" : ""} onClick={() => setTab(item)}>{item}</button>)}
      </nav>

      {tab === "Workspace" && <div className="content-grid">
        <section className="panel panel-wide">
          <header className="panel-header"><div><p className="eyebrow">Source batch</p><h2>SharePoint ingestion</h2></div><Status value={String(dataset?.ingestion?.status || "idle")} /></header>
          <div className="metrics">
            <Metric label="Provider" value={dataset?.provider || "sharepoint"} />
            <Metric label="Assets" value={String(dataset?.assets?.length || 0)} />
            <Metric label="Batch" value={String(dataset?.manifest?.batch_id || "Not published")} mono />
            <Metric label="Selected" value={selectedAsset || "None"} />
          </div>
          <div className="action-row">
            <ActionButton disabled={Boolean(busy)} onClick={() => run("Ingestion", () => client.startIngestion(datasetKey))}>Run ingestion</ActionButton>
            <ActionButton tone="quiet" disabled={Boolean(busy) || !dataset?.lifecycle.ingested} onClick={() => run("Schema discovery", () => client.discover(datasetKey))}>Discover schemas</ActionButton>
            <ActionButton tone="quiet" disabled={Boolean(busy) || !dataset?.lifecycle.ingested} onClick={() => run("Profiling", () => client.profile(datasetKey))}>Profile all assets</ActionButton>
          </div>
        </section>
        <section className="panel">
          <header className="panel-header"><div><p className="eyebrow">Batch inventory</p><h2>Assets</h2></div></header>
          <div className="asset-list">{dataset?.assets?.map((asset) => <button key={asset.asset_key} className={selectedAsset === asset.asset_key ? "selected" : ""} onClick={() => chooseAsset(asset.asset_key)}>
            <span className="file-icon">CSV</span><span><strong>{asset.file_name}</strong><small>{asset.row_count} rows · {asset.columns.length} columns</small></span><span>→</span>
          </button>)}{!dataset?.assets?.length && <Empty text="Run ingestion to publish the canonical SharePoint batch." />}</div>
        </section>
        <section className="panel">
          <header className="panel-header"><div><p className="eyebrow">Review gates</p><h2>Lifecycle</h2></div></header>
          <div className="gate-list">{Object.entries(dataset?.lifecycle || {}).filter(([, value]) => typeof value === "boolean").map(([key, value]) => <div key={key}><span className={value ? "gate-done" : "gate-open"}>{value ? "✓" : "○"}</span><strong>{key.replaceAll("_", " ")}</strong></div>)}</div>
        </section>
      </div>}

      {tab === "Profiles" && <section className="panel">
        <header className="panel-header"><div><p className="eyebrow">Bronze observability</p><h2>{selectedAsset || "Asset"} column profiles</h2></div><div className="score"><strong>{profiles?.quality.score ?? "—"}</strong><span>quality score</span></div></header>
        <div className="table-wrap"><table><thead><tr><th>Column</th><th>Physical type</th><th>Semantic</th><th>Nulls</th><th>Distinct</th><th>Duplicates</th></tr></thead><tbody>{profiles?.profiles.map((profile) => <tr key={profile.column_name}><td><strong>{profile.column_name}</strong></td><td><code>{profile.physical_type}</code></td><td>{profile.semantic_type}</td><td>{profile.null_count} <small>({profile.null_percentage}%)</small></td><td>{profile.distinct_count}</td><td>{profile.duplicate_count}</td></tr>)}</tbody></table></div>
        {!profiles?.profiles.length && <Empty text="Profile the Bronze batch to inspect columns." />}
      </section>}

      {tab === "Rules" && <section className="panel">
        <header className="panel-header"><div><p className="eyebrow">Controls</p><h2>Rule review</h2></div><div className="header-actions"><span className="violation-count">{violationCount} violations</span><ActionButton tone="quiet" disabled={Boolean(busy) || !profiles?.rules.length} onClick={() => run("Approve rules", () => client.approveAllRules(datasetKey))}>Approve all</ActionButton><ActionButton disabled={Boolean(busy)} onClick={() => run("Rule execution", () => client.executeRules(datasetKey))}>Execute approved</ActionButton></div></header>
        <div className="rule-list">{profiles?.rules.map((rule) => <RuleCard rule={rule} key={rule.rule_id} busy={Boolean(busy)} onReview={(decision) => run(`${decision} rule`, () => client.reviewRule(datasetKey, rule.rule_id, decision))} />)}{!profiles?.rules.length && <Empty text="Profiling generates deterministic rule candidates." />}</div>
      </section>}

      {tab === "Mapping" && <section className="panel">
        <header className="panel-header"><div><p className="eyebrow">Schema contract</p><h2>{selectedAsset || "Asset"} mapping</h2><p className="subtle">Target: {mapping?.target_table || "Not generated"}</p></div><div className="header-actions"><Status value={mapping?.status} /><ActionButton disabled={Boolean(busy) || !mapping} onClick={() => run("Mapping approval", () => client.approveAllMappings(datasetKey))}>Approve all assets</ActionButton></div></header>
        <div className="mapping-grid">{mapping?.columns.map((column) => <div key={column.source}><code>{column.source}</code><span>→</span><strong>{column.target}</strong><small>{column.type} · {column.nullable ? "nullable" : "required"}</small></div>)}</div>
        {!mapping && <Empty text="Profile the dataset to generate governed mappings." />}
      </section>}

      {tab === "Silver" && <div className="content-grid">
        <section className="panel panel-wide"><header className="panel-header"><div><p className="eyebrow">Medallion layer</p><h2>Silver publication</h2></div><Status value={dataset?.lifecycle.silver_approved ? "approved" : dataset?.lifecycle.transformed ? "published" : "pending"} /></header>
          <p className="body-copy">Approved mappings convert Bronze strings into governed ClickHouse types. Invalid rows remain available as bounded rejection evidence.</p>
          <div className="action-row"><ActionButton disabled={Boolean(busy) || !dataset?.lifecycle.bronze_approved} onClick={() => run("Silver publication", () => client.runSilver(datasetKey))}>Build Silver</ActionButton><ActionButton tone="quiet" disabled={Boolean(busy) || !dataset?.lifecycle.transformed} onClick={() => run("Silver approval", () => client.approveLayer(datasetKey, "SILVER"))}>Approve Silver</ActionButton></div>
        </section>
        {Object.entries(dataset?.silver || {}).map(([key, value]) => <section className="panel" key={key}><p className="eyebrow">{key}</p><h3>{value.table || "Silver table"}</h3><div className="metrics metrics-compact"><Metric label="Valid" value={String(value.valid_rows || 0)} /><Metric label="Rejected" value={String(value.rejected_rows || 0)} /></div></section>)}
        {!Object.keys(dataset?.silver || {}).length && <section className="panel"><Empty text="Approve Bronze and mappings, then build Silver." /></section>}
        <section className="panel"><p className="eyebrow">Bronze gate</p><h3>{dataset?.lifecycle.bronze_approved ? "Approved" : "Review required"}</h3><ActionButton tone="quiet" disabled={Boolean(busy) || !dataset?.lifecycle.profiled} onClick={() => run("Bronze approval", () => client.approveLayer(datasetKey, "BRONZE"))}>Approve Bronze</ActionButton></section>
      </div>}

      {tab === "Gold" && <div className="content-grid">
        <section className="panel panel-wide"><header className="panel-header"><div><p className="eyebrow">Business output</p><h2>Gold recipe control</h2></div><Status value={dataset?.lifecycle.gold_approved ? "approved" : dataset?.lifecycle.gold_published ? "published" : latestRecipe?.status} /></header>
          <p className="body-copy">Version, review, and publish a governed output from approved Silver assets. The default demo recipe creates a reviewable snapshot.</p>
          <div className="action-row"><ActionButton disabled={Boolean(busy) || !dataset?.lifecycle.silver_approved || !selectedAsset} onClick={() => run("Gold recipe", () => client.createGoldRecipe(datasetKey, selectedAsset!))}>Create recipe</ActionButton><ActionButton tone="quiet" disabled={Boolean(busy) || !latestRecipe || latestRecipe.status === "APPROVED"} onClick={() => run("Gold recipe approval", () => client.reviewGoldRecipe(datasetKey, latestRecipe!.recipe_id))}>Approve recipe</ActionButton><ActionButton tone="quiet" disabled={Boolean(busy) || latestRecipe?.status !== "APPROVED"} onClick={() => run("Gold publication", () => client.runGold(datasetKey, latestRecipe!.recipe_id))}>Publish Gold</ActionButton><ActionButton tone="quiet" disabled={Boolean(busy) || !dataset?.lifecycle.gold_published} onClick={() => run("Gold approval", () => client.approveLayer(datasetKey, "GOLD"))}>Approve Gold</ActionButton></div>
        </section>
        {recipes.map((recipe) => <section className="panel" key={recipe.recipe_id}><p className="eyebrow">Recipe v{recipe.version}</p><h3>{recipe.target_asset}</h3><p className="subtle">Source: {recipe.source_asset}</p><Status value={recipe.status} /></section>)}
        <section className="panel"><p className="eyebrow">Published result</p><h3>{String(dataset?.gold?.table || "No Gold table")}</h3><div className="metrics metrics-compact"><Metric label="Rows" value={String(dataset?.gold?.row_count || 0)} /><Metric label="Reconcile" value={String(dataset?.gold?.reconciliation || "pending")} /></div></section>
      </div>}

      {tab === "Lineage" && <section className="panel">
        <header className="panel-header"><div><p className="eyebrow">Audit trail</p><h2>Run history and lineage</h2></div><span className="subtle">{lineage?.activity.length || 0} events</span></header>
        <LineageRail lineage={lineage} />
        <div className="activity-list">{lineage?.activity.slice().reverse().map((event) => <article key={event.event_id}><div className="activity-mark" /><div><strong>{event.action.replaceAll("_", " ")}</strong><p>{event.detail || "Workflow state updated"}</p></div><div><Status value={event.status} /><time>{new Date(event.recorded_at).toLocaleString()}</time></div></article>)}</div>
      </section>}
    </main>
    <footer><span>AI Data Quality / Generic Dataset Demo</span><span>SharePoint · Graph · Airflow · ClickHouse · Power Apps</span></footer>
  </div>;
}

function Metric({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return <div className="metric"><span>{label}</span><strong className={mono ? "mono" : ""}>{value}</strong></div>;
}

function Empty({ text }: { text: string }) { return <div className="empty"><span>◇</span><p>{text}</p></div>; }

function RuleCard({ rule, busy, onReview }: { rule: Rule; busy: boolean; onReview: (decision: string) => void }) {
  return <article className="rule-card"><div className="rule-code">{rule.rule_type.slice(0, 2)}</div><div><strong>{rule.description}</strong><p><code>{rule.column_name || "dataset"}</code> · {rule.rule_type}</p></div><Status value={rule.status} /><div className="rule-actions"><button disabled={busy} onClick={() => onReview("APPROVED")}>Approve</button><button disabled={busy} onClick={() => onReview("REJECTED")}>Reject</button></div></article>;
}
