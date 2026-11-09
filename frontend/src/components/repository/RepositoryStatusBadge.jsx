import { cn } from "../../lib/utils";
import {
  isActiveStatus,
  statusLabel,
  statusTone,
} from "../../features/indexing/statusLabels";
import { Badge } from "../ui/Badge";

export function RepositoryStatusBadge({ status, errorCode, className }) {
  const tone = statusTone(status, errorCode);
  const active = isActiveStatus(status) && !errorCode;

  return (
    <Badge tone={tone} className={cn("gap-1.5", className)}>
      <span
        className={cn(
          "size-1.5 rounded-full",
          active && "animate-pulse",
          tone === "success" && "bg-success",
          tone === "danger" && "bg-danger",
          tone === "warning" && "bg-warning",
          tone === "info" && "bg-info",
          tone === "neutral" && "bg-muted/60",
        )}
        aria-hidden="true"
      />
      {statusLabel(status, errorCode)}
    </Badge>
  );
}
