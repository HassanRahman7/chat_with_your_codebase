import { useId, useState } from "react";
import { ArrowRight, Loader2 } from "lucide-react";

import { Button } from "../ui/Button";
import { Input } from "../ui/Input";

/**
 * Repository URL form used on the landing page and dashboard.
 * Validation is intentionally delegated to the backend; this component only
 * rejects an empty value and renders the normalized API error.
 */
export function RepositoryUrlForm({
  onSubmit,
  submitLabel = "Analyze repository",
  autoFocus = false,
  className,
}) {
  const inputId = useId();
  const errorId = useId();
  const [url, setUrl] = useState("");
  const [error, setError] = useState(null);
  const [pending, setPending] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    const value = url.trim();
    if (!value) {
      setError({ message: "Enter a GitHub repository URL." });
      return;
    }

    setPending(true);
    setError(null);
    try {
      await onSubmit(value);
      setUrl("");
    } catch (submissionError) {
      setError(
        submissionError?.message
          ? submissionError
          : { message: "Could not register the repository." },
      );
    } finally {
      setPending(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className={className} noValidate>
      <label htmlFor={inputId} className="sr-only">
        Public GitHub repository URL
      </label>
      <div className="flex flex-col gap-2 sm:flex-row">
        <Input
          id={inputId}
          type="url"
          inputMode="url"
          autoComplete="url"
          spellCheck={false}
          autoFocus={autoFocus}
          value={url}
          onChange={(event) => {
            setUrl(event.target.value);
            if (error) setError(null);
          }}
          placeholder="https://github.com/owner/repository"
          aria-invalid={Boolean(error)}
          aria-describedby={error ? errorId : undefined}
          disabled={pending}
          className="h-10 flex-1 bg-white"
        />
        <Button type="submit" size="lg" disabled={pending} className="sm:w-auto">
          {pending ? (
            <>
              <Loader2 size={15} className="animate-spin" aria-hidden="true" />
              Submitting
            </>
          ) : (
            <>
              {submitLabel}
              <ArrowRight size={15} aria-hidden="true" />
            </>
          )}
        </Button>
      </div>

      {error ? (
        <p id={errorId} role="alert" className="mt-2 text-[12px] text-danger">
          {error.message}
        </p>
      ) : (
        <p className="mt-2 text-[11px] text-muted/80">
          Public GitHub repositories only. No credentials are required.
        </p>
      )}
    </form>
  );
}
