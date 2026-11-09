import { ArrowRight, ShieldCheck } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { createRepository } from "../../features/repositories/repositoriesApi";
import { Button } from "../ui/Button";
import { RepositoryUrlForm } from "../repository/RepositoryUrlForm";
import { WorkspacePreview } from "./WorkspacePreview";

const SIGNALS = [
  { label: "Syntax-aware", detail: "Tree-sitter chunks" },
  { label: "Repository-scoped", detail: "No cross-repo mixing" },
  { label: "Cited answers", detail: "File + line evidence" },
];

export function Hero() {
  const navigate = useNavigate();

  async function handleAnalyze(url) {
    try {
      const result = await createRepository(url);
      navigate(`/repositories/${result.repository.id}`);
    } catch (error) {
      const existingId = error?.details?.repository_id;
      if (error?.code === "repository_already_exists" && existingId) {
        navigate(`/repositories/${existingId}`);
        return;
      }
      throw error;
    }
  }

  return (
    <section className="border-b border-line">
      <div className="mx-auto grid w-full max-w-6xl gap-12 px-4 pb-16 pt-14 sm:px-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.02fr)] lg:items-center lg:gap-14 lg:pb-24 lg:pt-20">
        <div className="animate-rise">
          <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-primary">
            Repository intelligence
          </p>

          <h1 className="mt-4 text-balance text-[40px] font-semibold leading-[1.06] tracking-tight text-ink sm:text-[52px]">
            Understand any codebase.{" "}
            <span className="text-primary">Ask it anything.</span>
          </h1>

          <p className="mt-5 max-w-xl text-[15px] leading-7 text-muted">
            Connect a GitHub repository and explore how it works. Get clear
            answers grounded in real files, functions and line-level citations.
          </p>

          <div className="mt-7 max-w-xl">
            <RepositoryUrlForm onSubmit={handleAnalyze} autoFocus />
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-3">
            <a href="#workflow">
              <Button variant="secondary">
                Explore how it works
                <ArrowRight size={15} aria-hidden="true" />
              </Button>
            </a>
            <a
              href="#status"
              className="inline-flex items-center gap-2 rounded-control px-2 py-2 text-sm font-medium text-muted transition-colors hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            >
              <ShieldCheck size={15} aria-hidden="true" />
              Check system status
            </a>
          </div>

          <dl className="mt-10 grid max-w-lg grid-cols-1 gap-4 border-t border-line pt-5 sm:grid-cols-3">
            {SIGNALS.map((signal) => (
              <div key={signal.label}>
                <dt className="text-[13px] font-medium text-ink">
                  {signal.label}
                </dt>
                <dd className="mt-0.5 font-mono text-[10px] uppercase tracking-wider text-muted/80">
                  {signal.detail}
                </dd>
              </div>
            ))}
          </dl>
        </div>

        <div className="animate-rise-delayed">
          <WorkspacePreview />
        </div>
      </div>
    </section>
  );
}
