import { useQuery } from "@tanstack/react-query";
import { Link, Outlet } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { api, queryKeys } from "../lib/api";
import { IconFolder, IconLayers, IconMark, IconPipeline, IconPlus } from "./Icons";

type Theme = "system" | "light" | "dark";

function useTheme(): [Theme, (t: Theme) => void] {
  const [theme, setTheme] = useState<Theme>(() => {
    try { return (localStorage.getItem("twin-theme") as Theme) || "system"; } catch { return "system"; }
  });
  useEffect(() => {
    const root = document.documentElement;
    if (theme === "system") root.removeAttribute("data-theme");
    else root.setAttribute("data-theme", theme);
    try { localStorage.setItem("twin-theme", theme); } catch { /* storage blocked */ }
  }, [theme]);
  return [theme, setTheme];
}

export function Shell() {
  const [theme, setTheme] = useTheme();
  const health = useQuery({ queryKey: queryKeys.health, queryFn: api.health, staleTime: 60_000 });
  const runs = useQuery({ queryKey: queryKeys.runs, queryFn: api.runs, refetchInterval: 5000 });
  const waiting = runs.data?.filter((r) => r.status === "awaiting_review").length ?? 0;

  return (
    <div className="shell">
      <aside className="rail">
        <div className="brand">
          <span className="brand-mark"><IconMark /></span>
          <span>
            <div className="brand-name">Agentic Twin</div>
            <div className="brand-sub">Orchestrator</div>
          </span>
        </div>
        <nav className="nav" aria-label="Main">
          <div className="nav-label">Work</div>
          <Link to="/" activeOptions={{ exact: true }} activeProps={{ className: "active" }}>
            <IconPipeline />Pipeline{waiting > 0 && <span className="count" aria-label={`${waiting} waiting for review`}>{waiting}</span>}
          </Link>
          <Link to="/ideas/new" activeProps={{ className: "active" }}><IconPlus />New idea</Link>
          <Link to="/projects" activeProps={{ className: "active" }}><IconFolder />Projects</Link>
          <div className="nav-label" style={{ paddingTop: 14 }}>System</div>
          <Link to="/architecture" activeProps={{ className: "active" }}><IconLayers />Architecture</Link>
        </nav>
        <div className="rail-foot">
          <div className="engine">
            <span>Planner</span>
            <b>{health.data ? (health.data.provider === "anthropic" ? health.data.model : "offline rules") : health.isError ? "API offline" : "…"}</b>
          </div>
          <div className="theme-switch" role="group" aria-label="Theme">
            {(["system", "light", "dark"] as Theme[]).map((t) => (
              <button key={t} aria-pressed={theme === t} onClick={() => setTheme(t)}>{t[0].toUpperCase() + t.slice(1)}</button>
            ))}
          </div>
        </div>
      </aside>
      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}
