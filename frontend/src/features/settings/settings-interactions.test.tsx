import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { Route, Routes } from "react-router";

import { oidcSettings, webhooks } from "../../test/handlers";
import { renderWithProviders } from "../../test/render";
import { server } from "../../test/setup";
import { SettingsLayout } from "./SettingsLayout";
import { SettingsSectionPage } from "./SettingsSectionPage";

function renderSettings(route: string) {
  return renderWithProviders(
    <Routes>
      <Route path="/app/settings" element={<SettingsLayout />}>
        <Route path=":section" element={<SettingsSectionPage />} />
      </Route>
    </Routes>,
    { route },
  );
}

function failing(method: "get", path: string) {
  server.use(
    http[method](path, () =>
      HttpResponse.json({ message: "boom" }, { status: 500 }),
    ),
  );
}

beforeEach(() => {
  window.__USER__ = { username: "cal", role: "admin" };
});
afterEach(() => {
  delete window.__USER__;
});

describe("API keys interactions (AC-012)", () => {
  it("toggles the all-users view, cancels the form, and dismisses the created key", async () => {
    const seen: string[] = [];
    server.use(
      http.get("/api/v1/api-keys", ({ request }) => {
        seen.push(new URL(request.url).search);
        return HttpResponse.json([]);
      }),
    );
    const user = userEvent.setup();
    renderSettings("/app/settings/api-keys");
    expect(await screen.findByText(/No API keys yet/)).toBeInTheDocument();
    await user.click(screen.getByLabelText("all users"));
    await waitFor(() => expect(seen.some((s) => s.includes("all"))).toBe(true));

    await user.click(screen.getByRole("button", { name: "+ New key" }));
    expect(screen.getByTestId("api-key-form")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(screen.queryByTestId("api-key-form")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "+ New key" }));
    await user.type(screen.getByLabelText("Name"), "k");
    await user.click(screen.getByRole("button", { name: "Create key" }));
    const created = await screen.findByTestId("api-key-created");
    await user.click(within(created).getByRole("button", { name: "Copy" }));
    await user.click(within(created).getByRole("button", { name: "Done" }));
    expect(screen.queryByTestId("api-key-created")).not.toBeInTheDocument();
  });

  it("shows an error card with retry when the list fails", async () => {
    failing("get", "/api/v1/api-keys");
    const user = userEvent.setup();
    renderSettings("/app/settings/api-keys");
    expect(await screen.findByText("Could not load API keys.")).toBeVisible();
    server.resetHandlers();
    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findAllByTestId("api-key-row")).toHaveLength(1);
  });
});

describe("Webhooks interactions (AC-013)", () => {
  it("edits a discord webhook and saves the converted options", async () => {
    let sent: Record<string, unknown> | null = null;
    server.use(
      http.put("/api/v1/webhooks/:id", async ({ request, params }) => {
        sent = (await request.json()) as Record<string, unknown>;
        const hook = webhooks.find((w) => w.id === params.id)!;
        return HttpResponse.json({ ...hook, ...sent });
      }),
    );
    const user = userEvent.setup();
    renderSettings("/app/settings/webhooks");
    const rows = await screen.findAllByTestId("webhook-row");
    await user.click(within(rows[0]).getByRole("button", { name: "Edit" }));
    const form = screen.getByTestId("webhook-form");
    expect(within(form).getByLabelText("Name")).toHaveValue("Discord ops");
    expect(within(form).getByLabelText("Embed colour")).toHaveValue("#ff0045");
    await user.type(within(form).getByLabelText("Bot username"), "!");
    await user.type(
      within(form).getByLabelText("Avatar URL"),
      "https://img.example.com/a.png",
    );
    await user.type(within(form).getByLabelText("Footer"), "via viewer");
    await user.clear(within(form).getByLabelText("Source filters"));
    await user.type(within(form).getByLabelText("Source filters"), "tv");
    await user.click(within(form).getByLabelText("Enabled"));
    await user.click(within(form).getByRole("button", { name: "Save" }));
    await waitFor(() => expect(sent).not.toBeNull());
    expect(sent).toMatchObject({
      enabled: false,
      source_filters: ["tv"],
      options: {
        username: "Rsync Viewer!",
        avatar_url: "https://img.example.com/a.png",
        footer: "via viewer",
      },
    });
    expect(await screen.findByTestId("toast")).toHaveTextContent(
      'Webhook "Discord ops" saved',
    );
    expect(screen.queryByTestId("webhook-form")).not.toBeInTheDocument();
  });

  it("creates a generic webhook with headers, switching type in the form", async () => {
    const user = userEvent.setup();
    renderSettings("/app/settings/webhooks");
    await screen.findAllByTestId("webhook-row");
    await user.click(screen.getByRole("button", { name: "+ Add webhook" }));
    await user.selectOptions(screen.getByLabelText("Webhook type"), "discord");
    expect(screen.getByLabelText("Embed colour")).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText("Webhook type"), "generic");
    await user.type(screen.getByLabelText("Name"), "Hook");
    await user.type(screen.getByLabelText("URL"), "https://example.com/h");
    await user.type(screen.getByLabelText("Headers (JSON object)"), "{{");
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("JSON object");
    await user.clear(screen.getByLabelText("Headers (JSON object)"));
    await user.type(
      screen.getByLabelText("Headers (JSON object)"),
      '{{"X-Token": "t"}',
    );
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(await screen.findByTestId("toast")).toHaveTextContent(
      'Webhook "Hook" created',
    );
    await user.click(screen.getByRole("button", { name: "+ Add webhook" }));
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(screen.queryByTestId("webhook-form")).not.toBeInTheDocument();
  });

  it("deletes a webhook after confirmation and reports test failures", async () => {
    server.use(
      http.post("/api/v1/webhooks/:id/test", () =>
        HttpResponse.json(
          { message: "Delivery failed: connection refused" },
          { status: 502 },
        ),
      ),
    );
    const user = userEvent.setup();
    renderSettings("/app/settings/webhooks");
    const rows = await screen.findAllByTestId("webhook-row");
    await user.click(within(rows[1]).getByRole("button", { name: "Test" }));
    expect(await within(rows[1]).findByRole("alert")).toHaveTextContent(
      "connection refused",
    );
    await user.click(within(rows[1]).getByRole("button", { name: "Delete" }));
    await user.click(within(rows[1]).getByRole("button", { name: "Cancel" }));
    await user.click(within(rows[1]).getByRole("button", { name: "Delete" }));
    await user.click(within(rows[1]).getByRole("button", { name: "Confirm" }));
    await waitFor(() =>
      expect(screen.getAllByTestId("toast").at(-1)).toHaveTextContent(
        'Webhook "Home Assistant" deleted',
      ),
    );
  });

  it("shows an error card when webhooks fail to load", async () => {
    failing("get", "/api/v1/webhooks");
    renderSettings("/app/settings/webhooks");
    expect(await screen.findByText("Could not load webhooks.")).toBeVisible();
  });
});

