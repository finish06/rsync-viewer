import { useEffect, useState } from "react";

import {
  useOidcSettings,
  useSaveOidcSettings,
  useTestOidcDiscovery,
} from "../../api/hooks";
import type { OidcSettings } from "../../api/types";
import { ErrorCard, Panel, Skeleton } from "../../components/Panel";
import { useToast } from "../../components/Toast";
import {
  CopyButton,
  EncryptionKeyNotice,
  Field,
  InlineError,
  inputClass,
  PrimaryButton,
  SecondaryButton,
} from "./FormBits";

interface FormState {
  issuer_url: string;
  client_id: string;
  client_secret: string;
  provider_name: string;
  scopes: string;
  enabled: boolean;
  hide_local_login: boolean;
}

function fromSettings(s: OidcSettings | undefined): FormState {
  return {
    issuer_url: s?.issuer_url ?? "",
    client_id: s?.client_id ?? "",
    client_secret: "",
    provider_name: s?.provider_name ?? "",
    scopes: s?.scopes ?? "openid email profile",
    enabled: s?.enabled ?? false,
    hide_local_login: s?.hide_local_login ?? false,
  };
}

export function SignInSection() {
  const settings = useOidcSettings();
  const save = useSaveOidcSettings();
  const discovery = useTestOidcDiscovery();
  const toast = useToast();
  const [form, setForm] = useState<FormState>(() => fromSettings(undefined));

  useEffect(() => {
    if (settings.data) setForm(fromSettings(settings.data));
  }, [settings.data]);

  const set = <K extends keyof FormState>(key: K, value: FormState[K]) =>
    setForm((f) => ({ ...f, [key]: value }));

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    const saved = await save.mutateAsync({
      issuer_url: form.issuer_url.trim(),
      client_id: form.client_id.trim(),
      client_secret: form.client_secret || null,
      provider_name: form.provider_name.trim(),
      scopes: form.scopes.trim() || "openid email profile",
      enabled: form.enabled,
      hide_local_login: form.hide_local_login,
    });
    setForm(fromSettings(saved));
    toast.notify("Sign-in settings saved");
  }

  if (settings.isPending) return <Skeleton className="h-48" />;
  if (settings.isError)
    return (
      <ErrorCard
        message="Could not load sign-in settings."
        onRetry={() => void settings.refetch()}
      />
    );
  const canSave = settings.data.encryption_key_configured;
  const needsSecret = !settings.data.has_client_secret;

  return (
    <Panel
      title="Sign-in (OIDC)"
      testId="signin-section"
      aside={
        settings.data.configured
          ? settings.data.enabled
            ? "enabled"
            : "configured, disabled"
          : "not configured"
      }
    >
      <EncryptionKeyNotice configured={canSave} />
      <form
        onSubmit={submit}
        className="mt-3 grid gap-3 sm:grid-cols-2"
        data-testid="oidc-form"
      >
        <Field
          label="Issuer URL"
          hint="e.g. https://id.example.com — discovery is fetched from /.well-known/openid-configuration"
        >
          <input
            className={inputClass}
            type="url"
            value={form.issuer_url}
            onChange={(e) => set("issuer_url", e.target.value)}
            required
          />
        </Field>
        <Field label="Provider name" hint="Shown on the login button">
          <input
            className={inputClass}
            value={form.provider_name}
            onChange={(e) => set("provider_name", e.target.value)}
            required
          />
        </Field>
        <Field label="Client ID">
          <input
            className={inputClass}
            value={form.client_id}
            onChange={(e) => set("client_id", e.target.value)}
            required
            autoComplete="off"
          />
        </Field>
        <Field
          label="Client secret"
          hint={
            needsSecret
              ? "Required for the first configuration."
              : "A secret is stored; leave blank to keep it."
          }
        >
          <input
            className={inputClass}
            type="password"
            value={form.client_secret}
            onChange={(e) => set("client_secret", e.target.value)}
            placeholder={needsSecret ? "" : "unchanged"}
            required={needsSecret}
            autoComplete="new-password"
          />
        </Field>
        <Field label="Scopes">
          <input
            className={inputClass}
            value={form.scopes}
            onChange={(e) => set("scopes", e.target.value)}
          />
        </Field>
        {/* Not a <label>: wrapping the button would rename it to the label text. */}
        <div className="text-sm">
          <span className="mb-1 block text-xs font-medium uppercase tracking-wider text-muted">
            Callback URL
          </span>
          <span className="flex gap-2">
            <code
              className="flex-1 truncate rounded bg-code-bg px-2 py-1.5 font-mono text-xs text-code-text"
              data-testid="oidc-callback-url"
            >
              {settings.data.callback_url}
            </code>
            <CopyButton text={settings.data.callback_url} />
          </span>
          <span className="mt-1 block text-xs text-muted">
            Register this redirect URI with your provider
          </span>
        </div>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={form.enabled}
            onChange={(e) => set("enabled", e.target.checked)}
          />
          Enable OIDC sign-in
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={form.hide_local_login}
            onChange={(e) => set("hide_local_login", e.target.checked)}
          />
          Hide the local login form
        </label>
        {form.enabled && form.hide_local_login && (
          <p
            role="note"
            className="rounded-md border border-warn/50 bg-warn/10 p-2 text-sm sm:col-span-2"
          >
            With local login hidden, only your identity provider can sign users
            in. Set <code>FORCE_LOCAL_LOGIN=true</code> in the environment to
            recover if it fails.
          </p>
        )}
        <div className="flex items-center gap-3 sm:col-span-2">
          <PrimaryButton busy={save.isPending} disabled={!canSave}>
            Save
          </PrimaryButton>
          <SecondaryButton
            disabled={!form.issuer_url || discovery.isPending}
            onClick={() => discovery.mutate(form.issuer_url.trim())}
          >
            {discovery.isPending ? "Testing…" : "Test discovery"}
          </SecondaryButton>
          <InlineError error={save.error} />
        </div>
      </form>
      {discovery.isError && (
        <div className="mt-3">
          <InlineError error={discovery.error} />
        </div>
      )}
      {discovery.isSuccess && (
        <div
          className="mt-3 rounded-md border border-ok/50 bg-ok/5 p-3 text-sm"
          data-testid="discovery-result"
        >
          <p className="mb-1 font-medium">Discovery successful</p>
          <dl className="grid gap-1 font-mono text-xs sm:grid-cols-[auto_1fr]">
            {Object.entries(discovery.data.endpoints).map(([key, value]) => (
              <div key={key} className="contents">
                <dt className="text-muted">{key}</dt>
                <dd className="truncate">{value}</dd>
              </div>
            ))}
          </dl>
        </div>
      )}
    </Panel>
  );
}
