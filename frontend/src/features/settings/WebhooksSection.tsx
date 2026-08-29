import { useState } from "react";

import { useSources, useWebhookMutations, useWebhooks } from "../../api/hooks";
import type { WebhookRead, WebhookWrite } from "../../api/types";
import { EmptyNote, ErrorCard, Panel, Skeleton } from "../../components/Panel";
import { useToast } from "../../components/Toast";
import {
  ConfirmButton,
  errorMessage,
  Field,
  inputClass,
  PrimaryButton,
  SecondaryButton,
} from "./FormBits";

const DISCORD_URL =
  /^https:\/\/(discord\.com|discordapp\.com)\/api\/webhooks\/\d+\/.+/;
const DEFAULT_COLOR = "#ff0045";

interface FormState {
  name: string;
  url: string;
  webhook_type: "generic" | "discord";
  headers: string;
  source_filters: string;
  enabled: boolean;
  discord_color: string;
  discord_username: string;
  discord_avatar_url: string;
  discord_footer: string;
}

function emptyForm(): FormState {
  return {
    name: "",
    url: "",
    webhook_type: "generic",
    headers: "",
    source_filters: "",
    enabled: true,
    discord_color: DEFAULT_COLOR,
    discord_username: "Rsync Viewer",
    discord_avatar_url: "",
    discord_footer: "",
  };
}

function fromWebhook(w: WebhookRead): FormState {
  const opts = (w.options ?? {}) as Record<string, unknown>;
  const color =
    typeof opts.color === "number"
      ? `#${opts.color.toString(16).padStart(6, "0")}`
      : DEFAULT_COLOR;
  return {
    name: w.name,
    url: w.url,
    webhook_type: w.webhook_type,
    headers: w.headers ? JSON.stringify(w.headers, null, 2) : "",
    source_filters: (w.source_filters ?? []).join(", "),
    enabled: w.enabled,
    discord_color: color,
    discord_username:
      typeof opts.username === "string" ? opts.username : "Rsync Viewer",
    discord_avatar_url:
      typeof opts.avatar_url === "string" ? opts.avatar_url : "",
    discord_footer: typeof opts.footer === "string" ? opts.footer : "",
  };
}

