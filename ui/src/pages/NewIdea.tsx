import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "@tanstack/react-router";
import { type FormEvent, useState } from "react";
import { ApiError, api, queryKeys } from "../lib/api";
import type { IdeaIn, ProjectKind } from "../lib/types";

const EXAMPLE: IdeaIn = {
  title: "DPF blockage early warning",
  problem:
    "Trucks on city duty cycles hit forced DPF regenerations and derates. We only find out when the lamp comes on, and the truck is off the road for a day.",
  outcome: "Predict DPF blockage five days ahead so the workshop can schedule a cleaning during planned downtime.",
  data_notes: "Telematics export with exhaust temperature and regeneration events for 40 trucks (not yet shared).",
  constraints: "Must run on a laptop; no customer data leaves the depot.",
  kind_hint: null,
};

const EMPTY: IdeaIn = { title: "", problem: "", outcome: "", data_notes: "", constraints: "", kind_hint: null };

export function NewIdeaPage() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const meta = useQuery({ queryKey: queryKeys.meta, queryFn: api.meta, staleTime: Infinity });
  const [idea, setIdea] = useState<IdeaIn>(EMPTY);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  const submit = useMutation({
    mutationFn: api.submitIdea,
    onSuccess: (run) => {
      qc.invalidateQueries({ queryKey: queryKeys.runs });
      navigate({ to: "/runs/$runId", params: { runId: run.id } });
    },
    onError: (e) => setFieldErrors(e instanceof ApiError ? e.fields : {}),
  });

  const set = <K extends keyof IdeaIn>(k: K, v: IdeaIn[K]) => setIdea((s) => ({ ...s, [k]: v }));
  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    setFieldErrors({});
    submit.mutate(idea);
  };

  const field = (key: keyof IdeaIn, label: string, hint: string, opts: { area?: boolean; required?: boolean; rows?: number } = {}) => {
    const id = `idea-${key}`;
    const err = fieldErrors[key];
    const common = {
      id,
      className: "input",
      value: (idea[key] as string) ?? "",
      "aria-invalid": err ? true : undefined,
      "aria-describedby": `${id}-hint`,
      required: opts.required,
      onChange: (e: { target: { value: string } }) => set(key, e.target.value as never),
    };
    return (
      <div className="field">
        <label htmlFor={id}>{label}{!opts.required && <span className="muted"> (optional)</span>}</label>
        {opts.area ? <textarea {...common} rows={opts.rows ?? 4} /> : <input {...common} />}
        <span className="hint" id={`${id}-hint`}>{hint}</span>
        {err && <span className="error">{err}</span>}
      </div>
    );
  };

  const kinds: { id: ProjectKind | null; label: string; description: string }[] = [
    { id: null, label: "Decide for me", description: "The classifier picks the kind from your description." },
    ...(meta.data?.kinds.map((k) => ({ id: k.id, label: k.label, description: k.description })) ?? []),
  ];

  return (
    <>
      <header className="page-head">
        <div className="titles">
          <nav className="crumbs" aria-label="Breadcrumb"><Link to="/">Pipeline</Link><span>/</span><span>New idea</span></nav>
          <h1>New idea</h1>
          <p className="muted">Write it the way you would explain it to a colleague at the depot. Specific beats polished.</p>
        </div>
        <div className="actions">
          <button className="btn" type="button" onClick={() => setIdea(EXAMPLE)}>Fill with an example</button>
        </div>
      </header>

      <div className="split">
        <form className="panel" onSubmit={onSubmit} noValidate={false}>
          <div className="panel-body form">
            {submit.isError && !Object.keys(fieldErrors).length && (
              <div className="banner bad" role="alert">{(submit.error as Error).message}</div>
            )}
            {field("title", "Title", "A short name, e.g. 'Turbo failure early warning'.", { required: true })}
            {field("problem", "Problem", "What goes wrong today, who feels it, how often.", { area: true, required: true })}
            {field("outcome", "Desired outcome", "What good looks like. Put a number on it if you can.", { area: true, required: true, rows: 3 })}
            {field("data_notes", "Data you have", "Telematics exports, service records, manuals, open datasets.", { area: true, rows: 3 })}
            {field("constraints", "Constraints", "Budget, hardware, privacy, deadlines.", { area: true, rows: 2 })}

            <fieldset className="field" style={{ border: 0, padding: 0, margin: 0 }}>
              <legend style={{ fontWeight: 500, fontSize: 13, marginBottom: 6 }}>Project kind</legend>
              <div className="kind-grid">
                {kinds.map((k) => (
                  <button type="button" key={k.id ?? "auto"} className="kind-option" aria-pressed={idea.kind_hint === k.id}
                          onClick={() => set("kind_hint", k.id)}>
                    <strong style={{ fontWeight: 500 }}>{k.label}</strong>
                    <small>{k.description}</small>
                  </button>
                ))}
              </div>
            </fieldset>

            <div className="form-foot">
              <Link to="/" className="btn">Cancel</Link>
              <button className="btn primary" type="submit" disabled={submit.isPending}>
                {submit.isPending ? "Submitting…" : "Start pipeline"}
              </button>
            </div>
          </div>
        </form>

        <aside className="panel">
          <div className="panel-head"><h2>What happens next</h2></div>
          <div className="panel-body">
            <ol className="list" style={{ gap: 10 }}>
              <li><strong>Classify.</strong> <span className="muted">Agent, ML model, data pipeline or hybrid, plus the vehicle domains involved.</span></li>
              <li><strong>Assess data.</strong> <span className="muted">Checked against the open datasets and field availability in this repository.</span></li>
              <li><strong>Plan.</strong> <span className="muted">A blueprint with components, milestones, metrics and risks.</span></li>
              <li><strong>Your review.</strong> <span className="muted">The run pauses. Approve, request changes, or reject.</span></li>
              <li><strong>Scaffold.</strong> <span className="muted">A starter project is written to <code>projects/</code>.</span></li>
            </ol>
            <div className="banner warn" style={{ fontSize: 12.5 }}>
              Planner: {meta.data ? (meta.data.provider === "anthropic" ? meta.data.model : "offline rules (set ANTHROPIC_API_KEY to use Claude)") : "…"}
            </div>
          </div>
        </aside>
      </div>
    </>
  );
}
