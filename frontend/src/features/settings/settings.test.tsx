import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { Route, Routes } from "react-router";

import {
  oidcSettings,
  smtpSettings,
  syntheticSettings,
} from "../../test/handlers";
import { renderWithProviders } from "../../test/render";
import { server } from "../../test/setup";
import { SettingsLayout, visibleSections } from "./SettingsLayout";
import { SettingsSectionPage } from "./SettingsSectionPage";
import { toWrite } from "./WebhooksSection";

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

beforeEach(() => {
  window.__USER__ = { username: "cal", role: "admin" };
});
afterEach(() => {
  delete window.__USER__;
});

describe("SettingsLayout (AC-011)", () => {
  it("shows every section to admins and filters by role", () => {
    expect(visibleSections().map((s) => s.slug)).toEqual([
      "api-keys",
      "webhooks",
      "email",
      "sign-in",
      "monitoring",
      "users",
      "changelog",
    ]);
    window.__USER__ = { username: "v", role: "viewer" };
    expect(visibleSections().map((s) => s.slug)).toEqual([
      "api-keys",
      "changelog",
    ]);
    window.__USER__ = { username: "o", role: "operator" };
    expect(visibleSections().map((s) => s.slug)).toEqual([
      "api-keys",
      "webhooks",
      "changelog",
    ]);
  });

  it("blocks direct links to admin sections for non-admins", async () => {
    window.__USER__ = { username: "v", role: "viewer" };
    renderSettings("/app/settings/users");
    expect(await screen.findByTestId("forbidden")).toHaveTextContent("admin");
  });
});

describe("API keys (AC-012)", () => {
  it("creates a key, reveals it once, and revokes", async () => {
    const user = userEvent.setup();
    renderSettings("/app/settings/api-keys");
    expect(await screen.findAllByTestId("api-key-row")).toHaveLength(1);

    await user.click(screen.getByRole("button", { name: "+ New key" }));
    await user.type(screen.getByLabelText("Name"), "nas-key");
    await user.selectOptions(screen.getByLabelText("Role override"), "viewer");
    await user.click(screen.getByRole("button", { name: "Create key" }));

    const created = await screen.findByTestId("api-key-created");
    expect(created).toHaveTextContent("rsv_brandnewkey_0123456789");
    expect(await screen.findByTestId("toast")).toHaveTextContent(
      'Key "nas-key" created',
    );

    const row = screen.getAllByTestId("api-key-row")[0];
    await user.click(within(row).getByRole("button", { name: "Revoke" }));
    await user.click(within(row).getByRole("button", { name: "Confirm" }));
    await waitFor(() =>
      expect(screen.getAllByTestId("toast").at(-1)).toHaveTextContent(
        "revoked",
      ),
    );
  });
});

