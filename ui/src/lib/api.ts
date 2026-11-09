import type { Health, IdeaIn, Meta, Project, ProjectFiles, ReviewDecision, RunDetail, RunSummary } from "./types";

export class ApiError extends Error {
  constructor(public status: number, message: string, public fields: Record<string, string> = {}) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit, as: "json" | "text" = "json"): Promise<T> {
  const res = await fetch(path, { headers: { "Content-Type": "application/json" }, ...init });
  if (!res.ok) {
    let message = `Request failed (${res.status})`;
    const fields: Record<string, string> = {};
    try {
      const body = await res.json();
      if (typeof body.detail === "string") message = body.detail;
      if (Array.isArray(body.detail)) {
        for (const d of body.detail) fields[String(d.loc?.[d.loc.length - 1] ?? "form")] = d.msg;
        message = "Some fields need attention.";
      }
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, message, fields);
  }
  return (as === "json" ? res.json() : res.text()) as Promise<T>;
}

export const api = {
  health: () => request<Health>("/api/health"),
  meta: () => request<Meta>("/api/meta"),
  runs: () => request<RunSummary[]>("/api/runs"),
  run: (id: string) => request<RunDetail>(`/api/runs/${id}`),
  submitIdea: (idea: IdeaIn) => request<RunDetail>("/api/ideas", { method: "POST", body: JSON.stringify(idea) }),
  review: (id: string, d: ReviewDecision) =>
    request<RunDetail>(`/api/runs/${id}/review`, { method: "POST", body: JSON.stringify(d) }),
  projects: () => request<Project[]>("/api/projects"),
  project: (slug: string) => request<ProjectFiles>(`/api/projects/${slug}`),
  file: (slug: string, path: string) =>
    request<string>(`/api/projects/${slug}/file?path=${encodeURIComponent(path)}`, undefined, "text"),
};

export const queryKeys = {
  health: ["health"] as const,
  meta: ["meta"] as const,
  runs: ["runs"] as const,
  run: (id: string) => ["run", id] as const,
  projects: ["projects"] as const,
  project: (slug: string) => ["project", slug] as const,
  file: (slug: string, path: string) => ["file", slug, path] as const,
};
