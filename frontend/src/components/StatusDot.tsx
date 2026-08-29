interface StatusDotProps {
  status: string;
  label?: string;
  size?: "sm" | "md";
}

export function StatusDot({ status, label, size = "md" }: StatusDotProps) {
  const dim = size === "sm" ? "h-2 w-2" : "h-2.5 w-2.5";
  return (
    <span data-status={status} className="inline-flex items-center gap-1.5">
      <span
        className={`${dim} rounded-full`}
        style={{ background: "var(--status)" }}
        aria-hidden
      />
      {label && <span className="sr-only">{label}</span>}
    </span>
  );
}
