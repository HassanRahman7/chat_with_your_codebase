import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  AlertTriangle,
  ArrowLeft,
  ExternalLink,
  GitBranch,
  GitCommitHorizontal,
  Loader2,
  RefreshCw,
  Trash2,
} from "lucide-react";

import { IndexingProgress } from "../components/indexing/IndexingProgress";
import { AppShell } from "../components/layout/AppShell";
import { DashboardSidebar } from "../components/layout/DashboardSidebar";
import { RepositoryStatusBadge } from "../components/repository/RepositoryStatusBadge";
import { Button } from "../components/ui/Button";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { Panel } from "../components/ui/Panel";
import {
  deleteRepository,
  startIndexing,
} from "../features/repositories/repositoriesApi";
import { formatDateTime, shortSha } from "../lib/format";
import { useRepositoryStatus } from "../hooks/useRepositoryStatus";
import { useSystemHealth } from "../hooks/useSystemHealth";

export function RepositoryPage() {
  const { repositoryId } = useParams();
  const navigate = useNavigate();
  const health = useSystemHealth();
  const { repository, status, state, error, refresh } =
    useRepositoryStatus(repositoryId);
  const [busyAction, setBusyAction] = useState(null);
  const [actionError, setActionError] = useState(null);
  const [confirmDelete, setConfirmDelete] = useState(false);

  async function handleReindex() {
    setBusyAction("reindex");
    setActionError(null);
    try {
      await startIndexing(repositoryId, { force: true });
      refresh();
    } catch (requestError) {
      setActionError(requestError);
    } finally {
      setBusyAction(null);
    }
  }

  async function handleDelete() {
    setBusyAction("delete");
    setActionError(null);
    try {
      await deleteRepository(repositoryId);
      navigate("/dashboard");
    } catch (requestError) {
      setActionError(requestError);
      setBusyAction(null);
    }
  }

  const job = status?.job;
  const jobActive = job?.status === "queued" || job?.status === "running";
  const notFound = error?.status === 404;

  return (
    <AppShell
      health={health}
      sidebar={<DashboardSidebar health={health} />}
    >
      {state === "loading" || state === "refreshing" ? (
        <Panel className="flex items-center justify-center gap-2 px-6 py-16 text-[13px] text-muted">
          <Loader2 size={15} className="animate-spin" aria-hidden="true" />
          Loading repository…
        </Panel>
      ) : state === "error" ? (
        <Panel className="px-6 py-14 text-center">
          <AlertTriangle
            size={20}
            className="mx-auto text-danger"
            aria-hidden="true"
          />
          <h1 className="mt-3 text-[18px] font-semibold text-ink">
            {notFound ? "Repository not found" : "Repository unavailable"}
          </h1>
          <p className="mx-auto mt-1 max-w-md text-[13px] text-muted">
            {error?.message ||
              "We could not load this repository from the API."}
          </p>
          <div className="mt-5 flex justify-center gap-2">
            {!notFound ? (
              <Button variant="secondary" onClick={refresh}>
                Try again
              </Button>
            ) : null}
            <Link to="/dashboard">
              <Button variant="primary">
                <ArrowLeft size={14} aria-hidden="true" />
                Back to repositories
              </Button>
            </Link>
          </div>
        </Panel>
      ) : (
        <div>
          <Link
            to="/dashboard"
            className="inline-flex items-center gap-1.5 rounded-control text-[12px] font-medium text-muted transition-colors hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          >
            <ArrowLeft size={13} aria-hidden="true" />
            Repositories
          </Link>

          <div className="mt-4 flex flex-wrap items-start justify-between gap-4">
            <div className="min-w-0">
              <h1 className="break-words text-[28px] font-semibold tracking-tight text-ink">
                {repository?.owner_name
                  ? `${repository.owner_name}/`
                  : ""}
                {repository?.repository_name}
              </h1>
              <a
                href={repository?.github_url}
                target="_blank"
                rel="noreferrer"
                className="mt-1.5 inline-flex max-w-full items-center gap-1.5 font-mono text-[11px] text-accent hover:underline"
              >
                <span className="truncate">{repository?.github_url}</span>
                <ExternalLink size={11} aria-hidden="true" />
              </a>
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
                <RefreshCw
                  size={13}
                  className={state === "refreshing" ? "animate-spin" : ""}
                  aria-hidden="true"
                />
                Refresh
              </Button>
              <Button
                variant="secondary"
                size="sm"
                onClick={handleReindex}
                disabled={busyAction === "reindex" || jobActive}
                title={
                  jobActive
                    ? "Indexing is already in progress"
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
                Delete
              </Button>
            </div>
          </div>

          {actionError ? (
            <div
              role="alert"
              className="mt-5 flex items-start gap-2 rounded-control border border-danger/25 bg-danger/[0.06] px-3 py-3 text-[12px] leading-5 text-danger"
            >
              <AlertTriangle size={14} className="mt-0.5 shrink-0" aria-hidden="true" />
              <span>{actionError.message || "That action could not be completed."}</span>
            </div>
          ) : null}

          <Panel className="mt-5 p-5">
            <IndexingProgress status={status} />
          </Panel>

          <Panel className="mt-4 p-5">
            <h2 className="text-[13px] font-semibold text-ink">
              Repository details
            </h2>
            <dl className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <Detail
                icon={GitBranch}
                label="Default branch"
                value={repository?.default_branch || "—"}
              />
              <Detail
                icon={GitCommitHorizontal}
                label="Active commit"
                value={
                  shortSha(status?.active_index?.commit_sha) ||
                  shortSha(repository?.active_commit_sha) ||
                  "No active index"
                }
                mono
              />
              <Detail
                label="Registered"
                value={formatDateTime(repository?.created_at)}
              />
              <Detail
                label="Last updated"
                value={formatDateTime(repository?.updated_at)}
              />
              <Detail
                label="Latest job"
                value={job ? `${job.status} · ${job.current_step || "—"}` : "—"}
              />
              <Detail
                label="Job started"
                value={formatDateTime(job?.started_at)}
              />
              <Detail
                label="Job completed"
                value={formatDateTime(job?.completed_at)}
              />
              <Detail
                label="Indexed at"
                value={formatDateTime(repository?.indexed_at)}
              />
            </dl>
          </Panel>
        </div>
      )}

      <ConfirmDialog
        open={confirmDelete}
        title={`Delete ${repository?.repository_name ?? "repository"}?`}
        description="This permanently removes the local clone and the stored repository record. The public GitHub repository itself is not affected."
        confirmLabel="Delete repository"
        onCancel={() => setConfirmDelete(false)}
        onConfirm={handleDelete}
        pending={busyAction === "delete"}
      />
    </AppShell>
  );
}

function Detail({ icon: Icon, label, value, mono = false }) {
  return (
    <div className="rounded-control border border-line bg-background/60 px-3 py-2.5">
      <dt className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-muted/80">
        {Icon ? <Icon size={11} aria-hidden="true" /> : null}
        {label}
      </dt>
      <dd
        className={`mt-1 break-words text-[12px] font-medium text-ink ${
          mono ? "font-mono" : ""
        }`}
      >
        {value}
      </dd>
    </div>
  );
}
