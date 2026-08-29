import { useEffect, useState } from "react";

import {
  useSaveSmtpSettings,
  useSmtpSettings,
  useTestSmtp,
} from "../../api/hooks";
import type { SmtpEncryption, SmtpSettings } from "../../api/types";
import { ErrorCard, Panel, Skeleton } from "../../components/Panel";
import { useToast } from "../../components/Toast";
import {
  EncryptionKeyNotice,
  Field,
  InlineError,
  inputClass,
  PrimaryButton,
  SecondaryButton,
} from "./FormBits";

interface FormState {
  host: string;
  port: string;
  username: string;
  password: string;
  encryption: SmtpEncryption;
  from_address: string;
  from_name: string;
  enabled: boolean;
}

function fromSettings(s: SmtpSettings | undefined): FormState {
  return {
    host: s?.host ?? "",
    port: s?.port ? String(s.port) : "587",
    username: s?.username ?? "",
    password: "",
    encryption: s?.encryption ?? "starttls",
    from_address: s?.from_address ?? "",
    from_name: s?.from_name ?? "Rsync Viewer",
    enabled: s?.enabled ?? true,
  };
}

export function EmailSection() {
  const settings = useSmtpSettings();
  const save = useSaveSmtpSettings();
  const test = useTestSmtp();
  const toast = useToast();
  const [form, setForm] = useState<FormState>(() => fromSettings(undefined));
  const [testAddress, setTestAddress] = useState("");

  useEffect(() => {
    if (settings.data) setForm(fromSettings(settings.data));
  }, [settings.data]);

  const set = <K extends keyof FormState>(key: K, value: FormState[K]) =>
    setForm((f) => ({ ...f, [key]: value }));

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    const saved = await save.mutateAsync({
      host: form.host.trim(),
      port: Number(form.port),
      username: form.username.trim() || null,
      password: form.password || null,
      encryption: form.encryption,
      from_address: form.from_address.trim(),
      from_name: form.from_name.trim() || "Rsync Viewer",
      enabled: form.enabled,
    });
    setForm(fromSettings(saved));
    toast.notify("Email settings saved");
  }

  if (settings.isPending) return <Skeleton className="h-48" />;
  if (settings.isError)
    return (
      <ErrorCard
        message="Could not load email settings."
        onRetry={() => void settings.refetch()}
      />
    );
  const canSave = settings.data.encryption_key_configured;

  return (
    <Panel
      title="Email (SMTP)"
      testId="email-section"
      aside={settings.data.configured ? "configured" : "not configured"}
    >
      <EncryptionKeyNotice configured={canSave} />
      <form
        onSubmit={submit}
        className="mt-3 grid gap-3 sm:grid-cols-2"
        data-testid="smtp-form"
      >
        <Field label="Host">
          <input
            className={inputClass}
            value={form.host}
            onChange={(e) => set("host", e.target.value)}
            required
          />
        </Field>
        <Field label="Port">
          <input
            className={inputClass}
            type="number"
            min={1}
            max={65535}
            value={form.port}
            onChange={(e) => set("port", e.target.value)}
            required
          />
        </Field>
        <Field label="Username">
          <input
            className={inputClass}
            value={form.username}
            onChange={(e) => set("username", e.target.value)}
            autoComplete="off"
          />
        </Field>
        <Field
          label="Password"
          hint={
            settings.data.has_password
              ? "A password is stored; leave blank to keep it."
              : undefined
          }
        >
          <input
            className={inputClass}
            type="password"
            value={form.password}
            onChange={(e) => set("password", e.target.value)}
            placeholder={settings.data.has_password ? "unchanged" : ""}
            autoComplete="new-password"
          />
        </Field>
        <Field label="Encryption">
          <select
            className={inputClass}
            aria-label="Encryption"
            value={form.encryption}
            onChange={(e) =>
              set("encryption", e.target.value as SmtpEncryption)
            }
          >
            <option value="starttls">STARTTLS</option>
            <option value="ssl_tls">SSL/TLS</option>
            <option value="none">None</option>
          </select>
        </Field>
        <Field label="From address">
          <input
            className={inputClass}
            type="email"
            value={form.from_address}
            onChange={(e) => set("from_address", e.target.value)}
            required
          />
        </Field>
        <Field label="From name">
          <input
            className={inputClass}
            value={form.from_name}
            onChange={(e) => set("from_name", e.target.value)}
          />
        </Field>
        <label className="flex items-center gap-2 self-end text-sm">
          <input
            type="checkbox"
            checked={form.enabled}
            onChange={(e) => set("enabled", e.target.checked)}
          />
          Email sending enabled
        </label>
        <div className="flex items-center gap-3 sm:col-span-2">
          <PrimaryButton busy={save.isPending} disabled={!canSave}>
            Save
          </PrimaryButton>
          <InlineError error={save.error} />
        </div>
      </form>

      <div
        className="mt-4 flex flex-wrap items-center gap-2 border-t border-border pt-3 text-sm"
        data-testid="smtp-test"
      >
        <span className="text-muted">Send a test email to</span>
        <input
          className={`${inputClass} w-64`}
          type="email"
          aria-label="Test email address"
          value={testAddress}
          onChange={(e) => setTestAddress(e.target.value)}
          placeholder="you@example.com"
        />
        <SecondaryButton
          disabled={!testAddress || test.isPending || !settings.data.configured}
          onClick={() => {
            test.mutate(testAddress, {
              onSuccess: (r) =>
                toast.notify(`Test email sent to ${r.to_address}`),
            });
          }}
        >
          {test.isPending ? "Sending…" : "Send"}
        </SecondaryButton>
        <InlineError error={test.error} />
      </div>
    </Panel>
  );
}
