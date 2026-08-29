import { screen, within } from "@testing-library/react";
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
    ).toHaveAttribute("href", "/settings");
    expect(
      within(menu).getByRole("menuitem", { name: "Log out" }),
    ).toBeInTheDocument();
  });
});
