import { useQuery } from "@tanstack/react-query";
import { api, queryKeys } from "../lib/api";

const LAYERS = [
  { name: "UI", path: "ui/", what: "Submit ideas, review blueprints, browse generated projects. React + TanStack Router, Query, Table." },
  { name: "API", path: "src/twinorch/api/app.py", what: "FastAPI. Validates input, maps errors to HTTP codes, serves the built UI." },
  { name: "Service", path: "src/twinorch/service.py", what: "Use-cases: start a run, resume after review, list runs and projects. Runs execute on worker threads." },
  { name: "Orchestration", path: "src/twinorch/graph/build.py", what: "LangGraph state machine: conditional routing, human-review interrupt, revision loop." },
  { name: "Intelligence", path: "src/twinorch/llm/", what: "Claude adapter (structured JSON, refusal fallback) or the offline rules engine, behind one interface." },
  { name: "Knowledge", path: "src/twinorch/research.py", what: "Deterministic data assessment against the research dataset inventory and data dictionary." },
  { name: "Scaffold", path: "src/twinorch/scaffold/", what: "Templates per project kind; writes a runnable starter project after approval." },
  { name: "Persistence", path: "src/twinorch/store/ + checkpoints.db", what: "SQLite for ideas, runs, events, projects; LangGraph SqliteSaver for graph state." },
  { name: "Domain", path: "src/twinorch/domain/", what: "Pydantic models and the catalog of kinds, domains and dataset mappings. No I/O." },
];

type Pos = { x: number; y: number };
const W = 112, H = 40;
const POS: Record<string, Pos> = {
  __start__: { x: 34, y: 110 }, intake: { x: 140, y: 110 }, classify: { x: 290, y: 110 }, assess_data: { x: 430, y: 200 },
  plan: { x: 570, y: 110 }, review: { x: 720, y: 110 }, scaffold: { x: 870, y: 110 }, register: { x: 1010, y: 110 }, __end__: { x: 1116, y: 110 },
};
const LABEL: Record<string, string> = {
  intake: "Intake", classify: "Classify", assess_data: "Assess data", plan: "Plan", review: "Human review", scaffold: "Scaffold", register: "Register",
};

const EDGES: { s: string; t: string; d: string; label?: string; lx?: number; ly?: number }[] = [
  { s: "__start__", t: "intake", d: "M42 110 H84" },
  { s: "intake", t: "classify", d: "M196 110 H234" },
  { s: "classify", t: "assess_data", d: "M300 130 C300 190 330 200 374 200", label: "ml · pipeline · hybrid", lx: 250, ly: 178 },
  { s: "classify", t: "plan", d: "M346 110 H514", label: "agent", lx: 430, ly: 102 },
  { s: "assess_data", t: "plan", d: "M486 200 C540 200 570 180 570 130" },
  { s: "plan", t: "review", d: "M626 110 H664" },
  { s: "review", t: "plan", d: "M720 90 C720 40 570 40 570 90", label: "revise", lx: 645, ly: 46 },
  { s: "review", t: "scaffold", d: "M776 110 H814", label: "approve", lx: 795, ly: 102 },
  { s: "review", t: "__end__", d: "M720 130 C720 236 1116 236 1116 118", label: "reject", lx: 920, ly: 228 },
  { s: "scaffold", t: "register", d: "M926 110 H954" },
  { s: "register", t: "__end__", d: "M1066 110 H1108" },
];

export function ArchitecturePage() {
  const meta = useQuery({ queryKey: queryKeys.meta, queryFn: api.meta, staleTime: Infinity });
  const conditional = (s: string, t: string) => meta.data?.edges.some((e) => e.source === s && e.target === t && e.conditional) ?? false;

  return (
    <>
      <header className="page-head">
        <div className="titles">
          <span className="eyebrow">System</span>
          <h1>Architecture</h1>
          <p className="muted">How an idea moves through the orchestrator, and which layer owns each step. Outer layers depend on inner ones, never the reverse.</p>
        </div>
      </header>

      <section className="panel" aria-label="Orchestration graph">
        <div className="panel-head">
          <h2>LangGraph flow</h2>
          <span className="muted" style={{ fontSize: 12 }}>
            {meta.data ? `${meta.data.edges.length} edges from the live graph · dashed = conditional` : "Loading graph…"}
          </span>
        </div>
        <div className="panel-body" style={{ overflowX: "auto" }}>
          <svg className="graph-svg" viewBox="0 0 1150 250" role="img" aria-label="Graph: intake, classify, optional data assessment, plan, human review with revise loop, scaffold, register" style={{ minWidth: 760 }}>
            <defs>
              <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
                <path d="M0 0 L10 5 L0 10 z" fill="var(--muted)" />
              </marker>
            </defs>
            {EDGES.map((e) => (
              <g key={`${e.s}-${e.t}`}>
                <path d={e.d} fill="none" stroke="var(--line-strong)" strokeWidth="1.5"
                      strokeDasharray={conditional(e.s, e.t) ? "5 4" : undefined} markerEnd="url(#arrow)" />
                {e.label && <text className="edge-label" x={e.lx} y={e.ly} textAnchor="middle">{e.label}</text>}
              </g>
            ))}
            {Object.entries(POS).map(([id, p]) =>
              id.startsWith("__") ? (
                <g key={id}>
                  <circle cx={p.x} cy={p.y} r="8" fill={id === "__start__" ? "var(--ink)" : "var(--surface)"} stroke="var(--ink)" strokeWidth="2" />
                  <text className="edge-label" x={p.x} y={p.y + 24} textAnchor="middle">{id === "__start__" ? "start" : "end"}</text>
                </g>
              ) : (
                <g key={id}>
                  <rect x={p.x - W / 2} y={p.y - H / 2} width={W} height={H} rx="6"
                        fill={id === "review" ? "var(--warn-soft)" : "var(--surface)"}
                        stroke={id === "review" ? "var(--warn)" : "var(--line-strong)"} strokeWidth="1.5" />
                  <text x={p.x} y={p.y + 4} textAnchor="middle" style={{ fontWeight: 500 }}>{LABEL[id]}</text>
                </g>
              ),
            )}
          </svg>
        </div>
      </section>

      <section className="panel" aria-label="Layers">
        <div className="panel-head"><h2>Layers</h2><span className="muted" style={{ fontSize: 12 }}>top calls down</span></div>
        <div className="layers">
          {LAYERS.map((l, i) => (
            <div key={l.name} className="layer">
              <span className="n">{String(i + 1).padStart(2, "0")}</span>
              <strong style={{ fontWeight: 500 }}>{l.name}</strong>
              <span className="what">{l.what}</span>
              <code className="muted">{l.path}</code>
            </div>
          ))}
        </div>
      </section>

      <section className="panel" aria-label="Extending">
        <div className="panel-head"><h2>Adding a new kind of project</h2></div>
        <div className="panel-body">
          <ol className="list" style={{ gap: 8 }}>
            <li>Add the kind to <code>ProjectKind</code> and describe it in <code>domain/catalog.py</code>.</li>
            <li>Add its file templates and dependencies in <code>scaffold/templates.py</code>.</li>
            <li>If it needs data, add it to <code>KINDS_NEEDING_DATA</code> and map its domains to datasets.</li>
            <li>Add a test in <code>tests/test_orchestrator.py</code>; the scaffold test compiles every generated file.</li>
          </ol>
          {meta.data && (
            <div className="tags">{meta.data.kinds.map((k) => <span key={k.id} className="tag">{k.label}: {k.stack.join(", ")}</span>)}</div>
          )}
        </div>
      </section>
    </>
  );
}
