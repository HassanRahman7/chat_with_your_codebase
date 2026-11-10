import { Link } from "react-router-dom";
import { ExternalLink, RefreshCw, Trash2 } from "lucide-react";

import { isActiveStatus } from "../../features/indexing/statusLabels";
import { formatDateTime, shortSha } from "../../lib/format";
import { RepositoryStatusBadge } from "./RepositoryStatusBadge";
import { Button } from "../ui/Button";

export function RepositoryTable({
  items,
  onReindex,
  onDelete,
  busyRepositoryId = null,
  busyAction = null,
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[760px] border-collapse text-left">
        <thead>
          <tr className="border-b border-line text-[10px] uppercase tracking-[0.14em] text-muted/80">
            <th className="px-4 py-2.5 font-medium">Repository</th>
            <th className="px-4 py-2.5 font-medium">Branch / commit</th>
            <th className="px-4 py-2.5 font-medium">Status</th>
            <th className="px-4 py-2.5 font-medium">Updated</th>
            <th className="px-4 py-2.5 text-right font-medium">Actions</th>
          </tr>
        </thead>
        <tbody>
          {items.map((repository) => {
            const busy = busyRepositoryId === repository.id;
            const active = isActiveStatus(repository.status);
            return (
              <tr
                key={repository.id}
                className="border-b border-line/70 align-middle last:border-0 hover:bg-black/[0.015]"
              >
                <td className="px-4 py-3">
                  <Link
                    to={`/repositories/${repository.id}`}
                    className="group block min-w-0 rounded-control focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
                  >
                    <span className="flex items-center gap-1.5 text-[13px] font-medium text-ink group-hover:text-accent">
                      {repository.owner_name ? (
                        <span className="font-normal text-muted">
                          {repository.owner_name}/
                        </span>
                      ) : null}
                      {repository.repository_name}
                      <ExternalLink
                        size={11}
                        className="opacity-0 transition-opacity group-hover:opacity-60"
                        aria-hidden="true"
                      />
                    </span>
                    <span
                      className="mt-0.5 block max-w-[280px] truncate font-mono text-[10px] text-muted/70"
                      title={repository.github_url}
                    >
                      {repository.github_url}
                    </span>
                  </Link>
                </td>
                <td className="px-4 py-3">
                  <span className="block text-[12px] text-ink">
                    {repository.default_branch || "—"}
                  </span>
                  <span className="mt-0.5 block font-mono text-[10px] text-muted/70">
                    {shortSha(repository.active_commit_sha) || "No active commit"}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <RepositoryStatusBadge status={repository.status} />
                </td>
                <td className="px-4 py-3 text-[12px] text-muted">
                  {formatDateTime(repository.updated_at)}
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center justify-end gap-1">
                    <Link to={`/repositories/${repository.id}/workspace`}>
                      <Button variant="secondary" size="sm">
                        Open
                      </Button>
                    </Link>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onReindex(repository)}
                      disabled={busy || active}
                      title={
                        active
                          ? "Indexing is already in progress"
                          : "Queue a new indexing job"
                      }
                      aria-label={`Re-index ${repository.repository_name}`}
                    >
                      <RefreshCw
                        size={13}
                        className={
                          busy && busyAction === "reindex" ? "animate-spin" : ""
                        }
                        aria-hidden="true"
                      />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onDelete(repository)}
                      disabled={busy}
                      className="text-muted hover:text-danger"
                      title="Delete repository"
                      aria-label={`Delete ${repository.repository_name}`}
                    >
                      <Trash2 size={13} aria-hidden="true" />
                    </Button>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
