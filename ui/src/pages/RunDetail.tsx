import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, getRouteApi } from "@tanstack/react-router";
import { useState } from "react";
import { KindChip, ReadinessChip, StatusChip } from "../components/Chips";
import { IconCheck, IconEdit, IconX } from "../components/Icons";
import { StageRail } from "../components/StageRail";
import { api, queryKeys } from "../lib/api";
import { ACTIVE, clockTime, humanize, relativeTime } from "../lib/format";
import type { Blueprint, Classification, DataAssessment, ReviewDecision, RunDetail } from "../lib/types";

const route = getRouteApi("/runs/$runId");

export function RunDetailPage() {
  const { runId } = route.useParams();
  const run = useQuery({
    queryKey: queryKeys.run(runId),
    queryFn: () => api.run(runId),
    refetchInterval: (q) => (q.state.data && ACTIVE.includes(q.state.data.status) ? 1000 : false),
  });

  if (run.isLoading) return <div className="panel panel-body"><div className="skeleton" /><div className="skeleton" /></div>;
  if (run.isError || !run.data) return <div className="banner bad">Run not found. <Link to="/">Back to pipeline</Link></div>;
  const r = run.data;
  const { classification, data, blueprint, project, idea } = r.state;

  return (
    <>
      <header className="page-head">
        <div className="titles">
          <nav className="crumbs" aria-label="Breadcrumb"><Link to="/">Pipeline</Link><span>/</span><span className="mono">{r.id}</span></nav>
          <h1>{r.title}</h1>
          <div className="tags" style={{ alignItems: "center" }}>
            <StatusChip status={r.status} />
            <KindChip kind={r.kind} />
            <span className="muted" style={{ fontSize: 12.5 }}>Planner {r.provider === "anthropic" ? r.model : "offline rules"} · updated {relativeTime(r.updated_at)}</span>
          </div>
        </div>
        {project && (
          <div className="actions">
            <Link to="/projects/$slug" params={{ slug: project.slug }} search={{ file: "README.md" }} className="btn primary">Open project</Link>
          </div>
        )}
      </header>

      <section className="panel" style={{ padding: "0 16px" }} aria-label="Stages"><StageRail run={r} /></section>

      {r.status === "failed" && r.error && <div className="banner bad" role="alert"><strong>Run failed.</strong> {r.error}</div>}

      <div className="split">
        <div className="stack">
          {r.status === "awaiting_review" && blueprint && <ReviewPanel run={r} />}
          {blueprint ? <BlueprintPanel bp={blueprint} revision={r.revision} /> : ACTIVE.includes(r.status) && (
            <div className="panel panel-body"><span className="muted">Planning… the blueprint appears here when ready.</span><div className="skeleton" /></div>
          )}
          {data && data.applicable && <DataPanel data={data} />}
          {classification && <ClassificationPanel c={classification} />}
          {idea && (
            <section className="panel">
              <div className="panel-head"><h2>Original idea</h2></div>
              <dl className="panel-body kv">
                <dt>Problem</dt><dd>{idea.problem}</dd>
                <dt>Outcome</dt><dd>{idea.outcome}</dd>
                {idea.data_notes && (<><dt>Data</dt><dd>{idea.data_notes}</dd></>)}
                {idea.constraints && (<><dt>Constraints</dt><dd>{idea.constraints}</dd></>)}
              </dl>
            </section>
          )}
        </div>

        <aside className="panel" aria-label="Timeline">
          <div className="panel-head"><h2>Timeline</h2><span className="muted num" style={{ fontSize: 12 }}>{r.events.length} events</span></div>
          <div className="timeline">
            {r.events.map((e) => (
              <div key={e.id} className={`event ${e.level}`}>
                <time dateTime={e.ts}>{clockTime(e.ts)}</time>
                <span className="node">{humanize(e.node)}</span>
                <span className="msg">{e.message}</span>
              </div>
            ))}
          </div>
        </aside>
      </div>
    </>
  );
}

function ReviewPanel({ run }: { run: RunDetail }) {
  const qc = useQueryClient();
  const [mode, setMode] = useState<"idle" | "revise" | "reject">("idle");
  const [comment, setComment] = useState("");
  const review = useMutation({
    mutationFn: (d: ReviewDecision) => api.review(run.id, d),
    onSuccess: (updated) => {
      qc.setQueryData(queryKeys.run(run.id), updated);
      qc.invalidateQueries({ queryKey: queryKeys.runs });
      setMode("idle");
      setComment("");
    },
  });

  return (
    <section className="panel" style={{ borderColor: "var(--warn)" }} aria-label="Review">
      <div className="panel-head" style={{ background: "var(--warn-soft)" }}>
        <h2 style={{ color: "var(--warn)" }}>Your review: blueprint v{run.revision}</h2>
        {(run.state.feedback?.length ?? 0) > 0 && <span className="muted" style={{ fontSize: 12 }}>{run.state.feedback!.length} earlier comment(s) addressed</span>}
      </div>
      <div className="panel-body">
        <p>Check the plan below. Approving writes a starter project to <code>projects/</code>. Requesting changes sends your comment back to the planner.</p>
        {mode !== "idle" && (
          <div className="field">
            <label htmlFor="review-comment">{mode === "revise" ? "What should change?" : "Reason for rejecting (optional)"}</label>
            <textarea id="review-comment" className="input" rows={3} value={comment} onChange={(e) => setComment(e.target.value)}
                      placeholder={mode === "revise" ? "e.g. Use the Scania APS dataset first and add a drift monitor." : ""} autoFocus />
          </div>
        )}
        {review.isError && <div className="banner bad" role="alert">{(review.error as Error).message}</div>}
        <div className="review-actions">
          {mode === "idle" ? (
            <>
              <button className="btn primary" disabled={review.isPending} onClick={() => review.mutate({ action: "approve", comment: "" })}>
                <IconCheck />{review.isPending ? "Approving…" : "Approve and scaffold"}
              </button>
              <button className="btn" onClick={() => setMode("revise")}><IconEdit />Request changes</button>
              <button className="btn danger" onClick={() => setMode("reject")}><IconX />Reject</button>
            </>
          ) : (
            <>
              <button className={`btn ${mode === "reject" ? "danger" : "primary"}`}
                      disabled={review.isPending || (mode === "revise" && !comment.trim())}
                      onClick={() => review.mutate({ action: mode, comment })}>
                {mode === "revise" ? "Send to planner" : "Reject idea"}
              </button>
              <button className="btn" onClick={() => setMode("idle")}>Cancel</button>
            </>
          )}
        </div>
      </div>
    </section>
  );
}

