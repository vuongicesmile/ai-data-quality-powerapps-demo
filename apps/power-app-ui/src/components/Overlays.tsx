import {
  Button,
  Dialog,
  DialogActions,
  DialogBody,
  DialogContent,
  DialogSurface,
  DialogTitle,
  Drawer,
  DrawerBody,
  DrawerHeader,
  DrawerHeaderTitle,
  Field,
  Input,
  ProgressBar,
  Select,
  Switch,
  Textarea,
  Toast,
  Toaster,
  ToastTitle,
  useId,
  useToastController,
} from "@fluentui/react-components";
import { DismissRegular } from "@fluentui/react-icons";
import { useEffect, useMemo, useState } from "react";
import { profileRows } from "../data/demoData";
import { useDemoWorkspace } from "../state/DemoWorkspaceProvider";

const runSteps = [
  ["Creating ingestion run", 15], ["Reading TimerApp lists", 35], ["Capturing Bronze snapshot", 55],
  ["Computing row hashes", 75], ["Profiling columns", 90], ["Generating rule suggestions", 100],
] as const;

function StartRunContent() {
  const { closeDialog, navigate, notify } = useDemoWorkspace();
  const [running, setRunning] = useState(false);
  const [step, setStep] = useState(0);
  useEffect(() => {
    if (!running) return;
    const timer = window.setInterval(() => setStep((current) => {
      if (current < runSteps.length - 1) return current + 1;
      window.clearInterval(timer);
      window.setTimeout(() => { closeDialog(); navigate("ingestion_detail"); notify("Data Quality Run completed successfully"); }, 450);
      return current;
    }), 650);
    return () => window.clearInterval(timer);
  }, [running, closeDialog, navigate, notify]);
  return <>
    <DialogTitle>Start Data Quality Run</DialogTitle>
    <DialogContent>{running ? <div className="run-progress"><strong>{runSteps[step][0]}...</strong><ProgressBar value={runSteps[step][1] / 100} /><span>{runSteps[step][1]}%</span></div> : <div className="dialog-stack">
      <div><small>Dataset</small><strong>TimerApp Projects</strong></div><div><small>Sources</small><span>4 approved TimerApp lists</span></div>
      <Switch label="Force recapture" />
    </div>}</DialogContent>
    {!running && <DialogActions><Button onClick={closeDialog}>Cancel</Button><Button appearance="primary" onClick={() => setRunning(true)}>Start Run</Button></DialogActions>}
  </>;
}

