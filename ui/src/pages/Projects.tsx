import { useQuery } from "@tanstack/react-query";
import { Link, getRouteApi, useNavigate } from "@tanstack/react-router";
import { createColumnHelper } from "@tanstack/react-table";
import { useMemo } from "react";
import { KindChip } from "../components/Chips";
import { DataTable } from "../components/DataTable";
import { api, queryKeys } from "../lib/api";
import { relativeTime } from "../lib/format";
import type { Project } from "../lib/types";

const col = createColumnHelper<Project>();
const columns = [
  col.accessor("title", {
    header: "Project",
    cell: (c) => (<div><div className="cell-title">{c.getValue()}</div><div className="cell-sub">projects/{c.row.original.slug}</div></div>),
  }),
  col.accessor("kind", { header: "Kind", cell: (c) => <KindChip kind={c.getValue()} /> }),
  col.accessor("file_count", { header: "Files", cell: (c) => <span className="num">{c.getValue()}</span> }),
  col.accessor("created_at", { header: "Created", cell: (c) => <span className="muted">{relativeTime(c.getValue())}</span> }),
];

export function ProjectsPage() {
  const navigate = useNavigate();
  const projects = useQuery({ queryKey: queryKeys.projects, queryFn: api.projects });
  return (
    <>
      <header className="page-head">
        <div className="titles">
          <span className="eyebrow">Output</span>
          <h1>Projects</h1>
          <p className="muted">Starter projects written by approved runs. Each one is a normal Python project you can open and extend.</p>
        </div>
      </header>
      <section className="panel">
        <DataTable
          data={projects.data ?? []}
          columns={columns}
          initialSort={[{ id: "created_at", desc: true }]}
          onRowClick={(p) => navigate({ to: "/projects/$slug", params: { slug: p.slug }, search: { file: "README.md" } })}
          rowLabel={(p) => `Open ${p.title}`}
          empty={<div className="empty"><strong>No projects yet</strong><span>Approve a blueprint in the pipeline and its project appears here.</span><Link to="/" className="btn">Go to pipeline</Link></div>}
        />
      </section>
    </>
  );
}

const detailRoute = getRouteApi("/projects/$slug");

export function ProjectDetailPage() {
  const { slug } = detailRoute.useParams();
  const { file } = detailRoute.useSearch();
  const navigate = useNavigate();
  const project = useQuery({ queryKey: queryKeys.project(slug), queryFn: () => api.project(slug) });
  const active = file ?? "README.md";
  const content = useQuery({
    queryKey: queryKeys.file(slug, active),
    queryFn: () => api.file(slug, active),
    enabled: !!project.data,
  });

  const grouped = useMemo(() => {
    const out = new Map<string, string[]>();
    for (const f of project.data?.files ?? []) {
      const dir = f.includes("/") ? f.slice(0, f.lastIndexOf("/")) : "";
      out.set(dir, [...(out.get(dir) ?? []), f]);
    }
    return [...out.entries()].sort(([a], [b]) => a.localeCompare(b));
  }, [project.data]);

  if (project.isError) return <div className="banner bad">Project not found. <Link to="/projects">Back to projects</Link></div>;
  const p = project.data;

  return (
    <>
      <header className="page-head">
        <div className="titles">
          <nav className="crumbs" aria-label="Breadcrumb"><Link to="/projects">Projects</Link><span>/</span><span className="mono">{slug}</span></nav>
          <h1>{p?.title ?? slug}</h1>
          {p && <div className="tags" style={{ alignItems: "center" }}><KindChip kind={p.kind} /><span className="muted mono" style={{ fontSize: 12 }}>{p.path}</span></div>}
        </div>
        {p && <div className="actions"><Link to="/runs/$runId" params={{ runId: p.run_id }} className="btn">View run</Link></div>}
      </header>
      <section className="panel browser">
        <nav className="files" aria-label="Files">
          {grouped.map(([dir, files]) => (
            <div key={dir || "root"}>
              {dir && <div className="dir">{dir}/</div>}
              {files.map((f) => (
                <button key={f} aria-current={f === active} title={f}
                        style={{ paddingLeft: dir ? 26 : 14 }}
                        onClick={() => navigate({ to: "/projects/$slug", params: { slug }, search: { file: f }, replace: true })}>
                  {f.slice(f.lastIndexOf("/") + 1)}
                </button>
              ))}
            </div>
          ))}
        </nav>
        <div className="viewer">
          <div className="viewer-head">{active}</div>
          {content.isLoading ? <div className="panel-body"><div className="skeleton" /></div> : content.isError ? (
            <div className="panel-body"><div className="banner bad">Could not load {active}.</div></div>
          ) : (
            <pre className="code" tabIndex={0} aria-label={`Contents of ${active}`}>
              {(content.data ?? "").split("\n").map((line, i) => <span key={i}>{line || " "}</span>)}
            </pre>
          )}
        </div>
      </section>
    </>
  );
}
