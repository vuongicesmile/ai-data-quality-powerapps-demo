import { createContext, useContext, useMemo, useState, type ReactNode } from "react";
import { initialRules } from "../data/demoData";
import type { DemoRule, DialogName, DrawerName, Layer, Role, ViewName } from "../ui/types";

interface DialogPayload {
  layer?: Layer;
  ruleId?: string;
  profileColumn?: string;
}

interface DemoWorkspaceState {
  view: ViewName;
  navigate: (view: ViewName) => void;
  role: Role;
  setRole: (role: Role) => void;
  rules: DemoRule[];
  reviewRule: (ruleId: string, status: DemoRule["status"]) => void;
  bronzeApproved: boolean;
  mappingApproved: boolean;
  silverApproved: boolean;
  goldApproved: boolean;
  goldRan: boolean;
  recipeApproved: boolean;
  approveLayer: (layer: Layer) => void;
  approveMapping: () => void;
  approveRecipe: () => void;
  runGold: () => void;
  selectedAsset: string | null;
  setSelectedAsset: (asset: string | null) => void;
  dialog: DialogName;
  dialogPayload: DialogPayload;
  openDialog: (dialog: Exclude<DialogName, null>, payload?: DialogPayload) => void;
  closeDialog: () => void;
  drawer: DrawerName;
  openDrawer: (drawer: Exclude<DrawerName, null>) => void;
  closeDrawer: () => void;
  notice: string;
  notify: (message: string) => void;
}

const DemoWorkspaceContext = createContext<DemoWorkspaceState | null>(null);

export function DemoWorkspaceProvider({ children }: { children: ReactNode }) {
  const [view, setView] = useState<ViewName>("workspace");
  const [role, setRoleState] = useState<Role>("Administrator");
  const [rules, setRules] = useState(initialRules);
  const [bronzeApproved, setBronzeApproved] = useState(false);
  const [mappingApproved, setMappingApproved] = useState(false);
  const [silverApproved, setSilverApproved] = useState(false);
  const [goldApproved, setGoldApproved] = useState(false);
  const [goldRan, setGoldRan] = useState(false);
  const [recipeApproved, setRecipeApproved] = useState(false);
  const [selectedAsset, setSelectedAsset] = useState<string | null>(null);
  const [dialog, setDialog] = useState<DialogName>(null);
  const [dialogPayload, setDialogPayload] = useState<DialogPayload>({});
  const [drawer, setDrawer] = useState<DrawerName>(null);
  const [notice, setNotice] = useState("");

  function navigate(next: ViewName) {
    setView(next);
  }

  function notify(message: string) {
    setNotice("");
    window.setTimeout(() => setNotice(message), 0);
  }

  function setRole(next: Role) {
    setRoleState(next);
    notify(`Role switched to ${next}`);
  }

  function reviewRule(ruleId: string, status: DemoRule["status"]) {
    setRules((current) => current.map((rule) => rule.id === ruleId ? { ...rule, status } : rule));
    notify(status === "APPROVED" ? "Rule approved" : "Rule rejected");
  }

  function approveLayer(layer: Layer) {
    if (layer === "Bronze") setBronzeApproved(true);
    if (layer === "Silver") setSilverApproved(true);
    if (layer === "Gold") setGoldApproved(true);
    notify(`${layer} layer approved`);
  }

  function openDialog(next: Exclude<DialogName, null>, payload: DialogPayload = {}) {
    setDialogPayload(payload);
    setDialog(next);
  }

  const value = useMemo<DemoWorkspaceState>(() => ({
    view, navigate, role, setRole, rules, reviewRule,
    bronzeApproved, mappingApproved, silverApproved, goldApproved, goldRan, recipeApproved,
    approveLayer,
    approveMapping: () => { setMappingApproved(true); notify("Mapping approved"); },
    approveRecipe: () => { setRecipeApproved(true); notify("Recipe approved and saved"); },
    runGold: () => { setGoldRan(true); notify("Gold recipe executed. Reconciliation passed."); },
    selectedAsset, setSelectedAsset,
    dialog, dialogPayload, openDialog,
    closeDialog: () => setDialog(null),
    drawer, openDrawer: setDrawer, closeDrawer: () => setDrawer(null),
    notice, notify,
  }), [view, role, rules, bronzeApproved, mappingApproved, silverApproved, goldApproved, goldRan, recipeApproved, selectedAsset, dialog, dialogPayload, drawer, notice]);

  return <DemoWorkspaceContext.Provider value={value}>{children}</DemoWorkspaceContext.Provider>;
}

export function useDemoWorkspace() {
  const state = useContext(DemoWorkspaceContext);
  if (!state) throw new Error("useDemoWorkspace must be used inside DemoWorkspaceProvider");
  return state;
}
