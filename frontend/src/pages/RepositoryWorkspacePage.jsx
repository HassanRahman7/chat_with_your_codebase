import { useCallback, useState } from "react";
import {
  ArrowLeft,
  AlertTriangle,
  GitBranch,
  GitCommitHorizontal,
  Loader2,
  RefreshCw,
  Trash2,
} from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { AppShell } from "../components/layout/AppShell";
import { DashboardSidebar } from "../components/layout/DashboardSidebar";
import { RepositoryStatusBadge } from "../components/repository/RepositoryStatusBadge";
import { FileExplorer } from "../components/repository/FileExplorer";
import { CodeViewer } from "../components/code/CodeViewer";
import { ChatWindow } from "../components/chat/ChatWindow";
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
import { WorkspaceProvider } from "../context/WorkspaceContext";

export function RepositoryWorkspacePage() {
  const { repositoryId } = useParams();
  const navigate = useNavigate();
  const health = useSystemHealth();
  const { repository, status, state, error, refresh } =
    useRepositoryStatus(repositoryId);
  const [busyAction, setBusyAction] = useState(null);
  const [actionError, setActionError] = useState(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [conversationId, setConversationId] = useState(null);
  const [selectedFile, setSelectedFile] = useState(null);

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
  const isReady = status?.repository_status === "ready";

  return (
    <AppShell health={health} sidebar={<DashboardSidebar health={health} />}>
      <WorkspaceProvider>
        {state === "loading" || state === "refreshing" ? (
          <Panel className="flex h-full items-center justify-center gap-2 px-6 py-16 text-[13px] text-muted">
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
          <div className="flex h-full flex-col">
            <div className="border-b border-line bg-background/90 backdrop-blur px-4 py-3 flex items-center justify-between shrink-0">
              <div className="flex items-center gap-3 min-w-0">
                <Link
                  to="/dashboard"
                  className="inline-flex items-center gap-1.5 rounded-control text-[12px] font-medium text-muted transition-colors hover:text-ink"
                >
                  <ArrowLeft size={13} aria-hidden="true" />
                  Repositories
                </Link>
                <h1 className="text-[16px] font-semibold text-ink truncate">
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
                  disabled={busyAction === "reindex" || jobActive || !isReady}
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
              </div>
            </div>

            <div className="flex-1 overflow-hidden flex">
              <FileExplorer repositoryId={repositoryId} />

              <CodeViewer
                repositoryId={repositoryId}
                filePath={selectedFile?.path}
                commitSha={selectedFile?.commitSha}
              />

              <ChatWindow
                repositoryId={repositoryId}
                conversationId={conversationId}
                setConversationId={setConversationId}
              />
            </div>

            {actionError ? (
              <div
                role="alert"
                className="absolute bottom-4 left-4 right-4 flex items-start gap-2 rounded-control border border-danger/25 bg-danger/[0.06] px-3 py-3 text-[12px] leading-5 text-danger z-20"
              >
                <AlertTriangle size={14} className="mt-0.5 shrink-0" aria-hidden="true" />
                <span>{actionError.message || "That action could not be completed."}</span>
              </div>
            ) : null}

            {!isReady && (
              <div className="absolute bottom-4 left-4 right-4 flex items-center justify-center z-20">
                <Panel className="rounded-control border border-warning/25 bg-warning/[0.06] px-4 py-3 text-[12px] text-warning flex items-center gap-2 shadow-sm">
                  <span className="flex size-3.5 shrink-0">
                    <span className="size-full rounded-full bg-warning animate-pulse" />
                  </span>
                  <span className="truncate">
                    Repository is being indexed. Chat and file browsing will be
                    available when indexing completes.
                  </span>
                </Panel>
              </div>
            )}
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
      </WorkspaceProvider>
    </AppShell>
  );
}
