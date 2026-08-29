import type { ReactNode } from "react";

interface PanelProps {
  title: string;
  aside?: ReactNode;
  children: ReactNode;
  testId?: string;
}

export function Panel({ title, aside, children, testId }: PanelProps) {
  return (
    <section className="card p-4" data-testid={testId}>
      <header className="mb-3 flex items-baseline justify-between gap-3">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-muted">
          {title}
        </h2>
        {aside && <div className="text-xs text-muted">{aside}</div>}
      </header>
      {children}
    </section>
  );
}

export function ErrorCard({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div
      role="alert"
      className="rounded-md border border-danger/40 bg-danger/5 p-3 text-sm"
    >
      <span className="text-danger">{message}</span>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="ml-3 rounded border border-border px-2 py-0.5 text-xs hover:bg-bg-secondary"
        >
          Retry
        </button>
      )}
    </div>
  );
}

export function EmptyNote({ children }: { children: ReactNode }) {
  return <p className="py-6 text-center text-sm text-muted">{children}</p>;
}

export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`skeleton ${className}`} aria-hidden />;
}
