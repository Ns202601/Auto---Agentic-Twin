import { NODE_LABEL } from "../lib/format";
import type { NodeId, RunDetail } from "../lib/types";

const ORDER: NodeId[] = ["intake", "classify", "assess_data", "plan", "review", "scaffold", "register"];

type StageState = "done" | "current" | "waiting" | "failed" | "skipped" | "pending";

function stageState(run: RunDetail, node: NodeId): StageState {
  const visited = new Set(run.visited);
  const kind = run.kind;
  if (node === "assess_data" && kind === "llm_agent") return "skipped";
  if (run.status === "awaiting_review" && node === "review") return "waiting";
  if (run.status === "failed" && run.current_node === node) return "failed";
  if (run.status === "failed" && !visited.has(node)) {
    // the node after the last completed one is where it failed
    const last = ORDER.filter((n) => visited.has(n)).pop();
    const next = ORDER[ORDER.indexOf(last ?? "intake") + 1];
    return node === next ? "failed" : "pending";
  }
  if (run.status === "rejected" && (node === "scaffold" || node === "register")) return "skipped";
  if (visited.has(node)) return "done";
  if ((run.status === "running" || run.status === "queued") && ORDER.indexOf(node) === nextIndex(run)) return "current";
  return "pending";
}

function nextIndex(run: RunDetail): number {
  const visited = new Set(run.visited);
  let i = 0;
  ORDER.forEach((n, idx) => { if (visited.has(n)) i = idx + 1; });
  if (ORDER[i] === "assess_data" && run.kind === "llm_agent") i += 1;
  return i;
}

const STATE_TEXT: Record<StageState, string> = {
  done: "Done", current: "Running", waiting: "Waiting for you", failed: "Failed", skipped: "Skipped", pending: "—",
};

export function StageRail({ run }: { run: RunDetail }) {
  return (
    <ol className="stages" aria-label="Pipeline stages">
      {ORDER.map((node) => {
        const s = stageState(run, node);
        return (
          <li key={node} className={`stage ${s}`} style={{ listStyle: "none" }} aria-current={s === "current" || s === "waiting" ? "step" : undefined}>
            <span className="bar" />
            <span className="name">{NODE_LABEL[node]}</span>
            <span className="state">{node === "plan" && run.revision > 1 && s === "done" ? `Done · v${run.revision}` : STATE_TEXT[s]}</span>
          </li>
        );
      })}
    </ol>
  );
}
