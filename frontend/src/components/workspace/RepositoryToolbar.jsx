import { useState } from "react";
import {
  ArrowLeft,
  Loader2,
  RefreshCw,
  Trash2,
  Info,
} from "lucide-react";
import { Link, useParams } from "react-router-dom";

import { RepositoryStatusBadge } from "../repository/RepositoryStatusBadge";
import { Button } from "../ui/Button";
import { ConfirmDialog } from "../ui/ConfirmDialog";
import { deleteRepository } from "../../features/repositories/repositoriesApi";
import { useRepositoryStatus } from "../../hooks/useRepositoryStatus";

export function RepositoryToolbar({ onDeleteNavigate }) {
  const { repositoryId } = useParams();
  const { repository, status, state, refresh } =
    useRepositoryStatus(repositoryId);
  const [busyAction, setBusyAction] = useState(null);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const job = status?.job;
  const jobActive =
    job?.status === "queued" || job?.status === "running";
  const isReady = status?.repository_status === "ready";

  async function handleReindex() {
    setBusyAction("reindex");
    try {
      await startIndexing(repositoryId, { force: true });
      refresh();
    } finally {
      setBusyAction(null);
    }
  }

  async function handleDelete() {
    setBusyAction("delete");
    try {
      await deleteRepository(repositoryId);
      if (onDeleteNavigate) {
        onDeleteNavigate();
      } else {
        window.location.href = "/dashboard";
      }
    } finally {
      setBusyAction(null);
    }
  }

  return (
    <>
      <header className="border-b border-line bg-background/90 backdrop-blur px-4 py-3 shrink-0 z-10 flex items-center justify-between">
        <div className="flex items-center gap-3 min-w-0">
          <Link
            to="/dashboard"
            className="inline-flex items-center gap-1.5 rounded-control text-[12px] font-medium text-muted transition-colors hover:text-ink"
          >
            <ArrowLeft size={13} aria-hidden="true" />
            Repositories
          </Link>
          <h1 className="text-[15px] font-semibold text-ink truncate max-w-xs">
            {repository?.owner_name
              ? `${repository.owner_name}/`
              : ""}
            {repository?.repository_name}
          </h1>
        </div>
        <div className="flex items-center gap-2">
          <RepositoryStatusBadge
            status={status?.repository_status ?? repository?.status}
            errorCode={job?.error_code}
          />
          <Button
            variant="secondary"
            size="sm"
            onClick={refresh}
            disabled={state === "refreshing"}
          >
            Refresh
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={handleReindex}
            disabled={
              busyAction === "reindex" ||
              jobActive ||
              !isReady ||
              state === "loading"
            }
            title={
              jobActive
                ? "Indexing is already in progress"
                : !isReady
                  ? "Repository is not ready yet"
                  : "Queue a new indexing job"
            }
          >
            {busyAction === "reindex" ? (
              <Loader2 size={13} className="animate-spin" aria-hidden="true" />
            ) : (
              <RefreshCw size={13} aria-hidden="true" />
            )}
            Re-index
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setConfirmDelete(true)}
            disabled={busyAction === "delete"}
            className="text-muted hover:text-danger"
          >
            <Trash2 size={13} aria-hidden="true" />
          </Button>
          <Info size={13} className="text-muted shrink-0" aria-hidden="true" />
        </div>
      </header>

      <ConfirmDialog
        open={confirmDelete}
        title={`Delete ${repository?.repository_name ?? "repository"}?`}
        description="This permanently removes the local clone and the stored repository record. The public GitHub repository itself is not affected."
        confirmLabel="Delete repository"
        onCancel={() => setConfirmDelete(false)}
        onConfirm={handleDelete}
        pending={busyAction === "delete"}
      />
    </>
  );
}
