import { Button, ProgressBar } from "@fluentui/react-components";
import { profileRows, sourceAssets } from "../data/demoData";
import { useDemoWorkspace } from "../state/DemoWorkspaceProvider";
import { DataTable, KpiGrid, PageHeader, SectionCard, StatusBadge, WorkflowNav } from "../components/Common";

export function BronzeView() {
  const { selectedAsset, setSelectedAsset, openDrawer } = useDemoWorkspace();
  const asset = sourceAssets.find((item) => item.name === selectedAsset);
  const bronzeRows = [1, 2, 3].map((index) => [
    String(index), String(index * 10), <code>{`W/"1${index}"`}</code>, <code>{`a1b${index}...`}</code>, "20/08 10:35",
    <Button appearance="transparent" onClick={() => openDrawer("payload")}>View JSON</Button>,
  ]);
  return <>
    <PageHeader title="Bronze Layer" subtitle="Immutable raw snapshots" back={{ label: "Back to Run Detail", view: "ingestion_detail" }} />
    <KpiGrid items={[
      { label: "Batch ID", value: <code>8f3a1c7d</code> }, { label: "Snapshot Version", value: "v1" }, { label: "Assets", value: "4" }, { label: "Rows", value: "19,482" },
    ]} />
    <SectionCard title="Asset Inventory"><DataTable
      headers={["Asset", "Rows", "Columns", "Snapshot Hash", "Captured At", "Status", "Actions"]}
      rows={sourceAssets.map((item) => [item.name, item.rows.toLocaleString(), String(item.columns), <code>{item.hash}</code>, item.capturedAt, <StatusBadge value={item.status} />, <Button appearance="transparent">Inspect</Button>])}
      onRowClick={(index) => setSelectedAsset(sourceAssets[index].name)}
    /></SectionCard>
    {asset && <SectionCard title={`Asset Detail: ${asset.name}`} actions={<Button onClick={() => setSelectedAsset(null)}>Close</Button>}>
      <DataTable headers={["Source Row", "Source Item ID", "eTag", "Row Hash", "Captured At", "Payload"]} rows={bronzeRows} />
    </SectionCard>}
    <WorkflowNav back={{ label: "Back to Run Detail", view: "ingestion_detail" }} next={{ label: "Next Step: View Profiles", view: "profiles" }} />
  </>;
}

export function ProfilesView() {
  const { openDialog } = useDemoWorkspace();
  return <>
    <PageHeader title="Data Quality Profiles" subtitle="Statistical analysis of Bronze layer" back={{ label: "Back to Bronze", view: "bronze" }} />
    <KpiGrid items={[
      { label: "Columns", value: "28" }, { label: "Rows Profiled", value: "19,482" }, { label: "Overall Quality", value: "91%" }, { label: "Profile Status", value: <StatusBadge value="COMPLETED" /> },
    ]} />
    <SectionCard title="Column Profiles"><DataTable
      headers={["Column", "Detected Type", "Semantic Type", "Null %", "Unique %", "Min", "Max", "Quality", "Issues"]}
      rows={profileRows.map((profile) => [
        <strong>{profile.column}</strong>, <code>{profile.detectedType}</code>, profile.semanticType, `${profile.nullPercentage}%`, `${profile.uniquePercentage}%`, profile.min, profile.max,
        <div className="table-quality"><ProgressBar value={profile.quality / 100} color={profile.quality < 85 ? "error" : profile.quality < 90 ? "warning" : "success"} /><span>{profile.quality}%</span></div>,
        profile.issues ? <strong className="danger-text">{profile.issues}</strong> : "—",
      ])}
      onRowClick={(index) => openDialog("profile", { profileColumn: profileRows[index].column })}
    /></SectionCard>
    <WorkflowNav back={{ label: "Back to Bronze", view: "bronze" }} next={{ label: "Next Step: Review Rules", view: "rules" }} />
  </>;
}
