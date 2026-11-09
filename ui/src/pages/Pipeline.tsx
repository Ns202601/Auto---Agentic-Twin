import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "@tanstack/react-router";
import { createColumnHelper } from "@tanstack/react-table";
import { useMemo, useState } from "react";
import { KindChip, StatusChip } from "../components/Chips";
import { DataTable } from "../components/DataTable";
import { IconPlus, IconSearch } from "../components/Icons";
import { api, queryKeys } from "../lib/api";
import { ACTIVE, NODE_LABEL, relativeTime } from "../lib/format";
import type { NodeId, RunStatus, RunSummary } from "../lib/types";

const col = createColumnHelper<RunSummary>();

const columns = [
  col.accessor("title", {
    header: "Idea",
    cell: (c) => (
      <div>
        <div className="cell-title">{c.getValue()}</div>
        <div className="cell-sub">{c.row.original.id}</div>
      </div>
    ),
  }),
  col.accessor("kind", { header: "Kind", cell: (c) => <KindChip kind={c.getValue()} /> }),
  col.accessor("status", { header: "Status", cell: (c) => <StatusChip status={c.getValue()} /> }),
  col.accessor("current_node", {
    header: "Stage",
    cell: (c) => (c.getValue() ? NODE_LABEL[c.getValue() as NodeId] ?? c.getValue() : "—"),
  }),
  col.accessor("revision", { header: "Plan ver.", cell: (c) => <span className="num">{c.getValue() ? `v${c.getValue()}` : "—"}</span> }),
  col.accessor("updated_at", {
    header: "Updated",
    cell: (c) => <span className="muted" title={c.getValue()}>{relativeTime(c.getValue())}</span>,
  }),
];

type Filter = "all" | RunStatus | "active";
const FILTERS: { id: Filter; label: string }[] = [
  { id: "all", label: "All" },
  { id: "awaiting_review", label: "Needs review" },
  { id: "active", label: "Running" },
  { id: "completed", label: "Completed" },
  { id: "rejected", label: "Rejected" },
  { id: "failed", label: "Failed" },
];

export function PipelinePage() {
  const navigate = useNavigate();
  const [filter, setFilter] = useState<Filter>("all");
  const [search, setSearch] = useState("");
  const runs = useQuery({
    queryKey: queryKeys.runs,
    queryFn: api.runs,
    refetchInterval: (q) => (q.state.data?.some((r) => ACTIVE.includes(r.status)) ? 1500 : 5000),
  });

  const data = runs.data ?? [];
  const counts = useMemo(() => ({
    total: data.length,
    review: data.filter((r) => r.status === "awaiting_review").length,
    completed: data.filter((r) => r.status === "completed").length,
    failed: data.filter((r) => r.status === "failed").length,
  }), [data]);

  const filtered = data.filter((r) =>
    filter === "all" ? true : filter === "active" ? ACTIVE.includes(r.status) : r.status === filter);

  return (
    <>
      <header className="page-head">
        <div className="titles">
          <span className="eyebrow">Idea pipeline</span>
          <h1>Pipeline</h1>
          <p className="muted">Every idea runs through the same graph: classify, check data, plan, your review, then scaffold.</p>
        </div>
        <div className="actions">
          <Link to="/ideas/new" className="btn primary"><IconPlus />New idea</Link>
        </div>
      </header>

      <section className="kpis" aria-label="Run summary">
        <button className="kpi" aria-pressed={filter === "all"} onClick={() => setFilter("all")}>
          <span className="eyebrow">Ideas</span><span className="value">{counts.total}</span>
        </button>
        <button className="kpi" aria-pressed={filter === "awaiting_review"} onClick={() => setFilter("awaiting_review")}>
          <span className="eyebrow">Needs your review</span><span className={`value ${counts.review ? "warn" : ""}`}>{counts.review}</span>
        </button>
        <button className="kpi" aria-pressed={filter === "completed"} onClick={() => setFilter("completed")}>
          <span className="eyebrow">Scaffolded</span><span className="value ok">{counts.completed}</span>
        </button>
        <button className="kpi" aria-pressed={filter === "failed"} onClick={() => setFilter("failed")}>
          <span className="eyebrow">Failed</span><span className={`value ${counts.failed ? "bad" : ""}`}>{counts.failed}</span>
        </button>
      </section>

      <section className="panel" aria-label="Runs">
        <div className="toolbar">
          <div className="segmented" role="group" aria-label="Filter by status">
            {FILTERS.map((f) => (
              <button key={f.id} aria-pressed={filter === f.id} onClick={() => setFilter(f.id)}>{f.label}</button>
            ))}
          </div>
          <label className="search">
            <IconSearch />
            <input id="run-search" placeholder="Search ideas" value={search} onChange={(e) => setSearch(e.target.value)} aria-label="Search ideas" />
          </label>
        </div>
        {runs.isLoading ? (
          <div className="panel-body">{[0, 1, 2].map((i) => <div key={i} className="skeleton" />)}</div>
        ) : runs.isError ? (
          <div className="panel-body"><div className="banner bad">Could not reach the orchestrator API. Start it with <code>python -m twinorch serve</code>.</div></div>
        ) : (
          <DataTable
            data={filtered}
            columns={columns}
            globalFilter={search}
            initialSort={[{ id: "updated_at", desc: true }]}
            onRowClick={(r) => navigate({ to: "/runs/$runId", params: { runId: r.id } })}
            rowLabel={(r) => `Open ${r.title}`}
            empty={
              data.length === 0 ? (
                <div className="empty">
                  <strong>No ideas yet</strong>
                  <span>Describe a problem from the field and the orchestrator will plan it.</span>
                  <Link to="/ideas/new" className="btn primary"><IconPlus />Submit your first idea</Link>
                </div>
              ) : undefined
            }
          />
        )}
      </section>
    </>
  );
}
