import { Button, Select } from "@fluentui/react-components";
import {
  ArrowSyncRegular,
  CheckmarkCircleRegular,
  DataBarVerticalRegular,
  DatabaseRegular,
  HistoryRegular,
  HomeRegular,
  LinkRegular,
  RulerRegular,
  TrophyRegular,
} from "@fluentui/react-icons";
import { useEffect, useRef, type ReactElement, type ReactNode } from "react";
import { viewTitles } from "../data/demoData";
import { useDemoWorkspace } from "../state/DemoWorkspaceProvider";
import type { Role, ViewName } from "../ui/types";

const navigation: Array<{ view: ViewName; label: string; icon: ReactElement }> = [
  { view: "workspace", label: "Workspace", icon: <HomeRegular /> },
  { view: "ingestion", label: "Ingestion Runs", icon: <ArrowSyncRegular /> },
  { view: "profiles", label: "Profiles", icon: <DataBarVerticalRegular /> },
  { view: "rules", label: "Rules & Evidence", icon: <RulerRegular /> },
  { view: "bronze_approval", label: "Bronze Approval", icon: <CheckmarkCircleRegular /> },
  { view: "mapping", label: "Mapping", icon: <LinkRegular /> },
  { view: "silver", label: "Silver", icon: <DatabaseRegular /> },
  { view: "gold", label: "Gold", icon: <TrophyRegular /> },
  { view: "activity", label: "Activity", icon: <HistoryRegular /> },
];

export function AppShell({ children }: { children: ReactNode }) {
  const { view, navigate, role, setRole } = useDemoWorkspace();
  const contentRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    contentRef.current?.scrollTo({ top: 0, behavior: "smooth" });
  }, [view]);
  return <div className="app-shell">
    <aside className="sidebar">
      <div className="sidebar-brand"><span className="brand-mark">AI</span><div><strong>Data Quality</strong><small>Governed Workflow</small></div></div>
      <nav className="sidebar-nav" aria-label="Main navigation">
        {navigation.map((item) => <Button
          key={item.view}
          appearance="transparent"
          icon={item.icon}
          className={view === item.view || (view === "ingestion_detail" && item.view === "ingestion") ? "active" : ""}
          onClick={() => navigate(item.view)}
        >{item.label}</Button>)}
      </nav>
      <div className="role-selector"><label htmlFor="role">Simulate role</label><Select id="role" value={role} onChange={(_, data) => setRole(data.value as Role)}>
        <option>Administrator</option><option>Operator</option>
      </Select></div>
    </aside>
    <main className="main-area">
      <header className="top-bar"><div className="breadcrumb">AI Data Quality Workspace / <strong>{viewTitles[view]}</strong></div><Select aria-label="Dataset" defaultValue="TimerApp Projects"><option>TimerApp Projects</option></Select></header>
      <div className="app-content" ref={contentRef}>{children}</div>
    </main>
  </div>;
}