describe("Webhooks (AC-013)", () => {
  it("validates the form before sending", () => {
    const base = {
      name: "x",
      url: "https://example.com/hook",
      webhook_type: "generic" as const,
      headers: "",
      source_filters: "movies, tv",
      enabled: true,
      discord_color: "#ff0045",
      discord_username: "",
      discord_avatar_url: "",
      discord_footer: "",
    };
    expect(toWrite({ ...base, name: " " }).error).toMatch(/Name/);
    expect(toWrite({ ...base, url: "ftp://x" }).error).toMatch(/URL/);
    expect(toWrite({ ...base, webhook_type: "discord" }).error).toMatch(
      /Discord/,
    );
    expect(toWrite({ ...base, headers: "not json" }).error).toMatch(/JSON/);
    const ok = toWrite({ ...base, headers: '{"Authorization": "Bearer t"}' });
    expect(ok.body).toMatchObject({
      source_filters: ["movies", "tv"],
      headers: { Authorization: "Bearer t" },
      options: null,
    });
    const discord = toWrite({
      ...base,
      webhook_type: "discord",
      url: "https://discord.com/api/webhooks/1/a",
    });
    expect(discord.body?.options).toMatchObject({
      color: 0xff0045,
      username: "Rsync Viewer",
    });
  });

  it("lists webhooks, tests one, and toggles enabled", async () => {
    const user = userEvent.setup();
    renderSettings("/app/settings/webhooks");
    const rows = await screen.findAllByTestId("webhook-row");
    expect(rows).toHaveLength(2);
    expect(rows[1]).toHaveTextContent("3 fails");

    await user.click(within(rows[0]).getByRole("button", { name: "Test" }));
    expect(await within(rows[0]).findByRole("status")).toHaveTextContent(
      "Delivered (HTTP 204)",
    );

    await user.click(within(rows[1]).getByRole("button", { name: "⏻ off" }));
    await waitFor(() =>
      expect(screen.getAllByTestId("toast").at(-1)).toHaveTextContent(
        "enabled",
      ),
    );
  });

  it("shows a server validation error inline on create", async () => {
    server.use(
      http.post("/api/v1/webhooks", () =>
        HttpResponse.json(
          { message: "Request validation failed" },
          { status: 422 },
        ),
      ),
    );
    const user = userEvent.setup();
    renderSettings("/app/settings/webhooks");
    await screen.findAllByTestId("webhook-row");
    await user.click(screen.getByRole("button", { name: "+ Add webhook" }));
    await user.type(screen.getByLabelText("Name"), "hook");
    await user.type(screen.getByLabelText("URL"), "https://example.com/x");
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Request validation failed",
    );
  });
});

describe("Email (AC-014)", () => {
  it("loads settings, keeps the password on save, and sends a test", async () => {
    let sent: Record<string, unknown> | null = null;
    server.use(
      http.put("/api/v1/settings/smtp", async ({ request }) => {
        sent = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({ ...smtpSettings, from_name: "Alerts" });
      }),
    );
    const user = userEvent.setup();
    renderSettings("/app/settings/email");
    const host = await screen.findByLabelText("Host");
    expect(host).toHaveValue("smtp.example.com");
    expect(screen.getByLabelText("Password")).toHaveAttribute(
      "placeholder",
      "unchanged",
    );

    await user.clear(screen.getByLabelText("From name"));
    await user.type(screen.getByLabelText("From name"), "Alerts");
    await user.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(sent).not.toBeNull());
    expect(sent).toMatchObject({
      password: null,
      from_name: "Alerts",
      port: 587,
    });
    expect(await screen.findByTestId("toast")).toHaveTextContent(
      "Email settings saved",
    );

    await user.type(
      screen.getByLabelText("Test email address"),
      "me@example.com",
    );
    await user.click(screen.getByRole("button", { name: "Send" }));
    await waitFor(() =>
      expect(screen.getAllByTestId("toast").at(-1)).toHaveTextContent(
        "Test email sent to me@example.com",
      ),
    );
  });

  it("disables saving without an encryption key", async () => {
    server.use(
      http.get("/api/v1/settings/smtp", () =>
        HttpResponse.json({
          ...smtpSettings,
          encryption_key_configured: false,
        }),
      ),
    );
    renderSettings("/app/settings/email");
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "ENCRYPTION_KEY",
    );
    expect(screen.getByRole("button", { name: "Save" })).toBeDisabled();
  });
});

describe("Sign-in (AC-015)", () => {
  it("requires the secret the first time and shows discovery results", async () => {
    const user = userEvent.setup();
    renderSettings("/app/settings/sign-in");
    const secret = await screen.findByLabelText("Client secret");
    expect(secret).toBeRequired();
    expect(
      screen.getByText("http://localhost/auth/oidc/callback"),
    ).toBeInTheDocument();

    await user.type(
      screen.getByLabelText("Issuer URL"),
      "https://id.example.com",
    );
    await user.click(screen.getByRole("button", { name: "Test discovery" }));
    expect(await screen.findByTestId("discovery-result")).toHaveTextContent(
      "https://id.example.com/jwks",
    );
  });

  it("marks the secret optional once stored and warns about lock-out", async () => {
    server.use(
      http.get("/api/v1/settings/oidc", () =>
        HttpResponse.json({
          ...oidcSettings,
          configured: true,
          has_client_secret: true,
          issuer_url: "https://id",
          client_id: "c",
          provider_name: "P",
          enabled: true,
          hide_local_login: true,
        }),
      ),
    );
    renderSettings("/app/settings/sign-in");
    const secret = await screen.findByLabelText("Client secret");
    expect(secret).not.toBeRequired();
    expect(secret).toHaveAttribute("placeholder", "unchanged");
    expect(screen.getByRole("note")).toHaveTextContent("FORCE_LOCAL_LOGIN");
  });
});

