import { cn } from "../../lib/utils";

export function Panel({ className, children, ...props }) {
  return (
    <section
      className={cn("rounded-card border border-line bg-white", className)}
      {...props}
    >
      {children}
    </section>
  );
}
