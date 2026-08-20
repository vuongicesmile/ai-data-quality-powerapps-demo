import { activityEvents } from "../data/demoData";
import { PageHeader, SectionCard, Timeline, WorkflowNav } from "../components/Common";

export function ActivityView() {
  return <>
    <PageHeader title="Activity History" subtitle="Audit log of all workflow events" back={{ label: "Back to Gold", view: "gold" }} />
    <SectionCard><Timeline events={activityEvents} /></SectionCard>
    <WorkflowNav back={{ label: "Back to Workspace", view: "workspace" }} />
  </>;
}
