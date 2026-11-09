import type { NodeId, ProjectKind, RunStatus } from "./types";

export const KIND_LABEL: Record<ProjectKind, string> = {
  llm_agent: "LLM agent",
  ml_model: "ML model",
  data_pipeline: "Data pipeline",
  hybrid: "Hybrid",
};

export const STATUS_LABEL: Record<RunStatus, string> = {
  queued: "Queued",
  running: "Running",
  awaiting_review: "Needs review",
  completed: "Completed",
  rejected: "Rejected",
  failed: "Failed",
};

export const NODE_LABEL: Record<NodeId, string> = {
  intake: "Intake",
  classify: "Classify",
  assess_data: "Assess data",
  plan: "Plan",
  review: "Review",
  scaffold: "Scaffold",
  register: "Register",
};

export const ACTIVE: RunStatus[] = ["queued", "running"];

const rtf = new Intl.RelativeTimeFormat("en", { numeric: "auto" });
export function relativeTime(iso: string): string {
  const secs = Math.round((new Date(iso).getTime() - Date.now()) / 1000);
  const abs = Math.abs(secs);
  if (abs < 45) return "just now";
  if (abs < 3600) return rtf.format(Math.round(secs / 60), "minute");
  if (abs < 86400) return rtf.format(Math.round(secs / 3600), "hour");
  return rtf.format(Math.round(secs / 86400), "day");
}

export function clockTime(iso: string): string {
  return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23" });
}

export function humanize(s: string): string {
  return s.replace(/_/g, " ");
}