describe("Email interactions (AC-014)", () => {
  it("sends every field on save and disables the test button until configured", async () => {
    let sent: Record<string, unknown> | null = null;
    server.use(
      http.put("/api/v1/settings/smtp", async ({ request }) => {
        sent = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({ configured: true, ...sent });
      }),
    );
    const user = userEvent.setup();
    renderSettings("/app/settings/email");
    const host = await screen.findByLabelText("Host");
    await user.clear(host);
    await user.type(host, "mail.example.org");
    await user.clear(screen.getByLabelText("Port"));
    await user.type(screen.getByLabelText("Port"), "465");
    await user.clear(screen.getByLabelText("Username"));
    await user.type(screen.getByLabelText("Username"), "bot");
    await user.type(screen.getByLabelText("Password"), "hunter2");
    await user.selectOptions(screen.getByLabelText("Encryption"), "ssl_tls");
    await user.clear(screen.getByLabelText("From address"));
    await user.type(screen.getByLabelText("From address"), "bot@example.org");
    await user.click(screen.getByLabelText("Email sending enabled"));
    await user.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(sent).not.toBeNull());
    expect(sent).toMatchObject({
      host: "mail.example.org",
      port: 465,
      username: "bot",
      password: "hunter2",
      encryption: "ssl_tls",
      from_address: "bot@example.org",
      enabled: false,
    });
    expect(screen.getByLabelText("Password")).toHaveValue("");
    expect(screen.getByRole("button", { name: "Send" })).toBeDisabled();
  });

  it("shows an error card when settings fail to load", async () => {
    failing("get", "/api/v1/settings/smtp");
    renderSettings("/app/settings/email");
    expect(
      await screen.findByText("Could not load email settings."),
    ).toBeVisible();
  });
});

