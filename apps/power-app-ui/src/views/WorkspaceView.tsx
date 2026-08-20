import { Badge, Button } from "@fluentui/react-components";
import { PlayRegular } from "@fluentui/react-icons";
import { profileRows, sourceAssets } from "../data/demoData";
import { useDemoWorkspace } from "../state/DemoWorkspaceProvider";
import { GovernanceStepper, KpiGrid, PageHeader, QualityBar, SectionCard, StatusBadge, WorkflowNav } from "../components/Common";

export function WorkspaceView() {
  const { navigate, openDialog, rules } = useDemoWorkspace();
  const pendingRules = rules.filter((rule) => rule.status === "PENDING");
  return <>
    <PageHeader title="AI Data Quality Workspace" subtitle="Governed data-quality workflow for TimerApp SharePoint lists" actions={
      <Button appearance="primary" icon={<PlayRegular />} onClick={() => openDialog("run")}>Run Data Quality Check</Button>
    } />
    <KpiGrid items={[
      { label: "Last Run", value: "20/08/2026 10:40" },
      { label: "Status", value: <StatusBadge value="WAITING_REVIEW" /> },
      { label: "Assets", value: "4" },
      { label: "Bronze Rows", value: "19,482" },
      { label: "Quality Score", value: "91%" },
      { label: "Approved Rules", value: String(rules.filter((rule) => rule.status === "APPROVED").length + 5) },
      { label: "Pending Rules", value: String(pendingRules.length) },
      { label: "Current Step", value: "Rule Review" },
    ]} />
    <GovernanceStepper />
    <div className="dashboard-grid">
      <SectionCard title="SharePoint Sources" actions={<Badge appearance="tint" color="success">4 Healthy</Badge>}>
        <div className="source-list">{sourceAssets.map((asset) => <div className="source-row" key={asset.name}><div><strong>{asset.name}</strong><small>{asset.rows.toLocaleString()} rows · Captured 10:35</small></div><StatusBadge value="Healthy" /></div>)}</div>
      </SectionCard>
      <SectionCard title="Data Quality Profiles" actions={<Button appearance="transparent" onClick={() => navigate("profiles")}>View all</Button>}>
        <div className="quality-list">{profileRows.slice(0, 5).map((profile) => <QualityBar key={profile.column} label={profile.column} score={profile.quality} />)}</div>
      </SectionCard>
      <SectionCard title="AI Suggested Rules" actions={<Badge appearance="tint" color="brand">Review required</Badge>}>
        <div className="suggestion-list">{pendingRules.map((rule) => <article key={rule.id}><strong>{rule.name}</strong><small>Confidence: {rule.confidence}% · Severity: {rule.severity}</small></article>)}</div>
        <Button appearance="transparent" onClick={() => navigate("rules")}>Review rules →</Button>
      </SectionCard>
    </div>
    <WorkflowNav next={{ label: "Next Step: Review Rules", view: "rules" }} />
  </>;
}
