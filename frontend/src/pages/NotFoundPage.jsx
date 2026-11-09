import { Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";

import { Button } from "../components/ui/Button";

export function NotFoundPage() {
  return (
    <main className="mx-auto flex min-h-screen w-full max-w-6xl flex-col items-start justify-center px-4 sm:px-6">
      <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-accent">
        404
      </p>
      <h1 className="mt-3 text-[28px] font-semibold tracking-tight text-ink">
        This page does not exist
      </h1>
      <p className="mt-2 text-[14px] text-muted">
        The route you requested is not part of the application.
      </p>
      <Link to="/" className="mt-6">
        <Button variant="secondary">
          <ArrowLeft size={15} aria-hidden="true" />
          Back to overview
        </Button>
      </Link>
    </main>
  );
}