function BlueprintPanel({ bp, revision }: { bp: Blueprint; revision: number }) {
  const totalDays = bp.milestones.reduce((s, m) => s + m.est_days, 0);
  const layers = [...new Set(bp.components.map((c) => c.layer))];
  return (
    <section className="panel" aria-label="Blueprint">
      <div className="panel-head"><h2>Blueprint</h2><span className="tag">v{revision}</span></div>
      <div className="panel-body">
        <p>{bp.summary}</p>
      </div>
      <div className="table-wrap" style={{ borderTop: "1px solid var(--line)" }}>
        <table className="grid">
          <thead><tr><th>Component</th><th>Layer</th><th>Purpose</th></tr></thead>
          <tbody>
            {layers.flatMap((layer) => bp.components.filter((c) => c.layer === layer)).map((c) => (
              <tr key={c.name} style={{ cursor: "default" }}><td className="cell-title">{c.name}</td><td><span className="tag">{c.layer}</span></td><td>{c.purpose}</td></tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="panel-body" style={{ borderTop: "1px solid var(--line)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
          <h3>Milestones</h3><span className="muted num" style={{ fontSize: 12 }}>{totalDays} working days</span>
        </div>
        <div className="milestones">
          {bp.milestones.map((m, i) => (
            <div key={i} className="milestone">
              <span className="idx">{String(i + 1).padStart(2, "0")}</span>
              <div><div style={{ fontWeight: 500 }}>{m.title}</div><div className="muted" style={{ fontSize: 12.5 }}>{m.deliverable}</div></div>
              <span className="days">{m.est_days} d</span>
            </div>
          ))}
        </div>
      </div>
      <div className="panel-body" style={{ borderTop: "1px solid var(--line)", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", display: "grid" }}>
        <div><h3 style={{ marginBottom: 6 }}>Success metrics</h3><ul className="list">{bp.eval_metrics.map((m) => <li key={m}>{m}</li>)}</ul></div>
        <div><h3 style={{ marginBottom: 6 }}>Risks</h3><ul className="list">{bp.risks.map((m) => <li key={m}>{m}</li>)}</ul></div>
        {bp.agent_tools.length > 0 && <div><h3 style={{ marginBottom: 6 }}>Agent tools</h3><div className="tags">{bp.agent_tools.map((t) => <span key={t} className="tag">{t}</span>)}</div></div>}
        {bp.model_candidates.length > 0 && <div><h3 style={{ marginBottom: 6 }}>Models to compare</h3><ul className="list">{bp.model_candidates.map((t) => <li key={t}>{t}</li>)}</ul></div>}
      </div>
    </section>
  );
}

function DataPanel({ data }: { data: DataAssessment }) {
  return (
    <section className="panel" aria-label="Data assessment">
      <div className="panel-head"><h2>Data assessment</h2><ReadinessChip readiness={data.readiness} /></div>
      <div className="panel-body">
        <p className="muted">{data.notes}</p>
        {data.matches.length > 0 && (
          <div>
            {data.matches.map((m) => (
              <div key={m.dataset_id} className="dataset">
                <span className="mono muted">{m.dataset_id}</span>
                <span style={{ fontWeight: 500 }}>{m.link ? <a href={m.link} target="_blank" rel="noreferrer">{m.name}</a> : m.name}</span>
                <span className={`chip ${m.ready ? "ok" : "warn"}`}>{m.ready ? "Ready" : "Check licence"}</span>
                <span className="reason">{m.reason}</span>
              </div>
            ))}
          </div>
        )}
        {data.gaps.length > 0 && (
          <div className="field">
            <h3>Fields not publicly available</h3>
            <div className="tags">{data.gaps.map((g) => <span key={g} className="tag">{g}</span>)}</div>
          </div>
        )}
      </div>
    </section>
  );
}

function ClassificationPanel({ c }: { c: Classification }) {
  const pct = Math.round(c.confidence * 100);
  return (
    <section className="panel" aria-label="Classification">
      <div className="panel-head"><h2>Classification</h2><KindChip kind={c.kind} /></div>
      <dl className="panel-body kv">
        <dt>Confidence</dt>
        <dd className="confidence"><span className="meter"><span style={{ width: `${pct}%` }} /></span><span className="num">{pct}%</span></dd>
        <dt>Domains</dt><dd><div className="tags">{c.domain_tags.map((t) => <span key={t} className="tag">{humanize(t)}</span>)}</div></dd>
        <dt>Rationale</dt><dd>{c.rationale}</dd>
        <dt>Project name</dt><dd className="mono">{c.project_name}</dd>
      </dl>
    </section>
  );
}
