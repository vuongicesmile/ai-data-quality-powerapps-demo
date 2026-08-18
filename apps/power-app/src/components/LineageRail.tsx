import type { Lineage } from "../types";

export function LineageRail({ lineage }: { lineage?: Lineage }) {
  const nodes = lineage?.nodes || [
    { id: "sharepoint", label: "SharePoint", status: "pending" },
    { id: "bronze", label: "Bronze", status: "pending" },
    { id: "profile", label: "Profile", status: "pending" },
    { id: "silver", label: "Silver", status: "pending" },
    { id: "gold", label: "Gold", status: "pending" },
  ];
  return <div className="lineage-rail" aria-label="Dataset lineage">
    {nodes.map((node, index) => <div className="lineage-stop" key={node.id}>
      <div className={`lineage-node ${node.status}`}><span>{node.status === "complete" ? "✓" : index + 1}</span></div>
      <strong>{node.label}</strong>
      <small>{node.status}</small>
      {index < nodes.length - 1 && <div className={`lineage-link ${node.status}`} aria-hidden="true" />}
    </div>)}
  </div>;
}
