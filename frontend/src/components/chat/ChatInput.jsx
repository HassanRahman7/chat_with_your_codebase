import { useCallback, useRef, useState } from "react";
import { ArrowRight, Loader2 } from "lucide-react";

import { askQuestion } from "../../features/chat/chatApi";
import { Button } from "../ui/Button";
import { Input } from "../ui/Input";

export function ChatInput({ repositoryId, conversationId, onAnswer, disabled }) {
  const [question, setQuestion] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState(null);

  const inputRef = useRef(null);

  async function handleSubmit(event) {
    event.preventDefault();
    const value = question.trim();
    if (!value || pending || disabled) return;

    setPending(true);
    setError(null);
    try {
      const result = await askQuestion(repositoryId, {
        question: value,
        conversationId,
      });

      onAnswer?.({ question: value, ...result });

      setQuestion("");
    } catch (submissionError) {
      setError(
        submissionError?.message || "Could not send your question. Please try again."
      );
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="border-t border-line bg-surface p-4 shrink-0 flex flex-col gap-3">
      <form onSubmit={handleSubmit} className="relative flex-1 flex-col gap-2">
        <div className="relative flex-1">
          <Input
            ref={inputRef}
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="Ask anything about this codebase…"
            disabled={pending || disabled}
            className="h-10 bg-white/5 border-white/10 text-white placeholder-white/40 focus:border-accent focus:outline-none"
          />
        </div>
        <Button
          type="submit"
          disabled={pending || disabled || !question.trim()}
          className="absolute right-2 top-2 h-8"
        >
          {pending ? (
            <Loader2 size={14} className="animate-spin" aria-hidden="true" />
          ) : (
            <ArrowRight size={14} aria-hidden="true" />
          )}
        </Button>
      </form>

      {disabled && !pending ? (
        <div className="flex items-start gap-2 px-2 py-1.5 rounded-control border border-warning/25 bg-warning/[0.06] text-[12px] text-warning">
          <span className="mt-0.5 shrink-0" aria-hidden="true">⏳</span>
          <span>
            Repository is still indexing. Ask a question once it is ready.
          </span>
        </div>
      ) : null}

      {error ? (
        <div className="flex items-start gap-2 px-2 py-1.5 rounded-control border border-danger/25 bg-danger/[0.06] text-[12px] text-danger">
          <span className="mt-0.5 shrink-0" aria-hidden="true">⚠</span>
          <span>{error}</span>
        </div>
      ) : null}
    </div>
  );
}
