import { Badge } from "../ui/Badge";

const SUPPORTED = ["Python", "JavaScript", "JSX"];
const PLANNED = ["TypeScript", "Java"];

export function SupportedLanguages() {
  return (
    <section className="border-b border-line">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-4 px-4 py-10 sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <div>
          <h2 className="text-[13px] font-semibold text-ink">
            Supported languages
          </h2>
          <p className="mt-1 text-[13px] text-muted">
            Parsing is registered per language, so adding grammars does not
            change the pipeline.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {SUPPORTED.map((language) => (
            <Badge key={language} tone="success">
              {language}
            </Badge>
          ))}
          {PLANNED.map((language) => (
            <Badge key={language} tone="neutral">
              {language} · planned
            </Badge>
          ))}
        </div>
      </div>
    </section>
  );
}
