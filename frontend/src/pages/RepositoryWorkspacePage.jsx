import { useState } from "react";
import { Loader2, AlertTriangle, ArrowLeft } from "lucide-react";
import { useParams, useNavigate } from "react-router-dom";

import { cn } from "../lib/utils";
import { AppLayout } from "../components/layout/AppLayout";
import { DashboardSidebar } from "../components/layout/DashboardSidebar";
import { RepositoryToolbar } from "../components/workspace/RepositoryToolbar";
import { FileExplorer } from "../components/repository/FileExplorer";
import { CodeViewer } from "../components/code/CodeViewer";
import { ChatWindow } from "../components/chat/ChatWindow";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { ChevronLeft, ChevronRight } from "lucide-react";
import {
  deleteRepository,
} from "../features/repositories/repositoriesApi";
import { useRepositoryStatus } from "../hooks/useRepositoryStatus";
import { useSystemHealth } from "../hooks/useSystemHealth";
import { WorkspaceProvider, useWorkspace } from "../context/WorkspaceContext";

export function RepositoryWorkspacePage() {
  const { repositoryId } = useParams();
  const navigate = useNavigate();
  const health = useSystemHealth();
  const { repository, status, state, error, refresh } =
    useRepositoryStatus(repositoryId);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [actionError, setActionError] = useState(null);
  const [conversationId, setConversationId] = useState(null);

  async function handleDelete() {
    setActionError(null);
    try {
      await deleteRepository(repositoryId);
      navigate("/dashboard");
    } catch (requestError) {
      setActionError(requestError);
    } finally {
    }
  }

  const job = status?.job;
  const jobActive = job?.status === "queued" || job?.status === "running";
  const notFound = error?.status === 404;
  const isReady = status?.repository_status === "ready";
  const chatDisabled = !isReady || jobActive;

  return (
    <AppLayout
      health={health}
      sidebar={<DashboardSidebar health={health} />}
    >
      <WorkspaceProvider>
        <WorkspaceContent
          repositoryId={repositoryId}
          repository={repository}
          status={status}
          state={state}
          error={error}
          refresh={refresh}
          isReady={isReady}
          chatDisabled={chatDisabled}
          conversationId={conversationId}
          setConversationId={setConversationId}
          actionError={actionError}
          setActionError={setActionError}
          confirmDelete={confirmDelete}
          setConfirmDelete={setConfirmDelete}
          handleDelete={handleDelete}
          navigate={navigate}
          notFound={notFound}
        />
        <ConfirmDialog
          open={confirmDelete}
          title={`Delete ${repository?.repository_name ?? "repository"}?`}
          description="This permanently removes the local clone and the stored repository record. The public GitHub repository itself is not affected."
          confirmLabel="Delete repository"
          onCancel={() => setConfirmDelete(false)}
          onConfirm={handleDelete}
          pending={false}
        />
      </WorkspaceProvider>
    </AppLayout>
  );
}

