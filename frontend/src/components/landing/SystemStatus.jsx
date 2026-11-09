import {
  CheckCircle2,
  CircleDashed,
  RefreshCw,
  XCircle,
} from "lucide-react";

import { API_BASE_URL } from "../../lib/apiClient";
import { Button } from "../ui/Button";
import { Panel } from "../ui/Panel";

const DEPENDENCY_LABELS = {
  postgresql: "PostgreSQL",
  chromadb: "ChromaDB",
};

const SUMMARY = {
  loading: { label: "Checking dependencies…", tone: "text-muted" },
  refreshing: { label: "Re-checking dependencies…", tone: "text-info" },
  online: { label: "All systems operational", tone: "text-success" },
  degraded: { label: "Degraded — a dependency is unavailable", tone: "text-warning" },
  offline: { label: "Backend unreachable", tone: "text-danger" },
};

function DependencyRow({ name, value }) {
  const visual =
    value === "ok"
      ? { icon: CheckCircle2, label: "Operational", tone: "text-success" }
      : value === "unavailable"
        ? { icon: XCircle, label: "Unavailable", tone: "text-danger" }
        : { icon: CircleDashed, label: "Not checked", tone: "text-muted" };
  const Icon = visual.icon;

  return (
    <div className="flex items-center justify-between gap-4 py-2.5">
      <span className="text-[13px] font-medium text-ink">
        {DEPENDENCY_LABELS[name] ?? name}
      </span>
      <span className={`inline-flex items-center gap-1.5 text-[12px] ${visual.tone}`}>
        <Icon size={13} aria-hidden="true" />
        {visual.label}
      </span>
    </div>
  );
}

export function SystemStatus({ health }) {
  const { state, data, error, checkedAt, refresh } = health;
  const dependencies = data?.dependencies ?? {};
  const busy = state === "loading" || state === "refreshing";
  const summary = SUMMARY[state] ?? SUMMARY.loading;
  const knownNames = Object.keys(DEPENDENCY_LABELS);

  return (
    <section id="status" className="scroll-mt-20">
      <div className="mx-auto grid w-full max-w-6xl gap-6 px-4 py-16 sm:px-6 lg:grid-cols-[0.9fr_1.1fr] lg:items-start lg:py-20">
        <div>
          <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-accent">
            System status
          </p>
          <h2 className="mt-3 text-[28px] font-semibold tracking-tight text-ink sm:text-[32px]">
            Live, not simulated
          </h2>
          <p className="mt-3 max-w-md text-[15px] leading-7 text-muted">
            This panel reads the backend health endpoint. Dependency rows show
            real connectivity checks, and failures are reported as they are.
          </p>
          <p className="mt-4 font-mono text-[11px] text-muted">{API_BASE_URL}</p>
        </div>

        <Panel className="p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div role="status" aria-live="polite">
              <p className={`text-[14px] font-semibold ${summary.tone}`}>
                {summary.label}
              </p>
              {data ? (
                <p className="mt-1 font-mono text-[10px] uppercase tracking-wider text-muted/80">
                  {data.service} · v{data.version}
                </p>
              ) : null}
            </div>
            <Button
              variant="secondary"
              size="sm"
              onClick={refresh}
              disabled={busy}
              aria-label="Refresh system status"
            >
              <RefreshCw
                size={13}
                className={busy ? "animate-spin" : undefined}
                aria-hidden="true"
              />
              Refresh
            </Button>
          </div>

          <div className="mt-4 divide-y divide-line border-y border-line">
            {knownNames.map((name) => (
              <DependencyRow key={name} name={name} value={dependencies[name]} />
            ))}
          </div>

          <div className="mt-4 min-h-10">
            {state === "offline" ? (
              <p className="text-[12px] leading-5 text-danger">
                Could not reach the API. Start the backend with{" "}
                <code className="font-mono text-[11px]">
                  uvicorn app.main:app --reload
                </code>{" "}
                and refresh.
              </p>
            ) : (
              <p className="text-[11px] text-muted">
                {checkedAt
                  ? `Last checked ${checkedAt.toLocaleTimeString()}`
                  : "Waiting for the first health check."}
              </p>
            )}
            {error?.message && state === "offline" ? (
              <p className="mt-1 font-mono text-[10px] text-muted/80">
                {error.message}
              </p>
            ) : null}
          </div>
        </Panel>
      </div>
    </section>
  );
}
