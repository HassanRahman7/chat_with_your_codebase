import { cn } from "../../lib/utils";

const TONE_BY_STATE = {
  loading: { dot: "bg-muted/60 animate-pulse", label: "Checking API", tone: "neutral" },
  refreshing: { dot: "bg-info animate-pulse", label: "Checking API", tone: "info" },
  online: { dot: "bg-success", label: "API online", tone: "success" },
  degraded: { dot: "bg-warning", label: "Degraded", tone: "warning" },
  offline: { dot: "bg-danger", label: "API offline", tone: "danger" },
};

const TONE_CLASSES = {
  neutral: "border-line bg-white text-muted",
  info: "border-info/25 bg-info/10 text-info",
  success: "border-success/25 bg-success/10 text-success",
  warning: "border-warning/25 bg-warning/10 text-warning",
  danger: "border-danger/25 bg-danger/10 text-danger",
};

/** Compact, honest health indicator driven entirely by `/api/health`. */
export function StatusPill({ health, className }) {
  const visual = TONE_BY_STATE[health?.state] ?? TONE_BY_STATE.loading;

  return (
    <span
      role="status"
      aria-live="polite"
      className={cn(
        "inline-flex items-center gap-2 rounded-full border px-2.5 py-1 text-[11px] font-medium",
        TONE_CLASSES[visual.tone],
        className,
      )}
    >
      <span className={cn("size-1.5 rounded-full", visual.dot)} aria-hidden="true" />
      {visual.label}
    </span>
  );
}
