import { Braces, GitBranch, MessageSquareQuote } from "lucide-react";

const STEPS = [
  {
    icon: GitBranch,
    title: "Connect a repository",
    copy: "Submit a public GitHub URL. The backend validates the host, clones it into controlled storage and records the exact commit.",
  },
  {
    icon: Braces,
    title: "Index code intelligently",
    copy: "Files are filtered, parsed with Tree-sitter and split into function- and class-aware chunks with preserved line ranges.",
  },
  {
    icon: MessageSquareQuote,
    title: "Ask with source-backed answers",
    copy: "Questions retrieve repository-scoped evidence. Answers cite real files and line ranges you can open and verify.",
  },
];

export function WorkflowSteps() {
  return (
    <section id="workflow" className="scroll-mt-20 border-b border-line">
      <div className="mx-auto w-full max-w-6xl px-4 py-16 sm:px-6 lg:py-20">
        <div className="max-w-2xl">
          <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-accent">
            Workflow
          </p>
          <h2 className="mt-3 text-[28px] font-semibold tracking-tight text-ink sm:text-[32px]">
            From repository URL to verifiable explanation
          </h2>
          <p className="mt-3 text-[15px] leading-7 text-muted">
            Two pipelines do the work: indexing turns source into a searchable,
            versioned index; answering retrieves evidence and explains it.
          </p>
        </div>

        <ol className="mt-10 grid gap-4 md:grid-cols-3">
          {STEPS.map((step, index) => {
            const Icon = step.icon;
            return (
              <li
                key={step.title}
                className="rounded-card border border-line bg-white p-6"
              >
                <div className="flex items-center justify-between">
                  <span className="flex size-9 items-center justify-center rounded-control border border-line bg-background text-ink">
                    <Icon size={16} strokeWidth={1.9} aria-hidden="true" />
                  </span>
                  <span className="font-mono text-[11px] text-muted/70">
                    {String(index + 1).padStart(2, "0")}
                  </span>
                </div>
                <h3 className="mt-5 text-[15px] font-semibold text-ink">
                  {step.title}
                </h3>
                <p className="mt-2 text-[13px] leading-6 text-muted">
                  {step.copy}
                </p>
              </li>
            );
          })}
        </ol>
      </div>
    </section>
  );
}
