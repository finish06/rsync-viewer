import type { ReactNode } from "react";

import { ApiRequestError } from "../../api/client";

export function errorMessage(error: unknown): string {
  if (error instanceof ApiRequestError) return error.message;
  if (error instanceof Error) return error.message;
  return "Something went wrong.";
}

export function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: ReactNode;
}) {
  // The hint lives outside the <label> so the accessible name stays exact.
  return (
    <div className="text-sm">
      <label className="block">
        <span className="mb-1 block text-xs font-medium uppercase tracking-wider text-muted">
          {label}
        </span>
        {children}
      </label>
      {hint && <span className="mt-1 block text-xs text-muted">{hint}</span>}
    </div>
  );
}

export const inputClass =
  "w-full rounded border border-border bg-card px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--ring)]";

export function PrimaryButton({
  children,
  busy,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { busy?: boolean }) {
  return (
    <button
      type="submit"
      {...props}
      disabled={busy || props.disabled}
      className="rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-white hover:bg-primary-hover disabled:opacity-50"
    >
      {busy ? "Working…" : children}
    </button>
  );
}

export function SecondaryButton({
  children,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type="button"
      {...props}
      className={`rounded-md border border-border px-3 py-1.5 text-sm hover:bg-bg-secondary disabled:opacity-50 ${props.className ?? ""}`}
    >
      {children}
    </button>
  );
}

export function DangerButton({
  children,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type="button"
      {...props}
      className="rounded-md border border-danger/50 px-3 py-1.5 text-sm text-danger hover:bg-danger/10 disabled:opacity-50"
    >
      {children}
    </button>
  );
}

export function InlineError({ error }: { error: unknown }) {
  if (!error) return null;
  return (
    <p role="alert" className="text-sm text-danger">
      {errorMessage(error)}
    </p>
  );
}

/** Two-step destructive action rendered inline (no browser dialogs). */
export function ConfirmButton({
  label,
  confirmLabel = "Confirm",
  onConfirm,
  busy,
  armed,
  onArm,
  onCancel,
}: {
  label: string;
  confirmLabel?: string;
  onConfirm: () => void;
  busy?: boolean;
  armed: boolean;
  onArm: () => void;
  onCancel: () => void;
}) {
  if (!armed) return <DangerButton onClick={onArm}>{label}</DangerButton>;
  return (
    <span className="inline-flex items-center gap-1">
      <DangerButton onClick={onConfirm} disabled={busy}>
        {busy ? "…" : confirmLabel}
      </DangerButton>
      <SecondaryButton onClick={onCancel}>Cancel</SecondaryButton>
    </span>
  );
}

export function CopyButton({
  text,
  label = "Copy",
}: {
  text: string;
  label?: string;
}) {
  return (
    <SecondaryButton
      onClick={() => {
        void navigator.clipboard?.writeText(text);
      }}
    >
      {label}
    </SecondaryButton>
  );
}

export function EncryptionKeyNotice({ configured }: { configured: boolean }) {
  if (configured) return null;
  return (
    <p
      role="alert"
      className="rounded-md border border-warn/50 bg-warn/10 p-2 text-sm"
    >
      <b>ENCRYPTION_KEY</b> is not set — saving is disabled until it is
      configured in the environment.
    </p>
  );
}
