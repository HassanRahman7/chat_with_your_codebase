import { useCallback } from "react";
import { formatDateTime } from "../../lib/format";
import { SourceCitation } from "./SourceCitation";

export function ChatMessage({ message, onCitationClick }) {
  const isUser = message.role === "user";

  const handleCitationClick = useCallback(
    (citation) => {
      onCitationClick?.(citation);
    },
    [onCitationClick]
  );

  return (
    <div
      className={`flex flex-col gap-2 ${
        isUser ? "ml-auto max-w-[85%]" : "mr-auto max-w-[90%]"
      }`}
    >
      <div className="flex items-start gap-2">
        {isUser ? null : (
          <div className="mt-1 shrink-0">
            <span className="flex size-5 items-center justify-center rounded-full bg-[#f0e7f7] text-primary text-[10px]">
              AI
            </span>
          </div>
        )}
        <div className="flex-1">
          <div
            className={`rounded-control p-3 text-[13px] leading-6 ${isUser ? "bg-[#f0e7f7] text-ink" : "bg-white text-ink border border-line"}`}
          >
            {message.content}
          </div>
          {message.citations && message.citations.length > 0 && !isUser ? (
            <div className="mt-2 flex flex-wrap gap-2">
              {message.citations.map((citation) => (
                <SourceCitation
                  key={citation.source_id}
                  citation={citation}
                  onClick={handleCitationClick}
                />
              ))}
            </div>
          ) : null}
        </div>
      </div>
      <div className="text-[10px] text-muted/60 mt-0.5 font-mono">
        {formatDateTime(message.created_at)}
      </div>
    </div>
  );
}
