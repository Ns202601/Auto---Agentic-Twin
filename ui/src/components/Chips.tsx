import { KIND_LABEL, STATUS_LABEL } from "../lib/format";
import type { ProjectKind, RunStatus } from "../lib/types";

const STATUS_TONE: Record<RunStatus, string> = {
  queued: "run", running: "run", awaiting_review: "warn", completed: "ok", rejected: "", failed: "bad",
};

export function StatusChip({ status }: { status: RunStatus }) {
  return <span className={`chip ${STATUS_TONE[status]}`}>{STATUS_LABEL[status]}</span>;
}

export function KindChip({ kind }: { kind: ProjectKind | null }) {
  if (!kind) return <span className="muted">—</span>;
  return <span className="tag">{KIND_LABEL[kind]}</span>;
}

export function ReadinessChip({ readiness }: { readiness: string }) {
  const tone = { ready: "ok", partial: "warn", blocked: "bad", not_applicable: "" }[readiness] ?? "";
  const label = { ready: "Data ready", partial: "Data partial", blocked: "Data blocked", not_applicable: "Not needed" }[readiness] ?? readiness;
  return <span className={`chip ${tone}`}>{label}</span>;
}