describe("Sign-in interactions (AC-015)", () => {
  it("saves the full form and clears the secret field afterwards", async () => {
    let sent: Record<string, unknown> | null = null;
    server.use(
      http.put("/api/v1/settings/oidc", async ({ request }) => {
        sent = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({
          ...oidcSettings,
          ...sent,
          configured: true,
          has_client_secret: true,
          client_secret: undefined,
        });
      }),
      http.post("/api/v1/settings/oidc/test-discovery", () =>
        HttpResponse.json(
          { message: "Discovery failed: HTTP 404" },
          { status: 400 },
        ),
      ),
    );
    const user = userEvent.setup();
    renderSettings("/app/settings/sign-in");
    await user.type(
      await screen.findByLabelText("Issuer URL"),
      "https://id.example.com",
    );
    await user.type(screen.getByLabelText("Provider name"), "Authentik");
    await user.type(screen.getByLabelText("Client ID"), "rsync");
    await user.type(screen.getByLabelText("Client secret"), "s3cret");
    await user.clear(screen.getByLabelText("Scopes"));
    await user.type(screen.getByLabelText("Scopes"), "openid email");
    await user.click(screen.getByLabelText("Enable OIDC sign-in"));
    await user.click(screen.getByLabelText("Hide the local login form"));
    await user.click(screen.getByRole("button", { name: "Copy" }));
    await user.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(sent).not.toBeNull());
    expect(sent).toEqual({
      issuer_url: "https://id.example.com",
      client_id: "rsync",
      client_secret: "s3cret",
      provider_name: "Authentik",
      scopes: "openid email",
      enabled: true,
      hide_local_login: true,
    });
    expect(await screen.findByTestId("toast")).toHaveTextContent(
      "Sign-in settings saved",
    );
    expect(screen.getByLabelText("Client secret")).toHaveValue("");

    await user.click(screen.getByRole("button", { name: "Test discovery" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("HTTP 404");
  });

  it("shows an error card when settings fail to load", async () => {
    failing("get", "/api/v1/settings/oidc");
    renderSettings("/app/settings/sign-in");
    expect(
      await screen.findByText("Could not load sign-in settings."),
    ).toBeVisible();
  });
});

describe("Monitoring interactions (AC-016)", () => {
  it("toggles the synthetic check off and fills every wizard field", async () => {
    let saved: Record<string, unknown> | null = null;
    let setup: Record<string, unknown> | null = null;
    server.use(
      http.put("/api/v1/settings/synthetic", async ({ request }) => {
        saved = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({
          enabled: false,
          interval_seconds: 300,
          last_status: "unknown",
          last_check_at: null,
          last_error: null,
        });
      }),
      http.post("/api/v1/settings/monitoring-setup", async ({ request }) => {
        setup = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json(
          {
            source_name: "x",
            key_name: "rsync-client-x",
            api_key: "rsv_k",
            snippet: "services: {}",
          },
          { status: 201 },
        );
      }),
    );
    const user = userEvent.setup();
    renderSettings("/app/settings/monitoring");
    const panel = await screen.findByTestId("synthetic-settings");
    expect(panel).toHaveTextContent("every 5 min");
    await user.click(within(panel).getByLabelText("Enabled"));
    await user.click(within(panel).getByRole("button", { name: "Save" }));
    await waitFor(() =>
      expect(saved).toEqual({ enabled: false, interval_seconds: 300 }),
    );
    expect(await screen.findByTestId("synthetic-settings")).toHaveTextContent(
      "disabled",
    );

    await user.type(screen.getByLabelText("Source name"), "x");
    await user.type(screen.getByLabelText("Rsync source"), "u@h:/p");
    await user.clear(screen.getByLabelText("Schedule (cron)"));
    await user.type(screen.getByLabelText("Schedule (cron)"), "0 * * * *");
    await user.clear(screen.getByLabelText("SSH key path on the client host"));
    await user.type(
      screen.getByLabelText("SSH key path on the client host"),
      "/keys/id",
    );
    await user.clear(screen.getByLabelText("Rsync arguments"));
    await user.type(screen.getByLabelText("Rsync arguments"), "-a");
    await user.selectOptions(screen.getByLabelText("Sync mode"), "push");
    await user.click(screen.getByRole("button", { name: "Generate" }));
    await waitFor(() => expect(setup).not.toBeNull());
    expect(setup).toEqual({
      source_name: "x",
      rsync_source: "u@h:/p",
      cron_schedule: "0 * * * *",
      ssh_key_path: "/keys/id",
      rsync_args: "-a",
      sync_mode: "push",
    });
    const result = await screen.findByTestId("wizard-result");
    await user.click(
      within(result).getByRole("button", { name: "Copy snippet" }),
    );
  });

  it("shows an error card when synthetic settings fail to load", async () => {
    failing("get", "/api/v1/settings/synthetic");
    renderSettings("/app/settings/monitoring");
    expect(
      await screen.findByText("Could not load synthetic settings."),
    ).toBeVisible();
  });
});

describe("Users interactions (AC-017)", () => {
  it("resets a password, deletes a user, and shows the empty/error states", async () => {
    const user = userEvent.setup();
    renderSettings("/app/settings/users");
    const rows = await screen.findAllByTestId("user-row");
    await user.click(
      within(rows[1]).getByRole("button", { name: "Reset password" }),
    );
    expect(await screen.findByTestId("toast")).toHaveTextContent(
      "Password reset sent to ops@example.com",
    );
    await user.click(within(rows[1]).getByRole("button", { name: "Delete" }));
    await user.click(
      within(rows[1]).getByRole("button", { name: "Delete user" }),
    );
    await waitFor(() =>
      expect(screen.getAllByTestId("toast").at(-1)).toHaveTextContent(
        "ops deleted",
      ),
    );
  });

  it("shows an error card when users fail to load", async () => {
    failing("get", "/api/v1/users");
    renderSettings("/app/settings/users");
    expect(await screen.findByText("Could not load users.")).toBeVisible();
  });
});
