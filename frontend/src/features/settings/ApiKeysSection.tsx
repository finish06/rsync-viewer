import { useState } from "react";

import { useApiKeys, useCreateApiKey, useRevokeApiKey } from "../../api/hooks";
import type { ApiKeyCreated } from "../../api/types";
import { currentUser, hasRole, type Role } from "../../app/user";
import { EmptyNote, ErrorCard, Panel, Skeleton } from "../../components/Panel";
import { useToast } from "../../components/Toast";
import { formatRelative } from "../../lib/format";
import {
  ConfirmButton,
  CopyButton,
  Field,
  InlineError,
  inputClass,
  PrimaryButton,
  SecondaryButton,
} from "./FormBits";

const ROLES: Role[] = ["viewer", "operator", "admin"];

export function ApiKeysSection() {
  const user = currentUser();
  const isAdmin = hasRole(user, "admin");
  const [showAll, setShowAll] = useState(false);
  const keys = useApiKeys(isAdmin && showAll);
  const create = useCreateApiKey();
  const revoke = useRevokeApiKey();
  const toast = useToast();

  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [role, setRole] = useState<string>("");
  const [created, setCreated] = useState<ApiKeyCreated | null>(null);
  const [armed, setArmed] = useState<string | null>(null);

  const allowedRoles = ROLES.filter((r) => !user || hasRole(user, r));

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    const result = await create.mutateAsync({
      name: name.trim(),
      role_override: role || null,
    });
    setCreated(result);
    setCreating(false);
    setName("");
    setRole("");
    toast.notify(`Key "${result.name}" created`);
  }

  return (
    <Panel
      title="API keys"
      testId="api-keys-section"
      aside={
        <span className="flex items-center gap-3">
          {isAdmin && (
            <label className="flex items-center gap-1">
              <input
                type="checkbox"
                checked={showAll}
                onChange={(e) => setShowAll(e.target.checked)}
              />
              all users
            </label>
          )}
          <SecondaryButton onClick={() => setCreating((v) => !v)}>
            + New key
          </SecondaryButton>
        </span>
      }
    >
      {creating && (
        <form
          onSubmit={submit}
          className="mb-4 grid gap-3 rounded-md border border-border p-3 sm:grid-cols-[1fr_auto_auto] sm:items-end"
          data-testid="api-key-form"
        >
          <Field label="Name">
            <input
              className={inputClass}
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              minLength={1}
              maxLength={100}
            />
          </Field>
          <Field label="Role" hint="≤ your role">
            <select
              className={inputClass}
              aria-label="Role override"
              value={role}
              onChange={(e) => setRole(e.target.value)}
            >
              <option value="">same as mine</option>
              {allowedRoles.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          </Field>
          <div className="flex gap-2">
            <SecondaryButton onClick={() => setCreating(false)}>
              Cancel
            </SecondaryButton>
            <PrimaryButton busy={create.isPending}>Create key</PrimaryButton>
          </div>
          <div className="sm:col-span-3">
            <InlineError error={create.error} />
          </div>
        </form>
      )}

      {created && (
        <div
          className="mb-4 rounded-md border border-ok/50 bg-ok/5 p-3 text-sm"
          data-testid="api-key-created"
        >
          <p className="mb-1 font-medium">
            Key created — copy it now, it will not be shown again.
          </p>
          <div className="flex items-center gap-2">
            <code className="flex-1 truncate rounded bg-code-bg px-2 py-1 font-mono text-xs text-code-text">
              {created.key}
            </code>
            <CopyButton text={created.key} />
            <SecondaryButton onClick={() => setCreated(null)}>
              Done
            </SecondaryButton>
          </div>
        </div>
      )}

      {keys.isPending && <Skeleton className="h-16" />}
      {keys.isError && (
        <ErrorCard
          message="Could not load API keys."
          onRetry={() => void keys.refetch()}
        />
      )}
      {keys.isSuccess && keys.data.length === 0 && (
        <EmptyNote>
          No API keys yet — create one to start sending logs.
        </EmptyNote>
      )}
      {keys.isSuccess && keys.data.length > 0 && (
        <table className="w-full text-sm">
          <thead className="text-left text-xs uppercase tracking-wider text-muted">
            <tr>
              <th className="py-1 pr-3">name</th>
              <th className="py-1 pr-3">prefix</th>
              <th className="py-1 pr-3">role</th>
              <th className="py-1 pr-3">created</th>
              <th className="py-1 pr-3">last used</th>
              <th className="py-1" />
            </tr>
          </thead>
          <tbody>
            {keys.data.map((key) => (
              <tr
                key={key.id}
                data-testid="api-key-row"
                className="border-t border-border"
              >
                <td className="py-1.5 pr-3 font-medium">{key.name}</td>
                <td className="py-1.5 pr-3 font-mono text-xs">
                  {key.key_prefix}…
                </td>
                <td className="py-1.5 pr-3">
                  {key.role_override ?? "inherited"}
                </td>
                <td className="py-1.5 pr-3 text-muted">
                  {formatRelative(key.created_at)}
                </td>
                <td className="py-1.5 pr-3 text-muted">
                  {formatRelative(key.last_used_at)}
                </td>
                <td className="py-1.5 text-right">
                  <ConfirmButton
                    label="Revoke"
                    armed={armed === key.id}
                    onArm={() => setArmed(key.id)}
                    onCancel={() => setArmed(null)}
                    busy={revoke.isPending}
                    onConfirm={() => {
                      void revoke.mutateAsync(key.id).then(() => {
                        setArmed(null);
                        toast.notify(`Key "${key.name}" revoked`);
                      });
                    }}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <InlineError error={revoke.error} />
    </Panel>
  );
}
