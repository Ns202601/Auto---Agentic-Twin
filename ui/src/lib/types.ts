// Mirrors the FastAPI responses in src/twinorch (service.py, domain/models.py).

export type ProjectKind = "llm_agent" | "ml_model" | "data_pipeline" | "hybrid";
export type RunStatus = "queued" | "running" | "awaiting_review" | "completed" | "rejected" | "failed";
export type NodeId = "intake" | "classify" | "assess_data" | "plan" | "review" | "scaffold" | "register";

export interface Health { status: string; version: string; provider: "anthropic" | "offline"; model: string }

export interface KindInfo { id: ProjectKind; label: string; description: string; stack: string[] }
export interface Meta {
  provider: string;
  model: string;
  kinds: KindInfo[];
  nodes: { id: NodeId; label: string }[];
  edges: { source: string; target: string; conditional: boolean }[];
}

export interface IdeaIn {
  title: string;
  problem: string;
  outcome: string;
  data_notes: string;
  constraints: string;
  kind_hint: ProjectKind | null;
}

export interface Classification {
  kind: ProjectKind;
  domain_tags: string[];
  rationale: string;
  confidence: number;
  project_name: string;
}
export interface DatasetMatch { dataset_id: string; name: string; ready: boolean; reason: string; link: string }
export interface DataAssessment {
  applicable: boolean;
  readiness: "ready" | "partial" | "blocked" | "not_applicable";
  matches: DatasetMatch[];
  gaps: string[];
  notes: string;
}
export interface Blueprint {
  summary: string;
  components: { name: string; layer: string; purpose: string }[];
  milestones: { title: string; deliverable: string; est_days: number }[];
  eval_metrics: string[];
  risks: string[];
  agent_tools: string[];
  model_candidates: string[];
}

export interface RunSummary {
  id: string;
  idea_id: string;
  title: string;
  status: RunStatus;
  kind: ProjectKind | null;
  current_node: NodeId | null;
  revision: number;
  provider: string;
  model: string;
  error: string | null;
  created_at: string;
  updated_at: string;
}

export interface RunEvent { id: number; ts: string; node: string; level: "info" | "decision" | "error"; message: string }

export interface RunDetail extends RunSummary {
  state: {
    idea?: IdeaIn;
    classification?: Classification;
    data?: DataAssessment;
    blueprint?: Blueprint;
    feedback?: string[];
    decision?: { action: string; comment: string };
    project?: { slug: string; path: string; files: string[] };
    outcome?: string;
  };
  events: RunEvent[];
  visited: string[];
  pending: string[];
}

export interface Project { slug: string; run_id: string; title: string; kind: ProjectKind; path: string; file_count: number; created_at: string }
export interface ProjectFiles extends Project { files: string[] }

export interface ReviewDecision { action: "approve" | "revise" | "reject"; comment: string }
