import { useState, useCallback } from "react";
import { X, ChevronRight } from "lucide-react";

import { Navbar } from "./Navbar";
import { cn } from "../../lib/utils";
import { useLocation } from "react-router-dom";

export function AppLayout({ health, children, sidebar }) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const location = useLocation();
  const isWorkspace = location.pathname.includes("/workspace");

  const toggleSidebar = useCallback(() => {
    setSidebarCollapsed((prev) => !prev);
  }, []);

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <Navbar health={health} />

      <div className="flex flex-1">
        {sidebar && (
          <aside
            className={cn(
              "flex flex-col shrink-0 border-r border-line bg-background transition-all duration-200 z-20",
              sidebarCollapsed ? "w-14" : "w-64",
            )}
          >
            <div className="flex items-center justify-between px-3 py-4 shrink-0 border-b border-line">
              {!sidebarCollapsed && (
                <div className="flex items-center gap-2">
                  <span className="flex size-6 items-center justify-center rounded-control bg-primary text-white">
                    <svg
                      width="16"
                      height="16"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      className="text-white"
                      aria-hidden="true"
                    >
                      <path d="M12 2L2 7l10 5 10-5-10-5z" />
                      <path d="M2 17l10 5 10-5" />
                      <path d="M2 12l10 5 10-5" />
                    </svg>
                  </span>
                  <span className="text-[13px] font-semibold text-ink">
                    Codebase AI
                  </span>
                </div>
              )}
              <button
                onClick={toggleSidebar}
                className="p-1.5 rounded-control text-ink/70 hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
                aria-label={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
              >
                {sidebarCollapsed ? (
                  <ChevronRight size={16} aria-hidden="true" />
                ) : (
                  <X size={16} aria-hidden="true" />
                )}
              </button>
            </div>
            <nav className="flex-1 overflow-y-auto py-3 px-2 space-y-1">
              {sidebar}
            </nav>
          </aside>
        )}

        <main className="flex-1 min-w-0 relative">
          {children}
        </main>
      </div>

      {!isWorkspace && (
        <footer className="border-t border-line">
          <div className="mx-auto flex w-full max-w-6xl flex-col gap-2 px-4 py-8 sm:flex-row sm:items-center sm:justify-between sm:px-6">
            <p className="text-[13px] text-muted">
              Codebase AI — every explanation connected to real code.
            </p>
            <p className="font-mono text-[11px] text-muted">
              React · FastAPI · ChromaDB
            </p>
          </div>
        </footer>
      )}
    </div>
  );
}