describe("Monitoring (AC-016)", () => {
  it("saves synthetic settings and runs the wizard", async () => {
    let saved: Record<string, unknown> | null = null;
    server.use(
      http.put("/api/v1/settings/synthetic", async ({ request }) => {
        saved = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({ ...syntheticSettings, ...saved });
      }),
    );
    const user = userEvent.setup();
    renderSettings("/app/settings/monitoring");
    const interval = await screen.findByLabelText("Interval (seconds)");
    expect(interval).toHaveValue(300);
    await user.clear(interval);
    await user.type(interval, "45");
    await user.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(saved).not.toBeNull());
    expect(saved).toEqual({ enabled: true, interval_seconds: 45 });
    expect(await screen.findByTestId("toast")).toHaveTextContent(
      "take effect immediately",
    );

    await user.type(screen.getByLabelText("Source name"), "NAS Backup");
    await user.type(screen.getByLabelText("Rsync source"), "bob@nas:/data");
    await user.click(screen.getByRole("button", { name: "Generate" }));
    const result = await screen.findByTestId("wizard-result");
    expect(result).toHaveTextContent("rsync-client-nas-backup");
    expect(result).toHaveTextContent("RSYNC_VIEWER_API_KEY=rsv_newkey123");
  });
});

describe("Users (AC-017)", () => {
  it("changes a role and surfaces the last-admin error inline", async () => {
    server.use(
      http.put("/api/v1/users/:id/role", () =>
        HttpResponse.json(
          { message: "Cannot demote the last admin" },
          { status: 400 },
        ),
      ),
    );
    const user = userEvent.setup();
    renderSettings("/app/settings/users");
    const rows = await screen.findAllByTestId("user-row");
    expect(rows[0]).toHaveTextContent("(you)");
    expect(within(rows[0]).queryByRole("combobox")).not.toBeInTheDocument();
    await user.selectOptions(
      within(rows[1]).getByLabelText("Role for ops"),
      "admin",
    );
    expect(await within(rows[1]).findByRole("alert")).toHaveTextContent(
      "Cannot demote the last admin",
    );
  });

  it("disables a user with a toast", async () => {
    const user = userEvent.setup();
    renderSettings("/app/settings/users");
    const rows = await screen.findAllByTestId("user-row");
    await user.click(within(rows[1]).getByRole("button", { name: "Disable" }));
    expect(await screen.findByTestId("toast")).toHaveTextContent(
      "ops disabled",
    );
  });
});

describe("Changelog (AC-018)", () => {
  it("renders versions with the current badge and expands sections", async () => {
    const user = userEvent.setup();
    renderSettings("/app/settings/changelog");
    const versions = await screen.findAllByTestId("changelog-version");
    expect(versions).toHaveLength(2);
    expect(versions[0]).toHaveTextContent("current");
    await user.click(within(versions[1]).getByRole("button"));
    expect(versions[1]).toHaveTextContent("SPA is the dashboard");
    expect(versions[1]).toHaveTextContent("legacy removed");
    await user.click(
      screen.getByRole("button", { name: "Show older versions" }),
    );
    await waitFor(() =>
      expect(
        screen.queryByRole("button", { name: "Show older versions" }),
      ).not.toBeInTheDocument(),
    );
  });
});
