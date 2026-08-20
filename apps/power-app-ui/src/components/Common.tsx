import {
  Badge,
  Button,
  Card,
  ProgressBar,
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableHeaderCell,
  TableRow,
  Text,
} from "@fluentui/react-components";
import { ArrowLeftRegular, ArrowRightRegular } from "@fluentui/react-icons";
import type { ReactNode } from "react";
import type { TimelineEvent, ViewName } from "../ui/types";
import { useDemoWorkspace } from "../state/DemoWorkspaceProvider";

export function PageHeader({ title, subtitle, back, actions }: { title: string; subtitle: string; back?: { label: string; view: ViewName }; actions?: ReactNode }) {
  const { navigate } = useDemoWorkspace();
  return <header className="page-header">
    <div>
      {back && <Button appearance="transparent" className="back-link" icon={<ArrowLeftRegular />} onClick={() => navigate(back.view)}>{back.label}</Button>}
      <h1>{title}</h1>
      <p>{subtitle}</p>
    </div>
    {actions && <div className="page-actions">{actions}</div>}
  </header>;
}

export function StatusBadge({ value }: { value: string }) {
  const normalized = value.toLowerCase().replaceAll("_", "-");
  const color = /approved|completed|captured|healthy|passed|valid/.test(normalized)
    ? "success"
    : /failed|rejected|invalid/.test(normalized) ? "danger" : /waiting|pending|review/.test(normalized) ? "warning" : "brand";
  return <Badge appearance="tint" color={color} className="status-badge"><span className="status-dot" />{value}</Badge>;
}

export function KpiGrid({ items }: { items: Array<{ label: string; value: ReactNode }> }) {
  return <div className="kpi-grid">{items.map((item) => <Card className="kpi-card" key={item.label}>
    <Text className="kpi-label">{item.label}</Text><div className="kpi-value">{item.value}</div>
  </Card>)}</div>;
}

export function SectionCard({ title, actions, children, className = "" }: { title?: string; actions?: ReactNode; children: ReactNode; className?: string }) {
  return <Card className={`section-card ${className}`}>
    {title && <div className="section-card-header"><h2>{title}</h2>{actions}</div>}
    <div className="section-card-body">{children}</div>
  </Card>;
}

export function DataTable({ headers, rows, onRowClick }: { headers: string[]; rows: ReactNode[][]; onRowClick?: (index: number) => void }) {
  return <div className="table-scroll"><Table size="small" aria-label={headers.join(", ")}>
    <TableHeader><TableRow>{headers.map((header) => <TableHeaderCell key={header}>{header}</TableHeaderCell>)}</TableRow></TableHeader>
    <TableBody>{rows.map((row, rowIndex) => <TableRow key={rowIndex} onClick={onRowClick ? () => onRowClick(rowIndex) : undefined} className={onRowClick ? "clickable-row" : ""}>
      {row.map((cell, cellIndex) => <TableCell key={cellIndex}>{cell}</TableCell>)}
    </TableRow>)}</TableBody>
  </Table></div>;
}

const steps = ["Capture Bronze", "Profile", "Generate Rules", "Review Rules", "Mapping", "Silver", "Gold"];
export function GovernanceStepper({ current = 3 }: { current?: number }) {
  return <div className="governance-stepper" aria-label="Data quality workflow">
    {steps.map((step, index) => <div className={`governance-step ${index < current ? "complete" : index === current ? "current" : ""}`} key={step}>
      <span className="step-circle">{index < current ? "✓" : index + 1}</span><strong>{step}</strong>
      {index < steps.length - 1 && <span className="step-line" />}
    </div>)}
  </div>;
}

export function Timeline({ events }: { events: TimelineEvent[] }) {
  return <div className="timeline">{events.map((event, index) => <article className="timeline-event" key={`${event.time}-${event.title}`}>
    <span className={`timeline-dot ${event.tone || "brand"}`} />
    <time>{event.time}</time><strong>{event.title}</strong><p>{event.description}</p>
    {index < events.length - 1 && <span className="timeline-line" />}
  </article>)}</div>;
}

export function QualityBar({ label, score }: { label: string; score: number }) {
  return <div className="quality-row"><div><span>{label}</span><strong>{score}%</strong></div><ProgressBar value={score / 100} color={score < 85 ? "error" : score < 90 ? "warning" : "success"} /></div>;
}

export function WorkflowNav({ back, next }: { back?: { label: string; view: ViewName }; next?: { label: string; view: ViewName } }) {
  const { navigate } = useDemoWorkspace();
  return <nav className="workflow-nav" aria-label="Workflow navigation">
    {back ? <Button icon={<ArrowLeftRegular />} onClick={() => navigate(back.view)}>{back.label}</Button> : <span />}
    {next && <Button appearance="primary" iconPosition="after" icon={<ArrowRightRegular />} onClick={() => navigate(next.view)}>{next.label}</Button>}
  </nav>;
}
