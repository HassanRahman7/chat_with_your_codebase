import { useLocation } from "react-router-dom";
import { Link, NavLink } from "react-router-dom";
import { Braces } from "lucide-react";

import { cn } from "../../lib/utils";
import { StatusPill } from "../system/StatusPill";

const NAV_LINKS = [
  { label: "How it works", href: "/#workflow" },
  { label: "Capabilities", href: "/#capabilities" },
  { label: "Status", href: "/#status" },
];

export function Navbar({ health, className, hideNavLinks }) {
  const location = useLocation();
  const isWorkspace = location.pathname.includes("/workspace");
  const showNavLinks = !hideNavLinks && !isWorkspace;

  return (
    <header
      className={cn(
        "sticky top-0 z-20 border-b border-line/80 bg-background/90 backdrop-blur",
        className,
      )}
    >
      <div className="mx-auto flex h-14 w-full max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
        <Link
          to="/"
          className="flex items-center gap-2.5 rounded-control focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          aria-label="Codebase AI home"
        >
          <span className="flex size-7 items-center justify-center rounded-control bg-surface text-white">
            <Braces size={15} strokeWidth={2.25} aria-hidden="true" />
          </span>
          <span className="text-[15px] font-semibold tracking-tight">
            Codebase AI
          </span>
        </Link>

        {showNavLinks && (
          <nav aria-label="Primary" className="hidden items-center gap-1 md:flex">
            <NavLink
              to="/dashboard"
              className={({ isActive }) =>
                cn(
                  "rounded-control px-3 py-1.5 text-[13px] font-medium transition-colors hover:bg-black/[0.04] hover:text-ink",
                  isActive ? "bg-surface text-white" : "text-muted",
                )
              }
            >
              Repositories
            </NavLink>
            {NAV_LINKS.map((link) => (
              <a
                key={link.href}
                href={link.href}
                className="rounded-control px-3 py-1.5 text-[13px] font-medium text-muted transition-colors hover:bg-black/[0.04] hover:text-ink"
              >
                {link.label}
              </a>
            ))}
          </nav>
        )}

        <StatusPill health={health} />
      </div>
    </header>
  );
}
