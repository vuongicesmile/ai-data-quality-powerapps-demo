import { Badge, Button, Tab, TabList } from "@fluentui/react-components";
import { BotSparkleRegular } from "@fluentui/react-icons";
import { useState } from "react";
import { silverAccepted } from "../data/demoData";
import { useDemoWorkspace } from "../state/DemoWorkspaceProvider";
import { DataTable, KpiGrid, PageHeader, SectionCard, StatusBadge, WorkflowNav } from "../components/Common";

export function SilverView() {
  const { silverApproved, openDialog } = useDemoWorkspace();
  const [tab, setTab] = useState<"accepted" | "rejected">("accepted");
  return <>
    <PageHeader title="Silver Layer" subtitle="Normalized, validated, governed data" back={{ label: "Back to Mapping", view: "mapping" }} actions={<StatusBadge value={silverApproved ? "APPROVED" : "WAITING_APPROVAL"} />} />
    <KpiGrid items={[
      { label: "Input Bronze Rows", value: "19,482" }, { label: "Accepted", value: "19,221" }, { label: "Rejected", value: <span className="danger-text">261</span> }, { label: "Acceptance Rate", value: "98.66%" },
    ]} />
    <SectionCard actions={<Button appearance="primary" onClick={() => openDialog("approve", { layer: "Silver" })}>Approve Silver</Button>}>
      <TabList selectedValue={tab} onTabSelect={(_, data) => setTab(data.value as "accepted" | "rejected")}>
        <Tab value="accepted">Accepted (19,221)</Tab><Tab value="rejected">Rejected (261)</Tab>
      </TabList>
      <div className="tab-panel">{tab === "accepted" ? <DataTable
        headers={["project_name", "customer_name", "start_date", "budget", "source_asset", "validation_status"]}
        rows={silverAccepted.map((row) => [...row.slice(0, 5), <StatusBadge value={row[5]} />])}
      /> : <DataTable headers={["Source Row", "Reason", "Rule", "Evidence"]} rows={[
        ["128", "Invalid email format", "rule-email", <Button appearance="transparent">View Evidence</Button>],
        ["441", "Budget below zero", "rule-budget", <Button appearance="transparent">View Evidence</Button>],
      ]} />}</div>
    </SectionCard>
    <WorkflowNav back={{ label: "Back to Mapping", view: "mapping" }} next={{ label: "Next Step: Gold Recipes", view: "gold" }} />
  </>;
}

export function GoldView() {
  const { recipeApproved, goldRan, goldApproved, approveRecipe, runGold, openDialog } = useDemoWorkspace();
  const [selectedRecipe, setSelectedRecipe] = useState("Customer Portfolio Summary");
  return <>
    <PageHeader title="Gold Recipes" subtitle="Business-level aggregations and summaries" back={{ label: "Back to Silver", view: "silver" }} actions={<Button appearance="primary" icon={<BotSparkleRegular />} onClick={() => openDialog("ai-recipe")}>Generate Recipe with AI</Button>} />
    <div className="gold-grid">
      <SectionCard title="Recipes"><div className="recipe-list">
        {["Customer Portfolio Summary", "Active Project Overview", "Budget by Status"].map((recipe, index) => <button className={selectedRecipe === recipe ? "selected" : ""} onClick={() => setSelectedRecipe(recipe)} key={recipe}><div><strong>{recipe}</strong><small>Version {index + 1} · Silver_Projects</small></div><StatusBadge value={index === 0 && recipeApproved ? "APPROVED" : index === 0 ? "DRAFT" : "APPROVED"} /></button>)}
      </div></SectionCard>
      <SectionCard title={`Recipe Detail: ${selectedRecipe}`} actions={<StatusBadge value={recipeApproved ? "APPROVED" : "DRAFT"} />}>
        <div className="recipe-detail"><div><span>Source</span><strong>Silver_Projects</strong></div><div><span>Target</span><strong>Gold_CustomerPortfolio</strong></div></div>
        <h3>Dimensions</h3><div className="tag-row"><Badge appearance="tint">customer_name</Badge></div>
        <h3>Measures</h3><div className="tag-row"><Badge appearance="tint">COUNT(project_name)</Badge><Badge appearance="tint">SUM(budget)</Badge><Badge appearance="tint">AVG(project_duration)</Badge></div>
        <div className="action-group recipe-actions"><Button>Edit Recipe</Button><Button onClick={approveRecipe}>Approve Recipe</Button><Button appearance="primary" disabled={!recipeApproved} onClick={runGold}>Run Recipe</Button></div>
      </SectionCard>
    </div>
    <SectionCard title="Gold Results: Customer Portfolio Summary" actions={<Badge appearance="tint" color={goldRan ? "success" : "warning"}>{goldRan ? "PASSED" : "NOT RUN"}</Badge>}>
      <DataTable headers={["Customer", "Projects", "Total Budget", "Average Duration"]} rows={[["Samsung", "34", "4.2B", "148 days"], ["LG", "19", "2.1B", "113 days"], ["Intel", "12", "1.4B", "176 days"]]} />
    </SectionCard>
    <SectionCard title="Reconciliation"><KpiGrid items={[
      { label: "Source Silver Rows", value: "19,221" }, { label: "Included Rows", value: "19,221" }, { label: "Excluded Rows", value: "0" }, { label: "Result Groups", value: "3" },
    ]} /><div className="reconciliation"><strong>{goldRan ? "✓ Reconciliation Status: PASSED" : "Run the recipe to reconcile results"}</strong><Button appearance="primary" disabled={!goldRan || goldApproved} onClick={() => openDialog("approve", { layer: "Gold" })}>{goldApproved ? "Gold Approved" : "Approve Gold"}</Button></div></SectionCard>
    <WorkflowNav back={{ label: "Back to Silver", view: "silver" }} next={{ label: "Finish: View Activity", view: "activity" }} />
  </>;
}