function WorkspaceContent({
  repositoryId,
  repository,
  status,
  state,
  error,
  refresh,
  isReady,
  chatDisabled,
  conversationId,
  setConversationId,
  actionError,
  setActionError,
  confirmDelete,
  setConfirmDelete,
  handleDelete,
  navigate,
  notFound,
}) {
  const {
    explorerCollapsed,
    setExplorerCollapsed,
    chatCollapsed,
    setChatCollapsed,
  } = useWorkspace();

  const job = status?.job;
  const jobActive = job?.status === "queued" || job?.status === "running";

  return (
    <>
      {state === "loading" || state === "refreshing" ? (
        <div className="flex h-full items-center justify-center gap-2 px-6 py-16 text-[13px] text-muted">
          <Loader2 size={15} className="animate-spin" aria-hidden="true" />
          Loading repository…
        </div>
      ) : state === "error" ? (
        <div className="flex h-full flex-col items-center justify-center px-6 py-14 text-center">
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
              <button
                onClick={refresh}
                className="rounded-control border border-line bg-white px-4 py-2 text-[13px] font-medium text-ink hover:bg-black/[0.04] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
                disabled={state === "refreshing"}
              >
                Try again
              </button>
            ) : null}
            <button
              onClick={() => navigate("/dashboard")}
              className="rounded-control border border-line bg-accent px-4 py-2 text-[13px] font-semibold text-white hover:bg-accent/90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            >
              <ArrowLeft size={14} className="mr-1" aria-hidden="true" />
              Back to repositories
            </button>
          </div>
        </div>
      ) : (
        <div className="flex h-full flex-col min-w-0">
          <RepositoryToolbar
            repository={repository}
            status={status}
            job={job}
            jobActive={jobActive}
            isReady={isReady}
            state={state}
            refresh={refresh}
            onReindex={() => {
              // Re-index handled by toolbar's own hook
            }}
            onDeleteNavigate={() => navigate("/dashboard")}
          />

          <div className="flex flex-row flex-1 overflow-hidden min-w-0 min-h-0 relative bg-white">
            {/* Panel A: File Explorer */}
            <div
              className={cn(
                "flex flex-col shrink-0 border-r border-line transition-all duration-200",
                explorerCollapsed ? "w-0 hidden" : "w-[260px]",
              )}
            >
              <FileExplorer
                repositoryId={repositoryId}
                className="flex-1 min-h-[200px]"
              />
            </div>

            {/* Explorer collapse toggle */}
            {!explorerCollapsed && (
              <button
                onClick={() => setExplorerCollapsed(true)}
                className="absolute left-[260px] top-1/2 -translate-y-1/2 p-1.5 rounded-control border border-line bg-white text-muted hover:bg-accent hover:text-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent z-20"
                aria-label="Collapse explorer"
              >
                <ChevronLeft size={14} className="text-muted" />
              </button>
            )}
            {explorerCollapsed && (
              <button
                onClick={() => setExplorerCollapsed(false)}
                className="absolute left-0 top-1/2 -translate-y-1/2 p-1.5 rounded-control border-r-0 border border-line bg-white text-muted hover:bg-accent hover:text-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent z-20"
                aria-label="Expand explorer"
              >
                <ChevronRight size={14} className="text-muted" />
              </button>
            )}

            {/* Panel B: Code Editor */}
            <div className="flex-1 min-w-0 min-h-0 flex flex-col overflow-hidden">
              <CodeViewer repositoryId={repositoryId} />
            </div>

            {/* Panel C: AI Chat */}
            <div
              className={cn(
                "flex flex-col shrink-0 border-l border-line transition-all duration-200",
                chatCollapsed ? "w-0 hidden" : "w-[400px]",
              )}
            >
              <ChatWindow
                repositoryId={repositoryId}
                conversationId={conversationId}
                setConversationId={setConversationId}
                disabled={chatDisabled}
                model="Nemotron 3 Ultra"
              />
            </div>

            {/* Chat collapse toggle */}
            {!chatCollapsed && (
              <button
                onClick={() => setChatCollapsed(true)}
                className="absolute right-[400px] top-1/2 -translate-y-1/2 p-1.5 rounded-control border border-line bg-white text-muted hover:bg-accent hover:text-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent z-20"
                aria-label="Collapse chat"
              >
                <ChevronLeft size={14} className="text-muted" />
              </button>
            )}
            {chatCollapsed && (
              <button
                onClick={() => setChatCollapsed(false)}
                className="absolute right-0 top-1/2 -translate-y-1/2 p-1.5 rounded-control border-l-0 border border-line bg-white text-muted hover:bg-accent hover:text-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent z-20"
                aria-label="Expand chat"
              >
                <ChevronRight size={14} className="text-muted" />
              </button>
            )}
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
              <div className="rounded-control border border-warning/25 bg-warning/[0.06] px-4 py-3 text-[12px] text-warning flex items-center gap-2 shadow-sm max-w-md">
                <span className="flex size-3.5 shrink-0">
                  <span className="size-full rounded-full bg-warning animate-pulse" />
                </span>
                <span className="truncate">
                  Repository is being indexed. Chat and file browsing will be
                  available when indexing completes.
                </span>
              </div>
            </div>
          )}
        </div>
      )}
    </>
  );
}