/** Validate + convert the form into the API body; returns an error string on failure. */
export function toWrite(form: FormState): {
  body?: WebhookWrite;
  error?: string;
} {
  const name = form.name.trim();
  const url = form.url.trim();
  if (!name) return { error: "Name is required." };
  if (!/^https?:\/\//.test(url))
    return { error: "URL must start with http:// or https://." };
  if (form.webhook_type === "discord" && !DISCORD_URL.test(url)) {
    return {
      error:
        "Discord webhooks need a URL like https://discord.com/api/webhooks/…",
    };
  }
  let headers: Record<string, string> | null = null;
  if (form.headers.trim()) {
    try {
      const parsed = JSON.parse(form.headers) as unknown;
      if (!parsed || typeof parsed !== "object" || Array.isArray(parsed))
        throw new Error();
      headers = Object.fromEntries(
        Object.entries(parsed as Record<string, unknown>).map(([k, v]) => [
          k,
          String(v),
        ]),
      );
    } catch {
      return {
        error:
          'Headers must be a JSON object, e.g. {"Authorization": "Bearer …"}.',
      };
    }
  }
  const filters = form.source_filters
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
  let options: Record<string, unknown> | null = null;
  if (form.webhook_type === "discord") {
    const colorInt = Number.parseInt(form.discord_color.replace("#", ""), 16);
    options = {
      color: Number.isNaN(colorInt) ? 0xff0045 : colorInt,
      username: form.discord_username.trim() || "Rsync Viewer",
      ...(form.discord_avatar_url.trim()
        ? { avatar_url: form.discord_avatar_url.trim() }
        : {}),
      ...(form.discord_footer.trim()
        ? { footer: form.discord_footer.trim() }
        : {}),
    };
  }
  return {
    body: {
      name,
      url,
      webhook_type: form.webhook_type,
      headers,
      source_filters: filters.length ? filters : null,
      options,
      enabled: form.enabled,
    },
  };
}

export function WebhooksSection() {
  const webhooks = useWebhooks();
  const sources = useSources();
  const { create, update, remove, test } = useWebhookMutations();
  const toast = useToast();
  const [editing, setEditing] = useState<"new" | string | null>(null);
  const [form, setForm] = useState<FormState>(emptyForm);
  const [formError, setFormError] = useState<string | null>(null);
  const [armed, setArmed] = useState<string | null>(null);
  const [rowMessage, setRowMessage] = useState<{
    id: string;
    text: string;
    ok: boolean;
  } | null>(null);

  const set = <K extends keyof FormState>(key: K, value: FormState[K]) =>
    setForm((f) => ({ ...f, [key]: value }));

  function openNew() {
    setForm(emptyForm());
    setFormError(null);
    setEditing("new");
  }
  function openEdit(w: WebhookRead) {
    setForm(fromWebhook(w));
    setFormError(null);
    setEditing(w.id);
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    const { body, error } = toWrite(form);
    if (error || !body) {
      setFormError(error ?? "Invalid form");
      return;
    }
    setFormError(null);
    try {
      if (editing === "new") {
        await create.mutateAsync(body);
        toast.notify(`Webhook "${body.name}" created`);
      } else if (editing) {
        await update.mutateAsync({ id: editing, body });
        toast.notify(`Webhook "${body.name}" saved`);
      }
      setEditing(null);
    } catch (err) {
      setFormError(errorMessage(err));
    }
  }

  return (
    <Panel
      title="Webhooks"
      testId="webhooks-section"
      aside={<SecondaryButton onClick={openNew}>+ Add webhook</SecondaryButton>}
    >
      {editing === "new" && (
        <WebhookForm
          form={form}
          set={set}
          onSubmit={submit}
          onCancel={() => setEditing(null)}
          error={formError}
          busy={create.isPending}
          sources={sources.data ?? []}
        />
      )}
      {webhooks.isPending && <Skeleton className="h-16" />}
      {webhooks.isError && (
        <ErrorCard
          message="Could not load webhooks."
          onRetry={() => void webhooks.refetch()}
        />
      )}
      {webhooks.isSuccess &&
        webhooks.data.length === 0 &&
        editing !== "new" && <EmptyNote>No webhooks configured.</EmptyNote>}
      {webhooks.isSuccess && (
        <ul className="divide-y divide-border">
          {webhooks.data.map((w) => (
            <li
              key={w.id}
              data-testid="webhook-row"
              data-status={w.enabled ? "ok" : "never"}
              className="py-2"
            >
              <div className="flex flex-wrap items-center gap-2 text-sm">
                <span
                  className="h-2.5 w-2.5 rounded-full"
                  style={{ background: "var(--status)" }}
                  aria-hidden
                />
                <span className="font-medium">{w.name}</span>
                <span className="rounded bg-bg-secondary px-1.5 text-xs">
                  {w.webhook_type}
                </span>
                {w.source_filters?.length ? (
                  <span className="text-xs text-muted">
                    {w.source_filters.join(", ")}
                  </span>
                ) : (
                  <span className="text-xs text-muted">all sources</span>
                )}
                <span
                  className={`text-xs ${w.consecutive_failures ? "text-danger" : "text-muted"}`}
                >
                  ⟳ {w.consecutive_failures} fails
                </span>
                <span className="ml-auto flex flex-wrap gap-1">
                  <SecondaryButton
                    disabled={test.isPending}
                    onClick={() =>
                      test
                        .mutateAsync(w.id)
                        .then((r) =>
                          setRowMessage({
                            id: w.id,
                            ok: true,
                            text: `Delivered (HTTP ${r.http_status})`,
                          }),
                        )
                        .catch((e: unknown) =>
                          setRowMessage({
                            id: w.id,
                            ok: false,
                            text: errorMessage(e),
                          }),
                        )
                    }
                  >
                    Test
                  </SecondaryButton>
                  <SecondaryButton onClick={() => openEdit(w)}>
                    Edit
                  </SecondaryButton>
                  <SecondaryButton
                    aria-pressed={w.enabled}
                    onClick={() =>
                      update
                        .mutateAsync({
                          id: w.id,
                          body: { enabled: !w.enabled },
                        })
                        .then(() =>
                          toast.notify(
                            `Webhook "${w.name}" ${w.enabled ? "disabled" : "enabled"}`,
                          ),
                        )
                        .catch((e: unknown) =>
                          setRowMessage({
                            id: w.id,
                            ok: false,
                            text: errorMessage(e),
                          }),
                        )
                    }
                  >
                    {w.enabled ? "⏻ on" : "⏻ off"}
                  </SecondaryButton>
                  <ConfirmButton
                    label="Delete"
                    armed={armed === w.id}
                    onArm={() => setArmed(w.id)}
                    onCancel={() => setArmed(null)}
                    busy={remove.isPending}
                    onConfirm={() =>
                      void remove
                        .mutateAsync(w.id)
                        .then(() => {
                          setArmed(null);
                          toast.notify(`Webhook "${w.name}" deleted`);
                        })
                        .catch((e: unknown) =>
                          setRowMessage({
                            id: w.id,
                            ok: false,
                            text: errorMessage(e),
                          }),
                        )
                    }
                  />
                </span>
              </div>
              {rowMessage?.id === w.id && (
                <p
                  role={rowMessage.ok ? "status" : "alert"}
                  className={`mt-1 text-xs ${rowMessage.ok ? "text-ok" : "text-danger"}`}
                >
                  {rowMessage.text}
                </p>
              )}
              {editing === w.id && (
                <WebhookForm
                  form={form}
                  set={set}
                  onSubmit={submit}
                  onCancel={() => setEditing(null)}
                  error={formError}
                  busy={update.isPending}
                  sources={sources.data ?? []}
                />
              )}
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}

function WebhookForm({
  form,
  set,
  onSubmit,
  onCancel,
  error,
  busy,
  sources,
}: {
  form: FormState;
  set: <K extends keyof FormState>(key: K, value: FormState[K]) => void;
  onSubmit: (e: React.FormEvent) => void;
  onCancel: () => void;
  error: string | null;
  busy: boolean;
  sources: string[];
}) {
  return (
    <form
      onSubmit={onSubmit}
      className="my-2 grid gap-3 rounded-md border border-border p-3 sm:grid-cols-2"
      data-testid="webhook-form"
    >
      <Field label="Name">
        <input
          className={inputClass}
          value={form.name}
          onChange={(e) => set("name", e.target.value)}
          required
        />
      </Field>
      <Field label="Type">
        <select
          className={inputClass}
          aria-label="Webhook type"
          value={form.webhook_type}
          onChange={(e) =>
            set("webhook_type", e.target.value as FormState["webhook_type"])
          }
        >
          <option value="generic">generic (JSON POST)</option>
          <option value="discord">discord</option>
        </select>
      </Field>
      <div className="sm:col-span-2">
        <Field label="URL">
          <input
            className={inputClass}
            type="url"
            value={form.url}
            onChange={(e) => set("url", e.target.value)}
            required
          />
        </Field>
      </div>
      <Field
        label="Source filters"
        hint={
          sources.length
            ? `comma-separated; known: ${sources.slice(0, 6).join(", ")}`
            : "comma-separated; empty = all sources"
        }
      >
        <input
          className={inputClass}
          value={form.source_filters}
          onChange={(e) => set("source_filters", e.target.value)}
        />
      </Field>
      <label className="flex items-center gap-2 self-end text-sm">
        <input
          type="checkbox"
          checked={form.enabled}
          onChange={(e) => set("enabled", e.target.checked)}
        />
        Enabled
      </label>
      {form.webhook_type === "generic" && (
        <div className="sm:col-span-2">
          <Field label="Headers (JSON object)">
            <textarea
              className={`${inputClass} font-mono`}
              rows={3}
              value={form.headers}
              onChange={(e) => set("headers", e.target.value)}
              placeholder='{"Authorization": "Bearer …"}'
            />
          </Field>
        </div>
      )}
      {form.webhook_type === "discord" && (
        <>
          <Field label="Embed colour">
            <input
              className={inputClass}
              type="color"
              aria-label="Embed colour"
              value={form.discord_color}
              onChange={(e) => set("discord_color", e.target.value)}
            />
          </Field>
          <Field label="Bot username">
            <input
              className={inputClass}
              value={form.discord_username}
              onChange={(e) => set("discord_username", e.target.value)}
            />
          </Field>
          <Field label="Avatar URL">
            <input
              className={inputClass}
              type="url"
              value={form.discord_avatar_url}
              onChange={(e) => set("discord_avatar_url", e.target.value)}
            />
          </Field>
          <Field label="Footer">
            <input
              className={inputClass}
              value={form.discord_footer}
              onChange={(e) => set("discord_footer", e.target.value)}
            />
          </Field>
        </>
      )}
      <div className="flex items-center gap-2 sm:col-span-2">
        <PrimaryButton busy={busy}>Save</PrimaryButton>
        <SecondaryButton onClick={onCancel}>Cancel</SecondaryButton>
        {error && (
          <p role="alert" className="text-sm text-danger">
            {error}
          </p>
        )}
      </div>
    </form>
  );
}
