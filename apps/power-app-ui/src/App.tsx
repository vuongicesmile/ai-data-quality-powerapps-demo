import { Spinner } from "@fluentui/react-components";
import { lazy, Suspense } from "react";
import { AppShell } from "./components/AppShell";
import { AiAssistant } from "./components/AiAssistant";
import { OverlayHost, ToastHost } from "./components/Overlays";
import { DemoWorkspaceProvider, useDemoWorkspace } from "./state/DemoWorkspaceProvider";

const WorkspaceView = lazy(() => import("./views/WorkspaceView").then((module) => ({ default: module.WorkspaceView })));
const IngestionRunsView = lazy(() => import("./views/IngestionViews").then((module) => ({ default: module.IngestionRunsView })));
const IngestionDetailView = lazy(() => import("./views/IngestionViews").then((module) => ({ default: module.IngestionDetailView })));
const BronzeView = lazy(() => import("./views/BronzeProfilesViews").then((module) => ({ default: module.BronzeView })));
const ProfilesView = lazy(() => import("./views/BronzeProfilesViews").then((module) => ({ default: module.ProfilesView })));
const RulesView = lazy(() => import("./views/GovernanceViews").then((module) => ({ default: module.RulesView })));
const BronzeApprovalView = lazy(() => import("./views/GovernanceViews").then((module) => ({ default: module.BronzeApprovalView })));
const MappingView = lazy(() => import("./views/GovernanceViews").then((module) => ({ default: module.MappingView })));
const SilverView = lazy(() => import("./views/PublishingViews").then((module) => ({ default: module.SilverView })));
const GoldView = lazy(() => import("./views/PublishingViews").then((module) => ({ default: module.GoldView })));
const ActivityView = lazy(() => import("./views/ActivityView").then((module) => ({ default: module.ActivityView })));

function CurrentView() {
  const { view } = useDemoWorkspace();
  switch (view) {
    case "workspace": return <WorkspaceView />;
    case "ingestion": return <IngestionRunsView />;
    case "ingestion_detail": return <IngestionDetailView />;
    case "bronze": return <BronzeView />;
    case "profiles": return <ProfilesView />;
    case "rules": return <RulesView />;
    case "bronze_approval": return <BronzeApprovalView />;
    case "mapping": return <MappingView />;
    case "silver": return <SilverView />;
    case "gold": return <GoldView />;
    case "activity": return <ActivityView />;
  }
}

export function App() {
  return <DemoWorkspaceProvider>
    <AppShell><Suspense fallback={<div className="view-loading"><Spinner label="Loading workspace" /></div>}><CurrentView /></Suspense></AppShell>
    <OverlayHost />
    <ToastHost />
    <AiAssistant />
  </DemoWorkspaceProvider>;
}
