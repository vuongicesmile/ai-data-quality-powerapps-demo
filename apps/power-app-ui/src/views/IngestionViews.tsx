import { Button, Tab, TabList } from "@fluentui/react-components";
import { PlayRegular } from "@fluentui/react-icons";
import { useState } from "react";
import { lifecycleEvents, runRows, sourceAssets } from "../data/demoData";
import { useDemoWorkspace } from "../state/DemoWorkspaceProvider";
import { DataTable, KpiGrid, PageHeader, SectionCard, StatusBadge, Timeline, WorkflowNav } from "../components/Common";

export function IngestionRunsView() {
  const { navigate, openDialog } = useDemoWorkspace();
  return <>
    <PageHeader title="Ingestion Runs" subtitle="History of data capture and processing runs" actions={<Button appearance="primary" icon={<PlayRegular />} onClick={() => openDialog("run")}>Run Data Quality Check</Button>} />
    <SectionCard><DataTable
      headers={["Run ID", "Dataset", "Started At", "Assets", "Rows", "Status", "Progress", "Triggered By", "Actions"]}
      rows={runRows.map((run) => [<strong className="brand-text">{run[0]}</strong>, "TimerApp Projects", run[1], run[2], run[3], <StatusBadge value={run[4]} />, run[5], run[6], <Button appearance="transparent">View</Button>])}
      onRowClick={(index) => index === 0 && navigate("ingestion_detail")}
    /></SectionCard>
    <WorkflowNav back={{ label: "Back to Workspace", view: "workspace" }} next={{ label: "Next Step: View Profiles", view: "profiles" }} />
  </>;
}

type DetailTab = "overview" | "assets" | "bronze" | "profiles" | "activity";
export function IngestionDetailView() {
  const { navigate } = useDemoWorkspace();
  const [tab, setTab] = useState<DetailTab>("overview");
  return <>
    <PageHeader title="Run 8f3a1c7d" subtitle="TimerApp Projects ingestion details" back={{ label: "Back to Runs", view: "ingestion" }} actions={<StatusBadge value="WAITING_REVIEW" />} />
    <KpiGrid items={[
      { label: "Dataset", value: "TimerApp Projects" }, { label: "Started", value: "20/08 10:35" }, { label: "Completed", value: "20/08 10:40" }, { label: "Duration", value: "5m 12s" },
      { label: "Trigger", value: "Manual" }, { label: "Assets Captured", value: "4" }, { label: "Bronze Rows", value: "19,482" }, { label: "Source Hash", value: <code>a1b2c3d4e5f6...</code> },
    ]} />
    <SectionCard title="Lifecycle Timeline"><Timeline events={lifecycleEvents} /></SectionCard>
    <SectionCard>
      <TabList selectedValue={tab} onTabSelect={(_, data) => setTab(data.value as DetailTab)}>
        <Tab value="overview">Overview</Tab><Tab value="assets">Assets</Tab><Tab value="bronze">Bronze</Tab><Tab value="profiles">Profiles</Tab><Tab value="activity">Activity</Tab>
      </TabList>
      <div className="tab-panel">
        {tab === "overview" && <p>This run successfully captured 4 assets from the TimerApp SharePoint lists. The Bronze layer is immutable and ready for review. AI generated 3 rule suggestions based on profiling anomalies.</p>}
        {tab === "assets" && <DataTable headers={["Asset Name", "Rows", "Status"]} rows={sourceAssets.map((asset) => [asset.name, asset.rows.toLocaleString(), <StatusBadge value="CAPTURED" />])} />}
        {tab === "bronze" && <Button onClick={() => navigate("bronze")}>View Bronze Snapshots →</Button>}
        {tab === "profiles" && <Button onClick={() => navigate("profiles")}>View Profiles →</Button>}
        {tab === "activity" && <Button onClick={() => navigate("activity")}>View Activity →</Button>}
      </div>
    </SectionCard>
    <WorkflowNav back={{ label: "Back to Runs", view: "ingestion" }} next={{ label: "Next Step: Inspect Bronze", view: "bronze" }} />
  </>;
}
