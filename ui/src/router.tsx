import type { QueryClient } from "@tanstack/react-query";
import { Link, createRootRouteWithContext, createRoute, createRouter } from "@tanstack/react-router";
import { Shell } from "./components/Shell";
import { api, queryKeys } from "./lib/api";
import { ArchitecturePage } from "./pages/Architecture";
import { NewIdeaPage } from "./pages/NewIdea";
import { PipelinePage } from "./pages/Pipeline";
import { ProjectDetailPage, ProjectsPage } from "./pages/Projects";
import { RunDetailPage } from "./pages/RunDetail";

interface RouterContext { queryClient: QueryClient }

const rootRoute = createRootRouteWithContext<RouterContext>()({
  component: Shell,
  notFoundComponent: () => (
    <div className="empty"><strong>Page not found</strong><Link to="/" className="btn">Go to pipeline</Link></div>
  ),
});

const pipelineRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  loader: ({ context }) => context.queryClient.ensureQueryData({ queryKey: queryKeys.runs, queryFn: api.runs }),
  component: PipelinePage,
});

const newIdeaRoute = createRoute({ getParentRoute: () => rootRoute, path: "/ideas/new", component: NewIdeaPage });

const runRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/runs/$runId",
  loader: ({ context, params }) =>
    context.queryClient.prefetchQuery({ queryKey: queryKeys.run(params.runId), queryFn: () => api.run(params.runId) }),
  component: RunDetailPage,
});

const projectsRoute = createRoute({ getParentRoute: () => rootRoute, path: "/projects", component: ProjectsPage });

const projectRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/projects/$slug",
  validateSearch: (search: Record<string, unknown>): { file?: string } => ({
    file: typeof search.file === "string" ? search.file : undefined,
  }),
  component: ProjectDetailPage,
});

const architectureRoute = createRoute({ getParentRoute: () => rootRoute, path: "/architecture", component: ArchitecturePage });

const routeTree = rootRoute.addChildren([pipelineRoute, newIdeaRoute, runRoute, projectsRoute, projectRoute, architectureRoute]);

export function makeRouter(queryClient: QueryClient) {
  return createRouter({ routeTree, context: { queryClient }, defaultPreload: "intent", defaultPreloadStaleTime: 0 });
}

declare module "@tanstack/react-router" {
  interface Register { router: ReturnType<typeof makeRouter> }
}