function DialogContents() {
  const { dialog, dialogPayload, closeDialog, approveLayer, reviewRule, approveRecipe, notify } = useDemoWorkspace();
  const [aiStage, setAiStage] = useState<"prompt" | "loading" | "preview">("prompt");
  const profile = useMemo(() => profileRows.find((row) => row.column === dialogPayload.profileColumn), [dialogPayload.profileColumn]);

  if (dialog === "run") return <StartRunContent />;
  if (dialog === "approve") return <><DialogTitle>Approve {dialogPayload.layer} Layer?</DialogTitle><DialogContent><p>This approval unlocks downstream governed capabilities.</p><Field label="Comment (optional)"><Textarea resize="vertical" /></Field></DialogContent><DialogActions><Button onClick={closeDialog}>Cancel</Button><Button appearance="primary" onClick={() => { if (dialogPayload.layer) approveLayer(dialogPayload.layer); closeDialog(); }}>Confirm Approval</Button></DialogActions></>;
  if (dialog === "reject-rule") return <><DialogTitle>Reject Rule</DialogTitle><DialogContent><Field label="Rejection reason" required><Textarea resize="vertical" placeholder="Provide a reason for rejection..." /></Field></DialogContent><DialogActions><Button onClick={closeDialog}>Cancel</Button><Button appearance="primary" onClick={() => { if (dialogPayload.ruleId) reviewRule(dialogPayload.ruleId, "REJECTED"); closeDialog(); }}>Confirm Rejection</Button></DialogActions></>;
  if (dialog === "edit-rule") return <><DialogTitle>Edit Rule</DialogTitle><DialogContent><div className="form-grid"><Field label="Rule name"><Input defaultValue="Email must be valid format" /></Field><Field label="Column"><Select defaultValue="Email"><option>Email</option></Select></Field><Field label="Rule type"><Select defaultValue="REGEX"><option>REGEX</option><option>NOT_NULL</option><option>RANGE</option></Select></Field><Field label="Severity"><Select defaultValue="High"><option>High</option><option>Medium</option><option>Low</option></Select></Field></div><Field label="Parameters"><Input defaultValue="^[a-zA-Z0-9._%+-]+@.+$" /></Field><Field label="Description"><Textarea defaultValue="Column semantic type and samples indicate email addresses." /></Field></DialogContent><DialogActions><Button onClick={closeDialog}>Cancel</Button><Button appearance="primary" onClick={() => { closeDialog(); notify("Rule saved"); }}>Save Rule</Button></DialogActions></>;
  if (dialog === "profile" && profile) return <><DialogTitle>Column Profile: {profile.column}</DialogTitle><DialogContent><div className="profile-dialog-grid"><div><small>Null Count</small><strong>124</strong></div><div><small>Unique Count</small><strong>19,358</strong></div><div><small>Detected Type</small><strong>{profile.detectedType}</strong></div><div><small>Semantic Type</small><strong>{profile.semanticType}</strong></div><div><small>Quality Score</small><strong>{profile.quality}%</strong></div></div><h3>Top Values</h3><div className="top-values"><span>Samsung <strong>34%</strong></span><span>LG <strong>19%</strong></span><span>Intel <strong>12%</strong></span></div></DialogContent><DialogActions><Button onClick={closeDialog}>Close</Button></DialogActions></>;
  if (dialog === "ai-recipe") return <><DialogTitle>✨ Generate Gold Recipe with AI</DialogTitle><DialogContent>{aiStage === "prompt" && <Field label="Describe your requirements"><Textarea resize="vertical" placeholder="Create customer-level portfolio summary with project count and total budget." /></Field>}{aiStage === "loading" && <div className="run-progress"><ProgressBar /><span>AI is analyzing Silver schema...</span></div>}{aiStage === "preview" && <div className="recipe-preview"><h3>AI Generated Recipe Preview</h3><p>Review the generated recipe. Explicit approval is required before execution.</p><div><strong>Recipe Name:</strong> Customer Portfolio Summary<br /><strong>Sources:</strong> Silver_Projects<br /><strong>Dimensions:</strong> customer_name<br /><strong>Measures:</strong> COUNT(project_name), SUM(budget)</div></div>}</DialogContent><DialogActions><Button onClick={closeDialog}>{aiStage === "preview" ? "Discard" : "Cancel"}</Button>{aiStage === "prompt" && <Button appearance="primary" onClick={() => { setAiStage("loading"); window.setTimeout(() => setAiStage("preview"), 900); }}>Generate</Button>}{aiStage === "preview" && <Button appearance="primary" onClick={() => { approveRecipe(); closeDialog(); }}>Approve Recipe</Button>}</DialogActions></>;
  return null;
}

export function OverlayHost() {
  const { dialog, closeDialog, drawer, closeDrawer } = useDemoWorkspace();
  return <>
    <Dialog open={dialog !== null} onOpenChange={(_, data) => !data.open && closeDialog()}><DialogSurface><DialogBody><DialogContents /></DialogBody></DialogSurface></Dialog>
    <Drawer type="overlay" position="end" open={drawer !== null} onOpenChange={(_, data) => !data.open && closeDrawer()}>
      <DrawerHeader><DrawerHeaderTitle action={<Button appearance="subtle" aria-label="Close" icon={<DismissRegular />} onClick={closeDrawer} />}>{drawer === "evidence" ? "Rule Evidence" : "Row Payload"}</DrawerHeaderTitle></DrawerHeader>
      <DrawerBody>{drawer === "evidence" ? <EvidenceDrawer /> : <PayloadDrawer />}</DrawerBody>
    </Drawer>
  </>;
}

function EvidenceDrawer() {
  return <div className="drawer-stack"><div className="drawer-kpi"><small>Violation Count</small><strong>76</strong><p>Sensitive raw data is masked.</p></div><h3>Sample Evidence</h3>{[["128", "test***@mail"], ["441", "abc***com"]].map(([row, value]) => <article className="evidence-card" key={row}><small>Source Row: {row}</small><code>{value}</code><strong>INVALID_EMAIL_FORMAT</strong></article>)}</div>;
}

function PayloadDrawer() {
  return <div className="drawer-stack"><small>Raw SharePoint Item JSON</small><pre>{JSON.stringify({ Id: 128, Title: "Cloud Migration", Customer: "Samsung", Budget: 1200000, Email: "test***@mail", StartDate: "2024-05-10", Status: "Active" }, null, 2)}</pre></div>;
}

export function ToastHost() {
  const { notice } = useDemoWorkspace();
  const toasterId = useId("data-quality-toaster");
  const { dispatchToast } = useToastController(toasterId);
  useEffect(() => {
    if (notice) dispatchToast(<Toast><ToastTitle>{notice}</ToastTitle></Toast>, { intent: "success", timeout: 3000 });
  }, [notice, dispatchToast]);
  return <Toaster toasterId={toasterId} position="bottom-end" />;
}
