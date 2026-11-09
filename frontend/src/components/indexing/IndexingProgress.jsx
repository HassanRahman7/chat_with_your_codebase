import {
  AlertTriangle,
  CheckCircle2,
  Database,
  FileSearch,
  Layers,
  Loader2,
} from "lucide-react";

import {
  isPipelinePending,
  statusLabel,
  statusTone,
  stepLabel,
} from "../../features/indexing/statusLabels";
import { cn } from "../../lib/utils";

const BAR_TONE = {
  success: "bg-success",
  danger: "bg-danger",
  warning: "bg-warning",
  info: "bg-info",
  neutral: "bg-muted/40",
};

export function IndexingProgress({ status }) {
  const job = status?.job;
  const publicStatus = status?.repository_status ?? "queued";
  const errorCode = job?.error_code;
  const pendingPipeline = isPipelinePending(errorCode);
  const tone = statusTone(publicStatus, errorCode);
  const progress = clampProgress(
    publicStatus === "ready" ? 100 : Number(job?.progress ?? 0),
  );
  const active = ["queued", "cloning", "scanning", "parsing", "embedding", "storing"].includes(
    publicStatus,
  );

  return (
    <div>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted/80">
            Indexing pipeline
          </p>
          <h2 className="mt-1 text-[20px] font-semibold tracking-tight text-ink">
            {statusLabel(publicStatus, errorCode)}
          </h2>
          <p className="mt-1 text-[13px] text-muted">
            {job
              ? stepLabel(job.current_step, publicStatus)
              : "No indexing job has been created yet."}
          </p>
        </div>

        <span
          className={cn(
            "rounded-control border px-2 py-1 font-mono text-[11px]",
            tone === "success" && "border-success/25 bg-success/10 text-success",
            tone === "danger" && "border-danger/25 bg-danger/10 text-danger",
            tone === "warning" && "border-warning/25 bg-warning/10 text-warning",
            tone === "info" && "border-info/25 bg-info/10 text-info",
            tone === "neutral" && "border-line bg-white text-muted",
          )}
        >
          {progress}%
        </span>
      </div>

      <div
        className="mt-5 h-1.5 overflow-hidden rounded-full bg-line"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={progress}
        aria-label="Repository indexing progress"
      >
        <div
          className={cn(
            "h-full rounded-full transition-[width] duration-500",
            BAR_TONE[tone],
            active && "animate-pulse",
          )}
          style={{ width: `${progress}%` }}
        />
      </div>

      {job ? (
        <dl className="mt-5 grid grid-cols-3 gap-3">
          <Metric
            icon={FileSearch}
            label="Files discovered"
            value={job.files_discovered}
          />
          <Metric
            icon={Layers}
            label="Files processed"
            value={job.files_processed}
          />
          <Metric icon={Database} label="Code chunks" value={job.total_chunks} />
        </dl>
      ) : null}

      {pendingPipeline ? (
        <Callout
          tone="warning"
          icon={AlertTriangle}
          title={
            job?.error_code === "embedding_pipeline_pending"
              ? "Chunks ready"
              : "Repository cloned"
          }
        >
          {job?.error_message ||
            "Indexing is paused at a completed phase boundary."}
        </Callout>
      ) : job?.status === "failed" ? (
        <Callout tone="danger" icon={AlertTriangle} title="Indexing failed">
          {job.error_message || "The repository could not be indexed."}
          {job.error_code ? (
            <span className="mt-1 block font-mono text-[10px] opacity-75">
              {job.error_code}
            </span>
          ) : null}
        </Callout>
      ) : null}

      {status?.active_index?.is_available ? (
        <div className="mt-5 flex items-center gap-2 rounded-control border border-success/20 bg-success/[0.06] px-3 py-2 text-[12px] text-success">
          <CheckCircle2 size={14} aria-hidden="true" />
          Active index available at commit{" "}
          <span className="font-mono">
            {status.active_index.commit_sha?.slice(0, 8)}
          </span>
        </div>
      ) : null}

      {active && !job ? (
        <div className="mt-5 flex items-center gap-2 text-[12px] text-muted">
          <Loader2 size={14} className="animate-spin" aria-hidden="true" />
          Waiting for the worker to report progress.
        </div>
      ) : null}
    </div>
  );
}

function Metric({ icon: Icon, label, value }) {
  return (
    <div className="rounded-control border border-line bg-background/60 px-3 py-2">
      <dt className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-muted/80">
        <Icon size={11} aria-hidden="true" />
        {label}
      </dt>
      <dd className="mt-1 text-[16px] font-semibold tabular-nums text-ink">
        {Number(value ?? 0).toLocaleString()}
      </dd>
    </div>
  );
}

function Callout({ tone, icon: Icon, title, children }) {
  return (
    <div
      className={cn(
        "mt-5 rounded-control border px-3 py-3 text-[12px] leading-5",
        tone === "warning" && "border-warning/25 bg-warning/[0.06] text-warning",
        tone === "danger" && "border-danger/25 bg-danger/[0.06] text-danger",
      )}
      role="status"
    >
      <p className="flex items-center gap-2 font-medium">
        <Icon size={14} aria-hidden="true" />
        {title}
      </p>
      <div className="mt-1 opacity-90">{children}</div>
    </div>
  );
}

function clampProgress(value) {
  if (!Number.isFinite(value)) return 0;
  return Math.min(100, Math.max(0, Math.round(value)));
}
