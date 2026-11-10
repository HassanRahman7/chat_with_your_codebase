import { useCallback } from "react";
import { FileCode2 } from "lucide-react";

import { useWorkspace } from "../../context/WorkspaceContext";

export function SourceCitation({ citation }) {
  const { selectCitation } = useWorkspace();

  const handleClick = useCallback(() => {
    selectCitation(citation);
  }, [citation, selectCitation]);

  return (
    <button
      onClick={handleClick}
      className="flex items-start gap-2 rounded-control border border-accent/20 bg-accent/[0.06] px-2.5 py-2 text-[11px] leading-5 text-accent hover:bg-accent/10 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
      role="button"
      aria-label={`Open ${citation.file_path} L${citation.start_line}-${citation.end_line}`}
    >
      <div className="mt-0.5 shrink-0">
        <FileCode2 size={12} className="text-accent" />
      </div>
      <div className="flex flex-col gap-0.5 min-w-0">
        <div className="flex items-center gap-1 text-[11px] font-medium">
          <span className="truncate">{citation.file_path}</span>
          {citation.symbol_name ? (
            <span className="font-mono text-[10px] opacity-80">
              • {citation.symbol_name}
            </span>
          ) : null}
        </div>
        <span className="font-mono text-[10px] opacity-70">
          L{citation.start_line}–{citation.end_line}
        </span>
      </div>
    </button>
  );
}
