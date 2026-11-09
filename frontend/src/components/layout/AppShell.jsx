import { Navbar } from "./Navbar";

export function AppShell({ health, children, sidebar }) {
  return (
    <div className="flex min-h-screen flex-col bg-background">
      <Navbar health={health} />
      {sidebar ? (
        <div className="mx-auto flex w-full max-w-6xl flex-1 gap-8 px-4 py-8 sm:px-6">
          {sidebar}
          <main className="min-w-0 flex-1">{children}</main>
        </div>
      ) : (
        <main className="flex-1">{children}</main>
      )}
      <footer className="border-t border-line">
        <div className="mx-auto flex w-full max-w-6xl flex-col gap-2 px-4 py-8 sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <p className="text-[13px] text-muted">
            Codebase AI — every explanation connected to real code.
          </p>
          <p className="font-mono text-[11px] text-muted">
            React · FastAPI · ChromaDB · Gemini
          </p>
        </div>
      </footer>
    </div>
  );
}
