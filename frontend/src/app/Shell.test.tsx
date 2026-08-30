import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { Route, Routes } from "react-router";

import { renderWithProviders } from "../test/render";
import { NAV, Shell } from "./Shell";

function renderShell(route = "/app") {
  return renderWithProviders(
    <Routes>
      <Route path="/app" element={<Shell />}>
        <Route index element={<p>overview body</p>} />
        <Route path="media" element={<p>media body</p>} />
      </Route>
    </Routes>,
    { route },
  );
}

describe("Shell (AC-001, AC-023)", () => {
  it("renders the five primary destinations in priority order", () => {
    renderShell();
    const nav = screen.getByRole("navigation", { name: "Primary" });
    expect(
      within(nav)
        .getAllByRole("link")
        .map((l) => l.textContent),
    ).toEqual(NAV.map((n) => n.label));
    expect(NAV.map((n) => n.label)).toEqual([
      "Overview",
      "Transfers",
      "Trends",
      "Media",
      "Uptime",
    ]);
  });

  it("marks the active route and renders the outlet", async () => {
    renderShell("/app/media");
    expect(screen.getByText("media body")).toBeInTheDocument();
    const nav = screen.getByRole("navigation", { name: "Primary" });
    expect(within(nav).getByRole("link", { name: "Media" })).toHaveAttribute(
      "aria-current",
      "page",
    );
  });

  it("shows the liveness pill on every page", async () => {
    renderShell("/app/media");
    expect(await screen.findByText("UP")).toBeInTheDocument();
  });

  it("keeps settings behind a secondary menu linking to server-rendered pages", async () => {
    const user = userEvent.setup();
    renderShell();
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Settings menu" }));
    const menu = screen.getByRole("menu");
    expect(
      within(menu).getByRole("menuitem", { name: "Settings" }),
    ).toHaveAttribute("href", "/app/settings");
    expect(
      within(menu).getByRole("menuitem", { name: "Log out" }),
    ).toBeInTheDocument();
  });
  it("applies the stored theme preference on load (AC-023)", async () => {
    document.documentElement.removeAttribute("data-theme");
    renderShell();
    await screen.findByText("UP");
    await waitFor(() =>
      expect(document.documentElement).toHaveAttribute("data-theme", "dark"),
    );
    document.documentElement.removeAttribute("data-theme");
  });
  it("hides operator/admin destinations from viewers and shows the user", async () => {
    const user = userEvent.setup();
    window.__USER__ = { username: "vic", role: "viewer" };
    try {
      renderShell();
      await user.click(screen.getByRole("button", { name: "Settings menu" }));
      const menu = screen.getByRole("menu");
      expect(menu).toHaveTextContent("vic · viewer");
      expect(
        within(menu).getByRole("menuitem", { name: "Settings" }),
      ).toHaveAttribute("href", "/app/settings");
      expect(
        within(menu).queryByRole("menuitem", { name: "Users" }),
      ).not.toBeInTheDocument();
      expect(
        within(menu).getByRole("menuitem", { name: "Notifications" }),
      ).toHaveAttribute("href", "/notifications");
    } finally {
      delete window.__USER__;
    }
  });

  it("shows Users only to admins", async () => {
    const user = userEvent.setup();
    window.__USER__ = { username: "adm", role: "admin" };
    try {
      renderShell();
      await user.click(screen.getByRole("button", { name: "Settings menu" }));
      expect(
        within(screen.getByRole("menu")).getByRole("menuitem", {
          name: "Users",
        }),
      ).toBeInTheDocument();
    } finally {
      delete window.__USER__;
    }
  });
});

describe("footer version (footer-version AC-002)", () => {
  it("shows the version linking to the changelog", async () => {
    window.__APP_VERSION__ = "2.21.0";
    try {
      renderShell();
      const footer = await screen.findByTestId("app-footer");
      expect(footer).toHaveTextContent("Rsync Viewer v2.21.0");
      expect(
        within(footer).getByRole("link", { name: "v2.21.0" }),
      ).toHaveAttribute("href", "/app/settings/changelog");
    } finally {
      delete window.__APP_VERSION__;
    }
  });

  it("degrades to plain text when no version was injected", async () => {
    renderShell();
    const footer = await screen.findByTestId("app-footer");
    expect(footer).toHaveTextContent("Rsync Viewer");
    expect(footer).not.toHaveTextContent("undefined");
    expect(within(footer).queryByRole("link")).not.toBeInTheDocument();
  });
});
