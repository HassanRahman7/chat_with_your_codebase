import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  AlertTriangle,
  FolderPlus,
  Loader2,
  RefreshCw,
  X,
} from "lucide-react";

import { AppShell } from "../components/layout/AppShell";
import { DashboardSidebar } from "../components/layout/DashboardSidebar";
import { RepositoryTable } from "../components/repository/RepositoryTable";
import { RepositoryUrlForm } from "../components/repository/RepositoryUrlForm";
import { Button } from "../components/ui/Button";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { Panel } from "../components/ui/Panel";
import { createRepository, deleteRepository, startIndexing } from "../features/repositories/repositoriesApi";
import { useRepositories } from "../hooks/useRepositories";
import { useSystemHealth } from "../hooks/useSystemHealth";

const PAGE_SIZE = 10;

export function DashboardPage() {
  const navigate = useNavigate();
  const health = useSystemHealth();
  const [offset, setOffset] = useState(0);
  const { items, pagination, state, error, refresh } = useRepositories({
    limit: PAGE_SIZE,
    offset,
  });
  const [showAddForm, setShowAddForm] = useState(false);
  const [busy, setBusy] = useState(null);
  const [actionError, setActionError] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);

  async function handleCreate(url) {
    try {
      const result = await createRepository(url);
      navigate(`/repositories/${result.repository.id}`);
    } catch (submissionError) {
      const existingId = submissionError?.details?.repository_id;
      if (
        submissionError?.code === "repository_already_exists" &&
        existingId
      ) {
        navigate(`/repositories/${existingId}`);
        return;
      }
      throw submissionError;
    }
  }

  async function handleReindex(repository) {
    setBusy({ id: repository.id, action: "reindex" });
    setActionError(null);
    try {
      await startIndexing(repository.id, { force: true });
      refresh();
    } catch (requestError) {
      setActionError(requestError);
    } finally {
      setBusy(null);
    }
  }

  async function handleDelete(repository) {
    setBusy({ id: repository.id, action: "delete" });
    setActionError(null);
    try {
      await deleteRepository(repository.id);
      setDeleteTarget(null);
      refresh();
    } catch (requestError) {
      setActionError(requestError);
    } finally {
      setBusy(null);
    }
  }

  return (
    <AppShell
      health={health}
      sidebar={<DashboardSidebar health={health} />}
    >
      <div className="py-2">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-[28px] font-semibold tracking-tight text-ink">
              Repositories
            </h1>
            <p className="mt-1 text-[13px] text-muted">
              Your indexed codebases
              {pagination.total > 0
                ? ` · ${pagination.total.toLocaleString()} registered`
                : ""}
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={refresh}
              disabled={state === "loading" || state === "refreshing"}
            >
              <RefreshCw
                size={13}
                className={
                  state === "refreshing" ? "animate-spin" : ""
                }
                aria-hidden="true"
              />
              Refresh
            </Button>
            <Button
              size="sm"
              onClick={() => setShowAddForm((value) => !value)}
              aria-expanded={showAddForm}
            >
              {showAddForm ? (
                <X size={14} aria-hidden="true" />
              ) : (
                <FolderPlus size={14} aria-hidden="true" />
              )}
              Add repository
            </Button>
          </div>
        </div>

        {showAddForm ? (
          <Panel className="mt-5 border-primary/20 bg-white p-4 shadow-sm">
            <h2 className="text-[13px] font-semibold text-ink">
              Add a public repository
            </h2>
            <p className="mb-3 mt-1 text-[12px] text-muted">
              Paste a GitHub URL. The backend validates the URL and queues the
              repository for cloning and indexing.
            </p>
            <RepositoryUrlForm onSubmit={handleCreate} autoFocus />
          </Panel>
        ) : null}

        {actionError ? (
          <div
            role="alert"
            className="mt-5 flex items-start gap-2 rounded-control border border-danger/25 bg-danger/[0.06] px-3 py-3 text-[12px] leading-5 text-danger"
          >
            <AlertTriangle size={14} className="mt-0.5 shrink-0" aria-hidden="true" />
            <span>{actionError.message || "That action could not be completed."}</span>
          </div>
        ) : null}

        <div className="mt-5">
          {state === "loading" || state === "refreshing" ? (
            <Panel className="flex items-center justify-center gap-2 px-6 py-16 text-[13px] text-muted">
              <Loader2 size={15} className="animate-spin" aria-hidden="true" />
              Loading repositories…
            </Panel>
          ) : state === "error" ? (
            <Panel className="px-6 py-14 text-center">
              <AlertTriangle size={20} className="mx-auto text-danger" aria-hidden="true" />
              <h2 className="mt-3 text-[16px] font-semibold text-ink">
                Repositories unavailable
              </h2>
              <p className="mx-auto mt-1 max-w-md text-[13px] text-muted">
                {error?.message || "We could not load registered repositories."}
              </p>
              <Button variant="secondary" className="mt-5" onClick={refresh}>
                Try again
              </Button>
            </Panel>
          ) : items.length === 0 ? (
            <Panel className="px-6 py-14 text-center">
              <h2 className="text-[16px] font-semibold text-ink">
                No repositories yet
              </h2>
              <p className="mx-auto mt-1 max-w-md text-[13px] text-muted">
                Connect a public GitHub repository to start exploring its code
                with AI.
              </p>
              {!showAddForm ? (
                <Button className="mt-5" onClick={() => setShowAddForm(true)}>
                  Add your first repository
                </Button>
              ) : null}
            </Panel>
          ) : (
            <Panel className="overflow-hidden">
              <RepositoryTable
                items={items}
                onReindex={handleReindex}
                onDelete={setDeleteTarget}
                busyRepositoryId={busy?.id ?? null}
                busyAction={busy?.action ?? null}
              />
              <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line px-4 py-3">
                <p className="font-mono text-[10px] uppercase tracking-[0.12em] text-muted/80">
                  Showing {items.length} of {pagination.total.toLocaleString()}
                </p>
                <div className="flex items-center gap-2">
                  <Button
                    variant="secondary"
                    size="sm"
                    disabled={offset === 0}
                    onClick={() => setOffset((value) => Math.max(0, value - PAGE_SIZE))}
                  >
                    Previous
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    disabled={!pagination.has_more}
                    onClick={() => setOffset((value) => value + PAGE_SIZE)}
                  >
                    Next
                  </Button>
                </div>
              </div>
            </Panel>
          )}
        </div>
      </div>

      <ConfirmDialog
        open={Boolean(deleteTarget)}
        title={`Delete ${deleteTarget?.repository_name ?? "repository"}?`}
        description="This permanently removes the local clone and the stored repository record. The public GitHub repository itself is not affected."
        confirmLabel="Delete repository"
        onCancel={() => setDeleteTarget(null)}
        onConfirm={() => handleDelete(deleteTarget)}
        pending={busy?.action === "delete"}
      />
    </AppShell>
  );
}
