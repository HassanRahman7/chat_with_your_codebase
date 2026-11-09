import { Braces, Database, FileSearch, ShieldCheck } from "lucide-react";

const FEATURES = [
  {
    icon: Braces,
    title: "Syntax-aware chunking",
    copy: "Complete functions, methods and classes are indexed as meaningful units instead of arbitrary line windows. Oversized symbols split only at safe syntax boundaries.",
  },
  {
    icon: Database,
    title: "Repository-scoped retrieval",
    copy: "Every query is filtered by repository and active index version. Evidence from one codebase can never leak into another.",
  },
  {
    icon: FileSearch,
    title: "Clickable, validated citations",
    copy: "The model cites server-issued source IDs. The backend fills in paths and line ranges from trusted metadata, then the viewer opens the exact lines.",
  },
  {
    icon: ShieldCheck,
    title: "Honest about uncertainty",
    copy: "If retrieval finds no sufficiently relevant evidence, the assistant says so instead of inventing a file, symbol or line number.",
  },
];

export function FeatureHighlights() {
  return (
    <section id="capabilities" className="scroll-mt-20 border-b border-line">
      <div className="mx-auto w-full max-w-6xl px-4 py-16 sm:px-6 lg:py-20">
        <div className="max-w-2xl">
          <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-accent">
            Capabilities
          </p>
          <h2 className="mt-3 text-[28px] font-semibold tracking-tight text-ink sm:text-[32px]">
            Built around evidence, not guesswork
          </h2>
        </div>

        <div className="mt-10 grid gap-4 sm:grid-cols-2">
          {FEATURES.map((feature) => {
            const Icon = feature.icon;
            return (
              <article
                key={feature.title}
                className="rounded-card border border-line bg-white p-6"
              >
                <span className="flex size-8 items-center justify-center rounded-control bg-surface text-white">
                  <Icon size={15} strokeWidth={1.9} aria-hidden="true" />
                </span>
                <h3 className="mt-4 text-[15px] font-semibold text-ink">
                  {feature.title}
                </h3>
                <p className="mt-2 text-[13px] leading-6 text-muted">
                  {feature.copy}
                </p>
              </article>
            );
          })}
        </div>
      </div>
    </section>
  );
}
