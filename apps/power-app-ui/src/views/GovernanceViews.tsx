import { Badge, Button, Tab, TabList } from "@fluentui/react-components";
import { useState } from "react";
import { mappingRows } from "../data/demoData";
import { useDemoWorkspace } from "../state/DemoWorkspaceProvider";
import type { RuleFilter } from "../ui/types";
import { DataTable, KpiGrid, PageHeader, SectionCard, StatusBadge, WorkflowNav } from "../components/Common";

export function RulesView() {
  const { rules, reviewRule, openDialog, openDrawer } = useDemoWorkspace();
  const [filter, setFilter] = useState<RuleFilter>("pending");
  const visibleRules = filter === "all" ? rules : rules.filter((rule) => rule.status.toLowerCase() === filter);
  const count = (status: string) => rules.filter((rule) => rule.status === status).length;
  return <>
    <PageHeader title="Rules & Evidence" subtitle="AI-generated data quality rules" back={{ label: "Back to Profiles", view: "profiles" }} />
    <SectionCard>
      <TabList selectedValue={filter} onTabSelect={(_, data) => setFilter(data.value as RuleFilter)}>
        <Tab value="pending">Pending Review ({count("PENDING")})</Tab><Tab value="approved">Approved ({count("APPROVED")})</Tab><Tab value="rejected">Rejected ({count("REJECTED")})</Tab><Tab value="all">All Rules</Tab>
      </TabList>
    </SectionCard>
    <div className="rule-list">{visibleRules.map((rule) => <SectionCard key={rule.id} className="rule-card" title={rule.name} actions={<StatusBadge value={rule.status} />}>
      <div className="rule-metadata"><Badge appearance="outline">{rule.column}</Badge><Badge appearance="outline">{rule.type}</Badge><Badge appearance="tint" color={rule.severity === "High" ? "danger" : "warning"}>{rule.severity}</Badge><span>AI confidence: <strong>{rule.confidence}%</strong></span></div>
      <p>{rule.description}</p>
      <div className="rule-footer"><span><strong className="danger-text">{rule.violations}</strong> violations detected</span><div>
        <Button appearance="transparent" onClick={() => openDrawer("evidence")}>View Evidence</Button>
        <Button onClick={() => openDialog("edit-rule", { ruleId: rule.id })}>Edit</Button>
        <Button onClick={() => openDialog("reject-rule", { ruleId: rule.id })}>Reject</Button>
        <Button appearance="primary" onClick={() => reviewRule(rule.id, "APPROVED")}>Approve</Button>
      </div></div>
    </SectionCard>)}</div>
    {!visibleRules.length && <SectionCard><div className="empty-state">No rules in this status.</div></SectionCard>}
    <WorkflowNav back={{ label: "Back to Profiles", view: "profiles" }} next={{ label: "Next Step: Approve Bronze", view: "bronze_approval" }} />
  </>;
}

export function BronzeApprovalView() {
  const { bronzeApproved, openDialog, rules, notify } = useDemoWorkspace();
  const pending = rules.filter((rule) => rule.status === "PENDING").length;
  const checklist = [
    ["Snapshot Complete", "4 immutable assets captured"],
    ["Profiles Complete", "28 columns profiled"],
    ["Rules Reviewed", pending ? `${pending} rules still pending review` : "All suggested rules reviewed"],
    ["Evidence Masked", "Sensitive values are protected"],
  ];
  return <>
    <PageHeader title="Bronze Approval" subtitle="Governance checkpoint for raw data layer" back={{ label: "Back to Rules", view: "rules" }} actions={<StatusBadge value={bronzeApproved ? "APPROVED" : "WAITING_REVIEW"} />} />
    {bronzeApproved && <div className="success-banner">✓ Bronze layer approved. Downstream mapping and Silver processing are unlocked.</div>}
    <KpiGrid items={[
      { label: "Assets", value: "4" }, { label: "Rows", value: "19,482" }, { label: "Columns Profiled", value: "28" }, { label: "Quality Score", value: "91%" },
    ]} />
    <SectionCard title="Approval Checklist"><div className="checklist">{checklist.map(([title, detail], index) => <div key={title}><span className={index === 2 && pending ? "warning-check" : "done-check"}>{index === 2 && pending ? "!" : "✓"}</span><div><strong>{title}</strong><small>{detail}</small></div></div>)}</div></SectionCard>
    {!bronzeApproved && <div className="approval-actions"><Button onClick={() => notify("Bronze rejection recorded")}>Reject Bronze</Button><Button appearance="primary" onClick={() => openDialog("approve", { layer: "Bronze" })}>Approve Bronze</Button></div>}
    <WorkflowNav back={{ label: "Back to Rules", view: "rules" }} next={{ label: "Next Step: Configure Mapping", view: "mapping" }} />
  </>;
}

export function MappingView() {
  const { mappingApproved, approveMapping } = useDemoWorkspace();
  return <>
    <PageHeader title="Schema Mapping" subtitle="Map source columns to canonical schema" back={{ label: "Back to Bronze Approval", view: "bronze_approval" }} actions={<StatusBadge value={mappingApproved ? "APPROVED" : "DRAFT"} />} />
    <SectionCard title="Column Mappings" actions={<div className="action-group"><Button>Edit Mapping</Button><Button appearance="primary" onClick={approveMapping}>Approve Mapping</Button></div>}>
      <div className="mapping-workbench">
        <div className="mapping-column"><h3>Source · SharePoint</h3>{mappingRows.map((row) => <div className="mapping-item" key={row[0]}><strong>{row[0]}</strong><code>{row[2]}</code></div>)}</div>
        <div className="mapping-arrows">{mappingRows.map((row) => <span key={row[0]}>→</span>)}</div>
        <div className="mapping-column"><h3>Target · dq_silverrow</h3>{mappingRows.map((row) => <div className="mapping-item" key={row[1]}><strong>{row[1]}</strong><small>{row[3]}</small></div>)}</div>
      </div>
    </SectionCard>
    <WorkflowNav back={{ label: "Back to Bronze Approval", view: "bronze_approval" }} next={{ label: "Next Step: View Silver Layer", view: "silver" }} />
  </>;
}
