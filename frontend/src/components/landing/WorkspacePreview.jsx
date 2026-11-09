import {
  FileCode2,
  Folder,
  Search,
  Sparkles,
} from "lucide-react";

/**
 * Static wireframe preview of the three-panel workspace.
 * Deliberately abstract: no fabricated repositories, statuses or citations.
 */
export function WorkspacePreview() {
  return (
    <figure className="m-0">
      <div className="overflow-hidden rounded-card border border-white/10 bg-surface shadow-2xl shadow-black/20">
        <div className="flex h-9 items-center gap-2 border-b border-white/10 px-3">
          <span className="flex gap-1.5" aria-hidden="true">
            <span className="size-2 rounded-full bg-white/20" />
            <span className="size-2 rounded-full bg-white/15" />
            <span className="size-2 rounded-full bg-white/10" />
          </span>
          <span className="mx-auto font-mono text-[10px] uppercase tracking-[0.14em] text-white/40">
            Workspace preview
          </span>
          <span className="rounded-full border border-white/10 px-1.5 py-0.5 font-mono text-[9px] text-white/40">
            MVP
          </span>
        </div>

        <div
          className="grid h-[300px] grid-cols-[0.85fr_1.4fr_1.05fr] divide-x divide-white/10"
          aria-hidden="true"
        >
          {/* Explorer */}
          <div className="p-2.5">
            <div className="mb-2 flex items-center justify-between">
              <span className="font-mono text-[9px] uppercase tracking-widest text-white/35">
                Explorer
              </span>
              <Search size={10} className="text-white/25" />
            </div>
            <div className="mb-2 h-5 rounded-[2px] border border-white/10 bg-white/[0.03]" />
            <div className="space-y-1.5">
              <ExplorerRow icon={Folder} width="w-16" accent />
              <ExplorerRow icon={Folder} width="w-12" indent />
              <ExplorerRow icon={FileCode2} width="w-20" indent />
              <ExplorerRow icon={FileCode2} width="w-14" indent active />
              <ExplorerRow icon={Folder} width="w-10" indent />
              <ExplorerRow icon={FileCode2} width="w-16" indent />
              <ExplorerRow icon={FileCode2} width="w-12" />
              <ExplorerRow icon={Folder} width="w-14" />
            </div>
          </div>

          {/* Code */}
          <div className="p-2.5">
            <div className="mb-2 flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-accent/70" />
              <span className="h-1.5 w-24 rounded-full bg-white/15" />
            </div>
            <div className="space-y-[7px]">
              {[
                ["w-28", "bg-primary/45"],
                ["w-40", "bg-white/12"],
                ["w-24", "bg-white/12"],
                ["w-36", "bg-accent/40"],
                ["w-32", "bg-white/12"],
                ["w-44", "bg-white/10"],
                ["w-20", "bg-white/12"],
                ["w-40", "bg-white/10"],
                ["w-28", "bg-accent/30"],
                ["w-36", "bg-white/12"],
                ["w-16", "bg-white/10"],
                ["w-44", "bg-white/10"],
                ["w-24", "bg-primary/30"],
                ["w-32", "bg-white/10"],
              ].map(([width, color], index) => (
                <div key={index} className="flex items-center gap-2">
                  <span className="w-3 shrink-0 text-right font-mono text-[8px] leading-none text-white/20">
                    {index + 1}
                  </span>
                  <span className={`h-[6px] rounded-[1px] ${width} ${color}`} />
                </div>
              ))}
            </div>
          </div>

          {/* Assistant */}
          <div className="flex flex-col p-2.5">
            <div className="mb-2 flex items-center gap-1.5">
              <Sparkles size={10} className="text-primary" />
              <span className="font-mono text-[9px] uppercase tracking-widest text-white/35">
                Assistant
              </span>
            </div>
            <div className="mb-3 ml-auto w-[70%] rounded-[3px] bg-white/10 p-2">
              <span className="block h-[5px] w-full rounded-[1px] bg-white/20" />
              <span className="mt-1 block h-[5px] w-2/3 rounded-[1px] bg-white/15" />
            </div>
            <div className="space-y-1.5">
              <span className="block h-[5px] w-full rounded-[1px] bg-white/12" />
              <span className="block h-[5px] w-11/12 rounded-[1px] bg-white/10" />
              <span className="block h-[5px] w-4/5 rounded-[1px] bg-white/10" />
            </div>
            <div className="mt-2.5 space-y-1.5">
              <CitationRow />
              <CitationRow />
            </div>
            <div className="mt-auto flex h-8 items-center gap-2 rounded-[3px] border border-white/10 bg-white/[0.03] px-2">
              <span className="h-[5px] w-20 rounded-[1px] bg-white/12" />
              <span className="ml-auto size-4 rounded-[2px] bg-primary/60" />
            </div>
          </div>
        </div>
      </div>
      <figcaption className="mt-3 text-center font-mono text-[10px] uppercase tracking-[0.14em] text-muted/70">
        Interface preview — not live data
      </figcaption>
    </figure>
  );
}

function ExplorerRow({ icon: Icon, width, indent = false, accent = false, active = false }) {
  return (
    <div
      className={`flex items-center gap-1.5 rounded-[2px] px-1 py-0.5 ${
        active ? "bg-accent/15" : ""
      } ${indent ? "ml-2.5" : ""}`}
    >
      <Icon
        size={9}
        className={accent ? "text-primary/70" : active ? "text-accent" : "text-white/30"}
      />
      <span
        className={`h-[5px] rounded-[1px] ${width} ${
          active ? "bg-accent/50" : "bg-white/12"
        }`}
      />
    </div>
  );
}

function CitationRow() {
  return (
    <div className="flex items-center gap-1.5 rounded-[2px] border border-accent/20 bg-accent/[0.07] px-1.5 py-1">
      <FileCode2 size={8} className="text-accent/70" />
      <span className="h-[4px] w-14 rounded-[1px] bg-accent/30" />
      <span className="ml-auto h-[4px] w-6 rounded-[1px] bg-white/15" />
    </div>
  );
}
