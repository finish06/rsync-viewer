import { useEffect, useState } from "react";
import { Link } from "react-router";

import {
  useMonitoringSetup,
  useSaveSyntheticSettings,
  useSyntheticSettings,
} from "../../api/hooks";
import type { MonitoringSetupResult } from "../../api/types";
import { ErrorCard, Panel, Skeleton } from "../../components/Panel";
import { useToast } from "../../components/Toast";
import { formatRelative } from "../../lib/format";
import {
  CopyButton,
  Field,
  InlineError,
  inputClass,
  PrimaryButton,
} from "./FormBits";

export function MonitoringSection() {
  return (
    <div className="space-y-4">
      <SyntheticPanel />
      <WizardPanel />
    </div>
  );
}

function SyntheticPanel() {
  const settings = useSyntheticSettings();
  const save = useSaveSyntheticSettings();
  const toast = useToast();
  const [enabled, setEnabled] = useState(false);
  const [interval, setInterval] = useState("300");

  useEffect(() => {
    if (settings.data) {
      setEnabled(settings.data.enabled);
      setInterval(String(settings.data.interval_seconds));
    }
  }, [settings.data]);

  if (settings.isPending) return <Skeleton className="h-24" />;
  if (settings.isError)
    return (
      <ErrorCard
        message="Could not load synthetic settings."
        onRetry={() => void settings.refetch()}
      />
    );
  const s = settings.data;

  return (
    <Panel
      title="Synthetic check"
      testId="synthetic-settings"
      aside={
        <Link to="/app/uptime" className="text-primary hover:underline">
          Uptime page →
        </Link>
      }
    >
      <p
        className="mb-3 text-sm"
        data-status={s.enabled ? s.last_status : "disabled"}
      >
        <span
          className="inline-block h-2.5 w-2.5 rounded-full align-middle"
          style={{ background: "var(--status)" }}
          aria-hidden
        />{" "}
        {s.enabled ? (
          <>
            <b className="uppercase">{s.last_status}</b> · every{" "}
            {Math.round(s.interval_seconds / 60)} min · last{" "}
            {formatRelative(s.last_check_at)}
            {s.last_error && (
              <span className="text-danger"> · {s.last_error}</span>
            )}
          </>
        ) : (
          "disabled"
        )}
      </p>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          save.mutate(
            { enabled, interval_seconds: Number(interval) },
            {
              onSuccess: () =>
                toast.notify(
                  "Synthetic monitoring updated — changes take effect immediately",
                ),
            },
          );
        }}
        className="flex flex-wrap items-end gap-3"
        data-testid="synthetic-form"
      >
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={enabled}
            onChange={(e) => setEnabled(e.target.checked)}
          />
          Enabled
        </label>
        <Field label="Interval (seconds)" hint="minimum 30">
          <input
            className={`${inputClass} w-32`}
            type="number"
            min={30}
            max={86400}
            value={interval}
            onChange={(e) => setInterval(e.target.value)}
          />
        </Field>
        <PrimaryButton busy={save.isPending}>Save</PrimaryButton>
        <InlineError error={save.error} />
      </form>
    </Panel>
  );
}

function WizardPanel() {
  const setup = useMonitoringSetup();
  const toast = useToast();
  const [form, setForm] = useState({
    source_name: "",
    rsync_source: "",
    cron_schedule: "0 */6 * * *",
    ssh_key_path: "~/.ssh/id_rsa",
    rsync_args: "-avz --stats",
    sync_mode: "pull" as "pull" | "push",
  });
  const [result, setResult] = useState<MonitoringSetupResult | null>(null);
  const set = <K extends keyof typeof form>(key: K, value: (typeof form)[K]) =>
    setForm((f) => ({ ...f, [key]: value }));

  return (
    <Panel title="Add an rsync client" testId="monitoring-wizard">
      <p className="mb-3 text-sm text-muted">
        Generates a docker-compose service that runs rsync on a schedule and
        ships its log here, with a dedicated API key.
      </p>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          setup.mutate(form, {
            onSuccess: (r) => {
              setResult(r);
              toast.notify(
                `Client "${r.source_name}" provisioned — key ${r.key_name} created`,
              );
            },
          });
        }}
        className="grid gap-3 sm:grid-cols-2"
        data-testid="wizard-form"
      >
        <Field
          label="Source name"
          hint="Becomes the source shown on the dashboard"
        >
          <input
            className={inputClass}
            value={form.source_name}
            onChange={(e) => set("source_name", e.target.value)}
            required
          />
        </Field>
        <Field label="Rsync source" hint="user@host:/path">
          <input
            className={inputClass}
            value={form.rsync_source}
            onChange={(e) => set("rsync_source", e.target.value)}
            required
            placeholder="backup@nas.local:/data"
          />
        </Field>
        <Field label="Schedule (cron)">
          <input
            className={inputClass}
            value={form.cron_schedule}
            onChange={(e) => set("cron_schedule", e.target.value)}
          />
        </Field>
        <Field label="SSH key path on the client host">
          <input
            className={inputClass}
            value={form.ssh_key_path}
            onChange={(e) => set("ssh_key_path", e.target.value)}
          />
        </Field>
        <Field label="Rsync arguments">
          <input
            className={inputClass}
            value={form.rsync_args}
            onChange={(e) => set("rsync_args", e.target.value)}
          />
        </Field>
        <Field label="Mode">
          <select
            className={inputClass}
            aria-label="Sync mode"
            value={form.sync_mode}
            onChange={(e) =>
              set("sync_mode", e.target.value as "pull" | "push")
            }
          >
            <option value="pull">pull (remote → local)</option>
            <option value="push">push (local → remote)</option>
          </select>
        </Field>
        <div className="flex items-center gap-3 sm:col-span-2">
          <PrimaryButton busy={setup.isPending}>Generate</PrimaryButton>
          <InlineError error={setup.error} />
        </div>
      </form>
      {result && (
        <div className="mt-4 space-y-2" data-testid="wizard-result">
          <p className="text-sm">
            API key <b>{result.key_name}</b> created — it is embedded below and
            will not be shown again.
          </p>
          <div className="relative">
            <pre className="max-h-80 overflow-auto rounded-md bg-code-bg p-3 font-mono text-xs text-code-text">
              {result.snippet}
            </pre>
            <div className="absolute right-2 top-2">
              <CopyButton text={result.snippet} label="Copy snippet" />
            </div>
          </div>
        </div>
      )}
    </Panel>
  );
}
