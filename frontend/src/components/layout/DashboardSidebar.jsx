import { Home, FolderGit2 } from "lucide-react";
import { Link, NavLink } from "react-router-dom";

import { cn } from "../../lib/utils";
import { StatusPill } from "../system/StatusPill";

export function DashboardSidebar({ health }) {
  return (
    <aside className="hidden w-44 shrink-0 lg:block">
      <div className="sticky top-20">
        <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted/80">
          Workspace
        </p>
        <nav className="mt-2 space-y-1" aria-label="Dashboard">
          <NavLink
            to="/dashboard"
            className={({ isActive }) =>
              cn(
                "flex items-center gap-2 rounded-control px-2.5 py-2 text-[13px] font-medium transition-colors",
                isActive
                  ? "bg-surface text-white"
                  : "text-muted hover:bg-black/[0.04] hover:text-ink",
              )
            }
          >
            <FolderGit2 size={14} aria-hidden="true" />
            Repositories
          </NavLink>
          <Link
            to="/"
            className="flex items-center gap-2 rounded-control px-2.5 py-2 text-[13px] font-medium text-muted transition-colors hover:bg-black/[0.04] hover:text-ink"
          >
            <Home size={14} aria-hidden="true" />
            Overview
          </Link>
        </nav>

        <div className="mt-6 border-t border-line pt-4">
          <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted/80">
            System
          </p>
          <div className="mt-2">
            <StatusPill health={health} />
          </div>
        </div>
      </div>
    </aside>
  );
}
